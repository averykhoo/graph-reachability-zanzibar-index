---
id: DW-1
title: decidable W4Fragment for a driver-side pre-check
brief: SOMEDAY -> LATER 2026-08-31b on measured evidence: W4Fragment scope pin is LOUD 0 / MIXED 3 / SILENT 7
pri: LATER
size: ?
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 04392ec66204
created: 2026-08-16
moved: 2026-09-06b
updated: 2026-09-06d
closed:
---

decidable `W4Fragment` for a driver-side pre-check. **Promoted SOMEDAY → LATER on
2026-08-31b, on measured evidence:** the scope pin classifies `W4Fragment`'s ten fields
**LOUD 0 · MIXED 3 · SILENT 7**, so for seven fields a schema outside the proven fragment is
accepted, runs, and answers queries with no signal to the operator — its correctness resting
on the differential net, not on `graph_correct`. A driver-side pre-check is what converts
those seven silent holes into a refusal or a warning.

## Traps

- ⚠ **Do NOT lift `ttuDirect` in Lean.** It is load-bearing for the current admission story; this row is the open descendant, and nothing is blocked meanwhile. (Moved here from `HANDOFF.md` "Standing traps" at the 2026-09-06 cutover -- the note carries no trap list; a trap lives with the item it guards.)

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates"
- the live table: `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` (`:228`)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-08-31b

Promoted SOMEDAY -> LATER on measured evidence: the new scope pin classifies W4Fragment's ten fields LOUD 0 / MIXED 3 / SILENT 7. For seven fields a schema outside the proven fragment is accepted, runs, and answers queries with no operator signal -- correctness resting on the differential net, not graph_correct. A driver-side pre-check is what converts those into a refusal or a warning. Live table: test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE.

### 2026-09-06b

Board cell rewritten 2026-08-31b (SOMEDAY -> LATER on the LOUD 0 / MIXED 3 / SILENT 7 scope-pin evidence; live table named). The pri was already LATER in the tree; the summary, brief and Read first now carry the evidence and the table symbol. Diff source: git 077bb50 -> HEAD.

### 2026-09-06d

The "do not lift ttuDirect in Lean" trap moved here from HANDOFF.md Standing traps at the 2026-09-06d cutover (see ## Traps). No change to the item itself.
