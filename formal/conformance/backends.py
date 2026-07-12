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


class GraphDriver:
    """A remove-capable, poison-safe graph driver: build once, apply ops
    incrementally through the synchronous v1 write path (routing + same-txn
    cascade). Mirrors `tests/test_matrix.py::GraphBackend.apply` exactly:
    `RuleSet.apply` fans a raw write onto its leaf families (so a REMOVE retracts
    the SAME derived leaves the matching ADD materialized — I5 routing symmetry),
    and `DeltaProcessor.run_cascade(wm)` drains the outbox from the pre-write
    watermark inside the same transaction. Paranoia mode stays ON (invariant
    checker inside every commit). `apply` returns True on a committed op and
    False on a `ValueError` (rolled back) — the caller applies the poison
    bookkeeping. Unlike the add-only `graphindex_drive`, this exposes per-op
    driving so callers can inspect state BETWEEN phases (drain / re-add churn).
    """

    def __init__(self, schema_text: str, object_wildcards=()):
        from index_v4.processor import DeltaProcessor
        from zanzibar_utils_v1 import parse_openfga_schema
        from tests.wildcard_helpers import make_wildcard_index

        self.store_id = "conf"
        self.ruleset = parse_openfga_schema(
            schema_text, object_wildcard_shapes=frozenset(object_wildcards))
        self.session, self.widx = make_wildcard_index(
            self.ruleset.schema_info, store_id=self.store_id)
        self.proc = None
        if self.ruleset.compiled is not None and self.ruleset.compiled.plans:
            self.proc = DeltaProcessor(self.widx, self.ruleset.compiled)

    def _route(self, tup, op: str) -> None:
        """Fan `tup` through `RuleSet.apply` onto its leaf families, adding or
        removing each derived leaf edge. Raises the `remove_tuple` propagation
        path's `ValueError` for a non-existent edge."""
        from zanzibar_utils_v1 import Entity, RelationalTriple

        sp = Ellipsis if _norm(tup.subject_predicate) == "..." else tup.subject_predicate
        triple = RelationalTriple(Entity(tup.subject_type, tup.subject_name),
                                  tup.relation,
                                  Entity(tup.object_type, tup.object_name), sp)
        fn = self.widx.add_tuple if op == "add" else self.widx.remove_tuple
        for d in self.ruleset.apply(triple):
            fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
               d.relation, d.object.type, d.object.name)

    def apply(self, tup, op: str) -> bool:
        """One op through the synchronous v1 path. Returns True if committed,
        False if the op was rejected (`ValueError`) and rolled back."""
        from index_v4.outbox import outbox_watermark
        try:
            wm = outbox_watermark(self.session, self.store_id)
            self._route(tup, op)
            if self.proc is not None:
                self.proc.run_cascade(wm)               # synchronous v1: same txn
            self.session.commit()
            return True
        except ValueError:
            self.session.rollback()
            return False

    def close(self) -> None:
        self.session.close()


def graphindex_drive_ops(schema_text: str, ops, object_wildcards=()):
    """Drive the real graph index through an interleaved add/remove op sequence,
    landing on a final graph state, and return the ACCEPTED final tuple set.

    Poison semantics mirror the set-engine `_drive` in
    `test_conformance_remove.py` exactly, so both backends traverse identical
    effective sequences: a rejected add (`ValueError` from graph-parity
    validation / cascade) poisons that tuple — all its later ops are skipped and
    it is excluded from the accepted-final set. Removes are always of present
    (accepted) tuples and must commit.

    `ops` is a list of `(kind, tuple)` with `kind in {'add', 'remove'}`. Returns
    `(session, widx, proc, store_id, accepted_final)`; the caller owns closing
    the session (via `widx.idx.session` or the returned `session`).
    """
    drv = GraphDriver(schema_text, object_wildcards)
    poisoned: set = set()
    present: set = set()
    for kind, tup in ops:
        if tup in poisoned:
            continue
        if kind == "add":
            if drv.apply(tup, "add"):
                present.add(tup)
            else:
                poisoned.add(tup)
        else:
            assert tup in present, f"remove of absent tuple generated: {tup}"
            ok = drv.apply(tup, "remove")
            assert ok, f"remove of a present tuple was rejected: {tup}"
            present.discard(tup)
    return drv.session, drv.widx, drv.proc, drv.store_id, present
