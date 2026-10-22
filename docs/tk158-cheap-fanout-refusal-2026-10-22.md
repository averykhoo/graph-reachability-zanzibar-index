# `TK158` -- make a `ClosureFanoutExceeded` refusal cheap (2026-10-22)

**ACTIVE-PLAN, opened 2026-10-22 -- the body is provenance, not a living status.** This is
the execution map for `TK158` (count before loading; undo instead of rebuild), written by
the PLAN stage of the session-2026-10-22 TK158 lane before any product edit. Every figure
and line number below is as of 2026-10-22 on this tree (`78b935a` + whatever the
concurrent `TK3` lane has in the working tree). Live state is the task row
(`python scripts/task.py show TK158`) and `python scripts/gate_status.py`, never this file.
Corrections append **dated at the top**, never edited into the body. Freeze it when
`TK158` closes.

Provenance labels: **READ** (code read first-hand this session), **PROBE** (a run this
session; the raw record is named), **REASONED**, **UNVERIFIED** (stated, not yet checked;
flagged in place). The measurement it builds on is
[`closure-fanout-cost-2026-10-14.md`](closure-fanout-cost-2026-10-14.md) (FROZEN) sec 4
and its Correction 2026-10-16; read that doc's old names through its sec (c) rename map.

## Correction 2026-10-22 (FIX stage) -- five review findings fixed, one not changed

Fix stage of the TK158 lane, after both REVIEW corrections below. Each finding was reproduced
first-hand before it was changed. Runners and logs are under `.scratch/tk158-tk3/`
(`tk158fix_sabotage.py`, `tk158fix_sabotage_pg.py`, `tk158fix-sabotage/*.log`). That directory
is gitignored, so the outputs are copied here.

1. **`scripts/pg_local.sh destroy` deleted the cluster's PARENT. FIXED.** READ: the destroy arm
   ran `rm -rf "$(dirname "$DATA")"`. That was safe only on the default layout, where the parent
   is the script's own `zanzibar-pg`. With the documented `ZANZIBAR_PG_DATA` override, it erased
   the reviewer's whole session scratchpad, including the builder's sabotage runner. The arm now:
   - removes `$DATA` and the script's own `server.log`;
   - `rmdir`s the parent only if that leaves it empty;
   - refuses (exit 1) a `$DATA` that exists but has no `PG_VERSION`.

   New module `tests/test_pg_local_destroy.py` (3 tests) needs no server: `ZANZIBAR_PG_BIN` is
   an empty directory. PROBED sabotage:
   - P1 (the old `rm -rf "$(dirname "$DATA")"`) gave `AssertionError: a sibling of the cluster
     was deleted`.
   - P2 (the refusal removed) gave `assert 0 == 1`.

   Instrument control: the first sabotage run was red for the wrong reason (`no Git Bash
   found`). git.exe here is `Git/mingw64/bin/git.exe`, so the bash lookup now walks every parent
   of git.exe. Not caused by TK158. The orchestrator may still want a row for the incident.
2. **The count block ran on the suspended (replay) path. FIXED.** READ: the guard was
   `if count > 0 and self.max_closure_fanout:`. It is now `... and not
   self._fanout_cap_suspended.on`, in `src/zanzibar/graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`.
   On that path the cap only warns, from the loaded lengths, which are unchanged. The count==load
   assertion therefore covers sync admissions only, the one place the counts decide anything.
   - PROBED (`probe_suspended_cost.py src 1000`, after the fix): `applied 1200 rows in 10.721s;
     count block 0 calls`. The reviewer measured `1700 calls, 1.499s (9.4%)` before the fix.
   - New test 9, `test_suspended_cap_takes_no_region_count`. Sabotage F2 (the old guard) gave
     `AssertionError: _closure_region_counts ran on the suspended path`.
3. **No test covered a `PathCountExceeded` through `Store._write`'s undo arm. FIXED (coverage
   only; the behaviour was already correct).** New test 10,
   `test_path_count_refusal_is_undone_without_rebuild[union-diamond|bool-diamond-grant]`, takes
   the reviewer's probe witnesses with `core.MAX_PATH_COUNT` patched to 1. It checks:
   - no rebuild;
   - the evaluator equals a fresh rebuild;
   - watermark == head;
   - DB rows unchanged;
   - still equal after a later write.

   Sabotage F3 (`except IndexResourceLimit` unreachable) gave `2 failed`: `AssertionError: the
   undo fell back to a rebuild 1 time(s)`.
