---
id: TK123
title: review the public API naming and ergonomics (connectedstore name, lookup results, docstrings)
brief: user ask 2026-10-07: package/module names (connectedstore), top-level imports, lookup ids, docstrings, __all__, docs
pri: NOW
size: M
deps: []
related: [TK122]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-15
updated: 2026-10-15
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

### 2026-10-13d

USER DECISION 2026-10-13d (in chat): promoted LATER -> NEXT, and the user ACCEPTED this naming table, so use it as the decided list without asking again:
- zanzibar.connectedstore -> zanzibar.store (the user-facing package)
- ConnectedStore -> Store (an instance is bound to one store_id, so it IS one store)
- zanzibar.graphindex.Store (internal model) -> IndexStore (frees the name; users never touch it)
- table zanzibar_store -> UNCHANGED (existing 0.0.x databases must still open)
- top-level zanzibar re-exports Store, LookupResult, parse_openfga_schema and the public exceptions, with an __all__
- the subpackage __all__ is trimmed of internals (log_gap, ensure_cursor, log_rows, ...)
- TupleSource, advance_index, build_index, setengine, graphindex keep their names.
One release, a CHANGELOG entry, no shims (TK120 precedent). First step: re-measure the file census (2026-10-07: about 145 files for the subpackage alone; IndexStore adds more and moves CORRESPONDENCE anchors and the claim-rot pin). Add a "Renamed in TK123" key to docs/architecture/overview.md. TK140 added UnloggedTuplesPresent to connectedstore.__all__ (public, keep it).

### 2026-10-14

USER DECISION 2026-10-14 (in chat): "okay to all suggestions for tk123". The DECIDED list is items 1-26 of the coordinator's accept list, whose detail lives in docs/tk123-api-review-2026-10-14.md (ACTIVE-PLAN; 59 verified items, A1-A59). In short:
- 1-2: advance_index refuses a boolean schema without a DeltaProcessor (A16). SetEngine on a governed store id refuses a schema that differs from SchemaRecord (A53). Both ship in 0.0.5, ahead of the API break.
- 3: the decided rename (connectedstore->store, ConnectedStore->Store, graphindex.Store->IndexStore; table zanzibar_store unchanged), with the inner module renamed too, so it is never zanzibar.store.store.Store. Plus a permanent test that old names do not survive in shipped strings (A1, A45).
- 4: lazy PEP 562 top-level exports: Store, LookupResult, parse_openfga_schema and all exceptions, incl. WriteLockUnsafe (A14, A18, A20).
- 5: trim __all__ (113 names) to the real surface; SetOps.__repr__ (A11-A13, A15).
- 6: ZanzibarError root plus SchemaError, keeping the builtin bases (A19).
- 7: keyword names subject_type/subject_name/object_type/object_name, with a test that the documented names bind (A4).
- 8: the set engine's LookupResult becomes SetLookupResult (A2).
- 9: build_index index id keyword-only; explicit TupleSource.check signature; SetEngine schema optional when a SchemaRecord exists; Ellipsis predicate refused; fixpoint paranoia documented (A5, A7, A9, A10, A43).
- 10: Store refuses a dirty Session (A54).
- 11: at_least validated; another store's token detected; never-issued token message (A35, A50).
- 12: StoreNotFound(KeyError) with a schema= hint, plus rollback (A27).
- 13: the stall error names the log id and tuple (A28).
- 14: strip internal ids from messages and public docstrings, with a test (A29, A38).
- 15: UnprovenExtensionWarning once per Store, at the caller (A30).
- 16: the fanout message names ZANZIBAR_MAX_CLOSURE_FANOUT (A31).
- 17: distinct admission messages (A32).
- 18: SchemaMismatch is order-insensitive and names the relation; a missing create_all gets a clear error (A34).
- 19: Store.result_keys/excluded_keys returning (type, name, predicate), plus return annotations (A21, A41). This also settles TK138 D3a: lookup results carry keys.
- 20: BuildReport named fields, IndexExists, 'any'/'all' markers documented, and the userset-in-reverse-lookup semantics documented (A23-A25).
- 21: docstrings, a short SetEngine.lookup docstring, stale module docstrings fixed (A37, A39, A40, A42).
- 22: PyPI page sections (async, wildcards, exceptions, in-memory rebuild, per-instance sync, prune_outbox/outbox_watermark re-exported, printing quickstart). USER 2026-10-14: add these to PYPI_README now; ALL of it gets folded into proper docs later, written by the model using the Diataxis framework (a separate row).
- 23: keep the positional order and ADD the OpenFGA string form, add_tuple("user:alice", "viewer", "doc:d1") / "group:eng#member" (A3).
- 24: InvariantViolation stays outside ZanzibarError.
- 25: 0.0.5 now (the landed fixes plus items 1-2), then this API break as 0.1.0.
- 26: Store(schema=...) accepts OpenFGA JSON (a string or a dict), converted to DSL before it is saved (A36).
SPLIT: Store.expand, lookup type/relation filters, an adopt helper. LEAVE: per the review doc.
Backwards compatibility (user 2026-10-14): "i'm willing to bet there are zero users now so backwards compat isn't an issue, but we can always bump a minor version if there's an issue." No shims.

