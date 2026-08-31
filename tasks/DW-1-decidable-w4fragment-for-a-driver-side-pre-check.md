---
id: DW-1
title: decidable W4Fragment for a driver-side pre-check
brief:
pri: LATER
size: ?
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 77a601be5a88
created: 2026-08-16
moved: 2026-08-31b
updated: 2026-08-31b
closed:
---

decidable `W4Fragment` for a driver-side pre-check

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates"

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-08-31b

Promoted SOMEDAY -> LATER on measured evidence: the new scope pin classifies W4Fragment's ten fields LOUD 0 / MIXED 3 / SILENT 7. For seven fields a schema outside the proven fragment is accepted, runs, and answers queries with no operator signal -- correctness resting on the differential net, not graph_correct. A driver-side pre-check is what converts those into a refusal or a warning. Live table: test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE.
