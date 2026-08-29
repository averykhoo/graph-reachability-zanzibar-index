---
id: P2
title: closed with P1 on 2026-08-16; retired on the HANDOFF board
brief:
pri:
size:
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash:
created: 2026-08-16
moved: 2026-08-16
updated: 2026-08-16
closed: 2026-08-16
---

Closed record, migrated for the archive. The disposition on file is: Closed ids stay retired ... P1, P2 ... (all done 2026-08-16)

## Traps

None. A closed record carries no traps — if this item comes back, the trap belongs to whatever new id files it.

## Read first

- `HANDOFF.md`
- `docs/history/session-log.md`
- `formal/history/PROOF_STATUS.md`

## Log

### 2026-08-21

Migrated by `migrate.py` (SPEC.md section 7) from an id that had a real recorded disposition, so it becomes a file rather than a bare line in `retired-ids.txt`. **Evidence lives at:** HANDOFF.md; docs/history/session-log.md; formal/history/PROOF_STATUS.md. **`created` and `moved` are approximations** — no creation date was ever recorded, so all three date fields carry the disposition date. **`pri` and `size` are EMPTY, deliberately.** This id was never ranked and never sized, and a closed record has no rank to have: it is not competing for a session’s attention. The earlier pass wrote `pri: LATER, size: ?` on all of these, which made `list --closed --pri LATER` return 56 rows that no one had ever put in that bucket — an invented fact that reads as a recorded one. `task.py` lint accepts an empty `pri`/`size` under `closed/` and still demands both on an open row.
