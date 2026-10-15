# `TK150` -- what one write that creates N closure rows costs the graph index (2026-10-14)

**ACTIVE-PLAN** (`docs/README.md` sec 3). Corrections are appended dated at the top, never
edited into the body. FROZEN when `TK150` closes. The task row is the index
(`python scripts/task.py show TK150`); this file is the body.

Provenance labels: **PROBE** (a benchmark run this session; its raw record is a line of
`benchmarks/results/fanout_cost_2026-10-14.jsonl`), **READ** (code read first-hand this
session), **REASONED**. Every figure is as of 2026-10-14 on the machine below, measured by
the `bench-fanout` agent; re-measure with the script rather than differencing against
these numbers.

## 0. The question

User, 2026-10-14: "run a test on ZANZIBAR_MAX_CLOSURE_FANOUT to see what the cost is for
10k, 100k, 1m, maybe higher if its reasonably fast, so we can quantify the cost to the
index". The cap (`src/zanzibar/graphindex/core.py::DEFAULT_MAX_CLOSURE_FANOUT`, 100,000)
bounds how many closure rows ONE sync write may materialise. This doc puts a price on one
such write, so the cap can be chosen from a table instead of a guess.

## 1. What the cap counts (READ 2026-10-14)

- `core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` reads the subject's ancestor
  set A and the object's descendant set D (two `SELECT`s over `Edge`), then computes
  `fanout = |A| x |D| + |A| + |D|` and refuses (`ClosureFanoutExceeded`) when
  `fanout > max_closure_fanout`, BEFORE materialising anything. The cap is strict `>`, so
  a write of exactly 100,000 rows is admitted at the default.
- The cap is resolved once per `ReachabilityIndex` (`resolve_max_closure_fanout`:
  constructor argument > `ZANZIBAR_MAX_CLOSURE_FANOUT` > default; `0` disables).
- It is a SYNC-ADMISSION bound only: `ConnectedStore.catch_up` and the non-bulk
  `build_index` run inside `fanout_cap_suspended`, the bulk constructor never reaches it,
  and removals are never capped (`TK112`; `docs/tk111-stall-aware-freshness-2026-10-02.md`
  sec 7).
- After the check, `_add_indirect_edges_batch_unsafe` reads the whole region in chunks of
  400 pairs, builds one ORM `Edge` per new pair (`session.add`), and `_emit`s one
  `DeltaOutbox` row per new pair. So **every closure row is also one outbox row**, and
  every new row is a live ORM object in the session until the flush.
- A refusal on the sync path escapes `advance_index` inside the second `try` of
  `connectedstore/store.py::ConnectedStore._write`, i.e. the generic `except Exception`
  arm, which rolls back AND calls `source.refresh_evaluator()` (a whole set-engine
  rebuild from `RelationTuple`). The refusal therefore costs O(store) on top of the two
  O(|A| + |D|) reads. Measured in sec 4.

## 2. Method (the script is `benchmarks/fanout_cost_bench.py`)

- **Path measured:** the user-facing sync `ConnectedStore.add_tuple` and `remove_tuple`
  on a SQLite FILE database (`sqlite:///<tmp>/fan_*.db`, default rollback journal), one
  write per process. PostgreSQL: sec 5.
- **Precondition, not measured:** raw tuples bulk-inserted as `RelationTuple` rows plus
  matching `TupleLog` ADD rows (so `ConnectedStore`'s `TK140` adoption check sees a fully
  logged store), then `build_index(session, store, bulk=True)` (the P13 offline
  constructor, never capped), then `ConnectedStore(session, store, paranoia=...)`.
- **Shapes** (schema in the script; `doc.viewer: [user, group#member] or viewer from parent`):
  - `userset`: `group:g` has N members; write `group:g#member viewer doc:d` (|A| = N, |D| = 0).
  - `object`: N docs with `parent folder:f`; write `user:u viewer folder:f` (|A| = 0, |D| = N).
  - `product`: a members and d docs, a = d = round(sqrt(N)); write
    `group:g#member viewer folder:f` (a*d + a + d rows from only a + d stored tuples).
