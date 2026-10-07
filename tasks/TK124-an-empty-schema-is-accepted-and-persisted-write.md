---
id: TK124
title: an empty schema is accepted and persisted write-once, bricking the store id
brief: ConnectedStore(schema="") persists an empty write-once schema; the store id is then unusable
pri: LATER
size: S
deps: []
related: [TK122]
parent: TK127
labels: [infra]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-07b
updated: 2026-10-07b
closed:
---

`ConnectedStore(session, "x", schema="")` is accepted and persisted write-once as an empty
ruleset, after which every write is refused and re-opening with the real schema raises
`SchemaMismatch`. There is no public way to drop a store, so the store id is lost (CONFIRMED
2026-10-07, 0.0.2 install trial). Fix: refuse a schema that declares no types, at parse time,
in BOTH parsers (product and oracle twin), with a `# REFUSED SHAPE` / `# WHY` / `# INSTEAD`
block (`tests/test_refused_shape_comments.py`). Pin the parity in
`tests/test_p23_parser_refusal_parity.py`'s family.

## Traps

- (!) Do NOT also refuse a schema without the `model` / `schema 1.1` header in the same
  change. Many in-repo test schemas may omit it (UNVERIFIED count). Measure first; that is a
  separate call.
- (!) A new refusal in one parser without its twin is red by design (`P23` parity fuzz).

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) sec 1 B2.
- `CLAUDE.md` sec "Gotchas / invariants" (refused-shape comment rule, parser parity).

## Log
