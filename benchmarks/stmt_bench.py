"""Statements-per-operation benchmark on a REAL ``ConnectedStore`` (P12-M, wave 0).

Unlike ``scale_bench.py`` / ``set_engine_bench.py`` -- which drive
``SetEngine.add_tuple`` / ``WildcardIndex.add_tuple`` directly through the
``build_set`` / ``build_graph`` harness paths and thereby BYPASS the composition
layer entirely -- this bench drives a live ``connectedstore.ConnectedStore`` (sync
schedule), so every P12 composition round-trip (log INSERT, ``_lock_store``, cursor
refresh, ``log_rows`` re-read, ``outbox_watermark``, cursor UPDATE, cascade) is on
the measured path.

The honest primary metric is **SQL statements per operation** (deterministic,
contention-immune), counted via an SQLAlchemy ``before_cursor_execute`` event
listener on the engine. In-memory SQLite makes wall-time a weak secondary signal
(a round-trip is ~microseconds and ``FOR UPDATE`` renders to nothing), but the
statement COUNT is exactly what the production PostgreSQL/MySQL targets pay per op.

Paranoia note: ``ConnectedStore`` opens the graph index via
``schema_io.open_graph_index`` -> ``ReachabilityIndex(session, store_id)`` directly;
it never calls ``install_paranoia``, and its constructor exposes no paranoia flag.
So the invariant checker is OFF here by construction (the production-realistic
mode) -- there is no knob to turn it on through ``ConnectedStore``. Reported as
``paranoia=off (unreachable via ConnectedStore)``.

Run:

    "C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe" -m benchmarks.stmt_bench

Deterministic: all data is enumerated by modular arithmetic, no RNG anywhere.
Additive tooling only -- touches no production code, writes no scale_bench.jsonl.
"""

from __future__ import annotations

import re
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore
from zanzibar_utils_v1 import Entity, RelationalTriple


# ---------------------------------------------------------------------------
# Statement counter (SQLAlchemy before_cursor_execute listener)
# ---------------------------------------------------------------------------

_FROM_RE = re.compile(r'\bFROM\s+["`]?(\w+)', re.IGNORECASE)


class StmtCounter:
    """Tallies every SQL statement the engine executes: total, by leading keyword
    (SELECT/INSERT/UPDATE/DELETE), occurrences of ``FOR UPDATE`` in the text, and --
    for SELECTs -- the first table named after ``FROM`` (so we can attribute the
    ``_lock_store`` re-takes on ``store_v4``, the ``log_rows`` read on
    ``tuple_log_v1``, and the ``outbox_watermark`` read on ``delta_outbox_v1``)."""

    def __init__(self) -> None:
        self.n = 0
        self.kw: Counter[str] = Counter()
        self.for_update = 0
        self.select_from: Counter[str] = Counter()

    def install(self, engine) -> None:
        event.listen(engine, 'before_cursor_execute', self._on_exec)

    def _on_exec(self, conn, cursor, statement, parameters, context, executemany):
        self.n += 1
        stripped = statement.lstrip()
        kw = stripped.split(None, 1)[0].upper() if stripped else '?'
        self.kw[kw] += 1
        up = statement.upper()
        if 'FOR UPDATE' in up:
            self.for_update += 1
        if kw == 'SELECT':
            m = _FROM_RE.search(statement)
            if m:
                self.select_from[m.group(1).lower()] += 1


@contextmanager
def count_statements(counter: StmtCounter):
    """Snapshot the counter's deltas around one operation. Yields a dict that is
    populated on exit with keys: n, kw (Counter), for_update, select_from (Counter)."""
    s_n, s_fu = counter.n, counter.for_update
    s_kw = Counter(counter.kw)
    s_sf = Counter(counter.select_from)
    snap: dict = {}
    try:
        yield snap
    finally:
        snap['n'] = counter.n - s_n
        snap['for_update'] = counter.for_update - s_fu
        snap['kw'] = counter.kw - s_kw
        snap['select_from'] = counter.select_from - s_sf


# ---------------------------------------------------------------------------
# Schemas (self-contained; valid DSL cross-checked against tests/fga_schemas)
# ---------------------------------------------------------------------------

