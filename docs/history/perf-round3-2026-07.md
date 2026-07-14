<!-- RETIRED 2026-07-15: round 3 (P12-M, P12a/b, N4–N9, P1-follow-up, P13) landed and pushed; this is the verbatim round-3 worklist/execution record, archived here. Living docs: open worklist → docs/perf-next-round.md; measured numbers → benchmarks/results/PERF_ANALYSIS.md; gates → docs/gate-runbook.md. -->

# Perf optimization — round 3 worklist + execution plan (rewritten 2026-07-14)

> **STATUS 2026-07-15: waves 0–2 COMPLETE and integration-gated** (full suite
> 531 + `verify.sh` all three phases, after each wave; the P1 follow-up
> additionally 6-seed fuzz-swept). Landed this round: P12-M, P12a, P12b, N4,
> N5, N6, N7, N8, N9, P1 follow-up. Numbers in `PERF_ANALYSIS.md` "Applied"
> (headlines: boolean sync write 221→207 stmts with composition overhead now
> at floor; graph lookup 74.5→3.0 / 134.8→5.0 stmts/op). **Everything left in
> this file is wave 3 = conditional**: needs a motivating measurement or a
> design call first. All work uncommitted pending review.

The living list of **remaining** performance opportunities, now including the
detailed P12 decomposition and the 2026-07-14 survey findings (N4–N14), plus the
execution plan for landing them via parallel Opus subagent tracks. Supersedes the
2026-07-14 morning version of this file. Measured-baseline record stays
[`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md);
cap-safe gate recipe stays [`docs/gate-runbook.md`](gate-runbook.md).

**Landed so far (git log is the audit trail):** P0, P1 (lookup reverse walk,
hybrid), P2, P3, P4, P5, P6, P7, P8, P9, P10, N3. See `PERF_ANALYSIS.md`
"Applied" for per-item numbers/mechanism. **P11 struck** (deployment reuses one
`ConnectedStore`; compile is once per store). **N1/N2 measured-and-skipped**
(N1: 0 redundant `_object_ids` calls; N2: <1% of profile). Do not revisit
without new profile evidence.

**Two structural facts that reshape this round** (2026-07-14 survey):

1. **The bench harness never exercises the composition layer.**
   `benchmarks/_harness.py` `build_set`/`build_graph` drive
   `SetEngine.add_tuple` / `WildcardIndex.add_tuple` directly, bypassing
   `ConnectedStore` / `advance_index` / the log / the cursor entirely. Every
   P12 round-trip is therefore **unmeasured today**, and no statements-per-op
   counter exists anywhere (grep: zero `before_cursor_execute` hits). P12-M
   fixes this first.
2. **The bench runs on in-memory SQLite**, where a round-trip is ~µs and
   secondary-index maintenance is cheap. Round-trip-count and index-count wins
   are real on the production targets (PostgreSQL/MySQL — the backends the
   whole `_lock_store` design exists for) but will be **understated in
   wall-time on the bench**. The honest primary metric for P12/N5 is
   **SQL statements per operation** (deterministic, contention-immune), with
   wall-time as a secondary signal.

**Reading the Lean column.** Per CLAUDE.md "Perf work & the Lean model": a
behavior-preserving micro-opt needs no Lean change (differential matrix +
hypothesis + conformance are the net). An optimization that *changes the
modeled algorithm* must update the corresponding Lean def and re-run
`formal/verify.sh` (phased), or log the gap in `formal/CORRESPONDENCE.md §7`.
**Nothing in waves 0–2 below is expected to need Lean work** — every item is
either below the model's abstraction (round-trips, copies, DB indexes,
allocation) or on an unmodeled surface (forward `lookup`, §8.1). Escalate to
the orchestrator (Fable) the moment an item's scope drifts toward modeled
territory (cascade order, reconcile structure, closure arithmetic, transaction
coupling, watermark semantics).

**The gate for every item:** `pytest tests/ -q` (~5.5 min, 531 passed) + the
targeted oracle gate for the surface touched (`tests/test_lookup_oracle.py`
for lookup/expand; `tests/test_matrix.py` for check/write parity), then the
phased `formal/verify.sh` (`lean` → `conf-heavy` → `conf-rest`) at wave
integration. Algorithm changes additionally need the multi-seed fuzz sweep
(gate-runbook §3) before push. Never edit a golden/oracle/snapshot result to
make an opt pass. Never run two heavy jobs (bench or pytest) concurrently.

---

## Execution plan (model policy: Fable orchestrates, Opus implements)

Rationale: this is the loop that landed the last round (P9 ‖ P3+P7) and closed
the formal roadmap. The orchestrator's non-delegable jobs: reviewing the P12b
guard and the N9 trust contract, sequencing the waves, running/watching the
integration gates, and keeping this doc + `PERF_ANALYSIS.md` honest.

- **Wave 0 (first, alone):** P12-M — the statements-per-write measurement
  bench. Everything else keys off its before-numbers.
- **Wave 1 (three parallel Opus tracks, disjoint files):**
  - **Track A — setengine algebra:** N4, then N8. Files: `setengine/memberset.py`,
    `setengine/engine.py` (read paths), `setengine/setops.py` if needed.
  - **Track B — storage DDL:** N5 (the whole index audit). Files:
    `setengine/models.py`, `index_v4/models.py`, `connectedstore/models.py` only.
  - **Track C — composition round-trips:** P12a, then P12b. Files:
    `index_v4/core.py` (`_lock_store` only), `connectedstore/apply.py`,
    `connectedstore/source.py`, `connectedstore/store.py`.
  - Tracks are file-disjoint (verified: setengine/ and index_v4/ don't
    cross-import; Track B touches only models files; Track C touches only the
    lock helper + connectedstore). Each track self-tests with its targeted
    gate; **the full suite + phased verify.sh run once at wave integration**
    (the P0 lesson: targeted gates miss cross-cutting interactions, and the
    paranoia checker only runs in the full index_v4 suite). Then re-run P12-M
    for after-numbers.
- **Wave 2 (after wave-1 integration):**
  - **Track D — graph read path:** N6, then N9 (both touch `index_v4/wildcard.py`,
    so sequenced within one track).
  - **Track E — setengine eval:** N7, then the P1 follow-up (both touch
    `setengine/engine.py`; the P1 follow-up is an **algorithm change** → ends
    with the multi-seed fuzz sweep).
  - Integration as wave 1.
- **Wave 3 (conditional — only with measurement justification from P12-M or a
  fresh profile):** N13, N14, N10, N11, N12, and the minor notes.

Subagent brief boilerplate (every implementation agent gets): the item's spec
below verbatim; the CLAUDE.md Lean rules; "targeted gate green before
reporting; do not run the full suite concurrently with anything; do not touch
goldens/oracle/snapshots; report actual test output".

---

## P12 — composition sync-write round-trips, decomposed (2026-07-14)

The old blanket warning ("do NOT casually touch") is replaced by a split: two
safe sub-items below the Lean model (P12a/P12b), one measurement prerequisite
(P12-M), and an explicit fence (P12c). The Lean model (`ReachedByW3d2E`,
`CORRESPONDENCE.md §6`) pins *what* is applied and *that* the cascade runs in
the same transaction — not how rows are fetched or how many round-trips it
takes. The fenced parts are the ones that would change the model.

**Round-trip inventory, one sync write with rewrite fan-out K** (verified
2026-07-14): ① log INSERT flush (`source.py:113`); ② `_lock_store`
`SELECT…FOR UPDATE` (`apply.py:90`); ③ **K more identical `_lock_store`
SELECTs** — one per `widx.add_tuple`/`remove_tuple` (`wildcard.py:252`; also
`:204,:278,:312`, `core.py:503,529,559,570,581`); ④ `session.refresh(cursor)`
SELECT (`apply.py:91`); ⑤ `log_rows` SELECT re-reading the row this
transaction just flushed (`apply.py:93`); ⑥ `outbox_watermark` SELECT, boolean
schemas only (`apply.py:100`); ⑦ cursor UPDATE flush + ⑧ COMMIT. Items ①⑦⑧ are
the irreducible exactly-once skeleton. ③ scales with fan-out; ②④⑤⑥ are
constants. Plus the index work itself (already optimized P2/P4/P6/P7).

### P12-M. Statements-per-write measurement bench — ✅ LANDED 2026-07-14 (wave 0)
**Measured** (`benchmarks/results/STMT_BASELINE_2026-07-14.md`, sync writes,
paranoia off — unreachable via `ConnectedStore`, which is the production mode):
pure-union add = **50.6 stmts/write** (lock re-takes **4.32**, not the predicted
1+K=2.66 — every `add_edge`/bridge fixup re-locks, not just each routed call);
boolean add = **221.2 stmts/write** (lock re-takes **14.52** — the cascade's
derived-family writes re-lock too). ⑤ `log_rows` = exactly 1.00/write both
schemas; ⑥ `outbox_watermark` = 0 on pure-union (skipped), 3.00 on boolean
(1 capture + ~2 cascade keyset drain reads — the drain reads are NOT fenced but
are modeled frontier machinery; leave them). Graph `lookup` = 74.5–134.8
stmts/op (N6's K+1 classify N+1 confirmed); graph `check` = 2.7–3.1 (already
lean; N13 has little headroom — deprioritized). Composition overhead proper
≈ 8/write once the lock undercount is corrected. **Net: P12a collapses 4.3→1
(union) / 14.5→1 (boolean) lock statements; index work (node/edge/residue,
~38–205 stmts) dominates the rest and is Track B/N5 + already-landed territory.**
- **What:** a new `benchmarks/stmt_bench.py` that drives a **real
  `ConnectedStore`** (sync schedule; pure-union AND boolean schema; varying
  fan-out) and counts SQL statements per op via an SQLAlchemy
  `before_cursor_execute` event listener, alongside wall-time. Also
  statements-per-check/lookup for the graph read path (feeds N6/N13).
  Nothing like it exists (verified). Deliverables: the script; before-numbers
  recorded in `benchmarks/results/STMT_BASELINE_2026-07-14.md`; a one-line
  pointer from `PERF_ANALYSIS.md`. Do NOT touch `scale_bench.jsonl`.
- **Why first:** it's the before/after evidence for P12a/P12b/N5 (invisible in
  SQLite wall-time), it validates the inventory above empirically (predicted:
  K+5-ish statements of pure composition overhead per sync write), and it
  tells us whether ③ (the K lock re-takes) dominates as predicted.
- **Risk:** none (additive tooling). **Lean:** none. **Gate:** the script runs
  clean; numbers sanity-checked against the inventory.

### P12a. Transaction-scoped `_lock_store` memo — ✅ LANDED 2026-07-14 (wave 1); lock SELECTs/write 4.32→1.00 (union), 14.52→1.00 (boolean)
- **Where:** `index_v4/core.py` `_lock_store` (~L80); call sites listed in ③.
- **What:** re-issuing `SELECT…FOR UPDATE` on a row this transaction already
  locked is a pure no-op round trip — the lock is held until commit/rollback.
  Memoize on the **live transaction object's identity**:
  ```python
  txn = self.session.get_transaction()
  if txn is not None and txn is self._locked_txn:
      return
  ...  # execute the FOR UPDATE select as today
  self._locked_txn = self.session.get_transaction()  # capture AFTER: the
      # lock SELECT itself may have autobegun the transaction
  ```
  **Verified mechanism** (SQLAlchemy 2.0.51, project env): `get_transaction()`
  returns a **fresh `SessionTransaction` object** after every commit/rollback,
  and `None` before autobegin — so the memo can never survive into a retried
  transaction (the exact failure mode to avoid: a retry skipping the real
  lock is the lost-update the lock exists to prevent, `core.py:15-21`). We
  hold a reference to the object, so identity comparison is sound (no id
  reuse). No savepoints/`begin_nested` anywhere in the repo (verified), so
  root-transaction identity is the whole story.
- **Why hot:** turns K+1 lock round-trips per sync write into 1. The largest
  constant on the composition write path; also helps every direct
  `WildcardIndex` write burst inside one transaction (harness, tests,
  processor façade writes).
- **Risk:** low-medium. The ONLY hazard is the memo outliving its transaction;
  the identity keying closes it structurally. A manual boolean flag is
  **forbidden** (rollback leak). Do not reorder anything else — the first
  `_lock_store` in `advance_index` must still precede the cursor read.
- **Lean:** none (locking/concurrency is not modeled).
- **Gate:** full `pytest tests/` (the SQLite-concurrency and connectedstore
  tests exercise rollback/retry paths) + conformance at integration. Post the
  P12-M delta.

### P12b. Sync-gated log-row handoff — ✅ LANDED 2026-07-14 (wave 1); log_rows SELECT/write 1.00→0.00; single-slot pending buffer; §8.1 logged
- **Where:** `connectedstore/source.py` `_append`/`add`/`remove`,
  `connectedstore/store.py` `_write`, `connectedstore/apply.py` `advance_index`.
- **What:** under sync, ⑤ re-SELECTs the single row this transaction just
  flushed. Thread it through instead:
  - `TupleSource._append` stashes the flushed row in `self._pending_rows`
    (a list); new `TupleSource.pop_pending_rows()` returns-and-clears it.
    The duplicate-add path appends nothing, so the hint is naturally empty
    there (`add` returns the watermark before any append — unchanged).
  - `ConnectedStore._write` passes `rows_hint=self.source.pop_pending_rows()
    or None` to `advance_index` (sync branch only). `catch_up` never passes a
    hint.
  - `advance_index(…, rows_hint=None)`: **after** `_lock_store()` +
    `session.refresh(cursor)` (unchanged, in that order), use the hint only if
    `rows_hint and cursor.applied_log_id == rows_hint[0].id - 1` and the hint
    ids are contiguous; else fall back to `log_rows` exactly as today. The
    fallback covers the real edge case: a store reopened `sync=True` with
    leftover async-era lag.
  - Guard review is an **orchestrator checkpoint** — the docstring contract
    (`apply.py:68-84`: contiguous prefix, monotone cursor, exactly-once) must
    remain literally true. Same rows, same order, same commit shape.
- **Why hot:** one SELECT per sync write; more importantly it makes the sync
  fast path allocation-free on the log-read side.
- **Risk:** medium (the guard is the whole item). Failure mode: applying a
  hint when intervening rows exist would skip/reorder log rows — the guard
  condition + contiguity check + fallback close it. The hint rows are
  session-flushed ORM objects, identical to what `log_rows` would return
  (same identity map).
- **Lean:** none — below the model, same class as P2's batching (row *source*,
  not row *content*). Log in `CORRESPONDENCE.md §8.1` at landing.
- **Gate:** full suite (esp. `test_connectedstore*`, async/catch_up tests) +
  conformance at integration; P12-M delta.

### P12c. FENCED — do not touch without a design round + Lean plan
- **`session.refresh(cursor)` (④):** the double-apply guard under the lock and
  the input to P12b's guard. Stays.
- **`outbox_watermark` capture-before-apply (⑥):** the cascade replay
  boundary; frontier machinery is modeled (`frontierRowsAbove`/`frontierMax`,
  `CORRESPONDENCE.md §5`). Other sessions legitimately raise the watermark
  between transactions; a stale-low cache replays foreign deltas. One SELECT
  per boolean write is the price. Stays.
- **Transaction coupling / exactly-once (①⑦⑧):** moving the cascade out of the
  write transaction, batching commits, async-first — genuine spec + Lean work
  (`ReachedByW3d2E` changes). Out of scope for this round.
- **`rebuild()` / incremental evaluator catch-up** (`source.py:124-132`,
  `setengine/engine.py rebuild`): the failure-path rebuild is what makes
  rollback correct — the in-memory engine holds phantom state that can't be
  incrementally undone without an undo journal, and *that* is a new algorithm
  on the evaluator-freshness watermark contract. Cold path anyway (ordinary
  rejections take the cheap branch, `store.py:100-106`). Cost documented;
  not changing. (N10 below defers *write-only auxiliary* state off the
  rebuild — a different, narrower thing.)

---

## Wave-1/2 items from the 2026-07-14 survey (N4–N9) + P1 follow-up

### N4. memberset: eliminate the defensive copies in `_ext` / `_normalize` — ✅ LANDED 2026-07-14 (wave 1); union/inter/sub −13…−29% both backends (microbench_memberset.py)
- **Where:** `setengine/memberset.py:98-103` (`_ext`), `:106-112` (`_normalize`).
- **What:** `_ext` copies both operands (`acc -= ops.new(m.neg); acc |=
  ops.new(m.pos)`); `_normalize` copies `ext_set` twice and `starpop` once.
  But `MemberSet.pos`/`neg` are **always `ops.freeze()` outputs** (verified at
  every construction site), and pyroaring `BitMap` supports `-=`/`|=`/`&`
  directly against `FrozenBitMap` (as `set` does against `frozenset`) —
  verified empirically. So: `_ext` → `acc -= m.neg; acc |= m.pos`;
  `_normalize` → `pos = ops.new(ext_set); pos -= starpop; starpop -= ext_set;
  return MemberSet(ops.freeze(pos), frozenset(stars), ops.freeze(starpop))`
  (order preserved: `pos -= starpop` reads `starpop` before it mutates; the
  caller-owned `ext_set` is only read). Net: ~7 defensive O(set) copies per
  algebra op → 1. **Record the invariant** ("pos/neg are always freeze
  outputs") as a comment — nothing enforces it at runtime; the homomorphism
  property test is the net.
- **Why hot:** every `union`/`intersect`/`subtract` on the expand /
  lookup_reverse path calls `_ext` twice + `_normalize` once. Same copy class
  as the two biggest wins to date (`direct_expand` 78cfc2f, `_starpop` P10),
  one layer up. Largest on star-heavy sets (demorgans/wide reverse).
- **Expected win:** constant-factor on a very hot inner path; scales with star
  population. Micro-bench like P10's to size it.
- **Risk:** low. **Lean:** none (`MemberSet.lean` models the pos/stars/neg
  *result*, byte-identical; `_ext`/`_normalize` are unmodeled internals).
- **Gate:** `tests/test_memberset.py` (the 3000-case homomorphism/ghost-safety
  net, both SetOps) + `test_matrix.py` + `test_lookup_oracle.py`; conformance
  at integration.

### N5. DB index audit: drop dead/redundant secondary indexes, add the composites — ✅ LANDED 2026-07-14 (wave 1); 13 indexes dropped, 3 composites added; per-table audit in the track report / PERF_ANALYSIS
One agent, models files only. Per-insert index maintenance is pure overhead on
THE bottleneck (graph build 15–156 writes/s; every write maintains every
index). All grep-audited 2026-07-14: no in-repo query uses any index slated to
drop (composite-unique leftmost prefixes cover every access pattern).
- **`setengine/models.py` `TupleV1` (:34-39):** drop the 6 single-column
  indexes (`subject_predicate`/`subject_type`/`subject_name`/`relation`/
  `object_type`/`object_name`). The only filtered query, `_row`
  (`engine.py:391-400`), conjoins all seven columns — served by
  `tuple_v1_unique`. `rebuild()` filters `store_id` only (index kept). 9 → 3
  B-trees per row.
- **`index_v4/models.py` `NodeV4` (:40-46):** drop the 4 single-column indexes
  (`predicate`/`type`/`name`/`wildcard`) — every NodeV4 query filters a
  `(store_id, predicate, type[, name][, wildcard])` prefix or by id
  (`core.py:422-427`, `processor.py:186-189,1013-1016,1029-1034`,
  `wildcard.py:190-194`); all covered by `node_v4_unique_constraint`. Keep
  `store_id` (FK).
- **`index_v4/models.py` `EdgeV4` (:65-67):** drop the standalone `store_id`
  and `subject_id` indexes (covered by `edge_v4_unique_constraint` prefixes);
  **replace** the standalone `object_id` index with a composite
  `(store_id, object_id)` (object-keyed scans: `core.py:320,617`,
  `processor.py:260`). ⚠ **MySQL/InnoDB caveat:** InnoDB requires an index
  whose *leftmost* column is the FK column and auto-creates one if missing —
  so dropping `subject_id`'s index buys nothing there (a hidden one comes
  back) and is still correct; on SQLite/PostgreSQL the drop is a real win.
  Note this in the commit message.
- **`index_v4/models.py` `ResidueV1` (:99):** drop the dead `relation` index —
  the docstring's "by-relation residue scan" does not exist; no query filters
  it (`_collect_residue_memberships` scans by `store_id`, `_residue_row` by
  `object_node_id`). Keep the column; fix the docstring.
- **`index_v4/models.py` `DeltaOutboxV1` (:126):** widen `store_id` →
  composite `(store_id, id)` (replacement, not additive). Serves the keyset
  drain (`outbox_rows`: `store_id AND id > ? ORDER BY id`, once per stratum
  round) and the watermark (`ORDER BY id DESC LIMIT 1`) as index-only seeks.
  Marginal on SQLite (rowid ordering is free), real on PostgreSQL.
- **`connectedstore/models.py` `TupleLogV1` (:36):** same widening,
  `store_id` → `(store_id, id)` — `log_rows` (per sync write) and
  `log_watermark` are the same keyset/max-id shapes, and the log is
  **append-only forever**, so this is asymptotic protection as it grows.
- **`connectedstore/models.py` `IndexCursorV1` (:49-56):** drop the redundant
  `index=True` on `index_store_id` (the `UniqueConstraint` already indexes it).
- **Risk:** low (indexes are perf-only; correctness invariant). The one hazard
  — a query silently regressing to a scan — is closed by the grep audit; the
  implementing agent must re-run that audit before landing.
- **Lean:** none. **Gate:** full suite + conformance at integration; P12-M +
  a write-heavy `scale_bench` point for after-numbers (expect modest SQLite
  wall-time movement; the statement/plan-level justification is the claim).

### N6. Graph lookup: batch the `_classify_into` N+1 — ✅ LANDED 2026-07-15 (wave 2); K+1 → 1+⌈K/900⌉ classify SELECTs via `_load_nodes` batch
- **Where:** `index_v4/wildcard.py:556-563` (`_classify_into` → `_node_by_id`
  per id), driven by `:547-548` and `:553-554`.
- **What:** `lookup`/`lookup_reverse` get the full result id-set in one query,
  then re-fetch each node row individually to classify concrete-vs-wildcard —
  K+1 round trips for K results. Batch-load the id set in one chunked `IN`
  (the existing `core._load_nodes` / `processor._nodes_by_ids` pattern) and
  classify from the map. K+1 → 2.
- **Why hot:** the façade lookup surface — asymptotic in result size.
- **Risk:** low (identity map makes batched rows identical; classification
  unchanged; `_node_by_id`'s other callers not in loops).
- **Lean:** none (forward lookup unmodeled, §8.1; result unchanged anyway).
- **Gate:** `test_lookup_oracle.py` + `test_matrix.py`; conformance at
  integration.

### N7. Set engine: memoize `_instances_of_type` per evaluation + delete dead `query_names` — ✅ LANDED 2026-07-15 (wave 2); per-eval memo dict, dead param+var deleted (all call sites passed empty query_names — verified)
- **Where:** `setengine/engine.py:607-612`; call sites `:733,:756,:862,:882`;
  dead var `:622`.
- **What:** `_instances_of_type` scans **all interned keys** — O(interner) —
  on the ∀-grant / star-parent paths, and all four call sites pass
  `frozenset()` as `query_names` (the union arm at `:611` is always empty).
  The interner never mutates during a read, so memoize by type within one
  evaluation (dict threaded like the `low` cell / P9 cache). Separately,
  `check` builds a `query_names` set at `:622` it never uses — delete.
  A stronger variant (a `names_of_type` index maintained in the `Interner`)
  would share across the many checks inside one `lookup` — do the per-eval
  memo first, escalate to the interner index only with measurement.
- **Why hot:** repeated O(interner) scans on `T:*#P`/star-tupleset schemas —
  **not exercised by current profiled workloads; needs measurement**, which is
  why it's wave 2 not wave 1.
- **Risk:** low (per-eval memo). **Lean:** none. **Gate:** `test_matrix.py`
  (star/∀ schemas 4-way) + `test_lookup_oracle.py` + hypothesis; conformance
  at integration.

### N8. Set engine read-path micro pair — ✅ LANDED 2026-07-14 (wave 1, rode with N4)
- **(a) TTU walks:** `engine.py:744` and `:872` build
  `list(ns.entities) + list(ns.usersets)` per node purely to iterate —
  `itertools.chain(ns.entities, ns.usersets)` (reads never mutate
  `node_sets`; laziness is safe).
- **(b) `direct_expand` small copy:** `engine.py:850` still wraps
  `ns.entities` in `ops.new()`; `&` doesn't mutate operands, so
  `pos |= (ns.entities & pop((rtype, '...')))` is equivalent. (The landed fix
  only removed the O(population) side.)
- **Risk:** low. **Lean:** none. **Expected win:** small constants; bundled
  here because Track A is already in these functions with the right gates.
- **Gate:** rides N4's.

### N9. Apply-path double validation: pre-validated graph write fast-path — ✅ LANDED 2026-07-15 (wave 2); `_add/_remove_tuple_trusted`, sole external caller `_apply_row`; public API validates unchanged; trust contract reviewed
- **Where:** `setengine/engine.py:338` validates; then `connectedstore/apply.py:55-57`
  → `index_v4/wildcard.py:246` re-validates **once per derived triple**.
- **What:** one raw write is charset-validated by the set engine (6 regex
  matches), then the graph re-validates 6·(1+k) fields for a k-leaf fan-out —
  where the only varying field is the compiler-generated leaf predicate
  (`<rel>.<idx>`, charset-valid by construction). Add an internal
  pre-validated entry point (e.g. `_add_tuple_trusted`) used **only** by
  `_apply_row`; the public `add_tuple` keeps validating (it's public API used
  directly by tests/harness).
- **Risk:** medium — an internal trust contract; get the routing wrong and an
  unvalidated identifier reaches the index. **Orchestrator reviews the
  contract.** Below the Lean model (identical accept/reject set — the skipped
  checks provably always pass on this path).
- **Expected win:** constant per write, scales with fan-out; measure with
  P12-M before deciding it's worth the contract. **Gate:**
  `test_fuzz_names.py`, `test_connectedstore_source.py`, `test_matrix.py`
  (validity parity), conformance.

### P1 follow-up: tighter object-wildcard `lookup` fallback — ✅ LANDED 2026-07-15 (wave 2); ALGORITHM CHANGE, fuzz-swept
- **Where:** `setengine/engine.py` — was `if self.schema_info.object_wildcard_shapes:`
  (any shape at all forced the O(store) sweep); now a precomputed
  `_owc_needs_sweep` (`_owc_lookup_needs_sweep()`, computed once in `__init__`).
- **⚠ The 2026-07-14 spec here was WRONG, in two ways (recorded per the honesty
  norm; the landed predicate is the corrected one):**
  1. It said to match `(T, rel)` against `_chain_targets`/`_ttu_map` *tupleset*
     keys — the **wrong end of the TTU**. The bridge the walk can't cross is
     the TTU's **target relation on the parent type** (`viewer` in
     `viewer from parent`), so the test is `r ∈ ttu_targets` for
     `r ∈ {rel} ∪ _object_deps[(T, rel)]` (the Computed reverse-closure).
  2. TTUs aren't the only bridge: a **non-wildcard userset restriction
     `[T#r]`** lifts wildcard-covered members onto another object too. (A
     *wildcard* userset `[T:*#r]` is not a bridge — it lands on the star node
     the walk already reaches.)
