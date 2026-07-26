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
# Two exception CLASSES already separate cleanly and need no help here:
#   * `index_v4.invariants.InvariantViolation` subclasses `AssertionError`, NOT
#     `ValueError` (`invariants.py:67` — "a rejection is a *correct* refusal; a
#     violation is corruption"). `core.py`/`processor.py` now raise it where they
#     used to `assert`, so every corruption signal already propagates through a
#     `except ValueError` and fails the test loudly. Nothing below weakens that.
#   * everything that is not an exception at all.
#
# What does NOT separate structurally is `ValueError` itself: `index_v4` uses it
# both for genuine write-admission refusals (cycle, undeclared wildcard shape,
# bad identifier, removing what is not there) and for internal-contract failures
# that are BUGS (a stale node id, a malformed wildcard encoding, an I5 routing
# breach). There is no `AdmissionRejected(ValueError)` class to key on.
#
# SMALLEST CHANGE THAT WOULD MAKE THIS STRUCTURAL (reported, not taken here —
# this file may not edit `index_v4/`): introduce
# `class AdmissionRejected(ValueError)` in `index_v4` and raise it at the four
# refusal sites (`core._add_edge_locked`'s two cycle raises,
# `core.remove_edge`/`wildcard._remove_tuple_trusted`'s "Non-existent edge",
# `wildcard._resolve`'s undeclared-wildcard-shape raises, plus
# `zanzibar_utils_v1._require`). Every other `ValueError` in the write path is
# then a bug by construction and this allow-list collapses to one `except`.
#
# Until then the classification is an explicit, documented allow-list matched on
# the message, and it FAILS CLOSED: an unrecognized `ValueError` propagates.
# Grounding: instrumented over every corpus x seed of the remove gate on
# 2026-07-26, the ONLY rejections that actually fire are the two cycle families.
# The rest are listed because they are reachable refusals for some corpus shape,
# each with its raise site.
_ADMISSION_REJECTION_MARKERS: tuple[str, ...] = (
    # core.py `_add_edge_locked`: the trivial cycle (subject node IS object node)
    # and the reverse-reachability cycle pre-check. These are the two that fire
    # on the conformance corpora (recombined `_extras` build userset cycles).
    "self-referential edge would create a cycle",
    "adding this edge would create a cycle",
    # wildcard.py `add_tuple`: the same cycle refusal re-raised with wildcard
    # context ("a wildcard tuple whose object participates in the wildcard's own
    # shape forms a cycle and is unsupported by construction").
    "wildcard tuple rejected:",
    # core.remove_edge / wildcard._remove_tuple_trusted: validity parity with the
    # set engine — removing an edge/node that was never there is a refusal.
    "Non-existent edge cannot be removed",
    "Non-existent node cannot be removed",
    # wildcard._resolve: the write names a `*` shape the schema never declared.
    "is not a declared subject-wildcard shape",
    "is not a declared object-wildcard shape",
    # zanzibar_utils_v1.validate_write_identifiers: out-of-charset identifier.
    "must match [",
)


def is_admission_rejection(exc: ValueError) -> bool:
    """True iff `exc` is a GENUINE write-admission refusal (see the block above).

    Deliberately excludes, so they propagate and FAIL the test:
      * `relation ... is a derived (boolean) relation` — the I5 exclusivity
        breach. In this harness every write goes through `RuleSet.apply`, so if
        that fires the DRIVER is wrong, not the tuple.
      * `node id ... no longer exists` — a stale id reaching the row writer.
      * `wildcard must be ''/'any'/'all'`, `name=='*' and a non-empty wildcard
        must go together`, `node-removal shortcut only supports count == -1` —
        internal encoding/contract failures.
      * anything unlisted (fail closed).
    """
    msg = str(exc)
    return any(m in msg for m in _ADMISSION_REJECTION_MARKERS)


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
        False if the op was a GENUINE admission rejection (rolled back).

        ZT-P4-7: this used to absorb every `ValueError`, which made the remove
        gate structurally unable to see an admission regression — a spurious
        raise on a legitimate add dropped the tuple from the driven store AND
        from the oracle built off that store, so both corners agreed and the test
        passed. Now only the classified refusals (`is_admission_rejection`) are
        absorbed; any other `ValueError` is rolled back and then re-raised as an
        `AssertionError` (chained to the original), so it fails the caller
        loudly instead of shrinking the store. `InvariantViolation` is an
        `AssertionError` and never entered this handler in the first place."""
        from index_v4.outbox import outbox_watermark
        try:
            wm = outbox_watermark(self.session, self.store_id)
            self._route(tup, op)
            if self.proc is not None:
                self.proc.run_cascade(wm)               # synchronous v1: same txn
            self.session.commit()
            return True
        except ValueError as e:
            if not is_admission_rejection(e):
                self.session.rollback()
                raise AssertionError(
                    f"GraphDriver.apply: {op} of {tup} raised a ValueError that is "
                    f"NOT a classified write-admission rejection — treating it as "
                    f"'rejected' would silently shrink BOTH the driven store and "
                    f"the oracle built from it (ZT-P4-7). Either index_v4 has a "
                    f"regression, or this is a new legitimate refusal that must be "
                    f"added to `_ADMISSION_REJECTION_MARKERS` deliberately.\n"
                    f"  {type(e).__name__}: {e}") from e
            self.session.rollback()
            return False

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

    "Rejected" means a CLASSIFIED write-admission refusal (`GraphDriver.apply` /
    `is_admission_rejection`, ZT-P4-7). Any other `ValueError` — and every
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