# (a) Pure union: no boolean operators, so the delta processor is None and no
#     cascade/outbox path runs. viewer unions a direct grant, a group userset,
#     and two computed usersets (editor, owner).
UNION_SCHEMA = '''
type user
type group
  relations
    define member: [user]
type doc
  relations
    define owner: [user]
    define editor: [user, group#member]
    define viewer: [user, group#member] or editor or owner
'''

# (b) Boolean: can_view is a derived predicate (viewer BUT NOT blocked), so the
#     schema compiles derived plans -> proc is non-None -> the cascade + outbox
#     path runs on every write, and ⑥ outbox_watermark is SELECTed per write.
BOOL_SCHEMA = '''
type user
type group
  relations
    define member: [user]
type doc
  relations
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, group#member] or editor
    define can_view: viewer but not blocked
'''

_N_GROUPS = 12
_N_USERS = 12
_N_DOCS = 40


def gen_union():
    """Deterministic distinct septuples for the union schema (264 total)."""
    t = []
    for g in range(_N_GROUPS):
        for u in range(_N_USERS):
            t.append(('...', 'user', f'u{u}', 'member', 'group', f'g{g}'))
    for d in range(_N_DOCS):
        t.append(('...', 'user', f'u{d % _N_USERS}', 'owner', 'doc', f'd{d}'))
        t.append(('member', 'group', f'g{d % _N_GROUPS}', 'editor', 'doc', f'd{d}'))
        t.append(('...', 'user', f'u{(d + 1) % _N_USERS}', 'viewer', 'doc', f'd{d}'))
    return t


def gen_bool():
    """Deterministic distinct septuples for the boolean schema (264 total)."""
    t = []
    for g in range(_N_GROUPS):
        for u in range(_N_USERS):
            t.append(('...', 'user', f'u{u}', 'member', 'group', f'g{g}'))
    for d in range(_N_DOCS):
        t.append(('member', 'group', f'g{d % _N_GROUPS}', 'editor', 'doc', f'd{d}'))
        t.append(('...', 'user', f'u{(d + 1) % _N_USERS}', 'viewer', 'doc', f'd{d}'))
        t.append(('...', 'user', f'u{(d + 2) % _N_USERS}', 'blocked', 'doc', f'd{d}'))
    return t


# Read query mixes (graph-served). Hits reference known warm-up subjects/objects;
# ghosts guarantee a miss. For the union schema the read relation is 'viewer'; for
# boolean it is 'can_view' (the derived predicate). d0 owner is u0 -> viewer(u0,d0)
# holds via the owner arm; can_view(u0,d0) holds unless u0 is blocked (u2 is).
def union_checks():
    qs = []
    for i in range(50):
        d = i % _N_DOCS
        if i % 5 == 4:
            qs.append(('...', 'user', f'ghost{i}', 'viewer', 'doc', f'd{d}'))
        else:
            qs.append(('...', 'user', f'u{d % _N_USERS}', 'viewer', 'doc', f'd{d}'))  # owner arm -> hit
    return qs


def bool_checks():
    qs = []
    for i in range(50):
        d = i % _N_DOCS
        if i % 5 == 4:
            qs.append(('...', 'user', f'ghost{i}', 'can_view', 'doc', f'd{d}'))
        else:
            qs.append(('...', 'user', f'u{(d + 1) % _N_USERS}', 'can_view', 'doc', f'd{d}'))  # direct viewer
    return qs


def user_lookups():
    return [('...', 'user', f'u{i % _N_USERS}') for i in range(20)]


def union_reverses():
    return [('viewer', 'doc', f'd{i % _N_DOCS}') for i in range(20)]


def bool_reverses():
    return [('can_view', 'doc', f'd{i % _N_DOCS}') for i in range(20)]


# ---------------------------------------------------------------------------
# Fan-out K (rewrite triples yielded by ruleset.apply for a written raw tuple)
# ---------------------------------------------------------------------------

def fanout_k(store: ConnectedStore, raw) -> int:
    sp = Ellipsis if raw[0] == '...' else raw[0]
    tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3],
                          Entity(raw[4], raw[5]), sp)
    return len(list(store.ruleset.apply(tr)))


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _mmm(xs):
    return (sum(xs) / len(xs), min(xs), max(xs)) if xs else (0.0, 0, 0)


