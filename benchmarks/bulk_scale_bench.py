"""Graph-at-scale curves via the P13 bulk builder (the M2 unlock) + the set engine
at the SAME scales, measured in the SAME process conditions -- the pareto-crossover
data the incremental graph build could never reach.

The pre-perf baseline (``BASELINE_2026-07-13.md``) capped every graph row at the
smallest scale of its tier: the incremental ``build_graph`` runs at 15-156 writes/s,
so a 200k-tuple graph build was hours. ``build_index(..., bulk=True)`` (P13)
constructs the identical pre-backfill state directly (topo + sparse path-count DP +
bulk INSERT), ~44-49x faster, so the graph can finally be built at 10^4-10^5 tuples.

This script builds a graph index at a given scale via the bulk builder and measures
its FLAT read surfaces (check/lookup/reverse), then -- in a separate invocation for a
clean RSS reading -- opens the SET engine on the SAME seeded tuple store and measures
its ``rebuild()`` cost, RSS, and the same read surfaces. Run ONE backend per process:

    python -m benchmarks.bulk_scale_bench --workload simple --scale 12500 --backend graph --json
    python -m benchmarks.bulk_scale_bench --workload simple --scale 12500 --backend set   --json

``--json`` appends one record to results/<out> (default graph_scale_2026-07-15.jsonl).

Seeding: the deterministic scale_bench generators (reused verbatim) are bulk-inserted
as ``TupleV1`` rows (dedup'd; the data is acyclic + admission-valid by construction,
so bypassing per-tuple ``TupleSource`` admission is safe and fast). The graph is then
built from that snapshot via ``build_index``; the set engine via ``rebuild()``. Both
share ONE in-memory SQLite, so both RSS figures include the ``TupleV1`` rows -- an
artifact of the shared-DB harness. In production the graph is DB-resident (RAM-bounded
by cache, not data size) while the set engine MUST hold all state in RAM; so this
harness UNDERSTATES the graph's memory advantage. Reads are time-boxed like scale_bench.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, SQLModel, create_engine

from setengine import PySets, RoaringSets
from setengine.models import TupleV1
from connectedstore import build_index, save_schema
from connectedstore.schema_io import open_set_engine

from benchmarks._harness import rss_mb, timed
from benchmarks.scale_bench import WORKLOADS, _rsz


def fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def seed_tuples(session: Session, store_id: str, schema: str, shapes, tuples) -> int:
    """Persist the schema and bulk-insert dedup'd raw tuples as TupleV1 rows."""
    save_schema(session, store_id, schema, shapes)
    seen: set = set()
    rows = []
    for t in tuples:
        if t in seen:
            continue
        seen.add(t)
        rows.append(TupleV1(store_id=store_id, subject_predicate=t[0], subject_type=t[1],
                            subject_name=t[2], relation=t[3], object_type=t[4],
                            object_name=t[5]))
    session.add_all(rows)
    session.commit()
    return len(rows)


