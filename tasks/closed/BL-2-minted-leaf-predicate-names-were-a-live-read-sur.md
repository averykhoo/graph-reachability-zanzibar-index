---
id: BL-2
title: minted leaf-predicate names were a live read surface; fixed 2026-08-21b in wildcard.py::check
pri:
size:
deps: []
related: []
parent:
labels: [infra]
source: board
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed: 2026-08-21b
---

Closed record, migrated for the archive. The disposition on file is: 'BL-2 (filed AND fixed 2026-08-21b; its six pins in tests/test_reg18_leaf_name_read_leak.py stay green as regression guards)' - the graph index GRANTED reads at minted leaf-predicate names on the shipped Python, falsifying the old banner's "Known live correctness bugs: 0"; fix fenced wildcard.py::WildcardIndex.check and moved the old body to ::WildcardIndex._check_internal; full record in the docs/spec-deviations.md 2026-08-21b entry

## Traps

None. A closed record carries no traps — if this item comes back, the trap belongs to whatever new id files it.

## Read first

- `HANDOFF.md`
- `docs/spec-deviations.md`
- `docs/history/session-log.md`
- `formal/history/PROOF_STATUS.md`

## Log

### 2026-08-21

Migrated by `migrate.py` (SPEC.md section 7) from an id that had a real recorded disposition, so it becomes a file rather than a bare line in `retired-ids.txt`. **Evidence lives at:** HANDOFF.md; docs/spec-deviations.md; docs/history/session-log.md; formal/history/PROOF_STATUS.md. **`created` and `moved` are approximations** — no creation date was ever recorded, so all three date fields carry the disposition date. **`pri` and `size` are EMPTY, deliberately.** This id was never ranked and never sized, and a closed record has no rank to have: it is not competing for a session’s attention. The earlier pass wrote `pri: LATER, size: ?` on all of these, which made `list --closed --pri LATER` return 56 rows that no one had ever put in that bucket — an invented fact that reads as a recorded one. `task.py` lint accepts an empty `pri`/`size` under `closed/` and still demands both on an open row.