4. **Nothing tested the count==load mismatch guard. FIXED.** New test 8,
   `test_count_load_mismatch_guard_fires_on_a_zero_count_row`, plants an I1-violating
   `Edge(direct=0, indirect=0)` ancestor row, then does an admitted capped add. It expects
   `InvariantViolation: closure region count mismatch`. Sabotage F1 (the guard `if False and
   ...`, the reviewer's S4) gave `Failed: DID NOT RAISE InvariantViolation`.
5. **`_old_lengths` took a set of row keys, not the old MultiSet. FIXED.** It now builds two
   `MultiSet`s valued by `indirect_edge_count`, as the impl does. Test 8 also asserts
   `_old_lengths == (1, 0)` against `count(*) == (2, 0)` on the planted row. Sabotage F4 (the
   set version) gave `assert (2, 0) == (1, 0)`.
6. **The `CORRESPONDENCE.md` §7.3 sentence was false. FIXED.** A dated `Corrected 2026-10-22
   (TK158)` note now follows the sentence in the resource-refusals bullet. It names
   `_closure_region_counts` and `TupleSource.undo_last_admission`, and adds
   `tests/test_tk158_cheap_refusal.py` to the pins. The T4 row (line 330) was re-read and still
   holds: an admitted write's loads, guard and expansion are unchanged, and the suspended path
   now loads exactly as HEAD did. PROBED `anchor_check.py`: `849 parsed ... 849 resolved`. PROBED
   `claim_rot.py --check` is RED, as expected:
   - `_closure_region_counts` and `undo_last_admission` are anchored but NOT pinned;
   - `_add_direct_edge_unsafe_impl` BODY CHANGED, from `79e5d47e62b0235a` to `2d50598d9792064e`
     (it moved again in this stage).

   The orchestrator regenerates the pin once, after both lanes land.

**Not changed (REASONED): a refusal on an already-corrupt store reports a resource limit.** With
a zero-count row and the region over the cap, the write is refused as `ClosureFanoutExceeded` on
the inflated `count(*)`, and the mismatch guard never runs. Surfacing the corruption there would
mean loading the region on the refusal path, which is the cost TK158 removes. The refusal is
still atomic, and only an I1-violating store reaches this case. That violation is the invariant
checker's job (paranoia mode), and an admitted write on the same store does raise the mismatch.
Decision: keep.

PROBED targeted run after the fix (SQLite): `tests/test_tk158_cheap_refusal.py` (now 20 tests),
`test_pg_local_destroy.py`, reg17, tk112, tk111_path_count_bound, tk123_no_internal_refs and the
five connectedstore modules gave `1 failed, 90 passed in 81.35s`. The one failure is
`test_tk123_no_internal_refs.py::test_public_docstrings_carry_no_internal_refs` on
`graphindex/cascade_mark.py <module> [doc] 'I5'`. That is the TK3 lane's new module, not this
lane's. The PostgreSQL leg was NOT re-run in this stage (UNVERIFIED for tests 8-10).

## Correction 2026-10-22 (adversarial REVIEW, correctness lens) -- no equivalence break found

Written by a second REVIEW stage of the lane; no product code changed. Raw record:
`.scratch/tk158-tk3/review-tk158-correctness.md` (gitignored; the literal lines are here).
Probes are under `.scratch/tk158-tk3/` (`probe_diff.py`, `probe_multi.py`,
`probe_pathcount.py`, `probe_zero_row.py`, `probe_suspended_cost.py`).

- **PROBE, HEAD-vs-tree differential** (`probe_diff.py`). Three schemas (`but not`,
  union + TTU, `and`), with wildcards. Caps are drawn per op from {0,0,1,2,3,5,8}, and
  `paranoia=True`. After every op the probe checks the graph index against the set engine
  over the full grid. On the tree it also checks the evaluator against a fresh rebuild after
  every refusal, and that the refusal did 0 rebuilds. The same scripts were run on a
  `git archive 78b935a`. Seed 1 (150 ops per schema) and seeds 2-5 (200 ops per schema):
  outcomes and grids are identical op-for-op ("ops compared 600 len 600 600 diffs 0" for
  each of seeds 2-5). There were 17/21/25 and more refusals per seed, with `problems 0`.
  **UNVERIFIED (not reproduced):** one early run showed 3 false `InvariantViolation: Cycle
  detected in backward path` where HEAD refused with `ClosureFanoutExceeded`. Two re-runs of
  the identical config were clean. `core.py` (mtime 17:27:05) and `processor.py` (17:26:32)
  were rewritten during that run, so it is attributed to a concurrent lane's edit.
- **PROBE, two sync instances on one store** (`probe_multi.py`): SQLite seed 7 / 150 ops
  (union: 7 refusals, bool: 6) and PostgreSQL seed 11 / 120 ops (2 and 4 refusals). After
  each refusal and catch-up, the refusing instance equals a fresh rebuild, graph answers
  equal set-engine answers on both instances, and A equals B. `problems 0`. On PG,
  `tests/test_tk158_cheap_refusal.py` + `tests/test_tk112_cap_policy.py`: `24 passed`.
- **PROBE, the D2 undo on `PathCountExceeded`** (`MAX_PATH_COUNT` patched to 1; no test
  covers it): union diamond and `but not` diamond each give `rebuilds on refusal: 0`,
  `fingerprint diff: []`, watermark == head, DB rows unchanged, and diff `[]` after a later
  write. So it is correct, but the test is missing.
- **PROBE, count block on the SUSPENDED path** (async `Store.catch_up`, 1700 rows, default
  cap 100000): tree `15.976s`, of which the count block was `1700 calls, 1.499s (9.4%)`;
  HEAD `13.416s`, 0 calls. The guard `count > 0 and self.max_closure_fanout` in
  `src/zanzibar/graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` does not
  exclude `_fanout_cap_suspended.on`. That window can never refuse, so `catch_up` and the
  non-bulk `build_index` pay two `count(*)` per edge add for the count==load check alone.
  This costs time but does not break correctness.
- **REASONED (READ):** `_last_admission` is reset after `_lock_source` and the catch-up of
  every `add` / `remove`, and `undo_last_admission` runs only from the second `try` of
  `Store._write`. That `try` is reached only after this call's `fn` returned, so a stale
  record from an earlier committed write cannot be undone. A duplicate add leaves `None` and
  falls back to a rebuild. The TK154 id stamp stays sound because each id the undo frees
  bumps `Interner.frees`.
- **Footgun found while running the PG leg (should-fix, not TK158):** `scripts/pg_local.sh
  destroy` runs `rm -rf "$(dirname "$DATA")"`, so with the documented `ZANZIBAR_PG_DATA`
  override it deletes the PARENT of the cluster directory. This review used
  `ZANZIBAR_PG_DATA=<session scratchpad>/pgreview` and the destroy deleted the whole session
  scratchpad. That included the builder's sabotage runner `scratchpad/sabotage.py`. The
  sabotage logs in `.scratch/tk158-tk3/sabotage/` survive.

## Correction 2026-10-22 (adversarial REVIEW, assurance lens) -- two test gaps

Written by the REVIEW stage of the same lane; nothing in product code was changed.
Raw record: `.scratch/tk158-tk3/tk158-review.md` (gitignored; the literal lines are here).

- **PROBE, reviewer mutants** (different from the builder's M1-M8; each applied by an
  exact-once replace and restored by an exact-once reverse replace with sha256 re-checked;
  run on `tests/test_tk158_cheap_refusal.py` + `tests/test_reg17_closure_fanout_cap.py` +
  `tests/test_tk112_cap_policy.py`, baseline `35 passed`):
  S1 `undo_last_admission` applies the inverse only for an `ADD` record -> RED (unban:
  `evaluator diverged from a fresh rebuild in: ['flow adjacency', ...]`).
  S2 the count block's `>` becomes `>=` -> RED
  (`test_reg17_closure_fanout_cap.py::test_cap_boundary_is_the_exact_region_size`).
  S3 the D count drops its `store_id` filter -> RED (`(1, 2) != (1, 1) for (2, 1)`).
  S5 `_reverse_edge_present` reads `subject -> object` instead of `object -> subject` ->
  RED (`test_over_cap_cycle_is_reported_as_a_cycle`).
  **S4 the count==load mismatch guard in `_add_direct_edge_unsafe_impl` disabled
  (`if False and ...`) -> GREEN, `35 passed`.** The guard is unpinned.
- **PROBE, the guard is reachable**: planting an I1-violating `Edge` row
  (`direct_edge_count=0, indirect_edge_count=0`) in the A region of a capped add gives
  `InvariantViolation: closure region count mismatch: count(*) gave (4, 0), the loaded region
  has (3, 0)`; with `max_closure_fanout=1` the same write is refused as
  `ClosureFanoutExceeded ... (4 ancestors x 0 descendants ...)`, and with the cap off it is
  admitted silently. REASONED: `Counter.__delitem__` ignores a missing key, so
  `MultiSet[k] = 0` silently drops the row, which is why count(*) and the loaded length differ.
- **READ, test 4's reference is not the old accounting**:
  `tests/test_tk158_cheap_refusal.py::_old_lengths` takes `len({e.subject_id ...})`, a SET
  of row keys, which equals count(*) by the unique constraint whatever the counts are. The
  old code's length was `len(MultiSet)`, which drops zero-count rows. The docstring's
  "verbatim" is false, and the test cannot see the one way the two differ.
- **Next action (for the builder, before close):** build `_old_lengths` from `MultiSet`
  exactly as the impl does, and add a test that plants the zero-count row above and expects
  the mismatch `InvariantViolation`. That test must go red under S4.
- REASONED, nit: on a REFUSED write the mismatch guard never runs, so a corrupt row inflates
  the count and the write is refused as a resource limit, and the Store arm then undoes it
  with no rebuild. Only reachable on an already-I1-corrupt store.

## Correction 2026-10-22 (IMPLEMENT stage) -- what landed, and the acceptance numbers

Written by the IMPLEMENT stage of the same lane, after the edits; the body below is the
PLAN stage's and is left as written.

**What landed (READ, this tree, not committed; line numbers as of 2026-10-22):**

- D1 as designed: `src/zanzibar/graphindex/core.py::ReachabilityIndex._closure_region_counts`
  (two `select(func.count()).select_from(Edge)` queries), `::_reverse_edge_present` (the
  one-row cycle point lookup, `indirect_edge_count > 0`), `::_raise_closure_fanout` (the
  unchanged message, factored out so both refusal sites share it). In
  `::_add_direct_edge_unsafe_impl` the count block sits before the loads and fires only for
  `count > 0` with the cap nonzero and NOT suspended; after the loads an admitted capped
  write raises `InvariantViolation('closure region count mismatch ...')` if the counts and
  the loaded lengths differ. The old post-load raise is kept (now unreachable while the
  counts agree) so the refusal never depends on the new block. Suspended (replay) writes
  are unchanged apart from paying the two counts.
- D2 as designed: `src/zanzibar/store/source.py::TupleSource.add` / `::remove` record
  `_last_admission = (op, septuple..., prior_watermark)` after the engine mutation and
  before `_append`; `::undo_last_admission` applies the inverse through
  `SetEngine.apply_logged` and assigns the watermark back, falling back to
  `refresh_evaluator` when nothing is recorded. `src/zanzibar/store/_store.py::Store._write`
  has `except IndexResourceLimit:` (rollback, undo, rebuild only if the undo raises,
  re-raise) ahead of `except Exception:`. `src/zanzibar/setengine/engine.py` untouched.
- `benchmarks/fanout_cost_bench.py point --warm` (name confirmed): times
  `_ensure_flow_graph()` as `warmup_flow_graph_s`, then the refusal, then a SECOND
  identical refusal (`write2_s`, `write2_phases`, rows added asserted 0). Phase timers
  `region_count_s` / `undo_s` added when the methods exist.
- Tests: `tests/test_tk158_cheap_refusal.py`, 16 tests (`pytest --collect-only`,
  2026-10-22), sec 4 items 1-6 plus the cycle-precedence test; item 6 (second instance)
  and everything else run through `tests/dbengine.py::shared_engine`, so the module
  re-runs on PostgreSQL with the DSN.

**Acceptance, SQLite file, `userset`, N = 1,000,000, default cap 100,000, paranoia off
(PROBE 2026-10-22, `python -m benchmarks.fanout_cost_bench point --shape userset --n
1000000 --mode refuse [--warm]`; raw records `.scratch/tk158-tk3/after-1m.jsonl`, scratch,
so copied here). Machine: same laptop, 6-9 `python.exe`, 15-31 % CPU busy (the TK3 lane
was live).**

| run | when | refusal `write_s` | phases | peak delta | rows added |
|---|---|---|---|---|---|
| BEFORE cold (sec 1d) | 16:03:33 | **78.89 s** | admit 16.46, expand 23.39, refresh_evaluator 31.33 | 3,827 MB | 0 / 0 |
| BEFORE warm (sec 1d probe) | ~16:20 | **73.00 s**, then 74.30 s | (probe, not phase-instrumented) | -- | 0 |
| AFTER cold | 16:35:23 | **15.818 s** | admit 15.633 (= the flow-graph build), region_count 0.107, expand 0.108, apply 0.173, undo 0.000 | 411.1 MB | 0 / 0 |
| AFTER warm, refusal #1 | 16:40:57 | **0.199 s** | admit 0.013, region_count 0.118, expand 0.119, apply 0.175, undo 0.000 | 0.0 MB | 0 / 0 |
| AFTER warm, refusal #2 | 16:40:57 | **0.146 s** | admit 0.018, region_count 0.109, expand 0.109, apply 0.119, undo 0.000 | 0.0 MB | 0 / 0 |

(`warmup_flow_graph_s` 14.489 on the warm run; `undo_s` rounds to 0.000.) So the warm
refusal is **0.15-0.20 s, well under 1 s**, and the second refusal costs no more than the
first (the undo no longer re-arms the flow graph). The cold figure is the D4 warm-up the
plan predicted: of 15.8 s, 15.6 s is `_ensure_flow_graph` on the first write after open,
which an ADMITTED first write pays too. Nearly all of what remains of a warm refusal is the
A count (0.11-0.12 s at |A| = 1M).

**PostgreSQL (PROBE 2026-10-22 16:48:54, `pg_local.sh` server, `--n 100001 --mode refuse
--warm --dsn ...`, raw record `.scratch/tk158-tk3/after-pg-100k.jsonl`):** warm-up
1.324 s; refusal #1 **0.044 s** (region_count 0.014, admit 0.008, apply 0.034), refusal #2
**0.032 s**; 0 rows added. So `count(*)` is cheap on PG too at this size (the sec 2 D1
"revisit if PostgreSQL disagrees" does not trigger). 1M on PG not run (memory-bound on
2026-10-14).

**PostgreSQL test leg (PROBE 2026-10-22, `ZANZIBAR_PG_REQUIRED=1`):**
`tests/test_tk158_cheap_refusal.py tests/test_postgres_ha.py tests/test_tk112_cap_policy.py
tests/test_reg17_closure_fanout_cap.py tests/test_connectedstore_multi_instance.py
tests/test_connectedstore_concurrency.py tests/test_connectedstore_source.py
tests/test_concurrency.py` -> **75 passed, 3 skipped, 2 failed**. The two failures are
`tests/test_postgres_ha.py::test_tk154_graph_node_ids_are_never_reused_on_postgresql` and
`::test_tk154_sabotage_control_restarted_sequence_translates_wrong`
(`AssertionError: assert {('doc', 'd',..., 'a', '...')} == {('user', 'a', '...')}` /
`Extra items in the left set: ('doc', 'd', 'reader')`). **PRE-EXISTING, not TK158:** the
first one fails identically on a `git archive` of HEAD `78b935a` (no TK158 or TK3 edits)
against the same server. The 3 skips are the SQLite-pinned-snapshot tests that skip by
design under a DSN. Server stopped afterwards; no `postgres.exe` left.

**The sec 1d UNEXPLAINED item (73.00 s vs 74.30 s) -- REASONED, not re-measured:** the
probe's "warm" refusal #1 already paid the full `refresh_evaluator` (~31 s) AND loaded the
region; refusal #2 paid the flow-graph rebuild (~21 s) but its rebuild/load share was
smaller because the identity map and SQLite page cache were hot after #1. Not worth
re-probing: the AFTER table shows both costs gone.

**Sabotage (PROBE 2026-10-22, runner `scratchpad/sabotage.py`, logs
`.scratch/tk158-tk3/sabotage/M*.log`):** all 8 sec 6 mutants RED; the literal outputs are
in the docstring of `tests/test_tk158_cheap_refusal.py`. One deviation from the plan table:
M4 (arm made unreachable) and M3 are caught by test 2, and test 1 also counts rebuilds so
M3 cannot pass by falling back. M1 and M2 both trip test 1; M2 additionally trips test 6.

**Correction to D3 (READ):** besides the T4 row and the sec 7.3 sentence, the new private
methods `_closure_region_counts` / `_reverse_edge_present` / `_raise_closure_fanout` are not
cited anywhere in `formal/CORRESPONDENCE.md`; the orchestrator's sec 7.3 correction should
name `_closure_region_counts` as where the bound now lives. Only the
`_add_direct_edge_unsafe_impl` body hash in `formal/correspondence_anchor_pin.txt` moves
(`TupleSource.add/remove`, `Store._write` are not pinned; `TupleSource.catch_up_evaluator`,
`_lock_source`, `Store.catch_up`, `SetEngine.apply_logged` are pinned and untouched).

## 0. The question

A refused grant through a 1M-member group cost **90.92 s and 3,828 MB** on 2026-10-14
(cost doc sec 4). The brief names two causes. This plan (1) confirms both sites on the live
tree, (2) finds a THIRD cost the brief does not name and decides what to do about it,
(3) fixes the design, the tests, the sabotage and the Lean/CORRESPONDENCE impact.

## 1. Census of the sites (READ 2026-10-22, line numbers as of that date)

### 1a. Cause 1 -- the graph index loads A and D before counting

- `src/zanzibar/graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`
  (def at line ~800). Lines ~836-845 load `triples_from` (every `Edge` with
  `object_id == subject_id`, the ancestor set A) and `triples_to` (every `Edge` with
  `subject_id == object_id`, the descendant set D) as full ORM rows with `.all()`, into
  two `MultiSet`s. Lines ~853-856: the in-impl cycle guard (`InvariantViolation`) reads
  `reachable_before_subject[object_id]` and `reachable_after_object[subject_id]`. Lines
  ~898-921: `n_anc = len(...)`, `n_desc = len(...)`, `fanout = n_anc*n_desc + n_anc + n_desc`,
  then the suspended-warning branch and the `ClosureFanoutExceeded` raise.
- **Why `count(*)` is exactly `len(MultiSet)` (READ + REASONED):**
  - `src/zanzibar/graphindex/models.py::Edge` has
    `UniqueConstraint('store_id', 'subject_id', 'object_id')`, so the rows with
    `object_id == X` have pairwise-distinct `subject_id` (and dually), and the MultiSet
    keys are distinct.
  - `src/zanzibar/graphindex/multiset.py::MultiSet.__setitem__` raises on a negative value
    and DELETES the key on 0 (`super().__delitem__`, which itself raises `KeyError` on an
    absent key). So `len` = number of rows only if every row has
    `indirect_edge_count > 0`. That is invariant I1, enforced at every write site
    (`_add_indirect_edges_batch_unsafe` raises `InvariantViolation('I1 violated:
    zero-reachability row would be persisted')`). A row with count 0 would have made the
    OLD code crash with `KeyError` at load, not count it.
  - Both a `SELECT` and a `SELECT count(*)` through `session.exec` autoflush first, so
    both see the same pending state.
  - So `count(*) WHERE store_id = s AND object_id = subject_id` = `n_anc`, and the
    dual = `n_desc`. The plan keeps the loads for ADMITTED writes and **asserts the
    equality at runtime** after them (an `InvariantViolation` on mismatch, free), as well as
    pinning it with a test (sec 4).
- **Indexes the counts ride (READ):** `ix_zanzibar_edge_store_object (store_id, object_id)`
  covers the A count; the unique constraint's index `(store_id, subject_id, object_id)`
  covers the D count. Both should be index-only counts on SQLite (REASONED; the A count
  measured 0.180 s at 1M, sec 1d). On PostgreSQL an index-only scan depends on the
  visibility map (UNVERIFIED cost; measured in the IMPLEMENT stage, sec 5).
- **Callers of `_add_direct_edge_unsafe` (READ, `grep` 2026-10-22):** `core.py` lines
  ~1207 (`_add_edge_locked`, +1), ~1252 (removal, -1), ~1313 (node removal, `(n, n, -1)`).
  Only the +1 path is capped, and it is reached from `add_edge_by_id`, the wildcard
  bridge writer and the delta processor's derived writes (all through `_add_edge_locked`
  or the bridge path). `_add_edge_locked` already does the reverse-edge cycle pre-check
  as a ONE-ROW point lookup (`select(Edge)...where(subject_id == object_id, object_id ==
  subject_id).first()`) before reaching the impl.

