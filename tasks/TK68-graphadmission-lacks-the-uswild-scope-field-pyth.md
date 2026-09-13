---
id: TK68
title: GraphAdmission lacks the usWild scope field Python enforces (UnsupportedByGraphIndex)
brief: Blocks P6 step 3b: reachedByW3d_edge_source_ne_R is FALSE once the write leg bridges
pri: LATER
size: S
deps: []
related: [P6]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-13d
moved: 2026-09-13d
updated: 2026-09-13d
closed:
---

`FullScope.lean::GraphAdmission` mirrors Python's schema-admission rejections field by
field, and one of them is missing: it has `objWild` for `UnsupportedByGraphIndex` on OBJECT
wildcards over derived relations, and no twin for the same rejection on WILDCARD USERSETS
over derived relations. The Lean admission predicate is therefore strictly weaker than the
shipped compiler. Inert today because no live chain calls `ensureInBridges`; `P6` step 3b
makes it live and immediately needs the field.

## Traps

⚠ **Do not try to save `reachedByW3d_edge_source_ne_R` with a premise — restate it.** The
type-index trap is in the `2026-09-13d` Log entry: `isDerived` and
`isSubjectWildcardUserset` are keyed on `(type, relation)` while that theorem concludes
about the predicate STRING, and a literal `[x:*#R]` restriction at an untainted key
`(x, R)` is legal Python. The wrapper `::reachedByW3d_Rnode_not_source` survives only
because it fixes the type to `dt`.

⚠ **This row is ONE measured instance, not a census of `GraphAdmission`.** It was found by
following a single broken proof. Whether other Python admission rejections are unmirrored
is unmeasured; do not let closing this row imply the structure was swept.

## Read first

- the `2026-09-13d` Log entry below — the gap, why it is inert today, and the type-index trap
- `formal/lean/ZanzibarProofs/FullScope.lean::GraphAdmission` — the structure, and `objWild`
  as the field this one should sit beside
- `formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset` —
  the predicate the new field must constrain, and its two disjuncts
- `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean::reachedByW3d_edge_source_ne_R` and
  `::reachedByW3d_Rnode_not_source` — the theorem that goes false and its one consumer
- `tasks/P6-ttustarfree-ii-bridges-on-rule-routed-write-path.md` — the `2026-09-13d` entry,
  for where this sits in step 3b

## Log

### 2026-09-13d

Found by P6 step 3a (2026-09-13d) while measuring the cone, not by a sweep of the admission structure -- so treat the scope of this row as ONE measured instance, not a census.

THE GAP. `FullScope.lean::GraphAdmission` (`:160`) carries `objWild : forall tr in S.objectWildcards, isDerived S tr = false` -- the Lean mirror of Python refusing OBJECT wildcards on derived relations. `zanzibar_utils_v1.py` rejects TWO shapes with `UnsupportedByGraphIndex`, the other being WILDCARD USERSETS OVER DERIVED RELATIONS (CLAUDE.md "Layout / mental model" names both), and `GraphAdmission` has no field for the second. So the Lean admission predicate admits a schema the shipped compiler refuses.

WHY IT IS INERT TODAY, AND WHEN IT STOPS BEING. `Schema.isSubjectWildcardUserset` only reaches a live chain through `ensureInBridges`, and no live chain calls that yet -- `writeRules` / `writeLoggedRules` are bridge-free folds. P6 step 3b is what makes it live, and the obligation surfaces immediately there: `Cascade.lean::reachedByW3d_edge_source_ne_R` (audited, `Audit.lean:714`) says no edge on a W3d state is sourced at a node with predicate R. A bridge edge is sourced at its CONCRETE endpoint, so once the write leg bridges, that statement is FALSE for any bridged-in shape whose predicate is R -- and its one Lean consumer, `::reachedByW3d_Rnode_not_source`, needs exactly `isSubjectWildcardUserset S dt R = false` at the SAME key `(dt, R)` it already knows is derived. That is this field.

MEASURED, not predicted: with the step-3b composition in the tree, `reachedByW3d_edge_source_ne_R` is the ONLY error `Cascade.lean` reports that is not mechanical, and `reachedByW3d_Rnode_not_source` is the only Lean consumer of it (grep 2026-09-13d: three other hits are two Audit lines and one prose citation in `CascadeStrata.lean:1594`).

(!) THE TYPE-INDEX TRAP, which is why the general lemma must be RESTATED and not merely re-premised. `isDerived` and `isSubjectWildcardUserset` are both keyed on `(type, relation)`, but `reachedByW3d_edge_source_ne_R` concludes about the predicate STRING `R`. A literal `[x:*#R]` restriction at an UNTAINTED key `(x, R)` is legal Python and bridges a node whose pred is `R`, so `a.pred != R` is false as a general claim no matter what field is added. The wrapper survives because it fixes the type to `dt`. Do not try to save the general statement with a premise.

SCOPE. Add the field next to `objWild`, discharge it where the other admission fields are discharged, and use it at `reachedByW3d_Rnode_not_source`. Sized S on the assumption that P6 step 3b pays the surrounding cone anyway; filed separately because it is a FIDELITY gap in its own right -- the Lean admission predicate is weaker than the shipped compiler -- and would be worth closing even if P6 were abandoned.