- **Per point:** wall time of the write and a phase breakdown (instrumented wrappers,
  window only: `admit` = `TupleSource.add`, `apply` = `advance_index`, `expand` =
  `_add_direct_edge_unsafe_impl`, `batch` = `_add_indirect_edges_batch_unsafe`, `ORM
  flush` = SQLAlchemy flush events, `outbox` = `_flush_outbox`, `commit`; `sql exec`
  overlaps the others); `Edge` and `DeltaOutbox` rows added (counted before and after);
  DB file bytes added; the write's peak working set minus the working set just before
  it (a 20 ms sampler thread; the process-lifetime peak is also recorded); removal time
  of the same tuple; median `check` latency over 300 calls before, after, and after the
  removal. Each point ASSERTS the probe answer flips (False -> True -> False), so a
  benchmark that silently measured nothing fails.
- **Load:** every record carries the count of `python.exe` / `lean.exe` / `lake.exe` /
  `postgres.exe` processes and system CPU busy % before, during and after; other agents
  share this laptop.
- **Safety:** a watchdog aborts a point when system available memory drops below
  1.5 GB (sabotage-checked: with the threshold set to 9,999,999 MB the point exits rc=3 at
  0.9 s and the driver deletes its DB file); bench DB files are deleted after every point.
- **Reps:** 3 per point up to 100k on SQLite, 1 above that and 1 on PostgreSQL. The
  `report` subcommand prints the median, and the raw records keep every rep. Points the
  watchdog stopped are kept in the JSONL with an `aborted` field and excluded from the
  tables.
- **Machine:** Windows 11 Pro, Intel i7-1365U (12 logical CPUs), 31.6 GB RAM (about
  6-8 GB available during the runs), Python 3.13.14, SQLAlchemy 2.0.51, SQLite 3.53.2.

## 3. Results, SQLite file (PROBE 2026-10-14, 17:15-18:20 local)

Generated by `python -m benchmarks.fanout_cost_bench report
benchmarks/results/fanout_cost_2026-10-14.jsonl`, median over `reps`. Columns: `write s` is
the wall time of the one `add_tuple` (admission + index + commit). `closure rows` and
`outbox rows` are `Edge` / `DeltaOutbox` rows counted before and after; the extra 1 is the
direct edge itself. `MB added` is DB file growth, and `us/row` = write s / closure rows.
`peak delta MB` is the write's peak working set minus the working set just before it.
`remove s` is `remove_tuple` of the same tuple. `check us` is the median
`ConnectedStore.check` before and after the write. `load` is the count of `python.exe`
processes on the machine and the system-wide CPU busy % during the write. This benchmark's
driver and point are 2 of the python processes, so ~7 belonged to other agents. The writer
is one of 12 logical CPUs (~8 %), so 30-60 % busy means other agents were working. The
`lean` / `lake` / `postgres` counts were 0 for every SQLite point.

