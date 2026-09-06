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
from zanzibar_utils_v1 import AdmissionRejected


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


def bulk_build_drive(schema_text: str, tuples, object_wildcards=()):
    """Build the real graph index OFFLINE from a tuple snapshot, via
    `connectedstore.build_index(bulk=True)` — the production bootstrap path
    (`index_v4/bulk_build.py`: one in-memory pass, closed-form path counts,
    in-memory boolean backfill, bulk INSERTs) — instead of growing it one logged
    write + cascade at a time as `graphindex_drive` does.

    Board row `P17`: the Lean headline theorems quantify over indexes grown from
    `emptyState` by the `ReachedBy` chain's own constructors (its only base
    constructor is `empty`, `CascadeStrataAssemble.lean`), so a bulk-built index
    is OUTSIDE the proof's scope by construction. This drive is what lets the
    state gate pin it to the model-driven state anyway
    (`test_conformance_bulk_state.py`).

    The snapshot is written through a `TupleSource` (admission-validated, the
    same seam `tests/test_bulk_build.py::_seed_source` uses), then
    `build_index(session, store_id)` — same store id for source and index, the
    production default — materializes the index. Conformance corpora are
    add-only, duplicate-free and admission-clean, so EVERY corpus tuple must
    land as a `TupleV1` row: `TupleSource.add` is idempotent on duplicates and
    absorbs nothing else, so a landed count below `len(tuples)` means the
    snapshot the bulk side saw is SMALLER than the one `graphindex_drive`
    replayed — the two sides would be comparing different stores. That is
    refused here (ZT-P4-7's rule: never silently shrink one side of a
    differential), not tolerated.

    Returns `(session, widx, store_id)` like `graphindex_drive`; the caller owns
    closing the session.
    """
    from sqlmodel import select

    from connectedstore import TupleSource, build_index, save_schema
    from setengine.models import TupleV1

    store_id = "conf"
    session = _fresh_session()
    save_schema(session, store_id, schema_text, frozenset(object_wildcards))
    src = TupleSource(session, store_id)
    for tup in tuples:
        src.add(tup.subject_predicate, tup.subject_type, tup.subject_name,
                tup.relation, tup.object_type, tup.object_name)
    session.commit()

    landed = len(session.exec(
        select(TupleV1).where(TupleV1.store_id == store_id)).all())
    if landed != len(tuples):
        raise AssertionError(
            f"bulk_build_drive: {landed} TupleV1 row(s) landed for a corpus of "
            f"{len(tuples)} tuple(s) — the snapshot build_index will read is not "
            f"the tuple list graphindex_drive replays (a duplicate the source "
            f"deduplicated, or a rejected write). Refusing to compare two "
            f"different stores.")

    _cursor, widx, _ruleset = build_index(session, store_id, bulk=True)
    return session, widx, store_id


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


# --------------------------------------------------------------------------- #
# Admission-rejection classification (ZT-P4-7, 2026-07-26)
# --------------------------------------------------------------------------- #
# `GraphDriver.apply` used to catch BARE `ValueError` and report "rejected".
# `graphindex_drive_ops` then drops a rejected add from `present`, and
# `test_conformance_remove.py` builds the ORACLE from that same graph-derived
# final set. So an `index_v4` bug that spuriously raised `ValueError` on a
# LEGITIMATE add removed the tuple from BOTH sides, both corners agreed on a
# smaller store, and the test stayed green: the gate was structurally incapable
# of detecting an admission regression.
#
# The classification is now STRUCTURAL — three disjoint exception classes, no
# message text anywhere:
#   * `zanzibar_utils_v1.AdmissionRejected` (a `ValueError` subclass) — a
#     CORRECT refusal of an inadmissible write: a cycle, an undeclared wildcard
#     shape, an out-of-charset identifier, a tuple no declared type restriction
#     admits, a remove of what is not there. Absorbed as "rejected" below.
#   * `index_v4.invariants.InvariantViolation` (an `AssertionError` subclass,
#     NOT a `ValueError` — "a rejection is a *correct* refusal; a violation is
#     corruption"). Never enters the handler at all; propagates.
#   * any OTHER `ValueError` — by construction an internal-contract failure and
#     therefore a BUG (a stale node id, a malformed wildcard encoding, an I5
#     routing breach). Rolled back and re-raised as an `AssertionError`.
#
# This replaces the `_ADMISSION_REJECTION_MARKERS` allow-list (message-substring
# matching, recorded at the time as an explicit stopgap): each of its entries is
# now the `AdmissionRejected` type at its raise site, and the excluded internal
# failures are exactly the sites left as plain `ValueError`. The FAIL-CLOSED
# direction is unchanged and is the whole point: an unclassified raise must not
# silently shrink BOTH the driven store and the oracle built from it.