- **Landed predicate** (deliberately over-inclusive — a needless fallback is
  only slow; a missed one drops results): fall back iff for some
  object-wildcard shape `(T, rel)` and some `r ∈ {rel} ∪ _object_deps[(T,rel)]`,
  `r ∈ ttu_targets` or `(T, r)` is a non-wildcard userset restriction anywhere.
  Validated empirically pre-gate: walk arm oracle-exact over ~1600 random
  states; fallback arm confirmed genuinely walk-incomplete. `wildcards.fga`/
  `gdrive.fga` → still sweep; github/boolean/demorgans → walk.
- **Lean:** none (forward lookup unmodeled, §8.1). **Gate run:** strict
  `test_lookup_oracle.py` (16) + matrix/wildcard-property (15) + hypothesis
  (12) + **6-seed sweep of `test_lookup_hypothesis.py` (7/19/31/53/71/97) all
  green**.

---

## Wave 3 — conditional items (need measurement or a design call first)

### N10. Defer flow-graph construction on read-triggered `rebuild()`
`setengine/engine.py:290-298,:434-438`: rebuild replays every tuple through
`_ruleset.apply()` purely to populate `_flow_adj`/`_edge_count` — state that
only write-time cycle detection reads. `refresh_evaluator` fires on
rollback/tokened-read fallback and is often followed by reads only. Lazy-build
on first write instead. **Medium risk** (flow graph must be complete before
the first cycle check; lazy build must reconstruct from in-memory state).
Distinct from the fenced incremental-catch-up (no watermark contact). Boolean
schemas already skip (`:489`) — this is for union/TTU schemas. Gate:
`test_matrix.py` cycle-rejection parity, storage/eval tests,
`conf-heavy` (rebuild-after-remove), hypothesis restoration.