| backend | shape | N | mode | paranoia | reps | write s | expand s | ORM flush s | closure rows | outbox rows | MB added | us/row | peak delta MB | KB/row RAM | remove s | check us before/after | load: py procs, CPU% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sqlite-file | userset | 10,000 | admit | off | 3 | 3.12 | 2.63 | 0.87 | 10,001 | 10,001 | 1.2 | 311.5 | 68 | 6.91 | 1.52 | 940 / 2,194 | 10, 44 |
| sqlite-file | object | 10,000 | admit | off | 3 | 3.36 | 2.69 | 0.94 | 10,001 | 10,001 | 1.2 | 336.3 | 61 | 6.24 | 1.53 | 826 / 2,044 | 10, 46 |
| sqlite-file | product | 10,000 | admit | off | 3 | 2.40 | 2.14 | 0.82 | 10,201 | 10,201 | 1.2 | 235.2 | 48 | 4.83 | 1.10 | 1,603 / 2,166 | 9,10, 36 |
| sqlite-file | userset | 100,000 | admit | off | 3 | 36.85 | 32.22 | 10.36 | 100,001 | 100,001 | 13.7 | 368.5 | 824 | 8.43 | 18.37 | 1,056 / 2,133 | 9,10, 53 |
| sqlite-file | object | 100,000 | admit | off | 3 | 37.00 | 30.96 | 9.63 | 100,001 | 100,001 | 13.8 | 370.0 | 802 | 8.21 | 18.26 | 899 / 2,002 | 10, 49 |
| sqlite-file | product | 100,000 | admit | off | 3 | 26.80 | 24.62 | 9.45 | 100,489 | 100,489 | 12.8 | 266.7 | 456 | 4.65 | 12.12 | 1,783 / 2,054 | 10, 51 |
| sqlite-file | userset | 300,000 | admit | off | 1 | 94.05 | 81.76 | 24.04 | 300,001 | 300,001 | 41.5 | 313.5 | 2,525 | 8.62 | 49.70 | 890 / 1,986 | 9, 31 |
| sqlite-file | object | 300,000 | admit | off | 1 | 105.63 | 86.97 | 26.24 | 300,001 | 300,001 | 41.6 | 352.1 | 2,507 | 8.56 | 54.49 | 792 / 1,860 | 9, 41 |
| sqlite-file | product | 300,000 | admit | off | 1 | 90.53 | 83.69 | 39.96 | 301,401 | 301,401 | 38.8 | 300.4 | 1,371 | 4.66 | 54.43 | 2,204 / 1,779 | 9, 48 |
| sqlite-file | product | 1,000,000 | admit | off | 1 | 271.84 | 250.75 | 113.05 | 1,002,001 | 1,002,001 | 130.8 | 271.3 | 4,514 | 4.61 | 132.66 | 1,877 / 1,836 | 9, 30 |
| sqlite-file | userset | 10,000 | admit | full | 3 | 6.82 | 2.68 | 0.84 | 10,001 | 10,001 | 1.2 | 681.4 | 93 | 9.51 | 5.19 | 891 / 1,904 | 10, 44 |
| sqlite-file | userset | 100,000 | admit | full | 3 | 74.28 | 28.25 | 8.78 | 100,001 | 100,001 | 13.7 | 742.8 | 1,048 | 10.73 | 54.48 | 864 / 2,155 | 9, 36 |
| sqlite-file | userset | 10,000 | admit | residue | 3 | 3.37 | 2.88 | 0.89 | 10,001 | 10,001 | 1.2 | 336.6 | 65 | 6.65 | 1.50 | 1,011 / 2,003 | 10, 54 |
| sqlite-file | userset | 100,000 | admit | residue | 3 | 34.10 | 29.85 | 9.40 | 100,001 | 100,001 | 13.7 | 341.0 | 826 | 8.45 | 17.08 | 843 / 1,850 | 9,10, 44 |

**Not measured, with reason (PROBE):** `userset` and `object` at N = 1,000,000. Both were
started, and the memory watchdog stopped both (system available memory under 1.5 GB):

- `userset` 1M: the precondition built (seed 41.8 s, bulk build 325.3 s, open 33.3 s).
  The watchdog stopped the write **168.8 s in, with the writer at 6,756 MB working set**,
  still expanding. Available memory at the point's start was 3.7 GB, because of other agents.
- `object` 1M: stopped **during the bulk build** of the 1M-doc precondition (317.6 s in,
  6,458 MB), before the measured write. The offline bulk constructor itself needs more
  than ~6.5 GB for 1M TTU-routed tuples.
- Linear extrapolation from the 300k points (REASONED): ~310-350 s and ~8.6 GB for one
  1M-row `userset` / `object` write.

**N = 10,000,000 was not run** (REASONED from the table). The writer needs 4.6-8.6 KB of
RAM per closure row, so one 10M-row write needs 46-86 GB, and this machine has 31.6 GB. At
~270 us/row it would also take ~45 min. Disk would NOT have been the limit (~130 B/row,
~1.3 GB). The task's bar for going higher (~3 min, ~3 GB) was already missed at 1M: 272 s
and 4.5 GB for the cheapest shape.

### 3a. Where the time goes (PROBE, paranoia off, median)