class GraphDriver:
    """A remove-capable, poison-safe graph driver: build once, apply ops
    incrementally through the synchronous v1 write path (routing + same-txn
    cascade). Mirrors `tests/test_matrix.py::GraphBackend.apply` exactly:
    `RuleSet.apply` fans a raw write onto its leaf families (so a REMOVE retracts
    the SAME derived leaves the matching ADD materialized — I5 routing symmetry),
    and `DeltaProcessor.run_cascade(wm)` drains the outbox from the pre-write
    watermark inside the same transaction. Paranoia mode stays ON (invariant
    checker inside every commit). `apply` returns True on a committed op and
    False on an `AdmissionRejected` (rolled back) — the caller applies the poison
    bookkeeping; any OTHER `ValueError` fails loudly (see `apply`). Unlike the add-only `graphindex_drive`, this exposes per-op
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
        path's `AdmissionRejected` for a non-existent edge."""
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
        False if the op was a GENUINE admission rejection (rolled back).

        ZT-P4-7: this used to absorb every `ValueError`, which made the remove
        gate structurally unable to see an admission regression — a spurious
        raise on a legitimate add dropped the tuple from the driven store AND
        from the oracle built off that store, so both corners agreed and the test
        passed. Now only `AdmissionRejected` — the declared refusal type — is
        absorbed; any other `ValueError` is rolled back and then re-raised as an
        `AssertionError` (chained to the original), so it fails the caller
        loudly instead of shrinking the store. `InvariantViolation` is an
        `AssertionError` and never entered this handler in the first place.

        Ordering matters: `AdmissionRejected` subclasses `ValueError`, so its
        `except` clause must come FIRST."""
        from index_v4.outbox import outbox_watermark
        try:
            wm = outbox_watermark(self.session, self.store_id)
            self._route(tup, op)
            if self.proc is not None:
                self.proc.run_cascade(wm)               # synchronous v1: same txn
            self.session.commit()
            return True
        except AdmissionRejected:
            self.session.rollback()
            return False
        except ValueError as e:
            self.session.rollback()
            raise AssertionError(
                f"GraphDriver.apply: {op} of {tup} raised a ValueError that is "
                f"NOT an `AdmissionRejected` write-admission refusal — treating "
                f"it as 'rejected' would silently shrink BOTH the driven store "
                f"and the oracle built from it (ZT-P4-7). Either index_v4 has a "
                f"regression, or this is a new legitimate refusal whose raise "
                f"site must be classified `AdmissionRejected` deliberately.\n"
                f"  {type(e).__name__}: {e}") from e

    def close(self) -> None:
        self.session.close()


def graphindex_drive_ops(schema_text: str, ops, object_wildcards=()):
    """Drive the real graph index through an interleaved add/remove op sequence,
    landing on a final graph state, and return the ACCEPTED final tuple set.

    Poison semantics mirror the set-engine `_drive` in
    `test_conformance_remove.py` exactly, so both backends traverse identical
    effective sequences: a rejected add poisons that tuple — all its later ops
    are skipped and it is excluded from the accepted-final set. Removes are
    always of present (accepted) tuples and must commit.

    "Rejected" means an `AdmissionRejected` write-admission refusal
    (`GraphDriver.apply`, ZT-P4-7). Any other `ValueError` — and every
    `InvariantViolation` — propagates out of here and fails the caller, instead
    of quietly shrinking the accepted set that the test's oracle is built from.

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
