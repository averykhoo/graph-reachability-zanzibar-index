"""Round-6 motivating measurements for the WRITE, CASCADE, BULK and SPACE candidates.

Companion to `benchmarks/profile_r6.py` (which covers the two READ paths, `R6-1`…`R6-6`).
Same contract: cProfile plus counters keyed to each candidate's own claim, over the
reviewed `scale_bench` datasets, and **it implements nothing**. The split mirrors the
repo's existing `scale_bench` / `bulk_scale_bench` division rather than growing one file.

  paranoia     R6-7   share of commit time in _check_outbox_sanity, and the GROWTH curve
                      that decides its O(N^2) claim (early-quartile vs late-quartile cost)
               R6-8   share in verify_outbox_deltas; BFS count vs distinct sources
  graph-write  R6-9   node_v4 SELECTs per write (the write-tail re-SELECT)
               R6-16  outbox rows emitted on a schema with NO derived relations, and
                      their share of write statements
  cascade      R6-10  _stored_tupleset_subjects calls + cum time per boolean write
               R6-11  _residue_cache_scope SCOPES ENTERED (cache torn down between
                      reconciles) — cProfile ncalls halved, see _ctxmgr_entries
               R6-12  reconcile_subject calls vs DISTINCT keys — the un-deduped _bumped
  bulk         R6-13  bulk_backfill._instances_of_type calls + cum
               R6-14  stored tupleset/userset re-enumeration in backfill
               R6-15  topo-sort share of bulk build
  space        R6-18  DIRECT A/B on file-backed SQLite: surrogate-PK + unique index vs
                      WITHOUT ROWID composite PK, identical rows, VACUUMed, bytes compared

⚠ Two framing facts that bound several of these BEFORE any number is read:

* **`R6-7` and `R6-8` run only at `PARANOIA_FULL`.** Production defaults to `off` and the
  recommended tier is `residue` (CLAUDE.md), neither of which reaches them; benchmarks
  disable paranoia outright. Their entire ceiling is GATE/TEST wall-clock. That is not
  nothing — the gate is tiled around a 10-min cap — but it is not a production win, and
  the audit's own verifier downgraded both on exactly this ground.
* **In-memory SQLite** understates per-statement cost (no RTT). Statement COUNTS and call
  counts transfer to PostgreSQL; seconds do not.

Run:

    python -m benchmarks.profile_r6_write --target paranoia    --scale 60
    python -m benchmarks.profile_r6_write --target graph-write --scale 150
    python -m benchmarks.profile_r6_write --target cascade     --scale 40
    python -m benchmarks.profile_r6_write --target bulk        --scale 400
    python -m benchmarks.profile_r6_write --target space       --rows 200000
    python -m benchmarks.profile_r6_write --target all

Deterministic: every dataset comes from the `scale_bench` generators, no RNG.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select

from benchmarks import scale_bench as sb
from benchmarks._harness import build_graph
from benchmarks.profile_r6 import (StmtCounter, _banner, _ctxmgr_entries, _find,
                                   _pct, _profile, _rows, _verdict)


# ---------------------------------------------------------------------------
# Target: paranoia  (R6-7, R6-8)
# ---------------------------------------------------------------------------

def target_paranoia(scale, commit_every):
    """The decisive question for R6-7 is not its SHARE but its GROWTH.

    `_check_outbox_sanity` rescans the whole outbox per commit and the outbox is
    append-only, so the claim is that per-commit cost rises with total historical
    writes -- O(N^2) over a run. A share alone cannot distinguish that from a large
    constant; comparing the first quartile of commits against the last can.
    """
    _banner(f'paranoia — gdrive/graph scale={scale}, commit_every={commit_every}, '
            f'PARANOIA_FULL   [R6-7, R6-8]')
    spec = sb.WORKLOADS['gdrive']
    tuples = list(spec['gen'](scale))
    print(f'  dataset: {len(tuples):,} raw tuples  (paranoia=True — the tests/ default)')

    def work():
        return build_graph(spec['schema'], spec['shapes'], tuples,
                           paranoia=True, commit_every=commit_every)

    (widx, ntup), stats, table = _profile(work)
    rows = _rows(stats)
    wall = max(ct for (_n, _t, ct) in rows.values()) if rows else 0.0

    ob_n, ob_t, ob_c = _find(rows, func='_check_outbox_sanity', file_frag='index_v4/invariants.py')
    vf_n, vf_t, vf_c = _find(rows, func='verify_outbox_deltas', file_frag='index_v4/invariants.py')
    ci_n, ci_t, ci_c = _find(rows, func='check_invariants', file_frag='index_v4/invariants.py')

    from index_v4.models import DeltaOutboxV1
    nob = len(widx.idx.session.exec(select(DeltaOutboxV1).where(
        DeltaOutboxV1.store_id == widx.idx.store_id)).all())

    print(f'\n  wall (profiled)       : {wall:.2f} s')
    print(f'  outbox rows at end    : {nob:,}')
    print(f'  check_invariants      : {ci_n:,} calls, {ci_c:.2f} s cum  ({_pct(ci_c, wall)})')
    print(f'  _check_outbox_sanity  : {ob_n:,} calls, {ob_c:.2f} s cum  ({_pct(ob_c, wall)})  <- R6-7')
    print(f'  verify_outbox_deltas  : {vf_n:,} calls, {vf_c:.2f} s cum  ({_pct(vf_c, wall)})  <- R6-8')
    print('\n' + table)

    # --- the growth curve (unprofiled: cProfile's overhead is per-call, and we are
    # comparing early calls against late ones, so it must not be in the measurement)
    print('  GROWTH — per-commit wall time as the outbox accumulates')
    session2, widx2 = _fresh_paranoid_graph(spec)
    from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
    ruleset = parse_openfga_schema(spec['schema'], object_wildcard_shapes=spec['shapes'])
    per = []
    n = 0
    for raw in tuples:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in ruleset.apply(tr):
            widx2.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                            d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        n += 1
        if n % commit_every == 0:
            t0 = time.perf_counter()
            widx2.idx.session.commit()
            per.append(time.perf_counter() - t0)
    if len(per) >= 8:
        q = len(per) // 4
        first, last = sum(per[:q]) / q, sum(per[-q:]) / q
        ratio = last / first if first else float('inf')
        print(f'    commits           : {len(per):,}')
        print(f'    first quartile    : {first * 1000:.2f} ms/commit')
        print(f'    last  quartile    : {last * 1000:.2f} ms/commit')
        print(f'    growth ratio      : {ratio:.2f}x  (1.0 = flat; >1 = cost rises with history)')
    else:
        first = last = ratio = None
        print('    (too few commits to quartile — raise --scale)')

    _verdict('R6-7',
             'I10 outbox sanity rescans the ENTIRE outbox per commit; cost grows with '
             'total historical writes (PARANOIA_FULL only — never production)',
             f'{_pct(ob_c, wall)} of a paranoid build over {nob:,} outbox rows; '
             + (f'per-commit cost {ratio:.2f}x from first to last quartile' if ratio else 'growth not sampled'),
             None if ratio is None else (ratio > 1.5 or ob_c / wall > 0.10))
    _verdict('R6-8',
             'delta verifier runs one BFS per flipped PAIR instead of per distinct source '
             '(PARANOIA_FULL only — gate wall-clock, not production)',
             f'{_pct(vf_c, wall)} of a paranoid build ({vf_n:,} calls)',
             vf_c / wall > 0.10 if wall else None)
    return {'wall': wall, 'outbox_rows': nob, 'growth': ratio}


def _fresh_paranoid_graph(spec):
    from tests.wildcard_helpers import make_wildcard_index
    from zanzibar_utils_v1 import parse_openfga_schema
    ruleset = parse_openfga_schema(spec['schema'], object_wildcard_shapes=spec['shapes'])
    return make_wildcard_index(ruleset.schema_info, store_id='par', paranoia=True)


# ---------------------------------------------------------------------------
# Target: graph-write  (R6-9, R6-16)
# ---------------------------------------------------------------------------

def target_graph_write(scale):
    _banner(f'graph-write — gdrive/graph scale={scale} (NO derived relations)   [R6-9, R6-16]')
    spec = sb.WORKLOADS['gdrive']
    tuples = list(spec['gen'](scale))

    from tests.wildcard_helpers import make_wildcard_index
    from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
    ruleset = parse_openfga_schema(spec['schema'], object_wildcard_shapes=spec['shapes'])
    session, widx = make_wildcard_index(ruleset.schema_info, store_id='gw', paranoia=False)
    print(f'  dataset: {len(tuples):,} raw tuples;  compiled boolean plans: '
          f'{bool(ruleset.compiled and ruleset.compiled.plans)}')

    ctr = StmtCounter(session)
    ctr.start()

    def work():
        n = 0
        for raw in tuples:
            sp = Ellipsis if raw[0] == '...' else raw[0]
            tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
            for d in ruleset.apply(tr):
                widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
            n += 1
        widx.idx.session.commit()
        return n
    nwrites, stats, table = _profile(work)
    ctr.stop()
    rows = _rows(stats)
    wall = max(ct for (_n, _t, ct) in rows.values()) if rows else 0.0

    from index_v4.models import DeltaOutboxV1, EdgeV4
    nob = len(session.exec(select(DeltaOutboxV1).where(DeltaOutboxV1.store_id == 'gw')).all())
    nedge = len(session.exec(select(EdgeV4).where(EdgeV4.store_id == 'gw')).all())

    db_n, db_t, db_c = _find(rows, func='_db_node', file_frag='index_v4/core.py')
    ln_n, ln_t, ln_c = _find(rows, func='_load_nodes', file_frag='index_v4/core.py')

    print(f'\n  raw writes            : {nwrites:,}  in {wall:.2f} s profiled')
    print(f'  SQL statements        : {ctr.total:,}  ({ctr.total / nwrites:,.2f} per raw write)')
    for k, v in sorted(ctr.counts.items(), key=lambda kv: -kv[1]):
        print(f'      {k:<12} {v:>9,}  ({v / nwrites:,.2f} per write)')
    print(f'  _db_node point SELECTs: {db_n:,}  ({db_n / nwrites:,.2f} per write, '
          f'{_pct(db_c, wall)})   <- R6-9')
    print(f'  _load_nodes batches   : {ln_n:,}  ({_pct(ln_c, wall)})')
    print(f'  edge_v4 rows          : {nedge:,}')
    print(f'  OUTBOX rows emitted   : {nob:,}  on a schema with NO derived relations  <- R6-16')
    print(f'      -> outbox rows per closure edge: {nob / max(nedge, 1):,.2f}')
    print('\n' + table)

    _verdict('R6-9',
             'write tail re-SELECTs the two nodes it just batch-loaded',
             f'{db_n / nwrites:,.2f} _db_node point SELECTs per raw write, {_pct(db_c, wall)} of build',
             db_c / wall > 0.10 if wall else None)
    _verdict('R6-16',
             'every closure flip writes a denormalized outbox row even on schemas with '
             'no derived relations (nothing consumes them)',
             f'{nob:,} outbox rows for {nedge:,} closure edges on a schema whose compiled '
             f'plans are empty',
             nob > 0)
    return {'stmts_per_write': ctr.total / nwrites, 'outbox_rows': nob, 'edges': nedge}


# ---------------------------------------------------------------------------
# Target: cascade  (R6-10, R6-11, R6-12)
# ---------------------------------------------------------------------------

def _cascade_fixture(spec, scale, incr):
    """Bootstrap a demorgans graph and return everything an incremental cycle needs.

    Split out so the PROFILED pass and the UNPROFILED wall-clock pass measure the
    same workload on independent stores (a second pass over the first pass's store
    would be measuring a different, larger graph).
    """
    from index_v4.processor import DeltaProcessor
    from zanzibar_utils_v1 import parse_openfga_schema
    tuples = list(spec['gen'](scale))
    widx, _ntup = build_graph(spec['schema'], spec['shapes'], tuples)
    ruleset = parse_openfga_schema(spec['schema'], object_wildcard_shapes=spec['shapes'])
    proc = DeltaProcessor(widx, ruleset.compiled)
    extra = [t for t in spec['gen'](scale + incr) if t not in set(tuples)][:incr]
    return tuples, widx, ruleset, proc, extra


def _cascade_cycles(widx, ruleset, proc, extra, on_cascade=None):
    """`incr` write + run_cascade + commit cycles — the path
    `tests/test_matrix.py::GraphBackend.apply` uses (synchronous v1)."""
    from index_v4.outbox import outbox_watermark
    from zanzibar_utils_v1 import Entity, RelationalTriple
    session = widx.idx.session
    n = 0
    for raw in extra:
        wm = outbox_watermark(session, widx.idx.store_id)
        sp = Ellipsis if raw[0] == '...' else raw[0]
        tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in ruleset.apply(tr):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation,
                           d.object.type, d.object.name)
        if on_cascade is not None:
            on_cascade()
        proc.run_cascade(wm)
        if on_cascade is not None:
            on_cascade()
        session.commit()
        n += 1
    return n


def _memo_stats(proc):
    """The memo's own non-vacuity counters, or None when no memo is installed.

    Instrument correction (ii) from `benchmarks/results/R6_PROFILE_2026-08-17.md`:
    a post-fix "0 calls" could mean the memo worked OR that the probe stopped
    reaching the code, and the two print identically. Hits/misses/distinct-keys
    distinguish them — a working memo shows HITS>0 with misses ≈ distinct keys;
    a probe that lost its workload shows hits=0 AND misses=0.
    """
    return getattr(proc, '_stored_cache_stats', None)


def target_cascade(scale, incr):
    """R6-10/11/12 live on the INCREMENTAL cascade, not on the bootstrap.

    ⚠ The first version of this probe profiled `build_graph`, which bootstraps derived
    state with `DeltaProcessor.backfill()` — the OFFLINE path. `reconcile_subject` was
    called **0 times**, so R6-11 and R6-12 came back INCONCLUSIVE against a run that
    never executed the code they describe. The measured path has to be the one
    `tests/test_matrix.py::GraphBackend.apply` uses: write, then `run_cascade(wm)` in
    the same transaction (synchronous v1). So: bootstrap first (unprofiled), then
    profile `incr` incremental write+cascade cycles.

    FIVE instrument properties this target now ASSERTS rather than merely prints
    (`docs/sabotage-procedure.md` §"A MEASUREMENT is an assurance step too"):

    1. **Non-vacuity.** `_stored_tupleset_subjects` calls > 0 and cascade reconciles
       > 0. `_find` returns 0 for a function it cannot locate BY NAME, so an inlined,
       renamed or wrapped-away function would otherwise print a beautiful `0.0%` win
       that is pure artifact. A zero is now a hard failure of the probe.
    1b. **Non-vacuity and PLACEMENT of the memo** — `_stored_cache_scope` entries > 0,
       memo HITS > 0, and `scopes == nwrites`, whenever the tree carries R6-10 at all.
       Added 2026-08-20 after adversarial review: the first two were printed with a
       comment naming HITS>0 as the disambiguator, and then never checked. Sabotage
       (`docs/sabotage-procedure.md`), `--bool-scale 12 --incr 8`, applied by
       monkeypatch:

         B. `_stored_cache_scope` made a no-op everywhere ->
            `AssertionError: INSTRUMENT BROKEN: _stored_cache_stats exists but
            _stored_cache_scope was entered 0 times`.  RED.
         A. the scope dropped from `run_cascade` ONLY (kept in `reconcile` /
            `reconcile_subject`) -> **the `hits > 0` check does NOT fire**: the nested
            scopes still serve `1,152 hits / 30 misses`. That is why `scopes ==
            nwrites` was added; it fires with
            `AssertionError: INSTRUMENT BROKEN: 38 outermost stored-cache scopes for
            8 cascades`.  RED.

       `scopes == nwrites` is DERIVED, not tuned: `_cascade_cycles` runs exactly one
       `run_cascade` per write and `scopes` counts outermost installs only. Baseline
       for both: `8 scopes, largest 4 distinct keys`, rc=0.
    2. **SQL statements, not seconds.** In-memory SQLite makes a round trip
       microseconds, so seconds UNDERSTATE the win; the transferable metric is the
       eliminated statement count (one PostgreSQL RTT each). `target_graph_write`
       already counted them; this target did not.
    3. **An unprofiled wall-clock pass**, on its own fresh store: under cProfile
       absolute throughput is depressed several-fold, so the profiled seconds are
       ratios-only.
    4. **The instrument restores its own subject.** This target monkeypatches
       `DeltaProcessor.reconcile_subject`; the restore is asserted, not assumed
       (`GS-2`'s class of failure — an instrument that mutates what it measures).

    ⚠ Scope note, so the number is not over-read: demorgans_law_2 stores NO `T:*`
    tupleset parent, so the RC2 star arm (`_instances_of_type`) is not exercised at
    all here — its call count is printed as evidence rather than assumed. For the same
    reason `DeltaProcessor.stored_userset_subjects` — the memo's OTHER guarded reader —
    is called **0 times** on this workload, so HALF the R6-10 change is invisible to
    every number below. Its pin is `tests/test_stored_cache_scope.py`, not a profile.
    """
    _banner(f'cascade — demorgans_law_2/graph scale={scale}, {incr} incremental '
            f'write+cascade cycles (boolean)   [R6-10, R6-11, R6-12]')
    spec = sb.WORKLOADS['demorgans']

    from index_v4.processor import DeltaProcessor
    tuples, widx, ruleset, proc, extra = _cascade_fixture(spec, scale, incr)
    session = widx.idx.session
    print(f'  dataset: {len(tuples):,} raw tuples (bootstrap, unprofiled)')
    print(f'  incremental writes    : {len(extra):,} fresh tuples through run_cascade')

    # Count reconcile_subject calls and their DISTINCT keys — R6-12's measurable
    # consequence (an un-deduped _bumped re-reconciles the same key).
    calls = []
    per_cycle = []
    orig = DeltaProcessor.reconcile_subject

    def counting(self, object_type, rel, obj_name, *a, **k):
        calls.append((object_type, rel, obj_name))
        return orig(self, object_type, rel, obj_name, *a, **k)

    ctr = StmtCounter(session)
    stage = {'i': 0}

    def on_cascade():
        # called twice per cycle: before run_cascade (clear) and after (sample)
        if stage['i'] % 2 == 0:
            del calls[:]                      # R6-12 is INTRA-cascade duplication
        else:
            per_cycle.append((len(calls), len(set(calls))))
        stage['i'] += 1

    DeltaProcessor.reconcile_subject = counting
    ctr.start()
    try:
        nwrites, stats, table = _profile(
            lambda: _cascade_cycles(widx, ruleset, proc, extra, on_cascade))
    finally:
        ctr.stop()
        DeltaProcessor.reconcile_subject = orig
    # (4) the instrument must have put its subject back
    assert DeltaProcessor.reconcile_subject is orig, \
        'INSTRUMENT BROKEN: reconcile_subject was not restored'

    rows = _rows(stats)
    wall = max(ct for (_n, _t, ct) in rows.values()) if rows else 0.0

    sts_n, sts_t, sts_c = _find(rows, func='_stored_tupleset_subjects', file_frag='index_v4/processor.py')
    rcs_raw, rcs_t, rcs_c = _find(rows, func='_residue_cache_scope', file_frag='index_v4/processor.py')
    scs_raw, scs_t, scs_c = _find(rows, func='_stored_cache_scope', file_frag='index_v4/processor.py')
    # ⚠ cProfile counts a @contextmanager TWICE per `with` (once entering, once
    # resuming the generator to exhaustion on exit), so its ncalls is 2x the number
    # of scopes actually entered. Reporting it raw is how `R6-11` acquired a "torn
    # down 8x per reconcile" figure that was really 4x, and it propagated to four
    # documents before anyone divided (found 2026-08-20b, corrected 2026-08-21).
    # Halve HERE, in the instrument, so the number cannot be re-derived wrong.
    rcs_n = _ctxmgr_entries(rcs_raw, '_residue_cache_scope')
    scs_n = _ctxmgr_entries(scs_raw, '_stored_cache_scope')
    di_n, di_t, di_c = _find(rows, func='_direct_incoming', file_frag='index_v4/processor.py')
    nb_n, nb_t, nb_c = _find(rows, func='_nodes_by_ids', file_frag='index_v4/processor.py')
    ins_n, ins_t, ins_c = _find(rows, func='_instances_of_type', file_frag='index_v4/processor.py')
    tp_n, _tp_t, _tp_c = _find(rows, func='tupleset_parents', file_frag='index_v4/processor.py')
    # R6-12 is about ONE cascade re-reconciling ONE key several times. Aggregating
    # across cycles would report the same key touched by successive WRITES as
    # duplication, which it is not -- so sum the per-cycle figures instead.
    rec_n = sum(c for c, _d in per_cycle)
    rec_d = sum(d for _c, d in per_cycle)
    worst = max((c for c, _d in per_cycle), default=0)

    # (1) NON-VACUITY, asserted. A probe that ran on nothing reports a clean 0.0%.
    assert nwrites == len(extra) and nwrites > 0, f'INSTRUMENT BROKEN: {nwrites} cycles ran'
    assert sts_n > 0, ('INSTRUMENT BROKEN: 0 _stored_tupleset_subjects calls — the '
                       'probe locates rows by FUNCTION NAME, so this means the workload '
                       'stopped reaching the code, not that the code got free')
    assert rec_n > 0, 'INSTRUMENT BROKEN: 0 cascade reconciles (bootstrap path profiled?)'

    # (1b) NON-VACUITY OF THE MEMO ITSELF -- asserted, not merely printed.
    # This was the hole: `hits`/`scs_n` were printed with a docstring explaining that
    # HITS>0 is the disambiguator, and then nothing checked it. Delete
    # `self._stored_cache_scope()` from `DeltaProcessor.run_cascade` and every other
    # assertion here still passed while the probe printed `hits 0 / misses 8,480` and
    # reported the item NOT MOTIVATED -- a silently-dropped scope read as a real
    # negative result. `ms is None` means a genuine BASELINE tree (no R6-10 at all),
    # which is a legitimate run; `ms` present with zero hits is a broken probe.
    ms = _memo_stats(proc)
    if ms is not None:
        assert scs_n > 0, ('INSTRUMENT BROKEN: _stored_cache_stats exists but '
                           '_stored_cache_scope was entered 0 times — the scope is not '
                           'installed on the profiled path')
        # Control on the halving itself (see _ctxmgr_entries): the processor keeps a
        # TRUE counter, but it increments only on the OUTER scope, so the relation is
        # `entries >= outer scopes`, never equality -- the reentrant inner `with`es are
        # real entries that bump no counter. If the halving were wrong in the other
        # direction (reporting raw ncalls), this would still hold, so it is a bound and
        # not a proof; what it does catch is a halved figure that has fallen BELOW the
        # independently-counted outer scopes, which is impossible.
        assert scs_n >= ms['scopes'], (
            f"INSTRUMENT BROKEN: {scs_n:,} _stored_cache_scope entries (cProfile, "
            f"halved) is FEWER than the {ms['scopes']:,} outer scopes the processor "
            f"counted itself — the @contextmanager halving is wrong for this run.")
        assert ms['hits'] > 0, (
            f"INSTRUMENT BROKEN: the memo served 0 hits ({ms['misses']:,} misses, "
            f"{ms['scopes']:,} scopes). The memo exists but was never consulted, so "
            f"the R6-10 numbers below are meaningless. A no-hits run must NOT be "
            f"reported as 'not motivated'.")
        # ...and the memo must be installed at the CASCADE level, which is a DERIVED
        # expectation, not a tuned constant: `_cascade_cycles` runs exactly one
        # `run_cascade` per write, and `scopes` counts OUTERMOST installs only (the
        # nested reconcile scopes no-op under it). So `scopes == nwrites`, exactly.
        #
        # This is the assertion that catches a scope silently demoted to the
        # `reconcile`/`reconcile_subject` level: `hits` stays high there (measured
        # below), so `hits > 0` alone does NOT catch it.
        assert ms['scopes'] == nwrites, (
            f"INSTRUMENT BROKEN: {ms['scopes']:,} outermost stored-cache scopes for "
            f"{nwrites:,} cascades. The memo is not scoped to the cascade — it was "
            f"demoted to per-reconcile (more scopes) or hoisted above the write loop "
            f"(fewer, which is also a CORRECTNESS bug: see "
            f"DeltaProcessor._stored_cache_scope's placement rule).")

    print(f'\n  wall (profiled)       : {wall:.2f} s')
    print(f'  SQL statements        : {ctr.total:,}  ({ctr.total / nwrites:,.1f} per '
          f'write+cascade cycle)   <- the metric that transfers to PostgreSQL')
    for k, v in sorted(ctr.counts.items(), key=lambda kv: -kv[1]):
        print(f'      {k:<12} {v:>9,}  ({v / nwrites:,.1f} per cycle)')
    print(f'  _stored_tupleset_subj : {sts_n:,} calls, {sts_c:.2f} s cum  ({_pct(sts_c, wall)})  <- R6-10')
    print(f'      _direct_incoming  : {di_n:,} calls, {di_c:.2f} s cum  ({_pct(di_c, wall)})   (the EdgeV4 SELECT)')
    print(f'      _nodes_by_ids     : {nb_n:,} calls, {nb_c:.2f} s cum  ({_pct(nb_c, wall)})   (the NodeV4 IN SELECT)')
    print(f'      tupleset_parents  : {tp_n:,} calls')
    print(f'      _instances_of_type: {ins_n:,} calls   (RC2 star arm — demorgans stores no `T:*` '
          f'tupleset parent, so 0 is EXPECTED and means this arm is unmeasured here)')
    if ms is None:
        print('  memo                  : NOT INSTALLED (baseline run)')
    else:
        tot = ms['hits'] + ms['misses']
        print(f"  memo                  : {ms['hits']:,} hits / {ms['misses']:,} misses "
              f"over {tot:,} guarded calls "
              f"({100.0 * ms['hits'] / tot if tot else 0.0:.1f}% hit rate); "
              f"{ms['scopes']:,} scopes, largest {ms['keys_max']:,} distinct keys "
              f"(ASSERTED nonzero above)")
        # ⚠ Read `hits` here, not `misses`. "misses == distinct keys summed over
        # scopes" is a TAUTOLOGY -- every miss inserts exactly one key and nothing
        # evicts -- so it cannot tell a working memo from a dropped scope. `hits` is
        # the only load-bearing counter, and `keys_max` vs `misses / scopes` is what
        # confirms the predicted O(subjects x leaves) -> O(leaves) shape.
        print(f"      shape check: keys_max {ms['keys_max']:,} vs mean keys/scope "
              f"{ms['misses'] / max(ms['scopes'], 1):,.1f} -- equal means every scope "
              f"reached the same key set (the predicted O(leaves)); "
              f"scopes == cycles ({nwrites:,}) ASSERTED above")
    print(f'  _residue_cache_scope  : {rcs_n:,} scopes entered  <- R6-11 '
          f'(cProfile ncalls {rcs_raw:,}, halved -- @contextmanager, see _ctxmgr_entries)')
    print(f'  _stored_cache_scope   : {scs_n:,} scopes entered '
          f'(cProfile ncalls {scs_raw:,}, halved)')
    print(f'  reconcile_subject     : {rec_n:,} calls over {rec_d:,} distinct keys '
          f'SUMMED PER CASCADE ({rec_n / max(rec_d, 1):,.2f}x intra-run re-reconcile; '
          f'worst single cascade {worst:,} calls)  <- R6-12')
    print('\n' + table)

    # (3) unprofiled wall clock, fresh store — cProfile depresses throughput
    # several-fold, so the profiled seconds above are ratios-only.
    _t, widx2, ruleset2, proc2, extra2 = _cascade_fixture(spec, scale, incr)
    t0 = time.perf_counter()
    _cascade_cycles(widx2, ruleset2, proc2, extra2)
    unprof = time.perf_counter() - t0
    print(f'  UNPROFILED wall       : {unprof:.3f} s for {len(extra2)} cycles '
          f'({unprof / max(len(extra2), 1) * 1000:.1f} ms/cycle)')

    _verdict('R6-10',
             'cascade check_fn re-enumerates stored tupleset/userset tuples via SQL '
             'once per candidate',
             f'{sts_n:,} calls, {_pct(sts_c, wall)} of the boolean build',
             sts_c / wall > 0.10 if wall else None)
    _verdict('R6-11',
             'residue cache is torn down between every reconcile_subject call',
             f'{rcs_n:,} cache scopes for {rec_n:,} reconciles',
             rcs_n >= rec_n * 0.9 if rec_n else None)
    _verdict('R6-12',
             '_bumped is un-deduplicated, so one reconcile can re-trigger the same key',
             f'{rec_n:,} calls over {rec_d:,} distinct keys summed PER CASCADE '
             f'= {rec_n / max(rec_d, 1):,.2f}x intra-run (worst cascade: {worst:,} calls)',
             rec_n > rec_d * 1.2 if rec_d else None)
    return {'reconciles': rec_n, 'distinct': rec_d, 'sts_share': sts_c / wall if wall else None,
            'sts_calls': sts_n, 'stmts': ctr.total, 'stmts_by_table': dict(ctr.counts),
            'unprofiled_wall': unprof, 'memo': ms}


# ---------------------------------------------------------------------------
# Target: bulk  (R6-13, R6-14, R6-15)
# ---------------------------------------------------------------------------

def target_bulk(scale):
    """R6-13/14/15 live in `index_v4/bulk_build.py` + `bulk_backfill.py`, which are
    reached ONLY through `connectedstore.build_index(..., bulk=True)`.

    ⚠ `benchmarks._harness.build_graph` does NOT reach them — it replays every routed
    triple through the incremental `widx.add_tuple` and bootstraps derived state with
    `DeltaProcessor.backfill()`. Profiling that would have reported 0 calls for both
    counters and produced a confident INCONCLUSIVE about code that never ran (the same
    error this file's `cascade` target already made once). So this target seeds a
    TupleV1 store exactly as `bulk_scale_bench` does and drives the real bulk path.
    """
    _banner(f'bulk — demorgans_law_2 via build_index(bulk=True), scale={scale}   '
            f'[R6-13, R6-14, R6-15]')
    spec = sb.WORKLOADS['demorgans']
    tuples = list(spec['gen'](scale))

    from sqlmodel import Session, SQLModel, create_engine
    from connectedstore import build_index
    from benchmarks.bulk_scale_bench import seed_tuples

    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    nrows = seed_tuples(session, 'src', spec['schema'], spec['shapes'], tuples)
    print(f'  dataset: {len(tuples):,} raw tuples -> {nrows:,} deduped TupleV1 rows')

    def work():
        _cur, widx, _rs = build_index(session, 'src', 'idx', bulk=True)
        return widx, nrows

    (widx, ntup), stats, table = _profile(work)
    rows = _rows(stats)
    wall = max(ct for (_n, _t, ct) in rows.values()) if rows else 0.0

    inst_n, inst_t, inst_c = _find(rows, func='_instances_of_type', file_frag='index_v4/bulk_backfill.py')
    sts_n, sts_t, sts_c = _find(rows, func='_stored_tupleset_subjects', file_frag='index_v4/bulk_backfill.py')
    rse_n, rse_t, rse_c = _find(rows, func='_reconcile_subject_edge', file_frag='index_v4/bulk_backfill.py')
    bf_n, bf_t, bf_c = _find(rows, func='backfill', file_frag='index_v4/processor.py')
    topo_n, topo_t, topo_c = _find(rows, func='_topo_order', file_frag='index_v4/bulk_build.py')

    print(f'\n  wall (profiled)       : {wall:.2f} s')
    print(f'  backfill              : {bf_n:,} calls, {bf_c:.2f} s cum  ({_pct(bf_c, wall)})')
    print(f'  bulk _instances_of_type: {inst_n:,} calls, {inst_c:.2f} s cum  ({_pct(inst_c, wall)})  <- R6-13')
    print(f'  bulk _stored_tupleset : {sts_n:,} calls, {sts_c:.2f} s cum  ({_pct(sts_c, wall)})  <- R6-14')
    print(f'  _reconcile_subject_edge: {rse_n:,} calls, {rse_c:.2f} s cum  ({_pct(rse_c, wall)})  (context)')
    print(f'  bulk _topo_order      : {topo_n:,} calls, {topo_c:.3f} s cum  ({_pct(topo_c, wall)})  <- R6-15')
    print('\n' + table)

    _verdict('R6-13',
             'bulk backfill full-scans the node set per check_fn evaluation',
             f'{inst_n:,} calls, {_pct(inst_c, wall)} of the build'
             + ('  (the bulk path RAN — bulk_backfill dominates the profile — but this '
                'function was never reached on this workload; it is the bulk twin of '
                'R6-3 and needs the same star/wildcard shapes to fire)' if inst_n == 0 else ''),
             None if inst_n == 0 else inst_c / wall > 0.10)
    _verdict('R6-14',
             'stored tupleset/userset parent enumerations re-sorted and re-built per evaluation',
             f'{sts_n:,} calls, {_pct(sts_c, wall)} of a bulk build',
             sts_c / wall > 0.10 if wall else None)
    _verdict('R6-15',
             'Kahn topo sort re-sorts the whole frontier after every emitted node',
             f'{topo_n:,} call(s), {_pct(topo_c, wall)} of the build — this share IS the '
             f'entire ceiling of the fix',
             None if topo_n == 0 else topo_c / wall > 0.05)
    return {'wall': wall, 'bulk_inst': inst_n, 'topo': topo_n}


# ---------------------------------------------------------------------------
# Target: space  (R6-18)
# ---------------------------------------------------------------------------

def target_space(rows_n):
    """Direct A/B of the two physical layouts, on real file-backed SQLite.

    R6-18 claims EdgeV4's surrogate PK costs "one whole B-tree off the biggest table".
    That is a property of the LAYOUT, not of this project's code, so it can be measured
    exactly without touching production models: build both layouts, insert identical
    rows, VACUUM, compare bytes. This is the CEILING of the fix — the real change would
    also have to carry a hand migration for persistent PostgreSQL and has no alembic.
    """
    _banner(f'space — EdgeV4 layout A/B, {rows_n:,} rows   [R6-18]')

    ddl_a = ('CREATE TABLE edge_a ('
             ' id INTEGER PRIMARY KEY,'
             ' store_id VARCHAR NOT NULL, subject_id INTEGER NOT NULL,'
             ' object_id INTEGER NOT NULL, direct_edge_count INTEGER NOT NULL,'
             ' indirect_edge_count INTEGER NOT NULL, derived BOOLEAN NOT NULL)')
    idx_a = ('CREATE UNIQUE INDEX ux_a ON edge_a (store_id, subject_id, object_id)')
    ddl_b = ('CREATE TABLE edge_b ('
             ' store_id VARCHAR NOT NULL, subject_id INTEGER NOT NULL,'
             ' object_id INTEGER NOT NULL, direct_edge_count INTEGER NOT NULL,'
             ' indirect_edge_count INTEGER NOT NULL, derived BOOLEAN NOT NULL,'
             ' PRIMARY KEY (store_id, subject_id, object_id)) WITHOUT ROWID')

    def build(ddl, idx, name):
        fd, path = tempfile.mkstemp(suffix=f'-{name}.sqlite')
        os.close(fd)
        os.unlink(path)
        con = sqlite3.connect(path)
        con.execute(ddl)
        if idx:
            con.execute(idx)
        con.executemany(
            f'INSERT INTO {name} (store_id, subject_id, object_id, direct_edge_count,'
            f' indirect_edge_count, derived) VALUES (?,?,?,?,?,?)',
            (('store-0001', i, (i * 7919) % rows_n, i % 3, 1 + i % 5, i % 2)
             for i in range(rows_n)))
        con.commit()
        con.execute('VACUUM')
        con.commit()
        con.close()
        size = os.path.getsize(path)
        os.unlink(path)
        return size

    a = build(ddl_a, idx_a, 'edge_a')
    b = build(ddl_b, None, 'edge_b')
    saved = a - b
    print(f'\n  A: surrogate PK + unique index : {a:>12,} bytes  ({a / rows_n:6.1f} B/row)')
    print(f'  B: WITHOUT ROWID composite PK  : {b:>12,} bytes  ({b / rows_n:6.1f} B/row)')
    print(f'  saved                          : {saved:>12,} bytes  '
          f'({100.0 * saved / a:.1f}% of the table)')

    _verdict('R6-18',
             'EdgeV4 carries a dead surrogate PK; a WITHOUT ROWID composite PK drops '
             'one whole B-tree off the biggest table',
             f'{100.0 * saved / a:.1f}% smaller on disk at {rows_n:,} rows '
             f'({a / rows_n:.1f} -> {b / rows_n:.1f} bytes/row)',
             saved > 0.15 * a)
    return {'a': a, 'b': b, 'saved_pct': 100.0 * saved / a}


# ---------------------------------------------------------------------------

TARGETS = {
    'paranoia': lambda a: target_paranoia(a.scale, a.commit_every),
    'graph-write': lambda a: target_graph_write(a.scale),
    'cascade': lambda a: target_cascade(a.bool_scale, a.incr),
    'bulk': lambda a: target_bulk(a.bool_scale),
    'space': lambda a: target_space(a.rows),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--target', default='all', choices=sorted(TARGETS) + ['all'])
    ap.add_argument('--scale', type=int, default=60, help='gdrive scale (write targets)')
    ap.add_argument('--bool-scale', type=int, default=40, help='demorgans scale (boolean targets)')
    ap.add_argument('--commit-every', type=int, default=1, help='raw tuples per commit')
    ap.add_argument('--incr', type=int, default=40, help='incremental write+cascade cycles')
    ap.add_argument('--rows', type=int, default=200000, help='rows for the space A/B')
    args = ap.parse_args()

    for name in (sorted(TARGETS) if args.target == 'all' else [args.target]):
        TARGETS[name](args)
    print()


if __name__ == '__main__':
    main()