`expand` is `_add_direct_edge_unsafe_impl`: the two reachability reads, the region node
load, the batch and the direct edge. `batch` is `_add_indirect_edges_batch_unsafe`: the
chunked region read, plus one ORM `Edge` and one outbox dict per new pair. The ORM flush
(the actual INSERTs) happens inside `advance_index` (autoflush), so `commit` itself is near
zero. `admit` is the set engine's admission in `TupleSource.add`, not the graph index.

| N | shape | write s | admit (set engine) s | expand s | of which batch s | ORM flush s | outbox insert s | commit s | disk B/row | DB bytes left after remove |
|---|---|---|---|---|---|---|---|---|---|---|
| 10,000 | userset | 3.12 | 0.20 | 2.63 | 1.32 | 0.87 | 0.25 | 0.018 | 123 | 1.6 MB |
| 10,000 | object | 3.36 | 0.38 | 2.69 | 1.32 | 0.94 | 0.23 | 0.028 | 125 | 1.6 MB |
| 10,000 | product | 2.40 | 0.02 | 2.14 | 1.31 | 0.82 | 0.21 | 0.011 | 120 | 1.4 MB |
| 100,000 | userset | 36.85 | 2.01 | 32.22 | 15.66 | 10.36 | 2.53 | 0.059 | 137 | 17.1 MB |
| 100,000 | object | 37.00 | 3.94 | 30.96 | 14.61 | 9.63 | 2.34 | 0.054 | 138 | 16.8 MB |
| 100,000 | product | 26.80 | 0.04 | 24.62 | 14.60 | 9.45 | 2.23 | 0.019 | 127 | 14.5 MB |
| 300,000 | userset | 94.05 | 5.85 | 81.76 | 40.00 | 24.04 | 6.37 | 0.030 | 138 | 52.1 MB |
| 300,000 | object | 105.63 | 11.89 | 86.97 | 42.27 | 26.24 | 6.65 | 0.093 | 139 | 50.8 MB |
| 300,000 | product | 90.53 | 0.04 | 83.69 | 43.11 | 39.96 | 6.72 | 0.068 | 129 | 44.1 MB |
| 1,000,000 | product | 271.84 | 0.07 | 250.75 | 136.17 | 113.05 | 20.99 | 0.019 | 131 | 147.4 MB |

- **The graph index is ~90 % of the write** at every size, and it is linear: 235-370 us
  per closure row from 10k to 1M on SQLite. For `product`, 10k -> 1M is 100x the rows and
  113x the time. No superlinear knee appeared before the memory wall.
- **The set engine's admission is also O(|A| + |D|)** for the `userset` / `object` shapes
  (~20-40 us per member or doc: 2.0 s at 100k, 5.8-11.9 s at 300k). It is ~0 for `product`.
- **Removal takes ~half as long as the add**: 1.1-1.5 s at 10k, 12-18 s at 100k, 50-54 s
  at 300k, 133 s at 1M. It needs ~2/3 of the add's memory. Removals are never capped.
- **Disk:** 120-139 bytes per closure row (`Edge` row + `DeltaOutbox` row + indexes).
  The DB file does not shrink after the removal; it ends ~1.1x the added bytes larger.
  REASONED from `_add_indirect_edges_batch_unsafe`: the removal emits one `REMOVED`
  outbox row per pair. So one add+remove of an N-row fan-out leaves 2N outbox rows until
  `zanzibar.graphindex.outbox.prune_outbox` runs (it is never auto-called), plus SQLite
  free pages.
- **Memory:** ~4.6 KB per NEW closure row. That is `product`, where |A| + |D| is tiny: one
  ORM `Edge`, one outbox dict and identity-map entries per row. Add ~3.8 KB per ancestor
  or descendant LOADED. That is `userset` / `object`, where |A| + |D| = N and their `Edge`
  and `Node` rows are loaded as ORM objects too. So the total is 4.6-8.6 KB per closure
  row, all held in one session until the commit.
- **`check` latency does not depend on N:** 0.8-2.2 ms median through `ConnectedStore.check`
  on a file DB at every size, before and after (a positive answer ~2 ms, a negative ~1 ms).
  The cost of a large fan-out is paid entirely by the write.

### 3b. Paranoia multiplier (PROBE, `userset`, 3 reps)

