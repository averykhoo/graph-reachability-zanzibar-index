---
id: TK167
title: an unappliable backlog row refuses every sync write on the store id with an unhelpful message
brief: after a PathCountExceeded stall every sync add/remove fails, even removing the bad tuple
pri: LATER
size: S
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-20b
updated: 2026-10-20b
closed:
---

Working as designed for correctness (rolled-back writes are absent from both backends), but a sync=True instance cannot even remove the offending tuple; the documented recovery is a sync=False removal plus rebuild_index. Agent fix: when a sync write fails on a backlog row that is not the caller s, say so and point at the recovery.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B6 (`docs/tk151-repros-2026-10-20/B6.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log
