# Round-4 perf comparison — 2026-07-16

Fresh benchmark pass after round 4 landed (R4-BF, N15, N16, M2 + follow-up, N17,
N10, N18, the index_v4 grab-bag micros, N12; N11 design-skipped). Two harnesses:
`benchmarks.stmt_bench` (statements-per-op over a real `ConnectedStore`) and
`benchmarks.bulk_scale_bench` (set-engine rebuild/read curve — the N10 headline
surface). Raw new rows: [`round4_scale_2026-07-16.jsonl`](round4_scale_2026-07-16.jsonl)
(4 set:roaring rows). Statement counts reproduce
[`STMT_BASELINE_2026-07-14.md`](STMT_BASELINE_2026-07-14.md) addendum 3 exactly.

## ⚠ Read this first — conditions caveat (same shape as the M2 follow-up's)

- **Absolute rates and wall times are NOT cross-session comparable.** Different
  memory pressure between sessions shifts every absolute number. The M2 follow-up
  session (2026-07-15) ran at ~2.1–2.5 GB free of 15.8 GB under heavy pressure (it
  swapped); **this session ran at ~2.67–2.69 GB free of 15.82 GB** — lighter, no
  swap. So where a round-4 baseline was captured in the M2 follow-up, **lead with
  the rebuild-time RATIO at matching workload/scale, flag it cross-session, and
  defer to same-session isolated measurements** (PERF_ANALYSIS "Applied") for the
  clean per-item figure.