| N | paranoia | write s | x off | remove s | x off | peak delta MB |
|---|---|---|---|---|---|---|
| 10,000 | off | 3.12 | 1.0 | 1.52 | 1.0 | 68 |
| 10,000 | residue | 3.37 | 1.08 | 1.50 | 0.99 | 65 |
| 10,000 | full | 6.82 | 2.19 | 5.19 | 3.41 | 93 |
| 100,000 | off | 36.85 | 1.0 | 18.37 | 1.0 | 824 |
| 100,000 | residue | 34.10 | 0.93 | 17.08 | 0.93 | 826 |
| 100,000 | full | 74.28 | 2.02 | 54.48 | 2.97 | 1,048 |

`ConnectedStore.DEFAULT_PARANOIA` is `off`. Here `residue` (the recommended production
level) is within noise of `off`, because this schema has no boolean relation and so no
residue rows to scan. On a boolean schema it costs more: the class docstring measured
+4-6 % on a 162/478-write workload. `full` doubles the write and triples the removal. Its
pre- and post-commit sweep is O(store): `commit` alone is 3.6 s at 10k.

## 4. The refusal path (PROBE 2026-10-14, default cap 100,000)

Same harness with `--mode refuse`: the env var is unset, so the cap is the default. Every
row was refused with `ClosureFanoutExceeded` and left zero `Edge` rows, zero outbox rows
and zero bytes.

| backend | shape | N | mode | paranoia | reps | write s | expand s | ORM flush s | closure rows | outbox rows | MB added | us/row | peak delta MB | KB/row RAM | remove s | check us before/after | load: py procs, CPU% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sqlite-file | userset | 100,001 | refuse | off | 1 | 8.39 | 2.30 | 0.01 | 0 | 0 | 0.0 | - | 352 | - | - | 832 / 968 | 9, 30 |
| sqlite-file | product | 100,001 | refuse | off | 1 | 0.04 | 0.01 | 0.00 | 0 | 0 | 0.0 | - | 0 | - | - | 1,161 / 962 | 9, 31 |
| sqlite-file | userset | 1,000,000 | refuse | off | 1 | 90.92 | 23.70 | 0.01 | 0 | 0 | 0.0 | - | 3,828 | - | - | 897 / 784 | 9, 38 |
| sqlite-file | product | 1,000,000 | refuse | off | 1 | 0.18 | 0.03 | 0.01 | 0 | 0 | 0.0 | - | 0 | - | - | 1,837 / 1,819 | 9, 46 |

| shape | N | refused in | admit (set engine) | expand (reads before the count) | `refresh_evaluator` | peak delta |
|---|---|---|---|---|---|---|
| userset | 100,001 | 8.39 s | 1.85 s | 2.30 s | 3.50 s | 352 MB |
| userset | 1,000,000 | **90.92 s** | 19.52 s | 23.70 s | **39.75 s** | **3,828 MB** |
| product (316 x 316) | 100,001 | 0.04 s | 0.02 s | 0.01 s | 0.01 s | 0 MB |
| product (1000 x 1000) | 1,000,000 | 0.18 s | 0.07 s | 0.03 s | 0.05 s | 0 MB |

**The cap bounds what is WRITTEN, not what a refused write COSTS.** A refusal costs
O(|A| + |D|) + O(store), not O(fanout):

1. READ: `core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` builds the ancestor and
   descendant multisets by loading every `Edge` row of both as ORM objects, and only then
   counts. For `product` that is 2,000 rows, which is cheap. For a 1M-member group it is
   1M rows: 23.7 s and most of the 3.8 GB.
2. READ: the refusal escapes `advance_index` inside the second `try` of
   `connectedstore/store.py::ConnectedStore._write`. That block's generic
   `except Exception` arm calls `self.source.refresh_evaluator()`, which rebuilds the whole
   set engine from `RelationTuple` (39.8 s for a 1M-tuple store). It has to: admission
   (`source.add`) already put the tuple into the in-memory evaluator before the index
   refused it.
3. The set engine's own admission is O(|A| + |D|) for these shapes (19.5 s at 1M).