Re-rank 2026-10-14 (round-4 rows bookkeeping): NEXT -> NOW. Closing TK142 left no NOW row (lint needs exactly one), and TK123 is the item being built now: the user accepted all its suggestions on 2026-10-14 ("okay to all suggestions for tk123"). Interim user-facing PYPI_README sections from item 22 are to be folded into Diataxis docs later (TK151); the fan-out cost measurement the user asked for is TK150.

USER 2026-10-14: go for the 0.0.5 release (items 1-2 plus everything on master). Do NOT prepare 0.1.0 in TK123: the user's word is "let's save 0.1 for when we have some docs" (TK151). Accept-list item 25 is amended accordingly: TK123's entries stay under CHANGELOG [Unreleased], and __version__ stays 0.0.5.

### 2026-10-15

Accept-list items 1-2 LANDED (written 2026-10-14, uncommitted when a Windows update killed the session; gated and committed 2026-10-15 as part of 0.0.5): (1) A16 advance_index(proc=None) on a boolean schema raises connectedstore.apply::MissingDeltaProcessor before any read/write; (2) A53 SetEngine on a governed store id compares its schema with the SchemaRecord (setengine/engine.py::_assert_schema_matches_record, same rule as ensure_schema) and raises SchemaMismatch, which moved to schema/errors.py (re-exported from connectedstore, same class). Pins: tests/test_tk123_equivalence_refusals.py. CHANGELOG [0.0.5] Fixed carries both. Items 3-26 (the API break) stay OPEN under [Unreleased] after 0.0.5; 0.1.0 waits on docs (TK151). Next action: after the 0.0.5 tag + install trial, start item 3 (the connectedstore->store rename census).

0.0.5 install trial (docs/pypi-trial-0.0.5-2026-10-15.md): findings that are ALREADY on the accept list, so no new row: F5 bare KeyError on an unknown store id -> item 12 (StoreNotFound); F5 StaleRead for a never-issued token -> item 11; F5 terse SchemaMismatch on reopen -> item 18; F3 internal ids (ZT-, TK, spec sec, tests/, docs/) in docstrings and F12 warning citing formal/ + ASK-2 -> item 14; F12 warning emitted twice per ConnectedStore -> item 15; F13 fanout message naming an unreachable ctor arg -> item 16; F13 undocumented fixpoint paranoia -> item 9; F3 SetEngine.check has no docstring -> item 21; F4 duplicate add returns the head id, F16 ids valid until the next write, F19 never expand a userset node -> item 22 (PYPI_README). Not on the list: TK153 (LATER). The silent stale-id mistranslation (F16, confirmed first-hand) is TK154 (NEXT).

Accept-list item 3 LANDED (the rename, A1/A45): package zanzibar.connectedstore -> zanzibar.store (inner store.py -> _store.py), ConnectedStore -> store/_store.py::Store, graphindex/models.py::Store -> IndexStore (table name zanzibar_store unchanged). No shims. Pins: tests/test_tk123_rename.py (old imports fail, leftover-dir refusal, old-name line scan of src + PYPI_README with a permanent sabotage test). claim_rot re-generated (pure re-path), MIN_TESTS_ALL ratcheted by the 5 new tests. CHANGELOG [Unreleased] Changed + overview.md 'Renamed in TK123' key. Deliberately NOT rewritten: formal/lean comment cites (rebuild cost), HANDOFF, dated/history docs, tasks. Detail: docs/tk123-api-review-2026-10-14.md landing entry 2026-10-15. Full phased gate run before commit. Next action: item 4 (lazy top-level imports), then items 5-26 per the build plan.
