---
id: TK133
title: Widen W4Fragment.term (NoTtuTarget) to (type, relation) so TK126's B/C shapes are proved
brief: TK126 B/C are served but outside W4Fragment: Lean NoTtuTarget is name-keyed; widening it is an XL re-proof
pri: SOMEDAY
size: L
deps: []
related: [TK126, TK132]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-10-08
moved: 2026-10-08
updated: 2026-10-08
closed:
---

`W4Fragment.term`'s `NoTtuTarget S R` (`GraphIndex/ReconcileCorrect.lean::NoTtuTarget`) is
keyed on the relation NAME: no TTU rewrite anywhere may target a name that is derived on
ANY type. Since TK126 (2026-10-08) Python serves TTUs whose target name is derived on some
other type (variants B/C of `docs/tk126-ttu-target-boolean-name-2026-10-07.md`, e.g. every
type defining its own `viewer`), and they are served-but-outside-`W4Fragment` (field
`term`). Their equivalence evidence is differential only
(`tests/test_tk126_ttu_target_name_collision.py`).

This row would bring them INSIDE the proved scope by making `term` `(type, relation)`-keyed.
REASONED (doc sec 4.3): a type-aware `NoTtuTarget` may even be derivable from
`GraphAdmission.matchDecl` plus the type-aware taint fixpoint, but the chain that consumes
it is stated over subject-predicate NAMES (`NoTtuTarget` occurs on 211 lines across 24
`.lean` files, measured 2026-10-07), so it means re-proving the subject-predicate chain
over `(type, predicate)`. Size REASONED XL (filed as L, the largest size the tool accepts), UNVERIFIED. Not needed for equivalence; it only
grows the proved scope.

**Next action:** none scheduled. If picked up, read doc sec 4.2 item 1 and 4.3 first, and
do the (a+) faithful-`isPure` row before this one.

## Read first

- [`docs/tk126-ttu-target-boolean-name-2026-10-07.md`](../docs/tk126-ttu-target-boolean-name-2026-10-07.md) sec 4.2-4.3 and 5 (a+) (the Lean side, measured counts).
- [`formal/CORRESPONDENCE.md`](../formal/CORRESPONDENCE.md) sec 7.1, the `TK126` entry (the recorded gap).
- [`tests/test_tk126_ttu_target_name_collision.py`](../tests/test_tk126_ttu_target_name_collision.py) (the differential evidence for the served shapes).

## Log