### 1b. Cause 2 -- `Store._write`'s error arm rebuilds the whole set engine

- `src/zanzibar/store/_store.py::Store._write` (def at line ~594). Second `try`
  (lines ~635-657): `advance_index(...)` then `commit`; its `except Exception` arm does
  `pop_pending_rows()`, `session.rollback()`, **`self.source.refresh_evaluator()`**, `raise`.
  The comment says why: admission already put the tuple into the in-memory evaluator.
- `src/zanzibar/store/source.py::TupleSource.refresh_evaluator` ->
  `::TupleSource._consistent_rebuild(self.engine.rebuild)` ->
  `src/zanzibar/setengine/engine.py::SetEngine.rebuild` (`_reset_state` + replay every
  `RelationTuple`). O(store).
- Other `refresh_evaluator()` call sites in `src/` (READ, `grep`): `_store.py` ~633 (the
  FIRST arm, admission raised a non-`AdmissionRejected`; unchanged), ~656 (this one), ~757
  (`Store.refresh`, the public reset; unchanged).
- `IndexResourceLimit` reaches `_write` unchanged: `src/zanzibar/store/apply.py::_apply_row`
  re-raises it (`except IndexResourceLimit: raise`) and promotes every other
  `ValueError` to `InvariantViolation`. Its two members are `ClosureFanoutExceeded` and
  `PathCountExceeded` (`src/zanzibar/schema/errors.py`). Only `Store._write` calls
  `source.add` / `source.remove` (`grep` 2026-10-22: `_store.py` ~580, ~592, ~610).

