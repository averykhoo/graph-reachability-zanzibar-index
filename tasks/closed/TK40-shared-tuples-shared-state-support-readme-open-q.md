---
id: TK40
title: shared tuples / shared state support (README open question, no design)
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

### 2026-08-29b

APPENDED to docs/architecture/decision-log.md's 'Out of scope (this round)' bullet, phrased as an exclusion with its price rather than a reopened question (a question contradicts the file's charter at :3-6). All three per-store anchors verified live: TupleLogV1 store_id-scoped at connectedstore/models.py:44 with every read filtering on it; log_watermark(session, store_id) at source.py:204-212 and IndexCursorV1 unique per index_store_id; _lock_store FOR UPDATE on the StoreV4 row at index_v4/core.py:449-471. Verification ADDED a fact the finding did not have and it is the sharpest one: log ids are globally monotonic ACROSS stores despite per-store scoping (store.py:313-314), which is why lag() counts rows instead of subtracting ids -- a sharing design assuming per-store id density breaks there. Confirmed decision-log contained no occurrence of 'shared'.
