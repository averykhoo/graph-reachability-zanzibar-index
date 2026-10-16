---
id: TK154
title: stale SetEngine LookupResult ids translate to the wrong keys after a write (no error)
brief: 0.0.5 trial F16: a stale lookup id is recycled and excluded_keys returns ANOTHER node key, silently
pri: NOW
size: S
deps: []
related: [TK123, TK139, TK153]
parent:
labels: []
source: docs/pypi-trial-0.0.5-2026-10-15.md
source_hash:
created: 2026-10-15
moved: 2026-10-16b
updated: 2026-10-16b
closed: 2026-10-16
---

The 0.0.5 install trial (F16) found that a `SetEngine` `LookupResult` kept across a write can
translate to the WRONG keys, silently. Ids are recycled int32 surrogates, valid "only until the
next write" (`result_keys` docstring). After the write, `excluded_keys(old)` either raises a raw
`KeyError`, or, once the id is reused, returns another node's key with no error. The session
reproduced this first-hand against `src/` on 2026-10-15: id `{2}` was `('user', 'm', '...')`,
and after `m`'s ban was removed and `eve` was banned it came back as `('doc', 'd', 'banned')`.

The candidate fix is to stamp each `LookupResult` with the engine's write epoch, so that
`result_keys` / `excluded_keys` raise a named error on a stale result instead of translating
it. The same question applies to `ConnectedStore`'s lookup results and the graph index's ids.
Decide whether to refuse there, or to document that it can't happen. Ship it with a sabotage
test: drop the epoch check, then watch the recycle repro come back green-and-wrong.

## Read first

- docs/pypi-trial-0.0.5-2026-10-15.md (F16; the verbatim repro is in the header)
- src/zanzibar/setengine/engine.py (`result_keys`, `excluded_keys`)

## Log

### 2026-10-15b

REASONED (agent gate-commit3, 2026-10-15b; not probed): TK123 item 19 (SetLookupResult rename, Store.result_keys / excluded_keys returning (type, name, predicate) keys) did NOT fix this row. It changes the surface names and adds a key-returning path, but a caller holding ids from an older result still translates them against the CURRENT id map, so a recycled id still names a different entity silently. The fix should be a write-epoch stamp carried on the result and checked at translation, and it must cover BOTH backends: set-engine ids are recycled int32, and graph Node rows are recycled too (SQLite rowid reuse; the Node table has no AUTOINCREMENT), so a graph-side id-bearing result has the same hazard.

### 2026-10-16

LANDED 2026-10-16 (ultracode workflow wf_b7f62b52-7cd: scout, fable decision, implementer, adversarial review, one fix round; then the session re-ran the tests and sabotages S1 and S3 first-hand). Map + decision + sabotage table: docs/tk154-stale-lookup-ids-2026-10-16.md.
Decision (D1 + D3, D2 rejected): set engine -- every SetLookupResult carries id_stamp = (interner serial, frees); serial is a fresh secrets.randbits(64) per Interner (a per-process counter was a review BLOCKER: it collides across processes), frees counts Interner.release. result_keys / excluded_keys refuse a mismatched stamp, which also covers rebuild() (re-assigns ids with no write, PROBE B) and another engine instance (PROBE X). Graph -- zanzibar_node is sqlite_autoincrement, so a removed node's id goes MISSING, never re-points; Store refuses to open a 0.0.x SQLite file whose zanzibar_node lacks AUTOINCREMENT (TablesOutdated, a breaking change listed in CHANGELOG [Unreleased]). New exported errors StaleLookupIds(ZanzibarError, KeyError) and TablesOutdated; both pickle. engine.interner.key is no longer documented in PYPI_README (a stale MemberSet from expand is still translatable through it: internal-grade surface, TK155 is where a keyed expand lands).
Tests: tests/test_tk154_stale_lookup_ids.py (14). First-hand 2026-10-16: green 14 passed; SAB154=S1 (stamp check removed) 4 failed 'DID NOT RAISE StaleLookupIds'; S3 (autoincrement off) 4 failed. Pins: correspondence_anchor_pin.txt re-hashed for Node, Interner.release, SetEngine.lookup_reverse; session read the diffs: a DDL option, a counter increment, a stamp on the constructed result -- no modelled algorithm changes, no Lean change.
UNVERIFIED: PostgreSQL never reuses node ids (REASONED: identity column). Gate: see the commit carrying this close.

Gate addendum 2026-10-16 (session, first-hand): tests-tile 2/4 went red on tests/test_tk123_no_internal_refs.py (refuse_reusable_node_ids docstring cited TK154; reworded, id moved to a comment) and tests-tile 4/4 on tests/test_tk79_outbox_replica.py::test_late_gc_rows_are_load_bearing, whose membership-level half REQUIRED SQLite to re-hand the GC-d node id to user:u9 (the exact hazard TK154 removes). That half now pins the opposite (id never re-handed; u9 gets a higher id); green, and red under SAB154=S3 with "id 9 was re-handed to a new node". Closure-level half unchanged.

### 2026-10-16b

2026-10-16b PostgreSQL leg RUN (was owed). (1) tests/test_postgres_ha.py vs local pg_local.sh cluster, ZANZIBAR_PG_REQUIRED=1: 17 passed. (2) tests-tile:1/4..4/4 with ZANZIBAR_TEST_DSN: all PASSED, 2685 passed + 3 skipped (the budgeted SQLite-only snapshot tests). (3) "PostgreSQL never reuses node ids" is now TESTED, not reasoned: tests/test_postgres_ha.py::test_tk154_graph_node_ids_are_never_reused_on_postgresql + permanent control ::test_tk154_sabotage_control_restarted_sequence_translates_wrong (ALTER SEQUENCE ... RESTART WITH the removed id makes the held result name another node). Sabotage observed: that rewind inserted into the main test -> AssertionError: assert not ({1} & {1, 2}). (4) The sabotage plugin moved from gitignored .scratch/tk150-154/sab154_plugin.py to formal/probes/tk154_sabotage_plugin_2026_10_16.py; all four modes re-run there: S1 4 failed, S2 2 failed, S3 4 failed, S4 1 failed (same failed counts as the doc's table; module now 14 tests), none 14 passed. One unrelated one-off red on the leg filed as a new LATER row (non-vacuity guard of the lock-discipline test). Next action: none on TK154.
