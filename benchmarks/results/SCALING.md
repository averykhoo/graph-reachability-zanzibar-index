# Scaling benchmark: set engine vs graph index

Reproduce with `benchmarks/scale_bench.py` (one process per row for clean RSS; every
row below uses the default `--checks 5000`):

```
python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 250  --json
python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 1000 --json
python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 4000 --json
python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 8000 --json
python -m benchmarks.scale_bench --workload gdrive    --backend graph --scale 250  --json
python -m benchmarks.scale_bench --workload demorgans --backend set   --scale 100  --json
python -m benchmarks.scale_bench --workload demorgans --backend set   --scale 500  --json
python -m benchmarks.scale_bench --workload demorgans --backend set   --scale 1500 --json
python -m benchmarks.scale_bench --workload demorgans --backend graph --scale 100  --json
```

Raw records accumulate in `benchmarks/results/scale_bench.jsonl`. Environment:
Windows 11, SQLite in-memory for **both** backends, single process, `pyroaring`
set backend, paranoia OFF. All rows below were measured in one session
(2026-07-08), so they are comparable to each other; absolute numbers shift with
machine load between sessions.

> Provenance: these rows supersede an earlier run whose demorgans query mix had a
> parity-aliasing bug (`role = (d + i%2) % n_roles` with `d = i % n` only ever
> selects even role indices at even scales, so half the role→cond→attr universe
> was never queried). The fixed mix (hash-strided role/user slots) exercises every
> role at the published scales. The superseded records are in git history.

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

## Cross-backend agreement

Each row records `answers_sig`, the bit-vector of the first 200 query answers as
hex. At every (workload, scale) where **both** backends ran — gdrive/250 and
demorgans/100 — the signatures are identical, i.e. the backends agree
**query-by-query** on those 200 queries, not merely on the aggregate true-count.
Scales with only a set-engine row make no cross-backend claim (graph builds at
15–50 writes/s, so large-scale graph loads are impractically slow to run here);
set-engine-vs-oracle parity at scale is covered by the test suite instead.

## Results

**gdrive (pure-union hierarchy).** ~105/200 of the mixed queries are true.

| N (docs) | raw tuples | backend | build | writes/s | check throughput | RSS after build |
|---:|---:|---|---:|---:|---:|---:|
| 250   | 4,200   | set (roaring) | 5.4 s   | 781 | **20,700 checks/s** | 68 MB |
| 250   | 4,200   | graph         | 83.0 s  | 51  | 415 checks/s        | 66 MB |
| 1,000 | 16,800  | set (roaring) | 21.1 s  | 797 | **18,653 checks/s** | 84 MB |
| 4,000 | 67,200  | set (roaring) | 84.7 s  | 794 | **19,511 checks/s** | 151 MB |
| 8,000 | 134,400 | set (roaring) | 170.0 s | 790 | **19,180 checks/s** | 244 MB |

(An earlier session's gdrive/4000 row dipped to 8,297 checks/s; this session's
re-run sits at 19,511, inside the band of every other scale — the dip was
single-run measurement noise, not an N-trend.)

**demorgans (5-level boolean+TTU cascade with conditions/attributes).** 110/200
of the mixed queries are true.

| N (docs) | raw tuples | backend | build | writes/s | check throughput | RSS after build |
|---:|---:|---|---:|---:|---:|---:|
| 100   | 4,850   | set (roaring) | 6.1 s   | 793 | **14,945 checks/s** | 68 MB |
| 100   | 4,850   | graph         | 329.5 s | 15  | 598 checks/s        | 65 MB |
| 500   | 54,250  | set (roaring) | 72.5 s  | 749 | **11,834 checks/s** | 120 MB |
| 1,500 | 162,750 | set (roaring) | 216.0 s | 754 | **14,239 checks/s** | 238 MB |

## Reading it

**1. Per-check latency does NOT grow with tuple count.** This is the headline
answer. Set-engine check throughput is flat across the whole range: gdrive holds
~19–21k checks/s from 4.2k to 134k tuples; demorgans holds ~12–15k checks/s across
a **33× tuple increase** (4.8k → 162.7k) with no downward trend (the 1,500-doc row
is faster than the 500-doc row). The reason: a `check` walks only the
*neighborhood the query touches* — a doc plus its bounded-depth ancestor folders
and their groups, or one doc's role → cond → attr cascade — **not** the whole
store. Adding unrelated docs/users doesn't enlarge that neighborhood, so latency
is constant. This is the structural difference from OpenFGA, which traverses on
the fly *with a DB round-trip per hop and no materialized closure*, so it pays
traversal-size × per-hop latency and slows as data grows. The set engine removes
the per-hop I/O (all in-RAM); the graph index removes the traversal (materialized
closure). Either way, no global-tuple-count cliff. (The set engine *would* slow
for a query over a single huge group — a group with 100k direct members makes that
group's check O(members) — but that's local fan-in, not total tuple count.)

**2. The graph index is O(1) per check but ~25–50× slower in absolute terms here.**
Graph check is depth- and size-independent by construction (the closure is
materialized, so `check` is a bounded number of point lookups), which is why it's
also flat. But each point lookup is a Python → SQLAlchemy → SQLite round-trip
(~1–4 ms), while the set engine answers from in-process roaring bitmaps with no I/O
boundary. On a single machine with in-memory SQLite, in-RAM bitmaps beat
per-probe DB round-trips almost regardless of algorithmic complexity — so the set
engine wins raw throughput 415→20.7k (gdrive) and 598→14.9k (demorgans).

**3. The trade is at write time.** The graph pays its memoization up front: build
runs at **15–51 writes/s** (closure materialization, plus a full `backfill()`
reconcile of every derived key for boolean schemas) versus the set engine's
**~750–800 writes/s** — 15–50× slower to load. That's the memoization spectrum
working exactly as designed: the graph moves cost from read time to write time and
storage; the set engine keeps writes cheap and pays at read time.

**4. RAM is ~linear in tuples for the set engine: ≈0.9–1.2 KB per raw tuple.**
gdrive: 161 MB of data for 134k tuples (1.2 KB/tuple). demorgans: 150 MB for 163k
tuples (0.9 KB/tuple). So a **1,500-doc demorgans store (163k tuples) fits in ~238
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
