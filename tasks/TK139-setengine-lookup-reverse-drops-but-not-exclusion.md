---
id: TK139
title: SetEngine.lookup_reverse drops but-not exclusions (excluded_node_ids empty) under a user:* grant
brief: 0.0.4 trial BROKEN-1: SetEngine.lookup_reverse drops but-not exclusions under user:*; reads as every user
pri: NEXT
size: S
deps: []
related: []
parent:
labels: []
source: docs/pypi-trial-0.0.4-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13c
updated: 2026-10-13c
closed:
---

BROKEN in the 0.0.4 install trial, re-run first-hand: `docs/pypi-trial-0.0.4-2026-10-13.md`
(BROKEN-1, repro p05 inline there).

With `define viewer: [user:*] but not banned`, a `user:*` grant and `mallory` banned,
`SetEngine.check(mallory)` is False but `SetEngine.lookup_reverse("viewer", "doc", "d")`
returns `markers={('user','...')}` with `excluded_node_ids=set()`: it reads as "every
user". `expand` carries the exclusion in `neg`; `lookup_reverse` copies only `pos` and
`stars`. `ConnectedStore.lookup_reverse` fills `excluded_node_ids`, and the PyPI README
tells users to subtract it. `tests/test_lookup_oracle.py` calls the drop intentional ("S3
lookup_reverse is the documented neg-dropping render of expand"), but nothing a user sees
says so, so a list-users UI over-grants.

Fix direction: fill `excluded_node_ids` from `neg` (as `SetEngine.lookup` already does),
so both backends render the same `LookupResult`; then flip the lookup-oracle property
that pins the drop. A positive pin, both backends, sabotage red.

## Read first

- `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse` and `SetEngine.lookup`.
- `tests/test_lookup_oracle.py` (the S3 property).

## Log
