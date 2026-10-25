"""TK162: what does TK144's implicit-userset channel cost graph lookup / lookup_reverse?

TK144 (OpenFGA's implicit userset self-relation) added brute-force passes to the graph
index's lookups: ``src/zanzibar/graphindex/wildcard.py::WildcardIndex._self_lookup``
(a ``check`` per entity of every derived family's type), ``::_self_reverse_extra`` and
``::_self_reverse_derived``. Nothing timed them on a large store. Results and the
conclusion: ``docs/tk162-self-lookup-cost-2026-10-26.md``.

For each query the same ``Store`` is timed twice: ``on`` = the shipped read, and
``off`` = the same index with ``WildcardIndex._reflexive_reads`` forced False, which
skips the three passes (the pre-TK144 read; its answers then omit the implicit
usersets, so ``off`` is a cost baseline, never a correct answer). The set engine's
``lookup`` / ``lookup_reverse`` on the same store is timed alongside, and the shipped
graph answer is compared key-for-key with it (``agree``).

Every size runs in its OWN process (``sweep`` spawns ``point``). The precondition is
bulk-inserted as ``RelationTuple`` + ``TupleLog`` rows and built with
``build_index(..., bulk=True)``, as in ``benchmarks/fanout_cost_bench.py``; setup is not
measured.

Usage (repo root, the repo's conda env)::

    python -m benchmarks.tk162_self_lookup_bench point --n 1000 --out x.jsonl
    python -m benchmarks.tk162_self_lookup_bench sweep --sizes 1000,10000,100000 --out x.jsonl
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / 'src'))   # this checkout's code, never an installed copy

from sqlalchemy import func  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from zanzibar.store import Store, build_index, save_schema  # noqa: E402
from zanzibar.graphindex.models import Node  # noqa: E402
from zanzibar.setengine.models import RelationTuple  # noqa: E402

from benchmarks.fanout_cost_bench import machine_load, seed  # noqa: E402

STORE = 'fan'   # fanout_cost_bench.seed writes this store id

# Deep computed-seed chain on doc (owner -> editor -> viewer) and one derived
# (`but not`) family on each of the two userset-bearing types, so every pass fires.
SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
    define banned: [user]
    define active: member but not banned
type doc
  relations
    define owner: [user, group#member]
    define editor: [user, group#member] or owner
    define viewer: [user, group#member] or editor
    define blocked: [user]
    define can_view: viewer but not blocked
"""

#: ``--schema plain``: the same schema with every ``but not`` read as ``or``, so no
#: relation is derived and ``_self_lookup``'s per-entity ``check`` loop has nothing to walk.
SCHEMAS = {'boolean': SCHEMA, 'plain': SCHEMA.replace(' but not ', ' or ')}

# (label, method, args). Userset subjects take the _self_lookup pass; user:u0 does not.
QUERIES = [
    ('lookup group:g0#member', 'lookup', ('member', 'group', 'g0')),
    ('lookup doc:d0#owner', 'lookup', ('owner', 'doc', 'd0')),
    ('lookup user:u0 (control)', 'lookup', ('...', 'user', 'u0')),
    ('reverse viewer doc:d0', 'lookup_reverse', ('viewer', 'doc', 'd0')),
    ('reverse can_view doc:d0', 'lookup_reverse', ('can_view', 'doc', 'd0')),
    ('reverse active group:g0', 'lookup_reverse', ('active', 'group', 'g0')),
]


