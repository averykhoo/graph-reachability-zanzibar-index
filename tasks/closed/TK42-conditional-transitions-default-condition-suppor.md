---
id: TK42
title: conditional transitions / default-condition support (README open question, no design)
brief:
pri: SOMEDAY
size: L
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

`README.md:403-404` — *"conditional transitions?"* and *"default condition exists?"*. OpenFGA has conditions; this implementation has none, and the questions are recorded without a design.

`SOMEDAY` by definition.

## Traps

⚠ **Conditions are evaluated at CHECK time; this design materializes closure at WRITE time.** That is the whole cost model of the graph index (`check` is O(1) because the transitive closure is materialized). A condition that depends on request context cannot be materialized, so this is not a feature addition — it is a question about which backend can support it at all, and the answer may be "the set engine only".

## Read first

- [`README.md`](README.md)`:403-404` — the questions
- [`docs/architecture/overview.md`](docs/architecture/overview.md) — the two cost models this feature would have to live in

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-27 (`J-8`, tier 4, sweep-j only); README.md:403-404 re-read this pass.

### 2026-08-29b

APPENDED to docs/architecture/decision-log.md after the Non-goals prose, as a clearly separated paragraph -- RESHAPED twice. Trap 1: the filed form was 'its own short bullet', but :197-202 is a single prose sentence of semicolon-separated noun phrases, so a bullet would have broken the section's form. Trap 2, the important one: the heading promises 'documented hooks only' and conditions have NO hook -- they are rejected at parse time (zanzibar_utils_v1.py:2207-2208, :2244-2246), so filing them in a hooks list would mislabel them; the paragraph says so in its first line. Premise verified: write-time materialization is real (index_v4/wildcard.py:5, README.md:305/:476) against the set engine memoizing nothing across queries, so 'set engine only' is a coherent conclusion. Confirmed no living doc states the WHY -- docs/architecture/system.md:127 gives mechanism only.
