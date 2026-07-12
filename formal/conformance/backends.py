"""Drive the real Python backends so conformance can compare them against the
Lean models.

SEMANTICS.md §10 / plan C1: the six-way comparison. The set engine is the backend
whose `check` the Lean set-engine MODEL (Phase 3) mirrors, so pinning
`sem` == set-engine here is direct evidence for T1 ahead of the proof.

Phase 6 adds the GRAPH side: `graphindex_answers` drives the real
`index_v4.WildcardIndex` + `DeltaProcessor` through the synchronous write path
(mirroring `tests/test_matrix.py::GraphBackend`), so the harness can diff it
against the Lean operational graph model (`zcli` mode "graph", whose outputs are
covered by `graph_correct` via `graphRun_reached` / `graphRun_check_eq_sem`).
"""

from __future__ import annotations

from types import EllipsisType

from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine


def _fresh_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def setengine_answers(schema_text: str, tuples, queries,
                      object_wildcards=()) -> list[bool]:
    """Build a SetEngine, load the tuples, and answer each query."""
    session = _fresh_session()
    eng = SetEngine(session, "s1", schema_text,
                    object_wildcard_shapes=frozenset(object_wildcards))
    for tup in tuples:
        eng.add_tuple(tup.subject_predicate, tup.subject_type, tup.subject_name,
                      tup.relation, tup.object_type, tup.object_name)
    return [
        bool(eng.check(sp, st, sn, rel, ot, on))
        for (sp, st, sn, rel, ot, on) in queries
    ]


def _norm(pred: str | EllipsisType) -> str:
    return "..." if pred is Ellipsis else pred


def graphindex_drive(schema_text: str, tuples, object_wildcards=()):
    """Build the real graph index and apply each tuple through the synchronous
    v1 write path (rule routing + same-transaction cascade).

    Mirrors `tests/test_matrix.py::GraphBackend` exactly: `RuleSet.apply` fans a
    raw write onto leaf families, `DeltaProcessor.run_cascade(wm)` drains the
    outbox from the pre-write watermark inside the same transaction. Paranoia
    mode stays ON (invariant checker inside every commit). A rejected write
    raises — conformance corpora must be admission-clean, matching the Lean
    driver's add-only accepted-writes-only chain (`graphRun` returns `none`
    there, and the test must treat both the same way).

    Returns `(session, widx, store_id)` so callers can either answer queries
    (`graphindex_answers`) or extract the final SQL state (the state-level
    conformance extractor). The caller owns closing the session.
    """
    from index_v4.outbox import outbox_watermark
    from index_v4.processor import DeltaProcessor
    from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
    from tests.wildcard_helpers import make_wildcard_index

    ruleset = parse_openfga_schema(schema_text,
                                   object_wildcard_shapes=frozenset(object_wildcards))
    session, widx = make_wildcard_index(ruleset.schema_info, store_id="conf")
    proc = None
    if ruleset.compiled is not None and ruleset.compiled.plans:
        proc = DeltaProcessor(widx, ruleset.compiled)

    for tup in tuples:
        sp = Ellipsis if _norm(tup.subject_predicate) == "..." else tup.subject_predicate
        triple = RelationalTriple(Entity(tup.subject_type, tup.subject_name),
                                  tup.relation,
                                  Entity(tup.object_type, tup.object_name), sp)
        wm = outbox_watermark(session, "conf")
        for d in ruleset.apply(triple):
            widx.add_tuple(_norm(d.subject_predicate), d.subject.type,
                           d.subject.name, d.relation, d.object.type,
                           d.object.name)
        if proc is not None:
            proc.run_cascade(wm)                    # synchronous v1: same txn
        session.commit()

    return session, widx, "conf"


def graphindex_answers(schema_text: str, tuples, queries,
                       object_wildcards=()) -> list[bool]:
    """Drive the real graph index (see `graphindex_drive`) and answer each
    query."""
    session, widx, _store_id = graphindex_drive(schema_text, tuples,
                                                object_wildcards)
    answers = [
        bool(widx.check(sp, st, sn, rel, ot, on))
        for (sp, st, sn, rel, ot, on) in queries
    ]
    session.close()
    return answers
