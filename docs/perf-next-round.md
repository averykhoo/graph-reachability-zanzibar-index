# Perf optimization — open worklist (slim, opened 2026-07-16 after round 4)

The living list of **remaining, not-yet-landed** performance opportunities.

- Round 3 (P12-M, P12a/b, N4–N9, the P1 follow-up, P13) landed and pushed; its
  full worklist + execution record is retired verbatim in
  [`docs/history/perf-round3-2026-07.md`](history/perf-round3-2026-07.md).
- Round 4 (R4-BF, N15, N16, M2 + follow-up, N17, N10, N18, the index_v4 grab-bag
  micros, N12; N11 design-skipped) landed and pushed; its execution record is
  retired verbatim in
  [`docs/history/perf-round4-2026-07.md`](history/perf-round4-2026-07.md).

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
  (phased), or log the gap in `formal/CORRESPONDENCE.md §7`. Each item's Lean line
  below states which side it sits on.

Everything here is **conditional**: it needs a motivating measurement (from
`benchmarks/stmt_bench.py` / `scale_bench` / a fresh profile) or a design call before
it's worth landing. Nothing below is expected to need Lean work unless its line says
so. **Never edit a golden/oracle/snapshot result to make an opt pass. Never run two
heavy jobs (bench or pytest) concurrently** (CPU contention corrupts bench numbers).

---

## Wave 3 — conditional items (need measurement or a design call first)

### N13. Graph `check`: batch node resolution (3–5 sequential point SELECTs → ~2) — DEPRIORITIZED
`index_v4/wildcard.py:331-388,:428-462`. check IS round-trip-bound (388–682/s
flat), so this is real — but **`stmt_bench` measured graph `check` at 2.7–3.1
stmts/op already (little headroom)**, so it's deprioritized: resolution
restructuring must preserve exact probe semantics (position rule,
missing-node-drops-key, `:349,:363-374`), and it's fiddly, for a small win.
Revisit only if a fresh statements-per-check profile shows more headroom;
medium risk. Behavior-preserving if done right. Gate: matrix 4-way + lookup
oracle + conformance.

### N14. Hoist `_keys_referencing` to one residue scan per `_map_deltas_to_keys` call
`index_v4/processor.py:316-332`, called per GC'd subject at `:836-839`. M
subject GCs = M full ResidueV1 scans + JSON decodes; hoist to one snapshot
scan building `subject_id → [Key]`. **Scope to the step-A loop only** (the
reconcile-step-5 calls mutate residues mid-flight). Only bites TTU/userset
schemas N3 doesn't already elide, on churn-heavy removes. Medium risk —
modeled delta→key territory (same class as P6): behavior-preserving only if
the key set is provably identical; full differential + hypothesis + paranoia
gate. Niche; needs a workload that shows it first.

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
  contract); N1/N2 (measured cold); P11 (struck).

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
  not changing. (N10 archived above deferred *write-only auxiliary* state off the
  rebuild — a different, narrower thing.)

---

## Standing hygiene / gate notes

- `setengine/` and `index_v4/` do not cross-import (verified 2026-07-14); keep
  parallel tracks file-disjoint — a track that discovers it needs a file
  outside its list stops and reports.
- **Full suite + phased verify.sh at every wave integration**, not just
  per-track targeted gates (the P0 lesson; the paranoia checker only runs in
  the full index_v4 suite). Cap-safe recipe: [`docs/gate-runbook.md`](gate-runbook.md).
- **Algorithm changes fuzz before push** (gate-runbook §3) — any item whose
  Lean line says it touches modeled territory (N14 pending; R4-BF landed
  2026-07-15 with its multi-seed sweep) ends with the multi-seed fuzz sweep.
- **Measurement hygiene:** never two bench/pytest processes at once. New
  statement-count results go in `STMT_BASELINE_2026-07-14.md` +
  `PERF_ANALYSIS.md` "Applied" entries; never overwrite `scale_bench.jsonl`.
- Model policy (the loop that landed rounds 1–3): Fable orchestrates and
  reviews (trust contracts, wave gates, any Lean touch); Opus subagents
  implement below-the-model items. Scope drift toward a modeled algorithm
  stops the track and escalates.
