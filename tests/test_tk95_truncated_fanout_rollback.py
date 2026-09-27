"""TK95: a fan-out refused part-way through must leave NO trace, whatever order it ran in.

WHY THIS EXISTS. ``zanzibar_utils_v1.py::RuleSet.apply`` yields a raw tuple's rewrite
fan-out out of a ``set``, so its order moves with ``PYTHONHASHSEED``. Both write paths
consume it inside one transaction, leaf by leaf -- ``tests/parity.py::_GraphSide.apply``
(every differential harness) and ``connectedstore/apply.py::_apply_row`` under
``advance_index`` (production). When a LATER leaf is refused, the leaves before it are
already written, and correctness rests entirely on the caller's rollback undoing exactly
that prefix -- a prefix whose CONTENTS are a hash-seed accident. `TK93` measured it
(`docs/tk93-ensure-raw-seed-dependence-2026-09-21.md` sec 4 and sec 7): every one of the
generator corpus's mid-fan-out aborts lands at position >= 2. A run-wide green cannot tell
a correct rollback from luck, so this module drives ONE refused fan-out in EVERY order and
compares.

THE FIXTURE IS THE CORPUS'S OWN, not an invented one. The 2026-09-27 capture
(`docs/tk95-truncated-fanout-rollback-2026-09-27.md` sec 1) recorded the (schema, store,
tuple) of every abort in ``tests/test_generator_coverage.py``'s two regime sweeps; they
are all a recursive TTU refusing a cycle. The two cases here are its two shapes:

* ``self-loop``  -- ``doc:d1#parent@doc:d1`` into a store holding ``user:u1 r1 doc:d1``.
  The fan-out is three leaves (the stored ``parent`` edge, ``doc:d1#r1 -> doc:d1#r2``,
  ``doc:d1#r2 -> doc:d1#r2``) and the last is a self-referential edge.
* ``two-cycle``  -- ``doc:d1#parent@doc:d2`` when ``doc:d2#parent@doc:d1`` is stored: the
  ``r2 -> r2`` leaf closes a cycle through existing closure rows, so the prefix also
  bumps REFERENCE COUNTS on rows that were there before.

WHAT IS ASSERTED, per case, per permutation of the fan-out (all ``n!`` of them):

1. the write is refused, unanimously (graph, both set engines -- ``genswarm.Diff`` raises
   ``AdmissionDivergence`` otherwise);
2. every table of the graph store, ``sqlite_sequence`` included, is BYTE-IDENTICAL,
   row ids included, to the moment before the write (stronger than
   ``invariants.py::snapshot_rows``, which is id-independent and reads two tables);
3. a follow-up sequence of accepted writes and a removal then lands on a store that is
   byte-identical, ids included, to a CONTROL store that never saw the refused write --
   the only way to see Python-side state (a cache, a buffer) that a DB rollback cannot
   reach;
4. the check grid agrees with the oracle and both set engines after the follow-ups.

ANTI-VACUITY, asserted rather than assumed: the fan-out has >= 2 leaves; across the
permutations the raiser lands at position 1 AND at position ``n`` (the empty prefix and
the whole prefix both occur); and whenever the raiser's position is > 1 the store
MID-TRANSACTION, at the moment the raiser was entered, differed from the pre-write store --
i.e. the prefix really wrote something for the rollback to undo. Without that last clause a
fan-out whose early leaves were no-ops would pass for free.

The production arm (`test_advance_index_batch_rollback_is_order_independent`) puts the
refused row behind a GOOD row in the same batch, so the rollback must also undo a whole
prior row, and runs ``advance_index`` with its per-batch node cache (perf N15) exactly as
production does. Two of its cases are the cycle shapes above as forged, unadmitted log
rows (corruption -- ``_apply_row`` promotes them to ``InvariantViolation``). The third,
``cap-fanout``, is the refusal production can hit on an ADMITTED row: the closure fan-out
cap (``ZT-P1-6a``), which escapes ``_apply_row`` as ``ClosureFanoutExceeded``. It has no
graph-arm twin because the set engine has no cap, so ``Diff`` would call it a divergence.

(!) Sorting the fan-out is the INSTRUMENT here, not a fix: do not sort it in production
(the row's own trap). The deliverable is a pin on outcome-equivalence.

MUTATION SWEEP (2026-09-27, `docs/sabotage-procedure.md` sec "Sweep the TEST MODULE with
mutations"): one mutation at a time, anchor matched exactly once, file bytes restored in a
``finally`` and ``git diff`` empty afterwards; baseline ``5 passed``. G = the graph arm,
P = the production arm; every expected red was written down BEFORE the run::

    M0  CONTROL: pytest.raises(exc) -> pytest.raises(KeyError)      P x3 red        (named)
    M1  parity.py::_GraphSide.apply  rollback() -> commit()         G x2 red
    M2  parity.py::_GraphSide.apply  rollback() -> pass             G x2 red
    M3  core.py::_node_cache_scope   teardown on success only       P x3 red
    M4  core.py::_add_direct_edge_unsafe  outbox-buffer reset gone  INERT, 5 passed
    M5  apply.py::advance_index      session.commit() per row       P x3 red
    M6  apply.py::_apply_row         skip a refused leaf, continue  P[self-loop], P[two-cycle]
    M7  instrument: forced order ignored (natural order yielded)    all 5 red (anti-vacuity)
    M8  instrument: prefix-wrote-something clause -> True           5 passed (expected)
    M9  instrument: that clause reads entered[0] (== before)        all 5 red

M4 is INERT for a reason READ in the source, not a hole in this module: on the add path
every refusal (both cycle checks in ``core.py::_add_edge_locked``, and the cap in
``_add_direct_edge_unsafe_impl``, whose comment says so) raises BEFORE the first
``_emit``, so the buffer that guard clears is always empty when a refusal lands. The guard
protects against a FAULT mid-expansion, which no refusal reaches. M6 leaves ``cap-fanout``
green because the mutant re-raises ``ClosureFanoutExceeded`` exactly as ``_apply_row``
does. M8 staying green says the clause is not needed on THIS fixture; M9 says it can fire.
"""
from __future__ import annotations

