---
id: R6-10
title: perf candidate landed 2026-08-20b: 2.54x on the incremental boolean write wall
pri:
size:
deps: []
related: []
parent: R6
labels: [perf]
source: board
source_hash:
created: 2026-08-20b
moved: 2026-08-20b
updated: 2026-08-20b
closed: 2026-08-20b
---

Closed record, migrated for the archive. The disposition on file is: banner/board: 'R6-10 landed 2026-08-20b (2.54x)'

## Traps

None. A closed record carries no traps — if this item comes back, the trap belongs to whatever new id files it.

## Read first

- `HANDOFF.md`
- `docs/history/session-log.md`

## Log

### 2026-08-21

Migrated by `migrate.py` (SPEC.md section 7) from an id that had a real recorded disposition, so it becomes a file rather than a bare line in `retired-ids.txt`. **Evidence lives at:** HANDOFF.md; docs/history/session-log.md. **`created` and `moved` are approximations** — no creation date was ever recorded, so all three date fields carry the disposition date. **`pri` and `size` are EMPTY, deliberately.** This id was never ranked and never sized, and a closed record has no rank to have: it is not competing for a session’s attention. The earlier pass wrote `pri: LATER, size: ?` on all of these, which made `list --closed --pri LATER` return 56 rows that no one had ever put in that bucket — an invented fact that reads as a recorded one. `task.py` lint accepts an empty `pri`/`size` under `closed/` and still demands both on an open row.
