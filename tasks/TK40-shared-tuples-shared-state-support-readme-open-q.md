---
id: TK40
title: shared tuples / shared state support (README open question, no design)
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

`README.md:400` — *"shared tuples / state?"* — the author's open-question list. No design, no consumer, no tests.

`SOMEDAY` by definition.

## Traps

⚠ **The source of truth is per-store and the index is a materialized view of it.** `TupleV1` + `TupleLogV1` are the truth and the graph index is derived; anything "shared" across stores has to say what that means for the log, the watermark, and `_lock_store`'s per-store serialization. That is the design, and it does not exist.

## Read first

- [`README.md`](README.md)`:400` — the question
- `connectedstore/source.py::TupleSource` — the per-store source of truth

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-25 (`J-10`, tier 4, sweep-j only); README.md:400 re-read this pass.
