# Perf — standing notes & guardrails (round-6 CANDIDATE worklist open; rounds 1–5 closed)

The living home for perf work. **The active worklist is the round-6 CANDIDATE
list**: [`perf-round6-audit-2026-08.md`](perf-round6-audit-2026-08.md) — 18
code-verified but **UNMEASURED** findings plus 16 unverified leads from the
2026-08-15 two-backend audit; nothing from it has landed. The measured
optimization arc ran rounds 1–5 and **round 5 concluded that worklist was
exhausted** for everything the then-current harnesses could measure — the last
two candidates (N13, N14) were assessed and declined on a fresh 2026-07-16
profile. The rest of this file is the **durable guidance** any round must read
first: the fence, the confirmed dead-ends, an open correctness note, and the
measurement/gate hygiene.

- Round 3 (P12-M, P12a/b, N4–N9, the P1 follow-up, P13) landed and pushed; retired
  verbatim in [`docs/history/perf-round3-2026-07.md`](history/perf-round3-2026-07.md).
- Round 4 (R4-BF, N15, N16, M2 + follow-up, N17, N10, N18, the index_v4 grab-bag
  micros, N12; N11 design-skipped) landed and pushed; retired verbatim in
  [`docs/history/perf-round4-2026-07.md`](history/perf-round4-2026-07.md).
- Round 5 (2026-07-16) landed **nothing** — it assessed the two remaining
  candidates (N13, N14) and declined both on a fresh profile; the assessment
  record (with both candidate write-ups verbatim) is retired in
  [`docs/history/perf-round5-2026-07.md`](history/perf-round5-2026-07.md).
- Round 6 (opened 2026-08-15) has **landed nothing**: a 24-agent,
  adversarially-verified audit of both backends produced the candidate list in
  [`perf-round6-audit-2026-08.md`](perf-round6-audit-2026-08.md). Per
  "Reopening a round" below, each item needs its motivating measurement —
  the audit satisfies the design-call half, not the measurement half. The doc
  retires to `docs/history/perf-round6-2026-08.md` when the round closes.
  **The measurement half is now done for ALL EIGHTEEN (2026-08-17)**:
  [`benchmarks/results/R6_PROFILE_2026-08-17.md`](../benchmarks/results/R6_PROFILE_2026-08-17.md),
  instruments `benchmarks/profile_r6.py` (reads) and `benchmarks/profile_r6_write.py`
  (write / cascade / bulk / space). **Land in this order:** `R6-10` (59.8% of
  incremental boolean write time — the headline) → `R6-6` (4.75 → 1.75 statements
  per `check`) → `R6-11` (cache torn down 8× per reconcile; one-line fix) →
  `R6-5` (32.7% ORM construction) → `R6-4` (30.1% and growing) → `R6-9` (4.51
  point SELECTs per write) → `R6-18` (53.1% off the biggest table) → `R6-16`
  (1.00 unconsumed outbox row per closure edge — co-design with `R6-7`/`R6-8`,
  which read those rows as paranoia's worklist) → `R6-7`+`R6-8` (gate-only, but
  per-commit cost grows **14×** over 336 commits) → `R6-1` (91.4% ceiling;
  prototype the two-tier memo first — the naive one is a correctness bug).
  **Declined on an upper bound:** `R6-15` (topo sort is 0.9% of a bulk build),
  `R6-12` (1.00× intra-run), `R6-14` (5.0%), `R6-2` (24% of a non-bottleneck at
  the price of a Lean model change). **Unreachable by any benchmarked workload:**
  `R6-3` = `R6-17`, and its bulk twin `R6-13` — 0 calls each.
  **`R6-19`, filed 2026-08-18** from the pass itself:
  `bulk_backfill._reconcile_subject_edge` at 25.3% of a bulk build belonged to no
  candidate. Filing decomposed the share — **cumulative 25.4%, self 2.0%** — so the
  item is a *call-site fan-out* (~139 plan evaluations per object reconcile), not a
  slow function, and its in-function ceiling is 2%. Overlaps declined `R6-14`.

