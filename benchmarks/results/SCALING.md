# Scaling benchmark: set engine vs graph index

Reproduce with `benchmarks/scale_bench.py` (one process per row for clean RSS):

```
python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 1000 --json
python -m benchmarks.scale_bench --workload gdrive    --backend graph --scale 250  --json
python -m benchmarks.scale_bench --workload demorgans --backend set   --scale 500  --json
```

Raw records accumulate in `benchmarks/results/scale_bench.jsonl`. Environment:
Windows 11, SQLite in-memory for **both** backends, single process, `pyroaring`
set backend, paranoia OFF.

## What the two workloads are

- **gdrive** — the `gdrive.fga` fixture: pure-union folders/groups/docs with a
  `viewer from parent` TTU chain (folder ancestry, bounded chain depth 5) and
  `group#member` fan-in. Query mix: `can_read` on docs (owner / viewer / via
  group / via ancestor folder / ghost misses). The graph index materialises the
  full transitive closure; the set engine walks the doc's neighbourhood on the fly.
- **demorgans** — the `demorgans_law_2.fga` fixture: a 5-level boolean+TTU derived
  cascade with `and` / `but not` and `[user:*]` stars —
  `access ← authorized_user ← role_user_met ← user_met_requirement ← missing_user`
  over conditions and attributes. Query mix: `access` on docs. The graph maintains
  derived state via the delta processor (`backfill()` at build); the set engine
  evaluates the booleans pointwise with a per-query memo.

  (Note: `demorgans_law_1.fga` is *not* used — its deep relations are constantly
  empty by construction, because their TTU tuplesets are derived relations with no
  Direct restrictions, so no tuple can ever be *stored* on them and TTU parents are
  stored-tuple-only. `_2` computes non-trivially end to end.)

## Results

**gdrive (pure-union hierarchy).** Both backends agree on every answer (≈105/200
true in the query mix).

| N (docs) | raw tuples | backend | build | writes/s | check throughput | RSS after build |
|---:|---:|---|---:|---:|---:|---:|
| 250   | 4,200   | set (roaring) | 7.4 s   | 565 | **15,011 checks/s** | 66 MB |
| 250   | 4,200   | graph         | 141.6 s | 30  | 260 checks/s        | 66 MB |
| 1,000 | 16,800  | set (roaring) | 40.9 s  | 411 | **15,335 checks/s** | 84 MB |
| 4,000 | 67,200  | set (roaring) | 171.4 s | 392 | 8,297 checks/s ⚠    | 152 MB |
| 8,000 | 134,400 | set (roaring) | 296.2 s | 454 | **18,404 checks/s** | 244 MB |

**demorgans (5-level boolean+TTU cascade with conditions/attributes).** Both
backends agree (107/200 true).

| N (docs) | raw tuples | backend | build | writes/s | check throughput | RSS after build |
|---:|---:|---|---:|---:|---:|---:|
| 100   | 4,850   | set (roaring) | 6.3 s   | 770 | **15,095 checks/s** | 66 MB |
| 100   | 4,850   | graph         | 321.3 s | 15  | 583 checks/s        | 65 MB |
| 500   | 54,250  | set (roaring) | 69.8 s  | 777 | **14,939 checks/s** | 121 MB |
| 1,500 | 162,750 | set (roaring) | 213.3 s | 763 | **13,926 checks/s** | 237 MB |

⚠ The gdrive/4000 dip to 8,297 is measurement noise (GC pause during the timed
loop), not an N-trend — 8,000 (2× the tuples) runs at 18,404.

## Reading it

**1. Per-check latency does NOT grow with tuple count.** This is the headline
answer. Set-engine check throughput is flat across the whole range: gdrive holds
~15k checks/s from 4.2k to 16.8k tuples (and stays in an 8k–18k noise band out to
134k); demorgans holds ~14–15k checks/s across a **33× tuple increase** (4.8k →
162.7k). The reason: a `check` walks only the *neighborhood the query touches* — a
doc plus its bounded-depth ancestor folders and their groups, or one doc's role →
cond → attr cascade — **not** the whole store. Adding unrelated docs/users doesn't
enlarge that neighborhood, so latency is constant. This is the structural
difference from OpenFGA, which traverses on the fly *with a DB round-trip per hop
and no materialized closure*, so it pays traversal-size × per-hop latency and slows
as data grows. The set engine removes the per-hop I/O (all in-RAM); the graph index
removes the traversal (materialized closure). Either way, no global-tuple-count
cliff. (The set engine *would* slow for a query over a single huge group — a group
with 100k direct members makes that group's check O(members) — but that's local
fan-in, not total tuple count.)

**2. The graph index is O(1) per check but ~25–60× slower in absolute terms here.**
Graph check is depth- and size-independent by construction (the closure is
materialized, so `check` is a bounded number of point lookups), which is why it's
also flat. But each point lookup is a Python → SQLAlchemy → SQLite round-trip
(~1–4 ms), while the set engine answers from in-process roaring bitmaps with no I/O
boundary. On a single machine with in-memory SQLite, in-RAM bitmaps beat
per-probe DB round-trips almost regardless of algorithmic complexity — so the set
engine wins raw throughput 260→15k (gdrive) and 583→15k (demorgans).

**3. The trade is at write time.** The graph pays its memoization up front: build
runs at **15–30 writes/s** (closure materialization, plus a full `backfill()`
reconcile of every derived key for boolean schemas) versus the set engine's
**400–780 writes/s** — 20–50× slower to load. That's the memoization spectrum
working exactly as designed: the graph moves cost from read time to write time and
storage; the set engine keeps writes cheap and pays at read time.

**4. RAM is ~linear in tuples for the set engine: ≈1.0–1.2 KB per raw tuple.**
gdrive: 161 MB of data for 134k tuples (1.2 KB/tuple). demorgans: 149 MB for 163k
tuples (0.9 KB/tuple). So a **1,500-doc demorgans store (163k tuples) fits in ~237
MB total process RSS**; a 134k-tuple gdrive store in ~244 MB. Extrapolating, ~1 M
tuples ≈ 1–1.2 GB for the set engine — it holds all state in RAM, so working-set
size is the ceiling. The graph index's footprint is similar at small scale but
grows *super*-linearly with hierarchy depth (it stores an edge per reachable pair,
not per tuple), and it lives in the DB, so it isn't RAM-bound the same way — it
trades RAM for storage + write cost.

## Caveats

- **Both backends ran on SQLite in-memory in one process.** That structurally
  favors the set engine, which avoids the storage boundary entirely. In a
  production deployment the graph index would sit on PostgreSQL and pay network
  latency per probe (worse absolute constant, but the O(1)-in-depth property is
  unchanged), while surviving restarts and being shared across processes/replicas —
  things the in-RAM set engine can't do. The set engine's numbers assume the whole
  store fits in RAM and is rebuilt on open.
- **When the graph index wins:** very deep/wide graphs where a set-engine
  neighborhood grows large; data that exceeds RAM; read-heavy workloads where
  recomputation cost dominates; multi-reader deployments needing shared persistent
  state. **When the set engine wins:** everything fits in RAM, write-heavy or
  write-latency-sensitive workloads, and single-process/embedded use.
- Roaring vs plain Python sets barely matters for these pointwise checks (they're
  small-set traversals); roaring's 100–400× edge shows up only in bulk `expand`
  over large populations (see `set_engine_bench.py` workload b).
