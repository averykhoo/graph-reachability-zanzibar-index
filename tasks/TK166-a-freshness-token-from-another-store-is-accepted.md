---
id: TK166
title: a freshness token from another store is accepted silently (and its refusal advice misleads)
brief: tokens are global log ids: a foreign token <= cursor passes check/lookup/expand silently
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

B4: at_least= from another store passes whenever it is at or below this store cursor, on check, lookup, lookup_reverse and expand; the answer is correct for the store asked, but the caller s read-your-writes demand is silently meaningless. Agent fix: one PK lookup of TupleLog.store_id for the token, refuse a foreign one. B5: when a foreign token IS refused, StaleRead / LookupNotFresh open with refresh/catch_up-and-retry advice that cannot help; the real cause is only in the last sentence. Adding a refusal is a behaviour change: decide before 0.1.0.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B4+B5 (`docs/tk151-repros-2026-10-20/B4.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log