### 1c. A THIRD cost the brief does not name -- the lazy flow-graph build (PROBE 2026-10-22)

cProfile of one refused `userset` write at N = 100,001 on SQLite, cap default
(probe `.scratch/tk158-tk3/probe/profile_refusal.py`; scratch, so the figures are copied
here): **13.88 s under the profiler**, of which

| phase | cum s | site |
|---|---|---|
| `refresh_evaluator` (cause 2) | 5.59 | `SetEngine.rebuild` 5.25 |
| `TupleSource.add` (admission) | 4.19 | `SetEngine._validate` -> `_would_cycle` -> `_flow_reaches` -> **`_ensure_flow_graph` 4.17** (100,003 calls; `_derived_pairs` 3.26) |
| `advance_index` -> `_add_direct_edge_unsafe_impl` (cause 1) | 2.87 | 200,004 ORM `Edge` instances built |
| `session.rollback` | 0.89 | `_restore_snapshot` expiring ~100k identity-map objects (a consequence of cause 1) |

The same point UNPROFILED through the benchmark (PROBE 2026-10-22 16:00,
`.scratch/tk158-tk3/baseline-100k.jsonl`, machine load 5 `python.exe`, 99.7 % CPU busy at
start because the concurrent TK3 lane was running a pytest census): `write_s` **6.49**,
`admit_s` 1.27, `expand_s` 1.77, `refresh_evaluator_s` 2.85, peak delta 366 MB.

