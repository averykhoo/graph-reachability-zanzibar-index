---
id: TK42
title: conditional transitions / default-condition support (README open question, no design)
pri: SOMEDAY
size: L
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
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
