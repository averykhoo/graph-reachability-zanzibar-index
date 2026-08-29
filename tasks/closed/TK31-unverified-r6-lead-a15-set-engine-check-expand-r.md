---
id: TK31
title: unverified R6 lead A15: set-engine check/expand re-walk the SchemaAST with isinstance dispatch
brief:
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

`setengine/engine.py::SetEngine.check.sat_expr` — lead **A15** of the 16-item appendix, `docs/perf-round6-audit-2026-08.md:931`.

`sat_expr` and `do_expr` re-interpret a lifetime-stable AST on every call, running a chain of up to six `isinstance` tests per node visit — and the codebase already has the compile-once pattern for exactly this (`zanzibar_utils_v1.py::_compile_check_fn` builds closure-composed plans with *"no AST walk, no per-node dispatch, short-circuit"*), but only for the graph side's derived plans, never for the set engine's evaluator, whose `check` is the inner loop of `lookup`. Sketch: AOT-compile each `(type, relation)` `Expr` at `__init__` into generator-closures mirroring `sat_expr`'s exact statement order. Finder: repeated-work, filed impact medium, algorithm change no.

**UNVERIFIED, and that is the whole point of the row.** The appendix preserves its leads *"verbatim and UNVERIFIED"* (`docs/perf-round6-audit-2026-08.md:757`): no adversarial pass confirmed that the code does what is claimed, that the fix sketch is semantics-preserving, or that the Lean note is right. This lead carries no motivating measurement of its own, and `docs/perf-next-round.md`'s reopening rule requires one before anything lands. `HOLD` is therefore the honest pri and it is the vocabulary's own definition (`docs/README.md` §5: *deferred by an explicit recorded decision*) — the decision is the audit's, at `:756`: each finder returned 5-6 findings and only the top 3 by filed impact went to verification. Promote to `LATER` when a profile or `benchmarks/stmt_bench.py` run puts a number on it, not before.

## Traps

⚠ **Re-verify against the code before acting.** The verified set above the appendix had fix sketches corrected and one fix refuted outright while its finding stood; nothing has been done to these sixteen. Treat the evidence block as a claim, not a finding.

⚠ **Read the audit's §"Traps the numbers do not carry" before taking this id.** Count the bullets there rather than trusting a number in prose: `migrate.py::R6_ROUND_WIDE_TRAPS` pins that count for the 14 GENERATED `R6-N` rows and refuses to build if it moves, but this row was filed by hand and rides no such refusal.

⚠ **A cited symbol may have MOVED.** `R6-6`'s target did: `BL-2` split `index_v4/wildcard.py::WildcardIndex.check` into a public deny fence plus `::WildcardIndex._check_internal` on 2026-08-21, and the audit still names `::check`. `formal/conformance/anchor_check.py` cannot catch that class — it reads only `formal/CORRESPONDENCE.md`, and both symbol names exist anyway. Resolve the symbol by reading the code, not by trusting the doc.

⚠ **"Byte-identical control flow" is the claim, and short-circuit ORDER is the thing that can silently move.** The `_drive` heap-stack protocol and the lowlink memo guard must survive verbatim; the net is the validation matrix under BOTH `SetOps`, hypothesis, and conformance. Also check the `CORRESPONDENCE.md` anchors on `check`/`expand` still resolve — and remember they resolve on NAME alone, so keeping the name is not evidence the model still describes the code (that is the `R6-6` lesson).

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)`:931` — this lead, verbatim (evidence + unreviewed fix sketch)
- the same file, §"Appendix — the 16 UNVERIFIED lower-ranked leads" (`:754-761`) — what "unverified" means here, in the audit's own words
- the same file, §"Traps the numbers do not carry" — the round-wide traps
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the P12c fence and the reopening rule (**every item still needs a motivating measurement**)
- `setengine/engine.py::SetEngine.check.sat_expr` — the code
- `python task.py show R6` — the parent: round-wide order, traps, and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-17, the `R6-A1..R6-A16` block (tier 3, sweep-g only; sweep-l never reached the appendix). Source: docs/perf-round6-audit-2026-08.md:931, inside the appendix at :754-953. CONFIRMED OPEN AND UNCHANGED by COVERAGE.md §C3: `grep -c 'R6-A'` -> 0, no id anywhere. Lead 15 of 16.

### 2026-08-29b

APPENDED to docs/perf-round6-audit-2026-08.md, new appendix subsection 'Cross-links and corrections the leads do not carry (added 2026-08-29b)'. Landed as ONE consolidated section rather than 13 inline notes: the leads are preserved verbatim by an explicit recorded decision, so corrections belong beside them, not inside them, and the doc already had the precedent (the demoted 'Traps the numbers do not carry' section). Each note was re-verified against the live tree by a four-agent fan-out before landing; per-id detail is in the section itself and in docs/history/tk-findings-adjudication-2026-08-29.md.
