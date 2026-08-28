---
id: TK24
title: unverified R6 lead A8: five cascade sites use per-id session.get N+1 loops beside the batch helper
pri: HOLD
size: ?
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

`index_v4/processor.py::DeltaProcessor._fan_out` — lead **A8** of the 16-item appendix, `docs/perf-round6-audit-2026-08.md:847`.

`_fan_out`'s ttu and userset branches, `_map_deltas_to_keys`' ttu arm, `_keys_referencing` and the subject-GC pre-pass each issue one `session.get` per id. `lookup_reachable` returns the FULL transitive-closure descendant set, so a well-connected entity turns one fan-out into hundreds of point SELECTs. `_nodes_by_ids` exists precisely for this — its docstring says *"replacing per-id session.get N+1 loops"* — and these five sites do not use it. Sketch: batch through the helper, or push the `(type, predicate)` filter into SQL. Finder: write-speed, filed impact medium, algorithm change no.

**UNVERIFIED, and that is the whole point of the row.** The appendix preserves its leads *"verbatim and UNVERIFIED"* (`docs/perf-round6-audit-2026-08.md:757`): no adversarial pass confirmed that the code does what is claimed, that the fix sketch is semantics-preserving, or that the Lean note is right. This lead carries no motivating measurement of its own, and `docs/perf-next-round.md`'s reopening rule requires one before anything lands. `HOLD` is therefore the honest pri and it is the vocabulary's own definition (`docs/README.md` §5: *deferred by an explicit recorded decision*) — the decision is the audit's, at `:756`: each finder returned 5-6 findings and only the top 3 by filed impact went to verification. Promote to `LATER` when a profile or `benchmarks/stmt_bench.py` run puts a number on it, not before.

## Traps

⚠ **Re-verify against the code before acting.** The verified set above the appendix had fix sketches corrected and one fix refuted outright while its finding stood; nothing has been done to these sixteen. Treat the evidence block as a claim, not a finding.

⚠ **Read the audit's §"Traps the numbers do not carry" before taking this id.** Count the bullets there rather than trusting a number in prose: `migrate.py::R6_ROUND_WIDE_TRAPS` pins that count for the 14 GENERATED `R6-N` rows and refuses to build if it moves, but this row was filed by hand and rides no such refusal.

⚠ **A cited symbol may have MOVED.** `R6-6`'s target did: `BL-2` split `index_v4/wildcard.py::WildcardIndex.check` into a public deny fence plus `::WildcardIndex._check_internal` on 2026-08-21, and the audit still names `::check`. `formal/conformance/anchor_check.py` cannot catch that class — it reads only `formal/CORRESPONDENCE.md`, and both symbol names exist anyway. Resolve the symbol by reading the code, not by trusting the doc.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)`:847` — this lead, verbatim (evidence + unreviewed fix sketch)
- the same file, §"Appendix — the 16 UNVERIFIED lower-ranked leads" (`:754-761`) — what "unverified" means here, in the audit's own words
- the same file, §"Traps the numbers do not carry" — the round-wide traps
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the P12c fence and the reopening rule (**every item still needs a motivating measurement**)
- `index_v4/processor.py::DeltaProcessor._fan_out` — the code
- `python task.py show R6` — the parent: round-wide order, traps, and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-17, the `R6-A1..R6-A16` block (tier 3, sweep-g only; sweep-l never reached the appendix). Source: docs/perf-round6-audit-2026-08.md:847, inside the appendix at :754-953. CONFIRMED OPEN AND UNCHANGED by COVERAGE.md §C3: `grep -c 'R6-A'` -> 0, no id anywhere. Lead 8 of 16.

### 2026-08-29b

CLOSED as already carried, and this one is doubly covered. Every element -- the five session.get sites, lookup_reachable returning the full descendant set, the unused _nodes_by_ids helper whose docstring literally says 'replacing per-id session.get N+1 loops', and the batch-or-push-the-filter sketch -- is verbatim in A8's own evidence and fix sketch. The cross-link ALSO already exists from the verified end: R6-5's verifier correction notes the processor call sites have their own per-id N+1 that its sketch does not cover. Symbols unmoved; only line numbers drifted (the ttu loop is ~1497, not the finder's 1277).
