---
id: R6-14
title: perf candidate declined on an upper bound (5.0%)
pri:
size:
deps: []
related: []
parent: R6
labels: [perf]
source: board
source_hash:
created: 2026-08-17
moved: 2026-08-17
updated: 2026-08-17
closed: 2026-08-17
---

Closed record, migrated for the archive. The disposition on file is: Declined on an upper bound (5.0%)

## Traps

None. A closed record carries no traps — if this item comes back, the trap belongs to whatever new id files it.

## Read first

- `HANDOFF.md`
- `docs/history/session-log.md`

## Log

### 2026-08-21

Migrated by `migrate.py` (SPEC.md section 7) from an id that had a real recorded disposition, so it becomes a file rather than a bare line in `retired-ids.txt`. **Evidence lives at:** HANDOFF.md; docs/history/session-log.md. **`created` and `moved` are approximations** — no creation date was ever recorded, so all three date fields carry the disposition date. That date is itself a fallback: the evidence string carries no session key, so `2026-08-17` is used, taken from the R6 profile run, benchmarks/results/R6_PROFILE_2026-08-17.md. **`pri` and `size` are EMPTY, deliberately.** This id was never ranked and never sized, and a closed record has no rank to have: it is not competing for a session’s attention. The earlier pass wrote `pri: LATER, size: ?` on all of these, which made `list --closed --pri LATER` return 56 rows that no one had ever put in that bucket — an invented fact that reads as a recorded one. `task.py` lint accepts an empty `pri`/`size` under `closed/` and still demands both on an open row.
