---
id: TK123
title: review the public API naming and ergonomics (connectedstore name, lookup results, docstrings)
brief: user ask 2026-10-07: package/module names (connectedstore), top-level imports, lookup ids, docstrings, __all__, docs
pri: LATER
size: M
deps: []
related: [TK122]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-07b
updated: 2026-10-07b
closed:
---

The user asked on 2026-10-07 for a later pass over the public API's naming and ergonomics,
after asking why the package is `zanzibar.connectedstore` and not `zanzibar.store`. Nothing is
decided yet. The 0.0.2 install trial supplies most of the agenda.

**Starting points (REASONED in chat on 2026-10-07, not decided):**
- `connectedstore` is a historical name: it CONNECTS the tuple log to the graph index.
  `store` is a poor replacement, because a store is already a tenant/namespace here
  (`store_id`, about 270 occurrences in `src/` on 2026-10-07; `zanzibar.graphindex.Store` /
  table `zanzibar_store`). Options raised: a lazy top-level `from zanzibar import
  ConnectedStore` (cheap; `zanzibar/__init__.py` deliberately imports nothing today), and/or
  renaming the subpackage (about 145 files on 2026-10-07: src 10, tests 37, formal 27, docs 36,
  tasks 28, plus root docs; mechanical, like `TK120`).
- `lookup` / `lookup_reverse` return internal node ids with no resolver on `ConnectedStore`,
  mixing all relations, with no type/relation filter.
- Public methods without docstrings (`add_tuple`, `remove_tuple`, `check`, `watermark`), and
  docstrings citing internal ids and files not in the wheel.
- `zanzibar.schema.__all__` has 70 names, many internal-looking; the README calls `__all__`
  the public surface.
- Doc gaps: async mode (`catch_up()`), standalone `SetEngine`, an unsupported-OpenFGA-features
  list, and where the exceptions live.
- Messages: the bare `KeyError` for an unknown store id, the `StaleRead` advice for a token
  beyond the log head, and the undeclared-relation tuple message.
- Silent acceptance: a typo'd restriction type (`[usr]`), and `check()` on an undeclared
  relation.

## Traps

- (!) A rename is an API break, which is cheap at 0.0.x and expensive later. Do it in ONE
  release, with a CHANGELOG entry, and no shims unless the user asks (`TK120` precedent).
- (!) Renaming a module moves `CORRESPONDENCE.md` anchors and the content pin
  (`formal/conformance/claim_rot.py --generate`), and FROZEN docs keep the old names. Add a
  "Renamed in" key to `docs/architecture/overview.md`, as `TK120` did.

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) sec 2 (the full list, with evidence).
- `docs/architecture/overview.md` sec "Renamed in TK120" (the rename precedent).

## Log
