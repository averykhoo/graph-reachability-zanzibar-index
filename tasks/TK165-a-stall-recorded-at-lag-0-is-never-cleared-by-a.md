---
id: TK165
title: a stall recorded at lag 0 is never cleared by a catch_up that applies nothing
brief: contradicts the IndexStalled docstring; only an applied write or rebuild_index clears it
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

If catch_up fails on an idle store (lag 0; e.g. a transient lock error while taking the store lock before finding no rows) it records stalled_after == applied_log_id. Later successful catch_up calls return 0 and leave the stall, so untokened lookups keep raising IndexStalled until some write is applied. Agent fix: on a zero-row successful batch with stalled_after == applied_log_id, clear the stall.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B3 (`docs/tk151-repros-2026-10-20/B3.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log
