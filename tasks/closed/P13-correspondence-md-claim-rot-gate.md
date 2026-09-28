---
id: P13
title: CORRESPONDENCE.md claim-rot gate
brief:
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal, infra]
source: board
source_hash: 7532056bb032
created: 2026-08-16
moved: 2026-09-27d
updated: 2026-09-27d
closed: 2026-09-27d
---

`CORRESPONDENCE.md` claim-rot gate

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [design](formal/history/claim-rot-gate-design-2026-08-16.md)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-27d

LANDED (aae414e + 57a05b7). formal/conformance/claim_rot.py adds verify.sh lean steps 4d2 and 4d3. 4d2 = anchor CONTENT pin: the body of every file::symbol anchored in CORRESPONDENCE.md is hashed into formal/correspondence_anchor_pin.txt; a changed body fails and names the map lines to re-read. 4d3 = prose-number lint: an N/M or N-of-M claim must cite an existing test or the generated block in its own sentence, or be dated and marked past. (A) reverse-anchor ratchet deliberately NOT built: it catches none of the four motivating defects and its backlog grew 253 -> 369 (census kept as claim_rot.py --coverage). Both design sabotages are permanent tests in tests/test_claim_rot_gate.py. The adversarial verifier found green sabotages in (C) (no word boundary on ordinal skip-words, thousands-separator ratios, four unpinned behaviours); all fixed and pinned. Final sweep: every mutant killed, M0 green. First run found seven stale ratios in CORRESPONDENCE.md, now marked past; the one with no test behind it is TK119. Map: docs/p13-claim-rot-gate-2026-09-27.md; design doc frozen by this close.
