---
id: TK102
title: take the derived-userset corpus into test_conformance_enum._SHAPES (the combinatorial arm)
brief: the one widening TK94 declined: _SHAPES is a fixed six-name dict, and its cost IS combinatorial
pri: NEXT
size: M
deps: []
related: [TK94]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-22d
moved: 2026-10-04g
updated: 2026-10-04g
closed:
---

## What it is

`formal/conformance/test_conformance_enum.py` is the EXHAUSTIVE small-scope arm: for each
shape it enumerates every store of up to `K` tuples from the declared tuple space over a
2-names-per-type pool and compares Lean `sem` x oracle x set engine x the real graph index
over the full grid. It parametrizes over its own hand-written `_SHAPES` dict
(`test_conformance_enum.py:136`, indexed at `:197`) -- **not** over `SCHEMAS`, which is why
`TK94` adding a 27th corpus cost that module exactly nothing (measured 2026-09-22).

`TK94` landed `SCHEMAS['derived_userset_subject']`, the first corpus pairing a DERIVED
relation with a stored userset subject. Taking it into `_SHAPES` is the one remaining way to
widen that class inside the conformance harness, and it is the genuinely combinatorial
move `TK94`'s first trap was really about.

## Why it is worth a row rather than a line in a doc

`TK94`'s arms are all *curated-store* arms: one store per corpus, or seeded churn derived
from it. The enum arm is the only one that drives PARTIAL stores exhaustively, and the
module's own docstring records that it is exactly the class of run that historically found
the `P6` leaf-family and 2026-07-17 stale-fanout divergences. A derived-userset subject
under partial stores -- in particular a store where the userset subject is present but the
subject object's `member` state is not yet -- is not reached by anything today.

## First action

Measure the tuple space and store count BEFORE adding the name, the way `_SHAPES` already
documents per shape. The current schema declares `group.allowed`, `group.blocked` and
`doc.viewer` with restrictions `[user]`, `[user]`, `[user, group#member]`, so over the
`_POOL` of 2 names per type the space is not obviously small. `_SHAPES`' third column is the
asserted store count, so the sizing is mechanical: build `_tuple_space(schema)` and
`len(list(_all_stores(space, k)))` for `k` in 2..4 and read them off.

## (!) Traps

- **(!) The runtime budget is a PHASE CAP, not a preference.** The module's docstring
  records that a naive all-shapes `K=4` blew the ~10-min `conf-rest` command cap and that
  two shapes are CAPPED at `K=3` for exactly that reason. A new shape competes with those
  caps; if it does not fit, the honest outcome is a documented `K`, never a silent one.
- **(!) The graph leg is gated on `GRAPH_FRAGMENT` membership** (`run_graph = name in
  GRAPH_FRAGMENT`, `:229`). `derived_userset_subject` is deliberately NOT in
  `GRAPH_FRAGMENT` (`W4Fragment.term`/`NoStoreSubjectR`, see `TK94`), so adding it to
  `_SHAPES` buys the spec/oracle/set-engine legs and the graph leg would be SKIPPED. Decide
  whether that is worth the runtime, and do NOT "fix" it by adding the name to
  `GRAPH_FRAGMENT` -- that is the ZT-P3-3 mistake `TK94` declined.
- **(!) `group_userset` is excluded from `_SHAPES` on an admission-domain argument**
  (`:62-70`: at `K=3`, 132 of its 299 stores are admission-INVALID for the set engine's
  userset-cycle guard, which would break the "exhaustive over admission-valid writes"
  premise). Check the same property for this schema before assuming it enumerates cleanly.

## Read first

- [`docs/tk94-derived-userset-corpus-2026-09-22.md`](../docs/tk94-derived-userset-corpus-2026-09-22.md)
  sec 2 (why the enum arm did not widen) and sec 5.6 (why this was deferred).
- `formal/conformance/test_conformance_enum.py` -- the docstring's "K per shape" block is
  the sizing precedent, including the measured runtimes that justify each cap.

## Log

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user: NEXT raised to 5, ranked by correctness certainty). Ranked FIRST of the five. Why (READ 2026-10-04g): formal/conformance/test_conformance_enum.py::_SHAPES is the only exhaustive every-store arm and has no derived_userset shape; its graph leg runs only when name in GRAPH_FRAGMENT (run_graph, :243), so a shape outside the fragment silently skips the graph. REASONED: the bigger win is a separate flag running the graph against the agreed spec/oracle answer wherever the graph ADMITS the schema, without adding the name to GRAPH_FRAGMENT. Fold P16 (widen the bounds) in here. Independent of TK120 ordering.
