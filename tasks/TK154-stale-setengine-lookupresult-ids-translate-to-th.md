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
moved: 2026-10-15b
updated: 2026-10-15b
closed:
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