### N11. Duplicate-add: return the known watermark instead of `SELECT MAX(id)`
`connectedstore/source.py:88-91`. One round trip per duplicate write; bites
retry-heavy workloads only. **Semantic judgement required**: `log_watermark`
is the global store head, `evaluator_watermark` this session's — equal in the
single-session deployment, but confirm the token contract only needs "≥ enough
to see this (absent) write" before changing. Skip unless P12-M shows
duplicates matter.

### N12. Cache `EntityPattern`s in `RelationalTriplePattern`
`zanzibar_utils_v1.py:174-182`: `@property`s rebuild frozen sub-patterns per
`match()` call. Low risk, likely <1% (P0 dispatch already prunes candidates).
Must preserve compiled-RuleSet snapshot bytes (`tests/snapshots/`). Bundle
with any future compile-layer touch rather than standalone.

### N13. Graph `check`: batch node resolution (3–5 sequential point SELECTs → ~2)
`index_v4/wildcard.py:331-388,:428-462`. check IS round-trip-bound (388–682/s
flat), so this is real — but resolution restructuring must preserve exact
probe semantics (position rule, missing-node-drops-key, `:349,:363-374`), and
it's fiddly. Wait for P12-M statements-per-check numbers; medium risk.
Behavior-preserving if done right. Gate: matrix 4-way + lookup oracle +
conformance.

