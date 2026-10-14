---
id: TK149
title: Lean graph mode under-reports a .ttu inside a derived def (2026-08-14 class, fail-closed)
brief: Lean graph mode misses a TTU-in-derived-def public edge + upos residues (fail-closed, outside W4)
pri: LATER
size: M
deps: []
related: [TK132, TK133]
parent:
labels: [formal]
source: docs/tk132-lean-ispure-ttu-target-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-14
updated: 2026-10-14
closed:
---

## What

The Lean operational model (`zcli` `graph` / `graph-state` modes, i.e. the `ReachedBy*` chain over
`GraphIndex/Leaf.lean` + `LeafRules.lean` + the cascade) UNDER-REPORTS a `.ttu` arm inside a
derived (boolean) def. On every such shape measured it misses one public edge and two residue
rows that Python writes, and answers one grid query `false` where the oracle, the Lean spec and
Python all say `true`. Fail-closed (a missed ALLOW, never a wrong ALLOW), and outside
`W4Fragment` (`computedOrDirect` bans a `.ttu` in a derived def), so no headline theorem
reaches it. First recorded 2026-08-14 (`formal/CORRESPONDENCE.md` §0, the "There is no rc for
out of the proved fragment" note); it had no task row until `TK132` filed this one (decision
2026-10-14, `docs/tk132-lean-ispure-ttu-target-2026-10-14.md` C4).

## Evidence (first-hand PROBE 2026-10-14, after `TK132`)

On `SlXt`, `SlXtR`, `StD`, TK126 `D` and `D_nested` the leaf-row edges now AGREE (that was
`TK132`), and the residual diff is exactly, on each:

- edge only in PYTHON: `('user', 'alice', '...', '') -> ('doc', 'd1', <rel>, '')`
- residue only in PYTHON: `('doc', 'd1', <rel>)` and `('doc', 'd2', <rel>)`, each
  `(∅, ∅, {('folder', 'f1', 'viewer')})`

with `<rel>` = `access` (SlXt/SlXtR/StD) or `viewer` (D/D_nested). Python matches the oracle on
all of them (scout P2/P6). The literal rows are POSITIVELY pinned (never xfailed) by
`formal/conformance/test_conformance_tk132_leaf_rows.py::test_residual_public_diff_is_exactly_the_c4_rows`,
which goes red the moment this is fixed (or widens).

## Next action

Locate where the model's derived-def evaluation drops the TTU residue (`upos`) row and the
public edge for a TTU arm under `excl` (compare `processor.py` reconcile on a TTU closure leaf
against `Reconcile*.lean`); decide whether to model it or record it as a fragment boundary.
Per CLAUDE.md "Who decides": the default assumption is that the MODEL is out of date here,
since Python matches the oracle.

## Log