import itertools

import pytest
from sqlalchemy import inspect, select, text
from sqlmodel import SQLModel

import zanzibar_utils_v1 as Z
from connectedstore.apply import advance_index, ensure_cursor
from connectedstore.models import TupleLogV1
from index_v4.invariants import InvariantViolation
from tests.genswarm import Diff
from tests.wildcard_helpers import make_wildcard_index

SCHEMA = """
type user
type doc
  relations
    define parent: [doc]
    define r1: [user]
    define r2: r1 from parent or r2 from parent
"""

# (name, stored-before, refused write, follow-ups).  Raw = (sp, s_type, s_name, rel, o_type, o_name).
CASES = [
    ('self-loop',
     [('...', 'user', 'u1', 'r1', 'doc', 'd1')],
     ('...', 'doc', 'd1', 'parent', 'doc', 'd1'),
     [('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd2')),
      ('add', ('...', 'user', 'u2', 'r1', 'doc', 'd1')),
      ('remove', ('...', 'user', 'u1', 'r1', 'doc', 'd1'))]),
    ('two-cycle',
     [('...', 'doc', 'd2', 'parent', 'doc', 'd1'),
      ('...', 'user', 'u1', 'r1', 'doc', 'd2')],
     ('...', 'doc', 'd1', 'parent', 'doc', 'd2'),
     [('add', ('...', 'doc', 'd3', 'parent', 'doc', 'd2')),
      ('add', ('...', 'user', 'u2', 'r1', 'doc', 'd3')),
      ('remove', ('...', 'doc', 'd2', 'parent', 'doc', 'd1'))]),
]
IDS = [c[0] for c in CASES]


def _triple(raw):
    sp = Ellipsis if raw[0] == '...' else raw[0]
    return Z.RelationalTriple(Z.Entity(raw[1], raw[2]), raw[3], Z.Entity(raw[4], raw[5]), sp)


