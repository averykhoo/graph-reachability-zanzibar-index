---
id: TK74
title: quiescence is a DRAINAGE check only -- should a cheap per-write staleness check exist?
brief: TK73 fallout: I9 audit_fixpoint is the only correctness net and runs per-write ONLY under GraphBackend.post_op
pri: LATER
size: M
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-17
updated: 2026-09-17
closed:
---

## What it is

`TK73` settled that the cascade's terminal assertion is a **drainage** check, not a
staleness check -- and after the fix it is a *fixpoint* assertion over the leftover keys
only, not over every derived key.

**The load-bearing observation (UNVERIFIED -- reported by a diagnosis verifier during
`TK73`, NOT reproduced first-hand; reproduce it before acting):** skipping a reconcile in
a *productive* round produced **2 wrong answers** against the oracle with **no raise from
either candidate fix**, paranoia off.

If that reproduces, the only real correctness net is I9 `audit_fixpoint`, which runs
per-write **only** under `tests/test_matrix.py::GraphBackend.post_op` -- i.e. in tests,
not in production. The question this row owns: should a cheap per-write staleness check
exist at all, and what would it cost?

## (!) Traps

- **(!) Reproduce the 2-wrong-answers claim FIRST.** It is the entire premise and it is
  unverified. If it does not reproduce, close this row rather than designing against it.
- **(!) Do not widen the settle pass into a full-store audit to "solve" this.** The settle
  pass is bounded at one extra reconcile per leftover key on purpose; making it O(store)
  per write trades a correctness gap for a performance cliff, and `audit_fixpoint` already
  exists for the full sweep.
- **(!) `ZANZIBAR_PARANOIA=residue` already exists** as the shipped runtime detector for
  the `ZT-P0-1` escalation class. Measure what it does and does NOT catch here before
  proposing a new knob -- the answer may be "widen paranoia", not "new check".

## Read first

- [`docs/tk73-cascade-quiesce-gc-2026-09-17.md`](../docs/tk73-cascade-quiesce-gc-2026-09-17.md)
  sec 7 -- where this question was raised and why it was left open.
- `index_v4/processor.py::DeltaProcessor.audit_fixpoint` -- the I9 net, and its cost shape.
- `index_v4/invariants.py` -- paranoia wiring and the sec 8.3 delta-scoped verifier.

## Log