def _sum_kw(snaps):
    """Aggregate keyword breakdown across a list of per-op snapshot dicts, as a
    per-op mean string like 'S2.0 I1.0 U1.0'."""
    tot = Counter()
    for s in snaps:
        tot += s['kw']
    n = max(1, len(snaps))
    parts = []
    for key, short in (('SELECT', 'S'), ('INSERT', 'I'), ('UPDATE', 'U'), ('DELETE', 'D')):
        if tot[key]:
            parts.append(f'{short}{tot[key] / n:.1f}')
    return ' '.join(parts) if parts else '-'


def _sum_from(snaps, table):
    tot = sum(s['select_from'].get(table, 0) for s in snaps)
    return tot / max(1, len(snaps))


# ---------------------------------------------------------------------------
# Per-schema measurement
# ---------------------------------------------------------------------------

def measure(name: str, schema: str, gen, checks, lookups, reverses):
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    counter = StmtCounter()
    counter.install(engine)             # count construction too (reported separately)
    session = Session(engine)

    with count_statements(counter) as ctor:
        store = ConnectedStore(session, name, schema=schema)
    ctor_n = ctor['n']

    tuples = gen()
    assert len(tuples) >= 250, f'{name}: need >=250 distinct tuples, have {len(tuples)}'
    warmup = tuples[:200]
    adds = tuples[200:250]              # 50 distinct NEW writes (measured)
    removes = adds[:20]                 # 20 of the just-added tuples (measured)

    # Warm-up store (unmeasured): 200 sync writes.
    for raw in warmup:
        store.add_tuple(*raw)

    # Fan-out K for the measured adds (computed off the live ruleset; no DB work).
    ks = [fanout_k(store, raw) for raw in adds]
    k_mean, k_min, k_max = _mmm(ks)

    results = {'ctor_n': ctor_n, 'k': (k_mean, k_min, k_max)}

    # --- add_tuple (50 distinct new) ---
    add_snaps = []
    t0 = time.perf_counter()
    for raw in adds:
        with count_statements(counter) as s:
            store.add_tuple(*raw)
        add_snaps.append(s)
    add_dt = time.perf_counter() - t0
    results['add'] = (add_snaps, add_dt)

    # --- remove_tuple (20 of the added) ---
    rem_snaps = []
    t0 = time.perf_counter()
    for raw in removes:
        with count_statements(counter) as s:
            store.remove_tuple(*raw)
        rem_snaps.append(s)
    rem_dt = time.perf_counter() - t0
    results['remove'] = (rem_snaps, rem_dt)

    # --- check (50) ---
    chk_snaps = []
    cq = checks()
    t0 = time.perf_counter()
    for q in cq:
        with count_statements(counter) as s:
            store.check(*q)
        chk_snaps.append(s)
    chk_dt = time.perf_counter() - t0
    results['check'] = (chk_snaps, chk_dt)

    # --- lookup (20) ---
    lk_snaps = []
    lq = lookups()
    t0 = time.perf_counter()
    for q in lq:
        with count_statements(counter) as s:
            store.lookup(*q)
        lk_snaps.append(s)
    lk_dt = time.perf_counter() - t0
    results['lookup'] = (lk_snaps, lk_dt)

    # --- lookup_reverse (20) ---
    rv_snaps = []
    rq = reverses()
    t0 = time.perf_counter()
    for q in rq:
        with count_statements(counter) as s:
            store.lookup_reverse(*q)
        rv_snaps.append(s)
    rv_dt = time.perf_counter() - t0
    results['lookup_reverse'] = (rv_snaps, rv_dt)

    # Non-degeneracy: at least one non-empty read result, else the read numbers
    # would be an all-empty fast path (and the schema/data are wrong).
    n_hit_chk = sum(1 for q in cq if store.check(*q))
    l_nonempty = any((r.node_ids or r.markers) for r in (store.lookup(*q) for q in lq))
    r_nonempty = any((r.node_ids or r.markers) for r in (store.lookup_reverse(*q) for q in rq))
    results['sanity'] = (n_hit_chk, len(cq), l_nonempty, r_nonempty)

    session.close()
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _op_row(label, snaps_dt, extra_from=None):
    snaps, dt = snaps_dt
    ns = [s['n'] for s in snaps]
    mean, lo, hi = _mmm(ns)
    kw = _sum_kw(snaps)
    fu = sum(s['for_update'] for s in snaps) / max(1, len(snaps))
    rate = len(snaps) / dt if dt else float('inf')
    cells = [label, f'{mean:.1f}', str(lo), str(hi), kw, f'{fu:.1f}', f'{rate:,.0f}']
    if extra_from is not None:
        cells.append(extra_from)
    return '| ' + ' | '.join(cells) + ' |'