- **Measured numbers** (all landed items, per-item mechanism/before-after):
  [`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md)
  "Applied" — git log is the audit trail. Round-4 scale-bench narrative:
  [`M2_FOLLOWUP_2026-07-15.md`](../benchmarks/results/M2_FOLLOWUP_2026-07-15.md) /
  [`N18_FOLLOWUP_2026-07-16.md`](../benchmarks/results/N18_FOLLOWUP_2026-07-16.md) /
  [`ROUND4_COMPARISON_2026-07-16.md`](../benchmarks/results/ROUND4_COMPARISON_2026-07-16.md).
- **Gates** (cap-safe recipe, phased `verify.sh`, fuzz sweep): don't duplicate —
  [`docs/gate-runbook.md`](gate-runbook.md).
- **The Lean column.** Per CLAUDE.md "Perf work & the Lean model": a
  behavior-preserving micro-opt needs no Lean change (differential matrix +
  hypothesis + conformance are the net). An optimization that *changes the modeled
  algorithm* must update the corresponding Lean def and re-run `formal/verify.sh`
  (phased), or log the gap in `formal/CORRESPONDENCE.md §7`.

## Reopening a round

Any new item is **conditional**: it needs a motivating measurement (from
`benchmarks/stmt_bench.py` / `scale_bench` / a fresh profile) or a design call
before it's worth landing. **Never edit a golden/oracle/snapshot result to make
an opt pass. Never run two heavy jobs (bench or pytest) concurrently** (CPU
contention corrupts bench numbers). Round 5's two declines are the current
evidence that the measurable surfaces are tapped out — re-derive a fresh profile
before reopening either.

---

## Minor notes (grab-bag, land opportunistically with adjacent work)

- ~~**Set-engine flow graph lacks bridge edges**~~ — RESOLVED 2026-07-16. The
  multi-hop star-bridge cycle proved constructible (not merely latent) and the
  flow graph is now bridge-aware; both backends reject it. See
  `docs/spec-deviations.md` (2026-07-16 entry) and `HANDOFF.md`. Correctness
  parity, was never a perf item.
- `invariants.py::verify_outbox_deltas` paranoia delta verifier is O(pairs × edges) per
  commit — production-paranoia cost, out of scope for bench numbers; noted so
  nobody profiles paranoia-on and panics. Now also filed as **R6-8** in the
  round-6 audit (a per-source BFS rewrite) — still gate/full-tier scope, not a
  bench item.
- Dead ends already confirmed, do NOT chase: rc pre-guard on `_gc_subject_node`
  (bridge-stripping drops rc post-scan — load-bearing scan); removing
  `ops.new()` in `_starpop` without the `update` primitive (Population
  contract); N1/N2 (measured cold); P11 (struck); N13 (no headroom, round 5);
  N14 (no workload exercises it, round 5).
- **Store-level write quota — DECLINED 2026-07-29, do NOT re-propose.**
  `ZANZIBAR_MAX_CLOSURE_FANOUT` bounds what ONE add may materialise; a *store-level*
  quota is not wanted ("it might be slow but it should not be limited by perf"). The
  "detect a DoS fan-out and bulk-rebuild instead" variant was **measured and refuted**:
  bulk wins 7–15× on TIME, but closure SIZE is byte-identical (a property of the
  topology), the worst single lock hold goes 105 ms → 2,685 ms at N=480, and the
  rebuild's outbox emits **zero REMOVED** — the fail-open direction. `sync=False` is
  the answer. Reopening means meeting that measurement, not re-arguing it:
  `docs/spec-deviations.md` (2026-07-29c entry).

---

## P12c — FENCED: do not touch without a design round + Lean plan

A standing do-not-touch list (from the round-3 P12 decomposition). These are the
composition-write round-trips that would change the modeled algorithm; leave them.

- **`session.refresh(cursor)`:** the double-apply guard under the lock and
  the input to P12b's guard. Stays.
- **`outbox_watermark` capture-before-apply:** the cascade replay
  boundary; frontier machinery is modeled (`frontierRowsAbove`/`frontierMax`,
  `CORRESPONDENCE.md §5`). Other sessions legitimately raise the watermark
  between transactions; a stale-low cache replays foreign deltas. One SELECT
  per boolean write is the price. Stays.
- **Transaction coupling / exactly-once (log INSERT flush / cursor UPDATE
  flush / COMMIT):** moving the cascade out of the write transaction, batching
  commits, async-first — genuine spec + Lean work (`ReachedByW3d2E` changes).
  Out of scope.
- **`rebuild()` / incremental evaluator catch-up** (`source.py::assert_read_isolation`,
  `setengine/engine.py rebuild`): the failure-path rebuild is what makes
  rollback correct — the in-memory engine holds phantom state that can't be
  incrementally undone without an undo journal, and *that* is a new algorithm
  on the evaluator-freshness watermark contract. Cold path anyway (ordinary
  rejections take the cheap branch, `store.py::ConnectedStore.__init__`). Cost documented;
  not changing. (N10 deferred *write-only auxiliary* state off the rebuild —
  a different, narrower thing.)

---

## Standing hygiene / gate notes

- `setengine/` and `index_v4/` do not cross-import (verified 2026-07-14); keep
  parallel tracks file-disjoint — a track that discovers it needs a file
  outside its list stops and reports.
- **Full suite + phased verify.sh at every wave integration**, not just
  per-track targeted gates (the P0 lesson; the paranoia checker only runs in
  the full index_v4 suite). Cap-safe recipe: [`docs/gate-runbook.md`](gate-runbook.md).
- **Algorithm changes fuzz before push** (gate-runbook §3) — any item whose
  Lean line says it touches modeled territory ends with the multi-seed fuzz sweep.
- **Measurement hygiene:** never two bench/pytest processes at once. New
  statement-count results go in `STMT_BASELINE_2026-07-14.md` +
  `PERF_ANALYSIS.md` "Applied" entries; never overwrite `scale_bench.jsonl`.
  **Before believing a profile, run the five-second test in
  [`sabotage-procedure.md`](sabotage-procedure.md) §"A MEASUREMENT is an assurance
  step too"** — a probe that ran on nothing reports a clean small share, and that
  cost four corrected verdicts in one session (2026-08-17).
- Model policy (the loop that landed rounds 1–4): Fable orchestrates and
  reviews (trust contracts, wave gates, any Lean touch); Opus subagents
  implement below-the-model items. Scope drift toward a modeled algorithm
  stops the track and escalates.