def run(workload: str, scale: int, backend: str, ops_name: str, checks: int,
        lookups: int, time_box: float, emit_json: bool, out_name: str) -> None:
    spec = WORKLOADS[workload]
    schema, shapes = spec['schema'], spec['shapes']
    tuples = list(spec['gen'](scale))
    cq = spec['checks'](scale, checks)
    lq = spec['lookups'](scale, lookups)
    rq = spec['reverses'](scale, lookups)

    gc.collect()
    rss_before = rss_mb('current')

    session = fresh_session()
    src = f'{workload}_src'
    n_tuples = seed_tuples(session, src, schema, shapes, tuples)
    gc.collect()
    rss_seeded = rss_mb('current')

    build_s = None
    rebuild_s = None
    if backend == 'graph':
        idx = f'{workload}_gidx'
        t0 = time.perf_counter()
        _, be, _ = build_index(session, src, idx, bulk=True)
        build_s = time.perf_counter() - t0
        impl = 'graph:bulk'
    else:
        ops = RoaringSets if (ops_name == 'roaring' and RoaringSets) else PySets
        # constructor replays once; time an explicit rebuild() as the canonical
        # set-engine "open a store" cost (reset + O(N) replay from TupleV1).
        be = open_set_engine(session, src, ops=ops)
        t0 = time.perf_counter()
        be.rebuild()
        rebuild_s = time.perf_counter() - t0
        impl = f'set:{ops.name}'

    gc.collect()
    rss_after = rss_mb('current')
    rss_peak = rss_mb('peak')

    check, lookup, reverse = be.check, be.lookup, be.lookup_reverse

    sample = [bool(check(*qq)) for qq in cq[:200]]
    trues = sum(sample)
    assert 0 < trues < len(sample), \
        f'degenerate check mix ({trues}/{len(sample)} true)'
    answers_sig = f'{int("".join("01"[b] for b in sample), 2):x}'

    l_sizes = [_rsz(lookup(*qq)) for qq in lq[:5]]
    r_sizes = [_rsz(reverse(*qq)) for qq in rq[:5]]
    assert any(s > 0 for s in l_sizes), 'degenerate lookup mix (all empty)'
    assert any(s > 0 for s in r_sizes), 'degenerate reverse mix (all empty)'

    check_rate, _, check_done = timed(lambda i: check(*cq[i % len(cq)]), checks, time_box)
    lookup_rate, _, lookup_done = timed(lambda i: lookup(*lq[i % len(lq)]), lookups, time_box)
    reverse_rate, _, reverse_done = timed(lambda i: reverse(*rq[i % len(rq)]), lookups, time_box)

    seeded_ram = (rss_seeded - rss_before) if (rss_seeded and rss_before) else None
    state_ram = (rss_after - rss_seeded) if (rss_after and rss_seeded) else None
    print(f'\n{workload}/{impl}  scale={scale}  tuples={n_tuples:,}')
    if build_s is not None:
        print(f'  bulk build (P13)  : {build_s:,.2f} s  ({n_tuples / build_s:,.0f} tuples/s)')
    if rebuild_s is not None:
        print(f'  set rebuild()     : {rebuild_s:,.2f} s  ({n_tuples / rebuild_s:,.0f} tuples/s)')
    print(f'  RSS after build   : {rss_after:,.0f} MB' if rss_after else '  RSS: n/a')
    print(f'  RSS (seed tuples) : {seeded_ram:,.0f} MB' if seeded_ram is not None else '')
    print(f'  RSS (backend data): {state_ram:,.0f} MB' if state_ram is not None else '')
    print(f'  peak RSS          : {rss_peak:,.0f} MB' if rss_peak else '')
    print(f'  check             : {check_rate:>12,.1f} /s  ({check_done} done, {trues}/200 true)')
    print(f'  lookup            : {lookup_rate:>12,.1f} /s  ({lookup_done} done, ~{max(l_sizes)} max)')
    print(f'  lookup_reverse    : {reverse_rate:>12,.1f} /s  ({reverse_done} done, ~{max(r_sizes)} max)')
    print(f'  answers signature : {answers_sig}')

    if emit_json:
        out = Path(__file__).resolve().parent / 'results'
        out.mkdir(exist_ok=True)
        rec = dict(workload=workload, impl=impl, scale=scale, tuples=n_tuples,
                   build_s=round(build_s, 3) if build_s is not None else None,
                   rebuild_s=round(rebuild_s, 3) if rebuild_s is not None else None,
                   rss_after_mb=round(rss_after, 1) if rss_after else None,
                   rss_seed_mb=round(seeded_ram, 1) if seeded_ram is not None else None,
                   rss_state_mb=round(state_ram, 1) if state_ram is not None else None,
                   peak_rss_mb=round(rss_peak, 1) if rss_peak else None,
                   checks=check_done, checks_per_s=round(check_rate, 1),
                   lookups=lookup_done, lookups_per_s=round(lookup_rate, 2),
                   reverses=reverse_done, reverses_per_s=round(reverse_rate, 2),
                   mean_lookup_size=round(sum(l_sizes) / len(l_sizes), 1),
                   mean_reverse_size=round(sum(r_sizes) / len(r_sizes), 1),
                   trues_of_200=trues, answers_sig=answers_sig)
        with (out / out_name).open('a') as fh:
            fh.write(json.dumps(rec) + '\n')

    session.close()


def main():
    p = argparse.ArgumentParser(description='Graph-at-scale (P13 bulk) + set-engine crossover bench')
    p.add_argument('--workload', choices=list(WORKLOADS), required=True)
    p.add_argument('--scale', type=int, required=True)
    p.add_argument('--backend', choices=['graph', 'set'], required=True)
    p.add_argument('--impl', choices=['py', 'roaring'], default='roaring')
    p.add_argument('--checks', type=int, default=5000)
    p.add_argument('--lookups', type=int, default=500)
    p.add_argument('--time-box', type=float, default=20.0, dest='time_box')
    p.add_argument('--json', action='store_true')
    p.add_argument('--out', default='graph_scale_2026-07-15.jsonl', dest='out_name')
    a = p.parse_args()
    run(a.workload, a.scale, a.backend, a.impl, a.checks, a.lookups, a.time_box,
        a.json, a.out_name)


if __name__ == '__main__':
    main()
