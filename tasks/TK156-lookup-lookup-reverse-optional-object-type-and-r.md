---
id: TK156
title: lookup / lookup_reverse: optional object-type and relation filter
brief: TK123 SPLIT A21b: both backends, pinned by the lookup oracle
pri: LATER
size: S
deps: []
related: [TK123]
parent:
labels: []
source: docs/tk123-api-review-2026-10-14.md
source_hash:
created: 2026-10-15b
moved: 2026-10-15b
updated: 2026-10-15b
closed:
---

SPLIT from `TK123` (review item A21b, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
`Store.lookup` / `lookup_reverse` take no object-type or relation filter, so a user who wants
"documents alice can view" filters the `result_keys` themselves (the 2026-10-14 probe:
`lookup() got an unexpected keyword argument 'relation'`). Add an optional type/relation filter
on the lookup surfaces, on both backends, pinned by `tests/test_lookup_oracle.py`'s brute-force
reference. A feature, hence not in the TK123 API break.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A21 (the SPLIT of the filter, A21b)
- `src/zanzibar/store/_store.py::Store.lookup` — the surface to extend
- `tests/test_lookup_oracle.py` — the brute-force reference that must pin it

## Log