READ: `SetEngine._ensure_flow_graph` (N10) builds the write-time cycle-detection flow graph
LAZILY, once, on the first flow-graph touch, by re-running `_derived_pairs` over every
stored membership -- O(store). `rebuild()` resets it (`_reset_state`; `_flow_built =
False`), so it is paid on the first write after open AND again on the first write after
every `refresh_evaluator()`.

Consequences (REASONED):

- In the benchmark the measured write is the first write after `Store(...)` opened, so its
  `admit` phase is the one-time flow-graph build, not the per-write admission. The cost
  doc's "admit 19.52 s at 1M" (sec 4) is this build. It is NOT a refusal cost: an
  ADMITTED first write pays it too.
- Today the rebuild makes it worse: a refusal discards the flow graph, so the NEXT write
  pays the O(store) build again. **The undo fixes that as a side effect**, because
  `apply_logged('REMOVE', ...)` maintains the built flow graph incrementally
  (`_apply_remove` -> `_flow_remove_edge`) instead of discarding it.
- So the acceptance "refusal well under 1 s" is measured on a WARM store (sec 5). The
  first-write warm-up is a separate, pre-existing O(store) cost; the plan records it and
  does NOT fix it here (decision D4).

### 1d. The "before" figures at 1M, and the count it would replace (PROBE 2026-10-22)

