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
moved: 2026-10-13c
updated: 2026-10-13c
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

### 2026-10-08b

Input from the 0.0.3 install trial (AGENT, docs/pypi-trial-0.0.3-2026-10-08.md), no action taken (row stays parked per the user): `zanzibar` has no `__all__`; ConnectedStore.add_tuple/remove_tuple/check/watermark have no docstrings and lookup/lookup_reverse do not say what they return; `LookupResult` has no docstring; docstrings and messages cite repo-only ids/files (ZT-P1-3, ZT-P1-8b, TK111/112, docs/...md, "boolean spec sec 8.1"); `connectedstore.__all__` exports internal-looking names (log_gap, ensure_cursor, log_rows); a missing store raises bare KeyError; store ids are not held to the identifier charset ('bad id!', 'a:b', 300 chars accepted); `at_least='abc'` -> raw TypeError, -1/True accepted; a never-issued token's StaleRead says "retry", which cannot succeed; sync mode is not persisted (reopening an async store without sync=False gives a sync instance); the `schema X.Y` header value is ignored; ClosureFanoutExceeded points at ReachabilityIndex(max_closure_fanout=...), unreachable from ConnectedStore; the async over-cap warning is a logging record and the README's "lands in neither backend" does not cover async; paranoia level `fixpoint` is undocumented; UnprovenExtensionWarning fires twice per construction. The PyPI-README gaps went to TK135, the BROKEN reopen byte-compare to TK136.

### 2026-10-13c

Partial progress on the "unsupported-OpenFGA-features list" doc gap (2026-10-13c, OpenFGA claims audit, docs/openfga-claims-audit-2026-10-13.md): PYPI_README.md now says the schema language is a subset of the OpenFGA DSL (schema 1.1, no conditions or modules) and lists all three wildcard extensions. A full feature list is still owed; the parser leniencies that list would need are TK137.

The 0.0.4 install trial (docs/pypi-trial-0.0.4-2026-10-13.md, CONFUSING / DOC GAP section, AGENT) adds ergonomics items for this row: missing docstrings on ConnectedStore.add_tuple/check/remove_tuple/watermark and SetEngine.check; internal ids (TK112, ZT-P1-8a, ASK-2, spec sec N) in public messages; UnprovenExtensionWarning stacklevel points into site-packages and fires 2-3 times per ConnectedStore; no ConnectedStore.expand and raw interner ids from SetEngine.expand; marker tuple shape differs per backend (3-tuple vs 2-tuple); ClosureFanoutExceeded suggests a knob a ConnectedStore user cannot pass; paranoia full/fixpoint undocumented; openfga_json_to_dsl drops the model header; reopen with a reordered restriction list raises SchemaMismatch without naming the relation; a failed ConnectedStore(s, unknown) raises bare KeyError and holds the SQLite write lock; standalone SetEngine neither commits nor persists its schema (undocumented); a duplicate ConnectedStore.add_tuple returns the head id with no no-op signal.
