---
id: TK37
title: hot multi-reader deployments want a shared invalidation signal, not per-reader log tailing
pri: SOMEDAY
size: M
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

A stale tokened read tails only the committed log delta into the evaluator (`catch_up_evaluator` → `apply_logged`, O(delta)), not a full rebuild. `docs/architecture/correctness.md:104-110` calls that *"fine at human scale"* and names the scaling gap: *"a hot multi-reader deployment would still want a shared invalidation signal to avoid per-reader tailing."* A documented scaling gap with no row.

`SOMEDAY` by the vocabulary's definition: revisit on a concrete need, and the concrete need is a deployment shape this repo does not have.

## Traps

⚠ **This is a correctness-adjacent surface, not just throughput.** The freshness contract (`at_least`, `StaleRead`) is what makes tokened reads correct across sessions; a shared invalidation signal is a new way for a reader to believe it is fresh. Any design must state what happens when the signal is LOST, and the answer must fail closed.

## Read first

- [`docs/architecture/correctness.md`](docs/architecture/correctness.md)`:104-110` — the gap, in its freshness context (LIVING)
- `connectedstore/store.py::ConnectedStore.catch_up_evaluator` — the per-reader tail

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-22 (`NG-1`, tier 4, sweep-n only); anchor re-read this pass at docs/architecture/correctness.md:104-110 (LIVING).