So the cap does what it says when the fan-out is the PRODUCT of two moderate sets. A write
whose own ancestor or descendant set is huge is slow to refuse, and the refusal holds both
locks for the whole time, just as an admitted write would.

## 5. PostgreSQL (PROBE 2026-10-14, 18:37-18:48 local)

The server was `scripts/pg_local.sh start` (PostgreSQL 17.10, conda env `zanzibar-pg`, on
the same laptop, at READ COMMITTED). The run used a dedicated database
`zanzibar_fanout_bench`, so a concurrent test run on `zanzibar_test` could not collide with
it. That database was dropped afterwards, and the server was stopped and confirmed stopped
(`pg_local: not running`, no `postgres.exe` left). There was 1 rep per point. `MB added`
is `pg_database_size` growth (heap + indexes), and the 6 `postgres` processes in `load`
are the server's own.

| backend | shape | N | mode | paranoia | reps | write s | expand s | ORM flush s | closure rows | outbox rows | MB added | us/row | peak delta MB | KB/row RAM | remove s | check us before/after | load: py procs, CPU% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| postgresql | userset | 10,000 | admit | off | 1 | 3.89 | 3.15 | 1.33 | 10,001 | 10,001 | 2.7 | 388.7 | 69 | 7.10 | 6.03 | 5,351 / 2,172 | 9, 24 |
| postgresql | product | 10,000 | admit | off | 1 | 2.57 | 2.01 | 0.88 | 10,201 | 10,201 | 2.7 | 251.7 | 50 | 5.07 | 6.21 | 1,181 / 2,228 | 9, 28 |
| postgresql | userset | 100,000 | admit | off | 1 | 42.04 | 34.71 | 13.05 | 100,001 | 100,001 | 28.3 | 420.4 | 831 | 8.51 | 68.82 | 1,262 / 2,328 | 9, 36 |
| postgresql | product | 100,000 | admit | off | 1 | 33.96 | 28.20 | 12.30 | 100,489 | 100,489 | 27.2 | 337.9 | 481 | 4.90 | 80.84 | 2,421 / 2,760 | 9, 29 |

- **The write costs about the same as on SQLite**, 1.05-1.27x: 2.6-3.9 s at 10k and
  34-42 s at 100k. The client-side memory per row is the same (4.9-8.5 KB/row), because
  the ORM objects live in the writer whatever the backend. Disk is ~2x SQLite's, at
  ~270-280 bytes/row.
- **Removal is 4-7x slower than on SQLite**: 6 s at 10k, and 69-81 s at 100k against
  12-18 s. In the phase breakdown, `sql_exec` is 55-71 s of it: the chunked region
  `SELECT`s and the per-row deletes. **Removals are never capped (by design, `TK112`)**,
  so on PostgreSQL the removal of a 100k fan-out holds the store lock about twice as long
  as its admission did.
- **`product` at 1M was not measured on PostgreSQL.** The memory watchdog stopped it
  286.5 s into the write, with the client at 4,853 MB and the server also holding memory
  on the same machine. The same write on SQLite took 272 s and 4.5 GB in total.
- `userset` / `object` at 1M were not attempted on PostgreSQL, since they already exceeded
  the available memory on SQLite (sec 3), and that memory is spent client-side.

## 6. Conclusions

- **Cost per closure row (PROBE, this laptop, paranoia off):** ~270-370 us of writer time,
  ~4.6-8.6 KB of writer RAM, ~130 bytes of disk and one `DeltaOutbox` row. Removal takes
  about half the time. `full` paranoia doubles the write and triples the removal.
- **It scales linearly** in the closure rows written, from 10k to 1M (sec 3a), with no
  knee before the memory wall. Reads (`check`) are flat in N.
- **The limiting resource is the WRITER'S MEMORY**, then wall time (which is how long the
  store write lock is held), and disk last. The whole region is held as ORM objects in one
  session, so a 1M-row write needs 4.5-8.6 GB in the writer process. Two of the three 1M
  shapes could not finish in the ~4-8 GB this shared laptop had free. Disk at 1M is only
  ~130 MB.