- **Same-session-comparable signals in this doc:** peak RSS at matching
  workload/scale (RSS tracks state size, which round-4 opts don't change); the
  **flatness** of the gdrive owc `lookup` curve *within* this session (the N17
  headline, session-invariant shape); and `answers_sig` byte-identity.
- **Not same-session comparable:** any rate/wall compared against the M2 follow-up
  or round-3 jsonl — those ran in different sessions. Called out inline each time.

Free physical memory (`Win32_OperatingSystem.FreePhysicalMemory`) recorded before
each ≥100 k row (and at session start):

| point | free RAM |
|---|--:|
| session start | 2.68 GB |
| before gdrive set 12000 (201,600) | 2.69 GB |
| before simple set 50000 (200,000) | 2.67 GB |

One bench/pytest process at a time, strictly sequential; every scale row ran alone.

---

## 1. Landed-item headline table

item → headline number → where measured. **"this run"** = re-measured here;
**"cited"** = the item's own landing measurement (not re-run this pass).

| item | headline | source | comparability |
|---|---|---|---|
| **N10** lazy flow-graph off `rebuild()` | gdrive 201.6 k set `rebuild()` **22.00 → 7.66 s**; simple 200 k **13.69 → 7.87 s** | **this run** vs M2 follow-up (pre-N10) | cross-session — see §2; clean same-session N10 = **4.99 → 1.26 s (4.0×)** at 67.2 k (cited, PERF_ANALYSIS) |
| **N17** sub-O(store) owc `lookup` | gdrive 201.6 k set `lookup` **0.16 → 238.7 /s**; flat 245 / 227 / 239 /s across 16.8 k → 201.6 k | **this run** vs M2 follow-up (pre-N17) | 3-orders-of-magnitude gap dwarfs the session factor; the **flat curve** is session-invariant (§2) |
| **N18** bulk-build RAM ceiling | gdrive 201.6 k graph peak RSS **3,512 → 1,117 MB (−68 %, 3.14×)**; build 390.5 → 314.2 s | cited — [`N18_FOLLOWUP_2026-07-16.md`](N18_FOLLOWUP_2026-07-16.md) | RSS is same-workload comparable; graph 200 k **not** re-run (per brief) |
| **grab-bag** micros | union add total **38.2 → 36.6** stmts (node_v4 10.96 → 9.30); boolean add **137.7 → 130.9** (node_v4 46.66 → 39.90) | **this run** (stmt_bench) reproduces `STMT_BASELINE` addendum 3 exactly | deterministic (statement counts, contention-immune) |
| **N12** cache `EntityPattern`s | `RuleSet.apply` gdrive fixture **155 → 73.5 ms (2.1×)** | cited — PERF_ANALYSIS "Applied" | isolated micro; end-to-end write loop flat (apply is a tiny fraction) |
| **N15** per-batch node cache | boolean add node_v4 **103.4 → 46.7 /write (−55 %)** | cited — `STMT_BASELINE` addendum 2 | deterministic stmt count |
| **N16** bulk-INSERT outbox rows | union add INSERT **20.4 → 13.0**; boolean add **40.8 → 28.5** | cited — `STMT_BASELINE` addendum | deterministic stmt count |
| **R4-BF** bulk boolean backfill | boolean *total* build **~201×** (demorgans) / ~60× (boolean_wildcards) | cited — PERF_ANALYSIS "Applied" | own landing measurement |
| **M2** scale-bench verdict | graph's one read-side niche = owc forward `lookup` (~1,066× at 200 k); set wins everywhere else | cited — [`M2_FOLLOWUP_2026-07-15.md`](M2_FOLLOWUP_2026-07-15.md) | verdict final |

---

## 2. Set-engine rebuild + read curve (this run) — the N10 + N17 surfaces

All four rows are `gdrive`/`simple` set:roaring via `bulk_scale_bench` (rebuild on
the same seeded store, then reads), same harness as the M2 follow-up.

| workload | tuples | rebuild_s | peak RSS | check /s | **lookup /s** | reverse /s | answers_sig |
|---|--:|--:|--:|--:|--:|--:|---|
| gdrive | 16,800 | 0.53 | 132 MB | 12,792.9 | 244.9 | 2,455.8 | `d9ddd99d…9999` |
| gdrive | 67,200 | 2.28 | 344 MB | 12,407.9 | 226.5 | 1,723.2 | `d9ddd99d…9999` |
| gdrive | 201,600 | 7.66 | 915 MB | 12,449.7 | **238.7** | 2,554.1 | `d9ddd99d…9999` |
| simple | 200,000 | 7.87 | 907 MB | 52,059.2 | 13,111.5 | 25,819.1 | `db6db6…6db` |

### N10 — `rebuild()` at matching workload/scale (cross-session)

| workload | tuples | M2 fu rebuild_s (2026-07-15, **pre-N10**) | this run (2026-07-16, **post-N10**) | peak RSS m2fu → this run |
|---|--:|--:|--:|--:|
| gdrive | 201,600 | 22.00 | **7.66** (2.87×) | 916 → 915 MB (flat) |
| simple | 200,000 | 13.69 | **7.87** (1.74×) | 907 → 907 MB (flat) |

**Honest reading.** The M2 follow-up set rebuild rows predate N10 (N10 = `422c5b9`,
2026-07-16; the M2 follow-up bench = `34e1f81`, 2026-07-15), so both drops fold in
N10 *and* a lighter-memory session. They are **cross-session — do not read the ratio
as pure N10.** The clean N10 figure is the same-session isolated **4.99 → 1.26 s
(4.0×)** at gdrive 67.2 k in PERF_ANALYSIS "Applied" (flow-graph fan-out was 74.8 %
of the eager rebuild wall). The cross-session ratios here are *directionally
consistent* and split exactly as the mechanism predicts: **gdrive (heavy TTU/rewrite
fan-out → large write-only flow graph → 2.87×) moves far more than simple
(direct-only → negligible flow graph → 1.74×, mostly the session-pressure
difference).** Peak RSS is same-workload comparable and is **flat** at both scales —
N10 defers only *write-only auxiliary* state that the read-only bench never builds,
so final state size is unchanged, exactly as intended.

### N17 — owc `lookup` no longer sweeps O(store) (this run)

The M2 follow-up measured gdrive 201.6 k **set** `lookup` at **0.16 /s** (the
pre-N17 O(store) sweep, `graph_scale_m2fu_2026-07-15.jsonl` row 10). This run, at
the identical workload/scale, measures **238.7 /s** — and the curve is **flat**
across scale (244.9 / 226.5 / 238.7 /s over 16.8 k → 67.2 k → 201.6 k), the O(1)
shape N17 delivered (`n17_scale_2026-07-15.jsonl` measured the same flat 207–224 /s
band up to 168 k). The M2 follow-up bench (`34e1f81`) predates N17 (`b7e9a75`), so
this is a same-workload/scale before/after. The absolute rate is not cross-session
comparable, but a **0.16 → 238.7 /s** gap (~1,490×) is three orders of magnitude —
far beyond any session factor — and the **within-session flatness** is the
session-invariant proof. `check`/`reverse` on gdrive are flat too (~12.4 k / ~1.7–2.6 k
/s); `simple` reads are the wildcard-free flat-and-fast band (check 52 k, lookup
13 k, reverse 26 k /s).

### Absent-baseline note (gdrive 16.8 k / 67.2 k)

Neither 16.8 k nor 67.2 k has a matching set:roaring row in
`graph_scale_m2fu_2026-07-15.jsonl` (its gdrive set point is 201.6 k only). Closest
references, cross-session (shape only, not a clean ratio): round-3
`graph_scale_2026-07-15.jsonl` gdrive set `rebuild()` was 5.49 s @50.4 k / 10.9 s
@100.8 k (pre-N10); the N10 same-session isolation at 67.2 k was 4.99 → 1.26 s. This
run's 2.28 s @67.2 k is post-N10 in a lighter session — consistent with lazy rebuild
being fast, but not a clean cross-session ratio.

---

## 3. Statement counts (this run) — reproduce `STMT_BASELINE` addendum 3

`benchmarks.stmt_bench`, real `ConnectedStore`, sync, `paranoia=off`. Every count
below is **byte-identical** to `STMT_BASELINE_2026-07-14.md` addendum 3 — the
round-4 stmt-affecting items (N16, N15, grab-bag) had already been recorded there,
and this pass confirms no drift. **No new addendum was written** (counts did not
move from addendum 3).

| op | stmts/op | node_v4 SELECT/op | INSERT/op | store_v4 SELECT/op |
|---|--:|--:|--:|--:|
| union add_tuple | 36.6 | 9.30 | 13.0 | 1.00 |
| union remove_tuple | 29.6 | — | 2.2 | 1.00 |
| union check | 2.7 | — | — | — |
| union lookup | 3.0 | — | — | — |
| union lookup_reverse | 2.9 | — | — | — |
| boolean add_tuple | 130.9 | 39.90 | 28.5 | 1.00 |
| boolean remove_tuple | 113.6 | — | 7.2 | 1.00 |
| boolean check | 3.1 | — | — | — |
| boolean lookup | 5.0 | — | — | — |
| boolean lookup_reverse | 4.8 | — | — | — |

Round-4 stmt-per-op movement (cumulative, from the pre-N16 post-round-3 floor,
per the `STMT_BASELINE` addenda; deterministic — contention-immune):

- **union add_tuple total: 46.2 → 38.9 (N16) → 38.2 (N15) → 36.6 (grab-bag).**
  node_v4 SELECT 11.62 → 10.96 (N15) → 9.30 (grab-bag).
- **boolean add_tuple total: 194.4 → 137.7 (N15) → 130.9 (grab-bag).** node_v4
  SELECT 103.42 → 46.66 (N15) → 39.90 (grab-bag). INSERT 40.8 → 28.5 (N16).
- `store_v4` SELECT/write is 1.00 both schemas (P12a memo, round 3); `tuple_log_v1`
  SELECT/write is 0.00 (P12b handoff, round 3). Read ops (check/lookup/reverse)
  unchanged from round 3.

---

## 4. Cross-backend agreement — clean

Every row's `answers_sig` matches the established value for its workload:
gdrive `d9ddd99d…9999` (matches the M2 follow-up + N18 follow-up gdrive value at
201.6 k, and holds at 16.8 k / 67.2 k here); simple `db6db6…6db` (matches the M2
follow-up simple 200 k). No correctness alarm.

---

## 5. Reproduce

```bash
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"

# (1) statements-per-op (real ConnectedStore) — reproduces STMT_BASELINE addendum 3
"$PY" -m benchmarks.stmt_bench

# (2) set-engine rebuild + read curve — NEW jsonl, existing results untouched.
#     Run each row ALONE, sequentially; record free RAM before each >=100k row:
#       powershell "Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory"
OUT=round4_scale_2026-07-16.jsonl
"$PY" -m benchmarks.bulk_scale_bench --workload gdrive --scale 1000  --backend set --json --out $OUT
"$PY" -m benchmarks.bulk_scale_bench --workload gdrive --scale 4000  --backend set --json --out $OUT
"$PY" -m benchmarks.bulk_scale_bench --workload gdrive --scale 12000 --backend set --checks 2000 --lookups 200 --time-box 10 --json --out $OUT
"$PY" -m benchmarks.bulk_scale_bench --workload simple --scale 50000 --backend set --checks 2000 --lookups 200 --time-box 10 --json --out $OUT
```

The graph-side N18 200 k anchor was **not** re-run — it is cited from
[`N18_FOLLOWUP_2026-07-16.md`](N18_FOLLOWUP_2026-07-16.md) (peak RSS 3,512 →
1,117 MB). No production code, tests, or existing results files were modified this
session — only `round4_scale_2026-07-16.jsonl` (new) and this report were created.
