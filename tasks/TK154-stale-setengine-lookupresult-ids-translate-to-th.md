---
id: TK154
title: stale SetEngine LookupResult ids translate to the wrong keys after a write (no error)
brief: 0.0.5 trial F16: a stale lookup id is recycled and excluded_keys returns ANOTHER node key, silently
pri: NEXT
size: S
deps: []
related: [TK123, TK139, TK153]
parent:
labels: []
source: docs/pypi-trial-0.0.5-2026-10-15.md
source_hash:
created: 2026-10-15
moved: 2026-10-15
updated: 2026-10-15
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
