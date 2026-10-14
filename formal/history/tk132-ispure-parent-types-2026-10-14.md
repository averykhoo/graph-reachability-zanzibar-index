# `TK132` — `isPure` asks over the tupleset's parent types; the deliberate pin regeneration (2026-10-14)

**FROZEN as-of 2026-10-14.** A history file: read it for METHOD and for the reasoning behind
one regeneration, never for current state. Live state is `python scripts/task.py show TK132`
and `python scripts/gate_status.py`. The plan, the scout's measurements and the executive
decision are in [`../../docs/tk132-lean-ispure-ttu-target-2026-10-14.md`](../../docs/tk132-lean-ispure-ttu-target-2026-10-14.md)
("Decision 2026-10-14"). Builder: agent `build-TK132`.

This records the **why** for a `statement_pin.py --generate` run, as
`formal/conformance/statement_pin.py`'s own failure text requires.

## 1. What landed, in one sentence

`GraphIndex/Leaf.lean::isPure`'s `.ttu` arm now asks "is the target underived on EVERY parent
type the tupleset admits" (`GraphIndex/Leaf.lean::ttuParentTypes`, the twin of
`Spec/Stratify.lean::exprRefs` and of Python's `boolean.py::_is_pure` over `_member_types`),
replacing the type-agnostic NAME test `!derivedAnywhere S tgt`; the leaf-layer fact the cascade
termination proofs read off the old test became the explicit, decidable schema carry
`GraphIndex/LeafRules.lean::LeafTtuTargetsUnderived`.

## 2. Why the two headline statements moved (the sentence the decision requires)

**The two statements gain a schema carry the faithful allocation needs; it is vacuous on
`W4Fragment`, and it is FALSE on `D`/`D_nested`/`SlXt`, whose previous coverage was of the
wrong model.**

- `Zanzibar.runCascade2_no_abort` and `Zanzibar.cascade2_drains` (`GraphIndex/CascadeStrata.lean`)
  gain `(hLTU : LeafTtuTargetsUnderived S)` immediately after `hNBD`. Nothing else in either
  statement changed.
- Vacuous on `W4Fragment`: `GraphIndex/CascadeStable.lean::leafTtuTargetsUnderived_of_computedOrDirect`
  discharges it from `computedOrDirect` (every leaf rule is `.computed`, so there is no TTU
  target to constrain). It needs `NodupKeys` — a premise the old leaf THEOREM did not need —
  because `computedOrDirect` reads `S.lookup` while `leafRewrites` filters `S.defs`;
  `GraphIndex/FragmentDecide.lean::LeafRuleWitness.leafTtuTargetsUnderived_needs_nodup` is the
  decided counterexample to the `NodupKeys`-free statement. Every discharge site holds
  `GraphAdmission.nodup`. `NodupKeys` is NOT on the headline statements.
- The honest SCOPE LOSS (challenge X3): before `TK132` the schema-level premises of both
  statements held on `D` (the mainstream "inherit from parent, minus a ban" idiom) and `SlXt`,
  so they nominally covered them; the new carry is false there
  (`GraphIndex/LeafRules.lean::LeafRuleWitness.slXt_not_leafTtuTargetsUnderived`). That
  coverage was of a model that allocated leaves differently from the code, so losing it is the
  correction, not a regression. Design L-B (a store-level declaredness premise + a typed
  closure lemma) would buy it back and is deferred to `TK133`.

The headline DEFINITION pin moved by exactly: `def:Zanzibar.isPure` changed; rows
`def:Zanzibar.ttuParentTypes` and `def:Zanzibar.LeafTtuTargetsUnderived` added
(`directTypes`, `ttuTargets`, `NodupKeys` were already pinned). Both pins were seen RED
first: `FAIL: the STATEMENT of Zanzibar.runCascade2_no_abort changed` and the same for
`Zanzibar.cascade2_drains`, `2 headline theorem statement(s) differ`. After
`--generate`: `58/58 statements match`, `282/282 definitions match`.

## 3. The threading, MEASURED (not the scout's estimate)

The scout's P3 name-closure predicted ~52 `hNBD` carriers to thread and ~21 discharge sites;
it was a whole-word over-approximation. Build-driven, `hLTU` was added to **13 declarations**:
the two restated `LeafRules.lean` lemmas (`ttuTargetsSatL_ne_of_noTtuTarget`,
`rewriteClosureL_subject_pred_ne_of_noTtuTarget`), `Cascade.lean`'s
`reachedByW3d_edge_source_ne_R` / `reachedByW3d_Rnode_not_source` /
`reconcileJobsL_Rnode_not_source` / `runCascade_no_abort` / `cascade_drains`,
`CascadeStable.lean::writeLegSubjectsWide_L`, `CascadeStrata.lean`'s
`reachedByW3d2_edge_source_ne_R` / `reachedByW3d2_Rnode_not_source` / `runCascade2_no_abort`
/ `cascade2_drains`, and `CascadeStrataSettle.lean::round2_key_reads_derived`. The rule used:
discharge at the FIRST enclosing declaration that already holds `hNK` and the
`ComputedOnly`/`ComputedOrDirect` premise (via `leafTtuTargetsUnderived_of_computedOnly` /
`_of_computedOrDirect`), rather than widen a further signature. Only the two `CascadeStrata`
headline statements are pinned; `Cascade.lean::cascade_drains` / `runCascade_no_abort` are not.
Deleted: `derivedAnywhere_eq_false_of_mem_exprArms_of_isPure`,
`derivedAnywhere_eq_false_of_mem_leafRewrites` (+ its `_nonvacuous` witness, replaced by
`LeafRuleWitness.leafTtuTargetsUnderived_snlBoth`). None was audited, so
`formal/audited_theorems.txt` only GREW (13 names added, 0 removed).

