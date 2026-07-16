# Perf — standing notes & guardrails (worklist currently empty; arc closed at round 5)

The living home for perf work. **The active worklist is currently empty.** The
measured optimization arc ran rounds 1–5 and **round 5 concluded the worklist is
exhausted** for everything the current harnesses can measure — the last two
candidates (N13, N14) were assessed and declined on a fresh 2026-07-16 profile.
What remains here is the **durable guidance** any future round must read first:
the fence, the confirmed dead-ends, an open correctness note, and the
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

- **Set-engine flow graph lacks bridge edges** (from the N17 parity find,
  `docs/spec-deviations.md` 2026-07-15 §3 residual): a MULTI-HOP cycle through a
  star bridge (rule edge out of a star userset + a rule chain back into a
  concrete of its shape) would still be set-accepted / graph-rejected. Needs
  bridge-aware `_flow_reaches` edges (in-bridges concrete→star per
  subject-wildcard shape, out-bridges star→concrete per owc shape). Correctness
  parity, not perf; no known corpus can build the shape today.
- `invariants.py:322-368` paranoia delta verifier is O(pairs × edges) per
  commit — production-paranoia cost, out of scope for bench numbers; noted so
  nobody profiles paranoia-on and panics.
- Dead ends already confirmed, do NOT chase: rc pre-guard on `_gc_subject_node`
  (bridge-stripping drops rc post-scan — load-bearing scan); removing
  `ops.new()` in `_starpop` without the `update` primitive (Population
  contract); N1/N2 (measured cold); P11 (struck); N13 (no headroom, round 5);
  N14 (no workload exercises it, round 5).

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
- **`rebuild()` / incremental evaluator catch-up** (`source.py:124-132`,
  `setengine/engine.py rebuild`): the failure-path rebuild is what makes
  rollback correct — the in-memory engine holds phantom state that can't be
  incrementally undone without an undo journal, and *that* is a new algorithm
  on the evaluator-freshness watermark contract. Cold path anyway (ordinary
  rejections take the cheap branch, `store.py:100-106`). Cost documented;
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
- Model policy (the loop that landed rounds 1–4): Fable orchestrates and
  reviews (trust contracts, wave gates, any Lean touch); Opus subagents
  implement below-the-model items. Scope drift toward a modeled algorithm
  stops the track and escalates.