- **At the current default (100,000)**, one admitted sync write costs ~27-37 s of store
  write-lock hold and 0.45-0.85 GB of writer RAM on this machine. Under `full` paranoia it
  is 74 s and 1 GB. Every other writer on the store waits that whole time: as the cap's
  own docstring says, the write runs inside `advance_index` holding both the source lock
  and the graph store lock.
- **PostgreSQL** (sec 5) costs about the same for the write (1.05-1.27x) and the same
  client RAM. Its uncapped REMOVAL is 4-7x slower than SQLite's: 69-81 s at 100k, longer
  than the capped add it undoes.
- **The refusal is not free** when the fan-out comes from one huge side (sec 4). Refusing
  the grant of a 1M-member group took 91 s and 3.8 GB. Most of that was reads before the
  count and the set-engine rebuild after it.

## 7. Recommendation on the default cap (REASONED)

**Lower `DEFAULT_MAX_CLOSURE_FANOUT` from 100,000 to 10,000.**

- The cap is a blast-radius bound on a SYNC write that holds the store's write locks for
  its whole expansion. At 100,000 that measured as a ~30-37 s lock hold and up to ~0.85 GB
  in one writer, which is not a bound an interactive service would choose. At 10,000 it
  measured as 2.4-3.4 s and 50-70 MB.
- It still cannot refuse anything this repo writes. The docstring's census (2026-07-27)
  puts the largest single-write expansion at 124 rows, so 10,000 leaves ~80x headroom.
- What it refuses that 100,000 admitted: a sync grant whose closure is between 10,001 and
  100,000 rows, e.g. sharing one object with a 20,000-member group. Such writes stay
  possible in three ways: raise the cap (env var or constructor argument), split the
  grant, or use the async schedule (`ConnectedStore(sync=False)` + `catch_up`), where the
  cap is suspended by design (`TK112`).
- The user said on 2026-10-14 that there are no users yet and backwards compatibility is
  not a concern, so changing the default now costs nothing beyond a release note.

**What an operator should set it to:** pick the longest single-write lock hold the store
can tolerate, and divide.

| tolerable write-lock hold (paranoia off) | cap | writer RAM for that write |
|---|---|---|
| ~1 s | 3,000 | ~25 MB |
| ~3 s | 10,000 | ~85 MB |
| ~10 s | 30,000 | ~260 MB |
| ~35 s (today's default) | 100,000 | ~0.85 GB |

Rules of thumb from sec 3: **cap = seconds / 350 us**, and **RAM = cap x 8.6 KB** per
concurrent writer process. 8.6 KB is the worst case, a single huge ancestor or descendant
set; it is ~4.6 KB when the fan-out is the product of two modest sets. Halve the cap under
`full` paranoia. These are laptop numbers (i7-1365U, with other agents busy). A server CPU
will be faster, but time and RAM stay linear in the cap. So measure once on the target with
`python -m benchmarks.fanout_cost_bench point --shape userset --n 10000` and scale.

**Follow-ups this measurement suggests (REASONED; this agent did not file them):**

1. Make the refusal cheap. In `_add_direct_edge_unsafe_impl`, count |A| and |D| with
   `SELECT count(*)` before loading them as ORM rows. On `IndexResourceLimit` in
   `ConnectedStore._write`, undo the one admitted tuple in the evaluator instead of
   rebuilding it. Today a refused 1M-member grant costs 91 s and 3.8 GB (sec 4).
2. Cut the per-row cost of an admitted write. The batch builds one ORM `Edge` per new pair,
   and the flush is 30-40 % of the write. A Core bulk insert, as `bulk_build` already uses,
   would cut both the time and the ~4.6 KB/row of memory. It changes no modelled algorithm
   (`CLAUDE.md` "Perf work & the Lean model"), so it needs no Lean change.
3. Document that an add+remove of an N-row fan-out leaves 2N outbox rows until
   `prune_outbox` runs.
4. Look at the removal path on PostgreSQL (sec 5): at 100k it is 69-81 s, mostly
   `sql_exec`. A lower add cap also bounds the removals that undo those adds, so a
   10,000 default bounds this to ~6 s too.