## 4. Sabotages, literal (2026-10-14, byte-exact backup + sha256-verified restore)

Each applied to the green tree, built with `lake build ZanzibarProofs.GraphIndex.LeafRules`
(S6: `...CascadeStable`). Lean line numbers are as of 2026-10-14.

- **S1** — revert the arm to `!isDerived S (ty, ts) && !derivedAnywhere S tgt`: rc=1, FOUR
  errors, `LeafRules.lean:2669:64 Tactic decide proved that the proposition leafRewrites SlXt
  = [...] is false` (`lrXt_cross_type_kept`); `2681:28 ... ¬TtuTargetsSatL SlXt fun x => x ≠
  "viewer" is false` (`hLTU_load_bearing`, third conjunct); `2686:80 ... ¬LeafTtuTargetsUnderived
  SlXt is false`; `2742:59 ... leafRewrites SlW3 = [...] is false` (`lrW3_merged_computed_ttu`).
- **S2** — the SAME-type test `!isDerived S (ty, tgt)`: rc=1, `Leaf.lean:1152:51 Tactic decide
  proved that the proposition Option.map (persistedLeaves StD "doc") (StD.lookup ("doc",
  "access")) = some [PLeaf.closure (Expr.computed "banned")] is false` (`stD_leaves`); the build
  stops at `Leaf`. **S2b** (S2 with `stD_leaves` neutralised to reach `LeafRules`): three
  errors, `LeafRules.lean:2613:64 ... leafRewrites LeafWitness.StD = [...] is false`
  (`lrStD_no_ttu_rule`), plus `lrMix_mixed_parent_drop` and `lrW3_merged_computed_ttu`.
- **S3** — parent types read off the wrong def (the lookup keyed `(ty, tgt)` on the container
  type instead of `(ty, ts)`): rc=1, the same `Leaf.lean:1152:51` `stD_leaves` error.
- **S5** — `.all` → `.any`: rc=1, exactly ONE error, `LeafRules.lean:2721:64 Tactic decide
  proved that the proposition leafRewrites SMix = [...] is false` (`lrMix_mixed_parent_drop`).
  Every other pin stays green, confirming challenge X2: `SMix` is the only pinned shape that
  tells `.all` from `.any`. Python control (permanent,
  `formal/conformance/test_conformance_leaf_rules.py::test_python_side_sabotages_are_caught`
  (d)): with `any` in `_is_pure`, compiling `WIT:SMix` RAISES the I5 exclusivity `ValueError`
  ("... carries a derived subject predicate ..."), and the sweep surfaces it as a failure.
- **S6** — drop `(hNK : NodupKeys S)` from `leafTtuTargetsUnderived_of_computedOrDirect`: rc=1,
  `CascadeStable.lean:2197:64 Unknown identifier hNK`. Compile-only evidence; the semantic
  record is `leafTtuTargetsUnderived_needs_nodup`.
- **S4** (Python, PERMANENT in two modules) — `_is_pure`'s TTU arm put back on the NAME test:
  the leaf-rules sweep reddens EXACTLY `TK126:D`, `TK126:D_nested`, `TK126:SlXt`, `WIT:W3`
  (`test_python_side_sabotages_are_caught` (c)), and the leaf-row state comparison reddens
  EXACTLY `SlXt`, `D`, `D_nested` while `SlXtR` / `StD` stay equal
  (`formal/conformance/test_conformance_tk132_leaf_rows.py::test_python_name_test_sabotage_reddens_exactly_the_tk132_shapes`).

## 5. The acceptance, first-hand

On the fixed tree, BEFORE any test edit, `formal/conformance/test_conformance_leaf_rules.py`
went `7 failed, 66 passed`: each of `TK119`'s four `_TK132_EXPECTED` positive pins reported
`got {}` (every diff vanished) and the sweep reported `assert set() == {'TK126:D', ...}`. The
dict and its test were then deleted, the four joined the agreeing set, `SMix` was added as a
witness, and the non-vacuity floor was re-measured at 49 (67 sources, all agreeing) and
ratcheted up from 44.

## 6. What this does NOT fix

The Lean `graph` mode still answers one grid query wrong on every `.ttu`-in-derived-def shape:
it misses one public edge and two `upos` residue rows that Python (and the oracle) have. That
is the 2026-08-14 class, independent of `TK132` (scout P2), now row `TK149` (LATER), and
positively pinned by
`formal/conformance/test_conformance_tk132_leaf_rows.py::test_residual_public_diff_is_exactly_the_c4_rows`.
