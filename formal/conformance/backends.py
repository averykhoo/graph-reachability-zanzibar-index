"""Drive the real Python set engine so conformance can compare it against `sem`.

SEMANTICS.md §10 / plan C1: the six-way comparison. The set engine is the backend
whose `check` the Lean set-engine MODEL (Phase 3) will mirror, so pinning
`sem` == set-engine here is direct evidence for T1 ahead of the proof.
"""

from __future__ import annotations

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
