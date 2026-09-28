---
id: TK117
title: ParityEngine._grid never asks object-* targets or star from-chain subjects; cap sample gaps
brief: coverage: object-* targets and star from-chain subjects never gridded; cap sample can skip own op
pri: LATER
size: M
deps: []
related: []
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H7. The section is copied below as it stood when filed; the doc is the body of record.


All three sit in one function, `tests/parity.py::ParityEngine._grid`, and every one of them
changes the `rng.sample` pool. **Recommended as ONE row** so the pool shifts once, not three
times. No product divergence was found in any of the three.

**Witness 5, object `*`** (*verify* `PROBED`, 2026-09-28). Schema `folder{viewer:[user]}`,
`doc{parent:[folder]; viewer: viewer from parent}`, `object_wildcard_shapes={('doc','parent')}`,
tuples `('...','folder','f1','parent','doc','*')` and `('...','user','a','viewer','folder','f1')`:

```
grid size=24 object-* queries=0 subject-* queries=8 ; witness in grid? False
check(user:a, viewer, doc:*): oracle, graph, set:py, set:roaring all True
sabotage (backends return False for object '*') on tests/test_parity_engine.py:
  M0: 19 passed ... {"graph_objstar": 0, "set_objstar": 0} ; MG: 19 passed ; MS: 19 passed
control tests/test_matrix.py -k union_wildcard: M0 3 passed ; MG 2 failed, 1 passed ; MS 2 failed, 1 passed
```

**Witness 12, star from-chain userset subject** (*verify* `PROBED`, seed-24 schema, 2026-09-28):
`doc{parent:[doc, doc:*]; r0:[user]; r1: r0 from parent; r2: r1; r3:[user, user:*];
r4: r2 from parent and (r0 from parent or r0 from parent)}`. Writes
`('...','doc','d2','parent','doc','d1')`, `('...','user','u1','r3','doc','d2')`,
`('...','doc','*','parent','doc','d1')`, `('...','user','u1','r0','doc','d1')`,
`('...','user','u1','r3','doc','d1')`.

```
graph joined: True None ; derived_families: [('doc', 'r4')]
Q ('r0','doc','*','r1','doc','d1') {'graph': True, 'set:py': True, 'set:roaring': True, 'oracle': True}  (same for r2, r4)
IN-GRID ... parity= False conf= False hyp= False   (all 3 queries)
star-userset subjects in parity grid: []
```

**Witness 9, cap sampling** (*verify2* `PROBED`, `v2_probe.py`, 2026-09-28; `github.fga`, 14
accepted writes, the last being `user:hank maintainer repo:docs`):

```
M0 no-lie cap=600: GREEN  graph_present=True leaf_families=0
final pool=1056 final compared=600 ever compared=931 never=125
never-compared TRUE: ('...', 'user', 'hank', 'maintainer', 'repo', 'docs')
planted lie cap=600: GREEN
planted lie cap=10**9: RED: check parity broken after add ('...', 'user', 'hank', 'maintainer', 'repo', 'docs'): q=('...', 'user', 'hank', 'maintainer', 'repo', 'docs') graph=False oracle=True
lie on the last write's own check escapes at cap=600 on 8/20 seeds   (independent store: 15/20)
```

**Proposed row** — *"`ParityEngine._grid` never asks object-`*` targets or star from-chain
subjects, and its cap sample can skip the last op's own effect"*, **LATER**, size S-M.
Brief: three coverage gaps in the default integration engine's grid, with no divergence found.
(a) `_note_names` drops object `*`, so no object-`*` query is ever asked, even after `doc:*`
is stored. Sabotaging the backends' object-`*` answers leaves `tests/test_parity_engine.py`
green. (b) Subject shapes come only from Direct restrictions, so star-userset subjects created
by a star tupleset (`doc:*#r0`, including on a derived target) are asked only on the lookup
surfaces. Mirror `tests/test_lookup_oracle.py::_subject_candidates`. (c) Above `grid_cap`,
Layer A is `rng.sample`d per op with no floor, so a divergence confined to the last write's
own queries escapes with probability about `(N-cap)/N`.
Fix: object `*` in Layer A for object-wildcard shapes, plus an rng-free Layer-B guarantee;
TTU from-chain shapes, including `*`, in `subject_shapes`; an rng-free WRITE-LOCAL floor
appended after the cap, and optionally a rotating cursor in place of `rng.sample`. Apply the
same to `tests/genswarm.py::grid_for` (cap 400) and `tests/test_hypothesis.py::_grid`.
Reconcile `docs/spec-deviations.md` item 2 ("full-grid" vs "sampled") with the spec's
"delta-affected pairs ∪ a sampled grid". Pin each witness positively. The planted-lie probe
must go GREEN → RED after the fix, with an M0 control. Leave
`formal/conformance/grid.py::grid` and
`formal/conformance/test_conformance_enum.py::_graph_query_filter` alone: they mirror the
Lean `hqs` / `hqo` scope, and `TK101` revisits the second.

## Log