def _dump(session) -> dict:
    """Every row of every table in the store's database, ids included, in a canonical
    order -- plus ``sqlite_sequence`` (the next-id state) when it exists. Flushes first so a
    mid-transaction dump sees the pending writes.

    The one column left out is the wall clock (``created_at``, on ``store_v4`` and the
    tuple/log tables): two stores built a millisecond apart differ there and nowhere else,
    and no row the refused write could add or leave behind is distinguished by it alone."""
    session.flush()
    conn = session.connection()
    present = set(inspect(conn).get_table_names())
    out = {}
    for t in SQLModel.metadata.sorted_tables:
        if t.name in present:
            cols = [c for c in t.columns if c.name != 'created_at']
            out[t.name] = [tuple(r) for r in conn.execute(
                select(*cols).order_by(*t.primary_key.columns or cols)).all()]
    if 'sqlite_sequence' in present:
        out['sqlite_sequence'] = sorted(
            tuple(r) for r in conn.execute(text('SELECT * FROM sqlite_sequence')).all())
    return out


def _natural_fanout(raw) -> list:
    rs = Z.parse_openfga_schema(SCHEMA)
    return list(rs.apply(_triple(raw)))


class _Forced:
    """Force ``ruleset.apply`` to yield ``order`` for the refused triple (and only it),
    and record, per ``add`` call, the store as it stood when that call was entered."""

    def __init__(self, ruleset, widx_owner, add_attr, session, refused, order):
        self.ruleset, self.owner, self.attr = ruleset, widx_owner, add_attr
        self.session, self.refused, self.order = session, _triple(refused), order
        self.entered: list[dict] = []
        self.raised_at: int | None = None

    def __enter__(self):
        real_apply = type(self.ruleset).apply

        def apply(triple, _self=self.ruleset):
            if triple == self.refused:
                natural = list(real_apply(_self, triple))
                assert sorted(map(repr, natural)) == sorted(map(repr, self.order)), \
                    'the forced order is not a permutation of the real fan-out'
                return iter(self.order)
            return real_apply(_self, triple)

        real_add = getattr(self.owner, self.attr)

        def add(*a, **k):
            self.entered.append(_dump(self.session))
            try:
                return real_add(*a, **k)
            except ValueError:
                self.raised_at = len(self.entered)
                raise

        self.ruleset.apply = apply                    # instance attribute shadows the method
        setattr(self.owner, self.attr, add)
        return self

    def __exit__(self, *exc):
        del self.ruleset.apply
        delattr(self.owner, self.attr)
        return False


def _check_nonvacuous(case, fan, runs):
    """``runs`` = [(raised_at, entered_dumps, before_dump)] over every permutation."""
    assert len(fan) >= 2, f'{case}: fan-out has {len(fan)} leaf -- nothing can be truncated'
    positions = [r[0] for r in runs]
    assert None not in positions, f'{case}: some order raised outside the fan-out loop'
    assert min(positions) == 1 and max(positions) == len(fan), (
        f'{case}: raiser positions {sorted(set(positions))} -- the empty prefix and the '
        f'whole prefix must both occur across the permutations')
    for pos, entered, before in runs:
        if pos > 1:
            assert entered[pos - 1] != before, (
                f'{case}: at position {pos} the prefix had written NOTHING -- the rollback '
                f'would have nothing to undo and this case proves nothing')


@pytest.mark.parametrize('case,stored,refused,follow', CASES, ids=IDS)
def test_refused_fanout_leaves_no_trace_in_any_order(case, stored, refused, follow):
    fan = _natural_fanout(refused)

    control = Diff(SCHEMA, paranoia=True)
    try:
        for raw in stored:
            assert control.add(raw), raw
        for op, raw in follow:
            assert getattr(control, op)(raw), (op, raw)
        want = _dump(control.graph.session)
    finally:
        control.close()

    runs = []
    for order in itertools.permutations(fan):
        d = Diff(SCHEMA, paranoia=True)
        try:
            for raw in stored:
                assert d.add(raw), raw
            before = _dump(d.graph.session)
            with _Forced(d.graph.ruleset, d.graph.widx, 'add_tuple', d.graph.session,
                         refused, list(order)) as f:
                assert d.add(refused) is False, f'{case}: accepted in order {order}'
            assert _dump(d.graph.session) == before, (
                f'{case}: the rollback left a trace; order={order}, raised at '
                f'position {f.raised_at}')
            runs.append((f.raised_at, f.entered, before))

            for op, raw in follow:
                assert getattr(d, op)(raw), (case, op, raw, order)
            assert _dump(d.graph.session) == want, (
                f'{case}: after the follow-ups the store differs from one that never saw '
                f'the refused write; order={order}, raised at position {f.raised_at}')
            n, bad = d.sweep()
            assert n > 0, f'{case}: the parity sweep compared nothing'
            assert not bad, f'{case}: order={order}: {bad[:3]}'
        finally:
            d.close()

    _check_nonvacuous(case, fan, runs)


