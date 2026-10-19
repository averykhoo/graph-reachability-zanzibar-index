---
id: TK155
title: Store.expand: Zanzibar Expand on the composed store, returning keys
brief: TK123 SPLIT A26: do not move SetEngine.expand's body (CORRESPONDENCE anchors it)
pri: NOW
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

SPLIT from `TK123` (review item A26, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
`Store` has no `expand`; a user who wants Zanzibar's Expand must drop to
`SetEngine.expand`, which returns a raw `MemberSet` of bitmap ids (and `pos` omits subjects
covered by a star, so the reading is pos + stars - neg). Add `Store.expand` delegating to the
evaluator with `at_least` freshness semantics mirroring `Store.check`, plus a key helper.
Constraint: `formal/CORRESPONDENCE.md` anchors `setengine/engine.py::SetEngine.expand` and its
nested closures, so do not move its body (it reds `verify.sh lean`). It is a feature with its
own freshness semantics, which is why it is not in the TK123 API break.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A26 (the SPLIT call and its probe)
- `src/zanzibar/setengine/engine.py::SetEngine.expand` — what `Store.expand` would delegate to
- `src/zanzibar/store/_store.py::Store.check` — the `at_least` semantics to mirror

## Log

### 2026-10-19

Promoted LATER -> NOW (TK156, TK157 -> NEXT) at the 2026-10-19 write-back: TK138/TK144 closed, and the user order stated 2026-10-16 (banner 2026-10-16b; TK151 Log) runs TK155-TK157 next, then TK151 last. The lint needs exactly one NOW.
