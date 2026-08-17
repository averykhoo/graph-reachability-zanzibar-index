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
               R6-11  _residue_cache_scope entries (cache torn down between reconciles)
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
from benchmarks.profile_r6 import (StmtCounter, _banner, _find, _pct, _profile,
                                   _rows, _verdict)


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

def target_cascade(scale, incr):
    """R6-10/11/12 live on the INCREMENTAL cascade, not on the bootstrap.

    ⚠ The first version of this probe profiled `build_graph`, which bootstraps derived
    state with `DeltaProcessor.backfill()` — the OFFLINE path. `reconcile_subject` was
    called **0 times**, so R6-11 and R6-12 came back INCONCLUSIVE against a run that
    never executed the code they describe. The measured path has to be the one
    `tests/test_matrix.py::GraphBackend.apply` uses: write, then `run_cascade(wm)` in
    the same transaction (synchronous v1). So: bootstrap first (unprofiled), then
    profile `incr` incremental write+cascade cycles.
    """
    _banner(f'cascade — demorgans_law_2/graph scale={scale}, {incr} incremental '
            f'write+cascade cycles (boolean)   [R6-10, R6-11, R6-12]')
    spec = sb.WORKLOADS['demorgans']
    tuples = list(spec['gen'](scale))
    print(f'  dataset: {len(tuples):,} raw tuples (bootstrap, unprofiled)')

    widx, ntup = build_graph(spec['schema'], spec['shapes'], tuples)

    from index_v4.processor import DeltaProcessor
    from index_v4.outbox import outbox_watermark
    from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
    ruleset = parse_openfga_schema(spec['schema'], object_wildcard_shapes=spec['shapes'])
    proc = DeltaProcessor(widx, ruleset.compiled)
    session = widx.idx.session

    # Fresh tuples the bootstrap has not seen: extend the generator past `scale`.
    extra = [t for t in spec['gen'](scale + incr) if t not in set(tuples)][:incr]
    print(f'  incremental writes    : {len(extra):,} fresh tuples through run_cascade')

    # Count reconcile_subject calls and their DISTINCT keys — R6-12's measurable
    # consequence (an un-deduped _bumped re-reconciles the same key).
    calls = []
    per_cycle = []
    orig = DeltaProcessor.reconcile_subject

    def counting(self, object_type, rel, obj_name, *a, **k):
        calls.append((object_type, rel, obj_name))
        return orig(self, object_type, rel, obj_name, *a, **k)

    DeltaProcessor.reconcile_subject = counting
    try:
        def work():
            n = 0
            for raw in extra:
                wm = outbox_watermark(session, widx.idx.store_id)
                sp = Ellipsis if raw[0] == '...' else raw[0]
                tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
                for d in ruleset.apply(tr):
                    widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                                   d.subject.type, d.subject.name, d.relation,
                                   d.object.type, d.object.name)
                del calls[:]                      # R6-12 is INTRA-cascade duplication
                proc.run_cascade(wm)
                per_cycle.append((len(calls), len(set(calls))))
                session.commit()
                n += 1
            return n
        nwrites, stats, table = _profile(work)
    finally:
        DeltaProcessor.reconcile_subject = orig

    rows = _rows(stats)
    wall = max(ct for (_n, _t, ct) in rows.values()) if rows else 0.0

    sts_n, sts_t, sts_c = _find(rows, func='_stored_tupleset_subjects', file_frag='index_v4/processor.py')
    rcs_n, rcs_t, rcs_c = _find(rows, func='_residue_cache_scope', file_frag='index_v4/processor.py')
    # R6-12 is about ONE cascade re-reconciling ONE key several times. Aggregating
    # across cycles would report the same key touched by successive WRITES as
    # duplication, which it is not -- so sum the per-cycle figures instead.
    rec_n = sum(c for c, _d in per_cycle)
    rec_d = sum(d for _c, d in per_cycle)
    worst = max((c for c, _d in per_cycle), default=0)

    print(f'\n  wall (profiled)       : {wall:.2f} s')
    print(f'  _stored_tupleset_subj : {sts_n:,} calls, {sts_c:.2f} s cum  ({_pct(sts_c, wall)})  <- R6-10')
    print(f'  _residue_cache_scope  : {rcs_n:,} entries  <- R6-11')
    print(f'  reconcile_subject     : {rec_n:,} calls over {rec_d:,} distinct keys '
          f'SUMMED PER CASCADE ({rec_n / max(rec_d, 1):,.2f}x intra-run re-reconcile; '
          f'worst single cascade {worst:,} calls)  <- R6-12')
    print('\n' + table)

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
    return {'reconciles': rec_n, 'distinct': rec_d, 'sts_share': sts_c / wall if wall else None}


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