# The production arm's cases: the two cycle shapes above (forged, unadmitted log rows --
# ``_apply_row`` promotes their refusal to ``InvariantViolation``) and the one refusal
# production can genuinely hit mid-fan-out on an ADMITTED row, the closure fan-out cap
# (``ZT-P1-6a``). Admission cannot predict the cap, so ``_apply_row`` lets
# ``ClosureFanoutExceeded`` escape as itself and the cursor stays put -- which makes the
# rollback of a completed prefix a live production path, not a corruption-only one.
# ``cap-fanout``: ``doc:d1#parent@doc:d2`` fans out to three leaves; ``doc:d1#r1 ->
# doc:d2#r2`` has 5 ancestors (u1..u5), over a cap of 3, while ``doc:d1#r2 -> doc:d2#r2``
# has exactly 3 (d0's r1/r2 and u0) and the bare ``parent`` edge 0 -- so exactly one leaf
# is refused, in every order.
PROD_CASES = [(name, stored, refused, InvariantViolation, None)
              for name, stored, refused, _ in CASES] + [
    ('cap-fanout',
     [('...', 'doc', 'd0', 'parent', 'doc', 'd1'),
      ('...', 'user', 'u0', 'r1', 'doc', 'd0')]
     + [('...', 'user', f'u{i}', 'r1', 'doc', 'd1') for i in range(1, 6)]
     + [('...', 'user', 'u9', 'r1', 'doc', 'd7')],
     ('...', 'doc', 'd1', 'parent', 'doc', 'd2'),
     Z.ClosureFanoutExceeded, 3),
]


@pytest.mark.parametrize('case,stored,refused,exc,cap', PROD_CASES,
                         ids=[c[0] for c in PROD_CASES])
def test_advance_index_batch_rollback_is_order_independent(case, stored, refused, exc, cap):
    fan = _natural_fanout(refused)
    runs = []
    for order in itertools.permutations(fan):
        rs = Z.parse_openfga_schema(SCHEMA)
        session, widx = make_wildcard_index(rs.schema_info, store_id='ix', paranoia=True)
        try:
            cursor = ensure_cursor(session, 'ix', 'src')

            def log(raw):
                session.add(TupleLogV1(store_id='src', op='ADD', subject_predicate=raw[0],
                                       subject_type=raw[1], subject_name=raw[2],
                                       relation=raw[3], object_type=raw[4],
                                       object_name=raw[5], created_at=0.0))

            for raw in stored[:-1]:
                log(raw)
            session.flush()
            advance_index(session, cursor, widx, rs, None)
            session.commit()
            # The batch that fails: the LAST stored tuple (good) then the refused row.
            log(stored[-1])
            log(refused)
            session.commit()
            if cap is not None:
                widx.idx.max_closure_fanout = cap
            before = _dump(session)
            with _Forced(rs, widx, '_add_tuple_trusted', session, refused, list(order)) as f:
                with pytest.raises(exc):
                    advance_index(session, cursor, widx, rs, None)
            session.rollback()
            assert widx.idx._node_cache is None, 'the N15 batch cache survived the failure'
            assert _dump(session) == before, (
                f'{case}: the failed batch left a trace; order={order}, raised at '
                f'position {f.raised_at}')
            # entered[0] is the good row's first leaf: re-base the positions on the
            # refused row's own fan-out.
            good = len(_natural_fanout(stored[-1]))
            runs.append((f.raised_at - good, f.entered[good:], f.entered[good]))
        finally:
            session.close()

    _check_nonvacuous(case, fan, runs)
