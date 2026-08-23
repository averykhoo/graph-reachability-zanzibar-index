---
id: TK28
title: unverified R6 lead A12: boolean bulk build holds three full-closure copies in RAM at once
pri: HOLD
size: ?
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`index_v4/bulk_build.py::bulk_build` — lead **A12** of the 16-item appendix, `docs/perf-round6-audit-2026-08.md:895`.

On a boolean schema the backfill's `reach_out`/`reach_in` (full transitive reachability in both directions, as Python sets) stay referenced for the rest of the function even though only `derived_pairs`/`explicit`/`residues` are read afterwards — so ~2x closure sits in RAM while Phase P builds `pvec` (the closure again, as dict-of-dicts) and a third full-closure list `edge_pairs` is materialized. N18 already had to bound Phase-W row dicts because peaks hit ~3x the DP at 200k tuples; these two allocations are the same RSS class and are untouched. Sketch: drop `bf` before `pvec` exists, and iterate instead of materializing `edge_pairs`. Finder: space, filed impact medium, algorithm change no.

**UNVERIFIED, and that is the whole point of the row.** The appendix preserves its leads *"verbatim and UNVERIFIED"* (`docs/perf-round6-audit-2026-08.md:757`): no adversarial pass confirmed that the code does what is claimed, that the fix sketch is semantics-preserving, or that the Lean note is right. This lead carries no motivating measurement of its own, and `docs/perf-next-round.md`'s reopening rule requires one before anything lands. `HOLD` is therefore the honest pri and it is the vocabulary's own definition (`docs/README.md` §5: *deferred by an explicit recorded decision*) — the decision is the audit's, at `:756`: each finder returned 5-6 findings and only the top 3 by filed impact went to verification. Promote to `LATER` when a profile or `benchmarks/stmt_bench.py` run puts a number on it, not before.

## Traps

⚠ **Re-verify against the code before acting.** The verified set above the appendix had fix sketches corrected and one fix refuted outright while its finding stood; nothing has been done to these sixteen. Treat the evidence block as a claim, not a finding.

⚠ **Read the audit's §"Traps the numbers do not carry" before taking this id.** Count the bullets there rather than trusting a number in prose: `migrate.py::R6_ROUND_WIDE_TRAPS` pins that count for the 14 GENERATED `R6-N` rows and refuses to build if it moves, but this row was filed by hand and rides no such refusal.

⚠ **A cited symbol may have MOVED.** `R6-6`'s target did: `BL-2` split `index_v4/wildcard.py::WildcardIndex.check` into a public deny fence plus `::WildcardIndex._check_internal` on 2026-08-21, and the audit still names `::check`. `formal/conformance/anchor_check.py` cannot catch that class — it reads only `formal/CORRESPONDENCE.md`, and both symbol names exist anyway. Resolve the symbol by reading the code, not by trusting the doc.

⚠ **Space, not time — so the profile will not show it.** `benchmarks/profile_r6*` measures wall time and statement counts; an RSS regression/improvement needs its own instrument. Decide how you will MEASURE this before deciding whether to land it, or the "win" is unfalsifiable.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)`:895` — this lead, verbatim (evidence + unreviewed fix sketch)
- the same file, §"Appendix — the 16 UNVERIFIED lower-ranked leads" (`:754-761`) — what "unverified" means here, in the audit's own words
- the same file, §"Traps the numbers do not carry" — the round-wide traps
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the P12c fence and the reopening rule (**every item still needs a motivating measurement**)
- `index_v4/bulk_build.py::bulk_build` — the code
- `python task.py show R6` — the parent: round-wide order, traps, and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-17, the `R6-A1..R6-A16` block (tier 3, sweep-g only; sweep-l never reached the appendix). Source: docs/perf-round6-audit-2026-08.md:895, inside the appendix at :754-953. CONFIRMED OPEN AND UNCHANGED by COVERAGE.md §C3: `grep -c 'R6-A'` -> 0, no id anywhere. Lead 12 of 16.
