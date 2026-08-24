---
id: HS-5
title: always-living docs lack the liveness state docs/README.md sec 2 requires; count lives in TK49
pri: LATER
size: S
deps: []
related: []
parent:
labels: [docs]
source: board
source_hash: e5eebcba22b2
created: 2026-08-20b
moved: 2026-08-24
updated: 2026-08-24b
closed:
---

always-living docs declare no liveness state, though [`docs/README.md`](docs/README.md) §2 requires one in the first lines. **The count is method-sensitive and does NOT live here — it lives in `TK49`.**

The deliverable is not the count: it is adjudicating which of the measured docs are *deliberately* exempt from §2. That half is untouched.

## Traps

⚠ **Do not restate the count in this row.** It read six, then nine, then eleven across three days, so any figure written into this title or body rots again — which is why `TK49` (the child) owns it and this row points there. Corrected 2026-08-24b: the body still said "six" after the 2026-08-24 retitle fixed only the title, so the retracted figure survived one layer down. That is the same one-summary-row-contradicting-its-own-child disease the A/B recorded as finding `P4`.

## Read first

- `python scripts/task.py show TK49` — the child that owns the measured count and its method
- ledger `2026-08-20`, then `2026-08-24` (the retitle and the reason for it)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer. The title is RE-WORDED (not clipped) to fit the 100-char cap without weakening the claim; the board cell survives verbatim above.

### 2026-08-24b

Body drift, and it was a WRONG FIGURE, not a formatting difference. The 2026-08-24 retitle fixed the title and left the body asserting 'six always-living docs' -- the exact retracted count TK49 corrects. Body rewritten to mirror the board cell (no count here; TK49 owns it), a trap added against restating it, and the read-first now points at TK49. source_hash re-stamped to the current board block.
