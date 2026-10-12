---
id: TK102
title: take the derived-userset corpus into test_conformance_enum._SHAPES (the combinatorial arm)
brief: the one widening TK94 declined: _SHAPES is a fixed six-name dict, and its cost IS combinatorial
pri: NOW
size: M
deps: []
related: [TK94]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-22d
moved: 2026-10-12c
updated: 2026-10-12c
closed: 2026-10-12c
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

### 2026-10-12b

Re-ranked 2026-10-12b (user approved the order in chat): TK118 NOW, then TK79, then TK102 (NEXT); TK97 and TK44 down to LATER (process tooling / coverage research with no known bug); TK134+TK135 stay LATER, user says no rush to release 0.0.4. Why TK118 first: it is the only row about a fail-OPEN, and it bears on what we tell production users about residue today.

### 2026-10-12c

IMPLEMENTED 2026-10-12c, uncommitted, gate NOT run (closing stage owns gate/commit/close). Body: docs/tk102-derived-userset-enum-2026-10-12.md (ACTIVE-PLAN). LANDED: test_conformance_enum.py::_SHAPES += derived_userset_subject (16-tuple space, K=3, 697 stores, CAPPED); ::_ORBIT_REDUCED (119) = spec+graph on one representative per pool-renaming orbit, oracle x set engine on all 697; ::_assert_renaming_closed pins the quotient precondition; ::_GRAPH_PY_DIFFERENTIAL declares the graph leg a Python-only differential (NOT GRAPH_FRAGMENT, ZT-P3-3); ::test_every_shape_declares_its_graph_leg; test_conformance_enum_state.py::_STATE_SHAPES excludes exactly the py-differential set (::test_state_leg_excludes_exactly_the_py_differential). RUN: new shape green in 104.07 s, no divergence, no Python fix needed. Sabotage S1-S6 all red (table in doc sec 4.1); S1 (derived add drops object descendants) is caught by NO pre-existing enum shape (7 passed under it) but also by the TK94 remove arm. Carriers updated (CORRESPONDENCE/ARCHITECTURE/FINAL_REVIEW), doc_counts regenerated (conf 1089->1092). RED: nothing known. OPEN: conf-tile:5/5 already 925 s pre-item (ledger 2026-10-12) -- consider raising tile K; P16 not folded in. NEXT ACTION: run the full phased gate, then commit and close.

STATE after review-1 + review-2 fixes (2026-10-12c), uncommitted, full gate NOT run. Supersedes the conf count and "RED: nothing known" in the entry above. Body: docs/tk102-derived-userset-enum-2026-10-12.md (two dated correction blocks at the top). LANDED: floors MIN_CONF_ALL 1093 / MIN_CONF_REST 958 (verify.sh; live collect 1093); doc_counts regenerated (1093 conf, 755 anchors). Write-order cost of the orbit quotient is pinned CORRECTLY: test_conformance_enum.py::_ORBIT_ORDER_UNDRIVEN = (116 undriven stores, 44 undriven sequence classes; 163 = 119 + 44), via ::test_orbit_reduction_write_order_cost_is_pinned (the earlier 328 / _ORBIT_ORDER_VARIANTS counted 68 representatives whose order IS driven -- false label, removed). ::test_exhaustive_small_scope now counts the non-representative oracle x set-engine branch (n_cheap_only == 578). Carriers (ARCHITECTURE, FINAL_REVIEW, CORRESPONDENCE enum rows) carry the 116/44 caveat. S1 six-shapes claim re-run in an isolated copy: GREEN, 6 passed in 569.29s. RUN: targeted 4 passed in 126.41s. Sabotage S7A-D and S11 red (docstrings + doc). RED: nothing known. OPEN: conf-tile:4/5 (601 s on the 2026-10-12 ledger) gains ~100-125 s from this shape; tile 5 already 925-1080 s -- a gate-config decision (raise tile K) before the phased gate. NOT TAKEN: closing the 44 undriven sequence classes (+44 graph-only drives, ~+25-30 s). NEXT ACTION: decide tile K, run the full phased gate, then commit and close.

LANDED 2026-10-12c. formal/conformance/test_conformance_enum.py::_SHAPES gains derived_userset_subject (16-tuple space, K=3, 697 stores). Oracle x set engine run on all 697; zcli spec + graph index run once per pool-renaming orbit (::_ORBIT_REDUCED = 119), soundness precondition pinned by ::_assert_renaming_closed. Graph leg is a declared Python-only differential (::_GRAPH_PY_DIFFERENTIAL, NOT GRAPH_FRAGMENT -- ZT-P3-3), guarded by ::test_every_shape_declares_its_graph_leg and the n_driven/n_graph/n_cheap_only pins in ::test_exhaustive_small_scope. Write-order cost of the quotient pinned by ::_ORBIT_ORDER_UNDRIVEN (116 undriven stores, 44 classes; 163 = 119 + 44) via ::test_orbit_reduction_write_order_cost_is_pinned. test_conformance_enum_state.py::_STATE_SHAPES excludes exactly the py-differential set (::test_state_leg_excludes_exactly_the_py_differential). No divergence found, no Python fix needed. Sabotage S1-S7, S11 all red (doc sec 4.1, test docstrings). Floors MIN_CONF_ALL 1093 / MIN_CONF_REST 958 in formal/verify.sh. Body (now FROZEN): docs/tk102-derived-userset-enum-2026-10-12.md. NOT TAKEN: K=4, reverse write order, the 44 undriven sequence classes, P16 (doc secs 2, 5). Full phased gate run before commit.