def plan(n: int):
    """~n tuples: D = n//8 docs x 4 tuples + G = n//20 groups x (10 members [+1 ban])."""
    d_count, g_count = max(1, n // 8), max(1, n // 20)
    u_count = max(100, n // 10)

    def gen():
        for i in range(g_count):
            for k in range(10):
                yield ('...', 'user', f'u{(i * 10 + k) % u_count}', 'member', 'group', f'g{i}')
            if i % 5 == 0:
                yield ('...', 'user', f'u{(i * 10) % u_count}', 'banned', 'group', f'g{i}')
            if i and i % 4 == 0:                         # some nesting
                yield ('member', 'group', f'g{i}', 'member', 'group', f'g{i // 4}')
        for j in range(d_count):
            yield ('...', 'user', f'u{j % u_count}', 'owner', 'doc', f'd{j}')
            yield ('member', 'group', f'g{j % g_count}', 'editor', 'doc', f'd{j}')
            yield ('...', 'user', f'u{(j * 7) % u_count}', 'viewer', 'doc', f'd{j}')
            yield ('...', 'user', f'u{(j * 3) % u_count}', 'blocked', 'doc', f'd{j}')
    return gen, dict(docs=d_count, groups=g_count, users=u_count)


def timed(fn, budget_s: float, max_reps: int):
    """Median ms over at least 3 reps, more while under ``budget_s`` (cap ``max_reps``)."""
    xs = []
    t_end = time.perf_counter() + budget_s
    while len(xs) < 3 or (len(xs) < max_reps and time.perf_counter() < t_end):
        t0 = time.perf_counter_ns()
        out = fn()
        xs.append((time.perf_counter_ns() - t0) / 1e6)
    return round(statistics.median(xs), 3), len(xs), out


def run_point(args) -> dict:
    rec: dict = dict(n=args.n, schema=args.schema, date=time.strftime('%Y-%m-%d %H:%M:%S'),
                     python=platform.python_version(), host=platform.node(),
                     backend='sqlite-file')
    rec['load_before'] = machine_load()
    work = Path(tempfile.gettempdir()) / 'zanzibar-tk162-bench'
    work.mkdir(parents=True, exist_ok=True)
    db_path = work / f'tk162_{args.schema}_{args.n}_{os.getpid()}.db'
    engine = create_engine(f'sqlite:///{db_path}')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    try:
        gen, shape = plan(args.n)
        rec.update(shape)
        t0 = time.perf_counter()
        save_schema(session, STORE, SCHEMAS[args.schema])
        session.commit()
        seed(session, gen)
        build_index(session, STORE, bulk=True)
        cs = Store(session, STORE, paranoia='off')
        rec['setup_s'] = round(time.perf_counter() - t0, 2)
        rec['tuples'] = int(session.exec(select(func.count()).select_from(RelationTuple)
                                         .where(RelationTuple.store_id == STORE)).one())
        rec['nodes'] = int(session.exec(select(func.count()).select_from(Node)
                                        .where(Node.store_id == STORE)).one())
        se = cs.source.engine
        cs.source.catch_up_evaluator()
        widx = cs.widx
        assert widx._reflexive_reads, 'schema has no self seeds: the TK144 passes never fire'
        rows = []
        for label, meth, qargs in QUERIES:
            gc.collect()
            row = dict(query=label)
            widx._reflexive_reads = True
            row['on_ms'], row['on_reps'], res = timed(
                lambda: getattr(cs, meth)(*qargs), args.budget, args.max_reps)
            widx._reflexive_reads = False
            row['off_ms'], row['off_reps'], res_off = timed(
                lambda: getattr(cs, meth)(*qargs), args.budget, args.max_reps)
            widx._reflexive_reads = True
            row['set_ms'], row['set_reps'], sres = timed(
                lambda: getattr(se, meth)(*qargs), args.budget, args.max_reps)
            g_keys = set(cs.result_keys(res)) | {('marker',) + m for m in res.markers}
            g_off = set(cs.result_keys(res_off)) | {('marker',) + m for m in res_off.markers}
            s_keys = set(se.result_keys(sres)) | {('marker',) + m for m in sres.markers}
            row['answers'] = len(g_keys)
            row['implicit_answers'] = len(g_keys - g_off)
            row['agree'] = g_keys == s_keys
            row['ratio_on_off'] = round(row['on_ms'] / row['off_ms'], 1) if row['off_ms'] else None
            rows.append(row)
            print(json.dumps(row), flush=True)
        rec['queries'] = rows
        rec['load_after'] = machine_load()
    finally:
        session.close()
        engine.dispose()
        if not args.keep_db:
            for p in (db_path, Path(str(db_path) + '-wal'), Path(str(db_path) + '-journal')):
                if p.exists():
                    p.unlink()
    if args.out:
        with open(args.out, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + '\n')
    return rec


def run_sweep(args) -> int:
    rc = 0
    for n in [int(s) for s in args.sizes.split(',')]:
        cmd = [sys.executable, '-m', 'benchmarks.tk162_self_lookup_bench', 'point',
               '--n', str(n), '--schema', args.schema, '--out', args.out,
               '--budget', str(args.budget),
               '--max-reps', str(args.max_reps)]
        print('>>', ' '.join(cmd), flush=True)
        r = subprocess.run(cmd, cwd=_ROOT)
        rc = rc or r.returncode
    return rc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('point', 'sweep'):
        s = sub.add_parser(name)
        s.add_argument('--out', default='')
        s.add_argument('--budget', type=float, default=2.0,
                       help='seconds of reps per query and mode (min 3 reps)')
        s.add_argument('--max-reps', type=int, default=50)
        s.add_argument('--schema', choices=sorted(SCHEMAS), default='boolean')
        if name == 'point':
            s.add_argument('--n', type=int, required=True)
            s.add_argument('--keep-db', action='store_true')
        else:
            s.add_argument('--sizes', default='1000,10000,100000')
    args = p.parse_args(argv)
    if args.cmd == 'point':
        run_point(args)
        return 0
    return run_sweep(args)


if __name__ == '__main__':
    sys.exit(main())
