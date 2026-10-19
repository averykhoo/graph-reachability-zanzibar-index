---
id: TK157
title: Store-level adopt helper (save_schema + build_index in one call)
brief: TK123 SPLIT A25b: returns the named BuildReport
pri: NEXT
size: S
deps: []
related: [TK123]
parent:
labels: []
source: docs/tk123-api-review-2026-10-14.md
source_hash:
created: 2026-10-15b
moved: 2026-10-19
updated: 2026-10-19
closed:
---

SPLIT from `TK123` (review item A25b, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
Adopting an existing tuple set into a logged store is a multi-step recipe today
(`save_schema` + `build_index` + opening `Store`, the README adoption recipe). Add one
`Store`-level adopt helper that runs it and returns the named `BuildReport`. A feature, hence
not in the TK123 API break; `save_schema` / `build_index` stay public either way.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A25 (the SPLIT of the adopt helper, A25b)
- `src/zanzibar/store/build.py::build_index` — the bootstrap step the helper wraps

## Log