def render(name, r):
    lines = []
    k_mean, k_min, k_max = r['k']
    n_hit, n_tot, l_ok, r_ok = r['sanity']
    lines.append(f'### {name}')
    lines.append('')
    lines.append(f'- construction statements: {r["ctor_n"]}')
    lines.append(f'- rewrite fan-out K over the 50 measured adds: '
                 f'mean {k_mean:.2f}, min {k_min}, max {k_max}')
    lines.append(f'- read sanity: check hits {n_hit}/{n_tot}, '
                 f'lookup non-empty={l_ok}, reverse non-empty={r_ok}')
    lines.append('')
    lines.append('| op | stmts/op (mean) | min | max | kw/op (S/I/U/D) | FOR UPDATE/op | ops/s | store_v4 SELECT/op |')
    lines.append('|---|--:|--:|--:|---|--:|--:|--:|')
    lines.append(_op_row('add_tuple', r['add'], f'{_sum_from(r["add"][0], "store_v4"):.1f}'))
    lines.append(_op_row('remove_tuple', r['remove'], f'{_sum_from(r["remove"][0], "store_v4"):.1f}'))
    lines.append(_op_row('check', r['check'], '-'))
    lines.append(_op_row('lookup', r['lookup'], '-'))
    lines.append(_op_row('lookup_reverse', r['lookup_reverse'], '-'))
    lines.append('')

    # Per-write SELECT attribution (the P12 inventory validation).
    def _fromline(snaps_dt, tbl):
        return f'{_sum_from(snaps_dt[0], tbl):.2f}'
    add = r['add']
    lines.append('Per-`add_tuple` SELECT attribution (mean/op):')
    lines.append('')
    lines.append('| table | SELECT/op | inventory item |')
    lines.append('|---|--:|---|')
    lines.append(f'| store_v4 | {_fromline(add, "store_v4")} | (2)+(3) `_lock_store` re-takes (predict 1+K) |')
    lines.append(f'| tuple_log_v1 | {_fromline(add, "tuple_log_v1")} | (5) `log_rows` (predict 1) |')
    lines.append(f'| delta_outbox_v1 | {_fromline(add, "delta_outbox_v1")} | (6) `outbox_watermark` (boolean only, predict 1) |')
    lines.append(f'| index_cursor_v1 | {_fromline(add, "index_cursor_v1")} | (4) cursor refresh (predict 1) |')
    lines.append(f'| node_v4 | {_fromline(add, "node_v4")} | index node resolution |')
    lines.append(f'| edge_v4 | {_fromline(add, "edge_v4")} | index closure work |')
    lines.append(f'| residue_v1 | {_fromline(add, "residue_v1")} | derived residue (boolean only) |')
    lines.append('')
    k_mean = r['k'][0]
    sv = _sum_from(add[0], 'store_v4')
    lines.append(f'store_v4 SELECT/write = **{sv:.2f}** vs predicted 1+K = **{1 + k_mean:.2f}** '
                 f'(K mean {k_mean:.2f}).')
    lines.append('')
    return '\n'.join(lines)


def main():
    print('# Statements-per-operation baseline (real ConnectedStore, sync)\n')
    print('paranoia=off (unreachable via ConnectedStore; ReachabilityIndex opened '
          'directly, no install_paranoia)\n')

    t0 = time.perf_counter()
    union = measure('union', UNION_SCHEMA, gen_union,
                    union_checks, user_lookups, union_reverses)
    boolean = measure('boolean', BOOL_SCHEMA, gen_bool,
                      bool_checks, user_lookups, bool_reverses)
    total_dt = time.perf_counter() - t0

    print(render('(a) pure-union schema', union))
    print(render('(b) boolean schema (and / but not; cascade + outbox)', boolean))
    print(f'\ntotal bench wall time: {total_dt:.1f}s')


if __name__ == '__main__':
    main()