All SQLite file, paranoia off, default cap 100,000, `userset` shape, this tree before any
TK158 edit. Machine: the same laptop as the cost doc (host DESKTOP-3RENS5H, Python
3.13.14), 7 `python.exe` processes, 28-38 % CPU busy (the concurrent TK3 lane was running).

- **Benchmark, cold first write** (`python -m benchmarks.fanout_cost_bench point --shape
  userset --n 1000000 --mode refuse`, 2026-10-22 16:03:33; raw record
  `.scratch/tk158-tk3/baseline-1m.jsonl`, scratch, so copied here): refused, 0 `Edge` rows
  and 0 outbox rows added, **`write_s` 78.89**, phases `admit_s` 16.46, `apply_s` 23.47
  (`expand_s` 23.39), `refresh_evaluator_s` 31.33, `orm_flush_s` 0.02, `sql_exec_s` 0.07;
  **peak delta 3,827 MB**. (2026-10-14: 90.92 s / 3,828 MB.)
- **Count vs load** (probe `.scratch/tk158-tk3/probe/count_vs_load.py 1000000`, finished
  16:22): for the write's subject `group:g#member`, `SELECT count(*) ... WHERE object_id =
  subject` returned **1,000,000 in 0.180 s**; the current ORM load of the same rows
  returned len 1,000,000 in **26.86 s**; equal = True.
- **Warm refusals** (same probe, after forcing `_ensure_flow_graph()`, which took
  **21.07 s**): refusal #1 **73.00 s**, refusal #2 **74.30 s**. ⚠ UNEXPLAINED: #1's refresh
  reset the flow graph, so #2 was expected to cost ~21 s more than #1, and it did not.
  Not needed for the design (both are dominated by causes 1 and 2), but the IMPLEMENT
  stage's phase-instrumented `--warm` run should account for it.
- **Warm, profiled, N = 100,001** (`WARM=1 profile_refusal.py 100001`): 8.99 s under the
  profiler = `refresh_evaluator` 5.08 + `_add_direct_edge_unsafe_impl` 2.75 +
  `session.rollback` 0.81 (expiring the ~100k loaded `Edge` objects) + small change.
  **Warm admission does not appear in the top 45 entries**, i.e. once the flow graph is
  built the set engine's admission of this write is cheap. So after D1 + D2 the warm
  refusal is predicted (REASONED) as: two counts (0.18 s + ~0 at 1M) + admission + undo,
  well under 1 s; the rollback's expiry cost goes away with the loads.

## 2. Design (decided 2026-10-22 by this lane; REASONED)

### D1. Count first, refuse before loading (graph index)

In `ReachabilityIndex._add_direct_edge_unsafe_impl`, on the addition path
(`count > 0`, so `subject_id != object_id` is already guaranteed by `_add_edge_locked`)
and only when the cap is active (`self.max_closure_fanout` nonzero):

1. `n_anc = SELECT count(*) FROM zanzibar_edge WHERE store_id = :s AND object_id = :subject`,
   `n_desc = ... AND subject_id = :object`. New private helper
   `ReachabilityIndex._closure_region_counts(subject_id, object_id) -> (n_anc, n_desc)`,
   `select(func.count()).select_from(Edge)`, the same idiom as
   `src/zanzibar/store/source.py::TupleSource.evaluator_lag`.
2. If `fanout > cap` and the cap is NOT suspended: first the cycle guard's point lookup
   (does `Edge(subject = object_id, object = subject_id)` exist?) -> the same
   `InvariantViolation("Cycle detected in backward path")` as today, so the old error
   PRECEDENCE (cycle before cap) is kept; otherwise raise the unchanged
   `ClosureFanoutExceeded` message (same numbers, same text). Nothing has been loaded.
3. Otherwise fall through to the UNCHANGED loads, cycle guard, expansion and batch. After
   the loads, when the counts were taken, `if len(A) != n_anc or len(D) != n_desc: raise
   InvariantViolation(...)` -- a free runtime pin of the equality in sec 1a. The suspended
   branch's warning uses the same counts.

Why not drop the loads: an ADMITTED write needs A and D (it enumerates `A x D`), so they
stay; only the refusal stops paying for them. Why not a bounded `LIMIT cap+1` count: it
would make the refusal O(cap) instead of O(|A| + |D|) index entries, but plain
`count(*)` over a covering index is already well under 1 s at 1M on SQLite (0.180 s, PROBE sec 1d)
and is simpler to pin. Revisit only if PostgreSQL disagrees (sec 6).

Cost to ADMITTED writes: two extra indexed `count(*)` round trips per capped edge add.
REASONED small against the two full loads that follow; measured in the IMPLEMENT stage
with the 10,000 admit point (`fanout_cost_bench point --shape userset --n 10000`) against
the cost doc's table. With the cap disabled (`0`) the counts are skipped entirely.

### D2. Undo the one admitted tuple instead of rebuilding (store layer)

- `TupleSource.add` / `TupleSource.remove` record, AFTER the engine mutation succeeded and
  BEFORE `_append`, `self._last_admission = (op, s_pred, s_type, s_name, relation, o_type,
  o_name, prior_watermark)` where `prior_watermark = self.evaluator_watermark` at that
  point (i.e. after the in-lock `catch_up_evaluator`, before `_advance_watermark`). The
  duplicate-add early return sets it to `None`.
- New `TupleSource.undo_last_admission()`: pops the record; if `None`, falls back to
  `refresh_evaluator()`; else `self.engine.apply_logged(<inverse op>, ...)` (`REMOVE`
  for an add, `ADD` for a remove) and `self.evaluator_watermark = prior_watermark`
  (assignment).
- `Store._write`'s second `try` gains an arm BEFORE `except Exception`:
  `except IndexResourceLimit:` -> `pop_pending_rows()`, `rollback()`, then
  `try: self.source.undo_last_admission() except Exception: self.source.refresh_evaluator()`
  (the rebuild stays as the fallback for an undo that itself fails), then `raise`. Every
  other exception keeps the rebuild.

Why `apply_logged` and not `_remove_tuple_direct` (READ): `_remove_tuple_direct` deletes
the `RelationTuple` ORM row and flushes, but after the rollback that row does not exist.
`apply_logged` is the in-memory-only trusted replay: it runs exactly the `_apply_add` /
`_apply_remove` sequence `rebuild()` would, maintains the flow graph if built, and has a
strict presence guard (`RuntimeError` on an absent tuple), so a wrong undo is loud. It is
the same path a replica uses to tail a committed REMOVE, so its "state after = rebuild at
that prefix" property is already exercised by the multi-instance suites.

Why the restored watermark is true (REASONED): `prior_watermark` was set by
`catch_up_evaluator` under `_lock_source` (the `SchemaRecord` row lock), so every row
with `id <= prior_watermark` is committed and applied, and rows committed by other
writers after our rollback releases the lock have `id > prior_watermark` and will be
tailed by the next catch-up. `_consistent_rebuild` would have jumped the watermark to
the head instead; both states are truthful.

Why only `IndexResourceLimit` (REASONED): the undo is licensed by knowing exactly what
the evaluator did since the last true state -- one `_apply_add` / `_apply_remove` of one
tuple. That holds for any failure after admission in principle, but an
`InvariantViolation` or a DB error is a bug signal for which the conservative rebuild is
the right response. `IndexResourceLimit` is the one documented, expected refusal family
on this path (`_apply_row`), so it is the one that gets the cheap path.

Atomicity (log, set engine, index), REASONED: the log row and the index changes are
discarded by the same `session.rollback()` as today; the set engine is restored by the
undo instead of the rebuild. The tests in sec 4 pin all three.

### D3. Lean / `CORRESPONDENCE.md` impact (READ 2026-10-22)

- **No modelled algorithm changes.** The count precedes the modelled expansion; an
  admitted write runs the same loads, guard, expansion and batch. The cap is not
  modelled in Lean (cost doc sec (c); `formal/CORRESPONDENCE.md` sec 7.3 "Two resource
  REFUSALS on the add path that the model does not have"). The set-engine undo is a
  Python-to-Python operational path with no Lean twin.
- **But the anchor CONTENT pin WILL go red** (`formal/verify.sh` step 4d2):
  `formal/correspondence_anchor_pin.txt` pins the body hash of
  `src/zanzibar/graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`
  (`79e5d47e62b0235a`). Rows citing it: the T4 row (`GraphIndex/Closure.lean::pathCount_addEdge`
  ... "ref-counted path-count closure maintenance") and sec 7.3's resource-refusals bullet,
  whose sentence "the bound is a read-only pre-check over the region
  `_add_indirect_edges_batch_unsafe` already loads" becomes FALSE after D1 (the bound is
  now a count taken BEFORE the region is loaded). So the IMPLEMENT stage must append a
  dated correction to that bullet ("Corrected 2026-10-22 (TK158): the bound is now two
  indexed counts taken before the region is loaded; the loads, guard and expansion of an
  admitted write are unchanged, and their lengths are asserted equal to the counts"),
  re-read the T4 row (still true: the arithmetic of an admitted write is unchanged), and
  then regenerate the pin with `python formal/conformance/claim_rot.py --generate`.
  **This touches `formal/CORRESPONDENCE.md` and the pin file: the orchestrator should own
  that regeneration once, after BOTH lanes land**, because the TK3 lane's processor edits
  may move pinned bodies too.
- Not pinned (READ, `grep` of the pin file): `Store._write`, `TupleSource.add`,
  `TupleSource.remove`. Pinned and NOT touched by this design: `SetEngine.apply_logged`,
  `SetEngine._apply_remove`, `TupleSource.catch_up_evaluator`, `TupleSource._lock_source`,
  `Store.catch_up`.

### D4. Not in this item (decided, REASONED)

- The lazy flow-graph build on the first write after open (sec 1c) is a pre-existing
  O(store) warm-up that every first write pays, refused or not. Making it incremental at
  open (or persistent) is a different item; D2 already stops a refusal from re-arming it.
  The IMPLEMENT stage records the cold figure next to the warm one so nobody reads the
  acceptance as "the first write after open is fast".
- `object`-shape refusals: the set engine's own cycle DFS from `folder:f#viewer` walks the
  N `doc` nodes (REASONED from `_flow_reaches`; UNVERIFIED by measurement). That is
  admission cost, O(|D|) in memory, paid by admitted writes too. Measured once in the
  IMPLEMENT stage (`--shape object --n 1000000 --mode refuse`, warm), not fixed here.