### N14. Hoist `_keys_referencing` to one residue scan per `_map_deltas_to_keys` call
`index_v4/processor.py:316-332`, called per GC'd subject at `:836-839`. M
subject GCs = M full ResidueV1 scans + JSON decodes; hoist to one snapshot
scan building `subject_id → [Key]`. **Scope to the step-A loop only** (the
reconcile-step-5 calls mutate residues mid-flight). Only bites TTU/userset
schemas N3 doesn't already elide, on churn-heavy removes. Medium risk —
modeled delta→key territory (same class as P6): behavior-preserving only if
the key set is provably identical; full differential + hypothesis + paranoia
gate. Niche; needs a workload that shows it first.

## Round 4 candidates (added 2026-07-15): make the graph index testable/usable at scale

The strategic driver: the graph index's value proposition (O(1) durable
DB-served reads, no per-process RAM ∝ store, many replicas, structural
freshness tokens) only materializes at scales the bench has never reached —
graph curves have 3 small anchor points because **build throughput** (15–156
writes/s) makes a 10⁵–10⁶-tuple index impractical to construct. These items
attack build/apply throughput, in ROI order. Note the asymmetry: steady-state
*incremental* write cost is largely the algorithm itself (closure maintenance
is O(ancestors×descendants) per write — the memoization you're buying); the
big recoverable waste is in **bulk construction** and per-batch SQL overhead.

### P13. Bulk closure builder for `build_index` — ✅ LANDED 2026-07-15; **43.9–48.6× on pure-union builds, 33.6× on the isolated boolean load phase** (boolean *total* build 1.44× — the unchanged shared `backfill()` dominates it; that's the next bulk-phase candidate). Identity gate green over 4 corpora incl. multigraph fan-in (m≥2); design: `docs/p13-bulk-build-design.md`
- **Where:** `connectedstore/build.py` (currently replays per tuple through
  `ruleset.apply` → `widx.add_tuple`, paying the full incremental closure
  update + admission-grade SQL per triple); `index_v4` gains a bulk
  constructor.
- **What:** offline-build the final state directly: materialize all routed
  direct edges in memory, topologically order (admission guarantees acyclic),
  compute per-pair path counts by DP (the closed form the Lean T4 model
  states: `pathCount` as Σ of products — arguably *closer* to the model than
  the incremental twin), then bulk-INSERT nodes/edges with final counts;
  wildcard bridges seeded per shape; boolean residues via the existing
  `proc.backfill()` bulk pass (P6 precedent). Incremental cost today is Σᵢ
  O(Aᵢ×Dᵢ) region work + per-write SQL; bulk cost is O(V·E) DP + one bulk
  write of the final closure — each final pair written once, not incremented
  per contributing write.
- **Pin (this is the crux):** a differential **bulk ≡ incremental-replay
  state-equality gate** — build the same store both ways, compare full
  node/edge/residue state (the conformance state extractor already knows how
  to project state) + run the I1–I12 invariant checker on the bulk result +
  the matrix on top. **Lean:** the incremental add is the modeled algorithm;
  the bulk builder is an alternative *constructor of the same modeled state*.
  Log in `CORRESPONDENCE.md §7/§8` with the state-equality gate as the net
  (or model it later if it becomes load-bearing). Orchestrator/design review
  required before implementation; outbox semantics need a decision (offline
  build should suppress/discard per-flip outbox rows the way `backfill`
  does — verify).
- **Why:** turns "graph at 100k tuples" from hours into minutes → unlocks M2.
- **Risk:** medium-high (new constructor for ref-counted state); the
  state-equality gate is what makes it shippable.

### N15. Per-batch node-resolution cache in the apply/cascade path
- **What:** node_v4 SELECTs are 11.6/write (union) and 103/write (boolean) —
  25–50% of all write statements; the same subject/object/bridge/leaf nodes
  are re-resolved per row within one `advance_index` batch / cascade run.
  Cache `(pred, type, name, wildcard) → NodeV4` for the duration of a batch,
  invalidating on node creation/GC-deletion (the hard part — GC deletes node
  rows mid-cascade; a stale hit would resurrect a dead id, so the cache must
  be invalidated by the GC paths or keyed to check liveness).
- **Risk:** medium (GC invalidation). **Lean:** none (resolution is below the
  model). **Gate:** full suite incl. paranoia + conformance; stmt_bench delta.

### N16. Bulk-INSERT the emit/outbox and edge rows
- **What:** INSERTs are ~40% of union write statements (20.4/write). Outbox
  `_emit` rows are plain value inserts — batchable via `executemany`/
  `session.execute(insert(...), [rows])` at flush points; edge inserts ride
  the P2 batch already but flush row-at-a-time. Constant-factor; biggest on
  networked DBs (per-statement latency), visible in stmt counts everywhere.
- **Risk:** low-medium (ordering: outbox ids must stay monotone within the
  txn — verify autoincrement behavior under executemany on SQLite/Postgres).
  **Lean:** none. **Gate:** full suite + conformance (outbox order is
  load-bearing for the cascade) + stmt_bench.

### M2. Graph scale-bench (after P13): find the pareto crossover
- **What:** extend `scale_bench` to graph curves at 3 decades (10⁴–10⁶),
  built via P13, measuring check/lookup/reverse statements AND wall-time vs
  the set engine at the same scales — plus set-engine **rebuild time and RSS**
  at each scale (its real scaling limits: cold-start and RAM, not per-op
  speed). Deliverable: the actual crossover chart the architecture docs can
  cite instead of the current "graph wins at scale" extrapolation from 3
  anchor points.

### Minor notes (grab-bag, land opportunistically with adjacent work)
- `core.py:377-403` remove_node neighbour-debit tail N+1 (batchable `IN`; cold
  path). `core.py:454-464` `_require_live_nodes` 2 SELECTs → 1.
- `wildcard.py:502-508` `_collect_residue_memberships` builds sets for
  single-membership tests and decodes `upos` unconditionally.
- `invariants.py:322-368` paranoia delta verifier is O(pairs × edges) per
  commit — production-paranoia cost, out of scope for bench numbers; noted so
  nobody profiles paranoia-on and panics.
- Dead ends already confirmed, do NOT chase: rc pre-guard on `_gc_subject_node`
  (bridge-stripping drops rc post-scan — load-bearing scan); removing
  `ops.new()` in `_starpop` without the `update` primitive (Population
  contract); N1/N2 (measured cold); P11 (struck).

---

## Parallelization / hygiene (carried forward + this round)

- `setengine/` and `index_v4/` do not cross-import (verified 2026-07-14);
  wave tracks above are file-disjoint by construction — keep them that way; a
  track that discovers it needs a file outside its list stops and reports.
- **Full suite + phased verify.sh at every wave integration**, not just
  per-track targeted gates (the P0 lesson; paranoia checker only runs in the
  full suite).
- **Algorithm changes fuzz before push** (gate-runbook §3) — this round that
  means the P1 follow-up (and anything that drifts into algorithm territory).
- **Measurement hygiene:** never two bench/pytest processes at once. New
  statement-count results go in `STMT_BASELINE_2026-07-14.md` +
  `PERF_ANALYSIS.md` "Applied" entries; never overwrite `scale_bench.jsonl`.
- Fable orchestrates and reviews (P12b guard, N9 trust contract, wave gates);
  Opus subagents implement. **Fable-level Lean work is expected NOWHERE in
  waves 0–2**; any scope drift toward modeled algorithms stops the track and
  escalates.
