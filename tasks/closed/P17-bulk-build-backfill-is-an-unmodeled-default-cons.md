---
id: P17
title: bulk build/backfill is an unmodeled default constructor -- model it or scope-exclude it
brief:
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 7c191c74bd66
created: 2026-08-16
moved: 2026-09-06b
updated: 2026-09-06b
closed: 2026-09-06b
---

bulk build/backfill is an unmodeled **default** constructor — model it or scope-exclude it in writing

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(h) + §3.1 item 6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-06b

Option (c), user-decided: formal/conformance/test_conformance_bulk_state.py pins build_index(bulk=True) against the incremental Python graph state, exact, over all 25 GRAPH_FRAGMENT corpora (26 tests; multiplicity sabotage red: incremental=3 bulk=1). Scope statement written in FINAL_REVIEW.md s3.1 item 6 + s4(h); CORRESPONDENCE s8.1 entries for P13/R4-BF. Lean bulk=replay theorem deferred as P24 (SOMEDAY); unpinned I14 loop filed as P22.