## 3. Interaction with other lanes and rows (READ)

- `TK3` (concurrent lane) edits the `WildcardIndex` / `DeltaProcessor` write paths and a
  `before_commit` hook. Overlap risk: a refusal raised inside the processor cascade on a
  boolean schema (the TK112 `unban` witness: a REMOVE whose derived ADD is refused) must
  still reach `_write` as `IndexResourceLimit`; if TK3's hook runs at commit, it runs after
  `advance_index`, so the refusal never reaches it. To re-check after both land.
- `TK164` (NEXT) changes the exception hierarchy. `IndexResourceLimit` is currently an
  `AdmissionRejected` subclass; the new `except IndexResourceLimit` arm must keep naming
  the class `_apply_row` re-raises, whatever TK164 renames.

## 4. Test plan

New module `tests/test_tk158_cheap_refusal.py` (so it lands in a tile automatically):

1. **Evaluator equals a fresh rebuild after a refusal** (the brief's acceptance test).
   For each TK112 witness (`ban`, `join-banned-group`, `unban` -- the last one exercises
   the REMOVE undo) plus a plain `userset` grant: build the region with the cap off, set
   the cap, take a canonical snapshot, do the refused write, then compare the live
   evaluator against a SECOND `SetEngine` rebuilt from the DB: id-independent membership
   relation (the `_membership_edges` idiom from `tests/test_setengine_storage.py`), the
   interner's live key set, the flow graph's `_edge_count` keyed by `NodeKey` (after
   `_ensure_flow_graph()` on the fresh engine), `evaluator_watermark == log_watermark`, and
   the full check grid via the oracle. Plus: log head unchanged, `Edge` and `DeltaOutbox`
   row sets unchanged (snapshot before / after), and the store still writable.
2. **The refusal does not rebuild**: monkeypatch `SetEngine.rebuild` (and
   `TupleSource.refresh_evaluator`) to raise; the refusal must still raise
   `ClosureFanoutExceeded`, not the sentinel.
3. **The refusal does not load the region**: count `Edge` ORM instances loaded during the
   refused write (SQLAlchemy `load` event on `Edge`), with a 1,000-member group and cap
   10; must be 0 (or at most the one-row cycle point lookup -- pin the exact observed
   number).
4. **Count equals the old loaded-set count** (equivalence): hypothesis or a fixed grid of
   shapes (`userset`, `object`, `product`, a chain with path counts > 1, a wildcard
   bridge): for every `(subject_id, object_id)` about to be added, assert
   `_closure_region_counts` equals `(len(A), len(D))` computed the old way. Plus the
   runtime assertion in D1 means every existing test that adds an edge under an active
   cap now also checks it.
5. **Fallback**: make `apply_logged` raise inside the undo; the write still raises
   `ClosureFanoutExceeded` and the evaluator equals a rebuild (the fallback ran).
6. **Watermark after undo**: after a refused write, a concurrent second instance's
   committed write is tailed by the next `catch_up_evaluator` (no `WatermarkGap`, no
   `RuntimeError`). SQLite file DB with two sessions; repeat on PostgreSQL via the DSN.
7. Existing pins that must stay green unchanged: `tests/test_reg17_closure_fanout_cap.py`,
   `tests/test_tk112_cap_policy.py`, `tests/test_tk111_path_count_bound.py`,
   `tests/test_connectedstore_source.py`, the multi-instance and concurrency modules, and
   on PostgreSQL `tests/test_postgres_ha.py`.

## 5. Acceptance measurement plan

- Extend `benchmarks/fanout_cost_bench.py` `point --mode refuse` with an optional
  `--warm` flag (UNVERIFIED name) that calls `cs.source.engine._ensure_flow_graph()`
  before the measured write and then times a SECOND identical refusal too, recording
  `write_s`, `write2_s` and the phases of each. The cold `write_s` stays as before so the
  record is comparable with the cost doc.
- Before (this tree, pre-change) and after, SQLite file, `userset`, N = 1,000,000,
  `--mode refuse`, 1 rep each, literal numbers dated in a Correction here. Target: warm
  refusal well under 1 s; cold first write recorded as is (sec 1c).
- PostgreSQL: the same at N = 100,001 (1M was memory-bound on PG on 2026-10-14) against a
  dedicated database, server stopped afterwards.

## 6. Sabotage plan (`docs/sabotage-procedure.md`)

Each mutant applied to the IMPLEMENTED code, the named test run, the literal output
recorded in that test's docstring and here:

| mutant | must go red |
|---|---|
| `undo_last_admission` body -> `pass` | test 1 (evaluator != rebuild: the refused tuple is still a member) |
| undo restores the op but not the watermark | test 1's watermark assertion and/or test 6 |
| undo applies the SAME op instead of the inverse | test 1 (`apply_logged` presence `RuntimeError` -> fallback rebuild; so ALSO assert the fallback did not run, via a counter, or the mutant passes) |
| `except IndexResourceLimit` arm deleted (back to rebuild) | test 2 |
| D1's count block deleted (back to load-then-count) | test 3 |
| count query drops `store_id` filter | test 4 with two stores sharing node ids |
| count uses `subject_id` for A (swapped) | test 4 (`object` / `product` shapes) and the runtime assertion |
| cycle point lookup skipped on the over-cap path | a test that an over-cap CYCLIC bridge write still raises the cycle `InvariantViolation` (add it to test 4's module) |

Instrument control: before each mutant, confirm the test passes on the unmutated tree in
the same process setup, and that the mutant actually applied (assert the anchor's match
count is 1, the `chr(92)` lesson in memory).

## 7. PostgreSQL leg (to run in the IMPLEMENT stage)

`bash scripts/pg_local.sh start`, export the printed DSN as `ZANZIBAR_TEST_DSN` (and
`ZANZIBAR_PG_REQUIRED=1`), run `tests/test_postgres_ha.py`, `tests/test_tk158_cheap_refusal.py`,
`tests/test_tk112_cap_policy.py`, `tests/test_reg17_closure_fanout_cap.py`, the
connectedstore concurrency / multi-instance modules; then `bash scripts/pg_local.sh stop`
and confirm no `postgres.exe` is left.

## 8. What the orchestrator must integrate (not edited by this lane)

- `CHANGELOG.md`: a "Fixed" line -- a `ClosureFanoutExceeded` refusal no longer loads the
  closure region or rebuilds the set engine.
- `formal/CORRESPONDENCE.md` sec 7.3 correction + pin regeneration (D3).
- `userdocs/` (READ 2026-10-22, `grep`): `userdocs/explanation/limits.md` § "A refused
  write is not free" lists all three costs and the 2026-10-14 table (8.4 s / 91 s). After
  TK158 its second and third bullets are false, and its "about 20 s was the set engine's
  admission" is better described as the one-time flow-graph build on the first write after
  open (sec 1c), which an admitted first write pays too. Rewrite with the post-change
  numbers. `userdocs/how-to/fanout-cap.md` line ~85 ("The refusal is complete ...")
  stays true.
- `src/zanzibar/schema/errors.py::ClosureFanoutExceeded` docstring is already FALSE-NOW on
  the default (cost doc sec (c)); not this item, but adjacent.
