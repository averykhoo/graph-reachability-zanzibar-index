---
id: AW-1
title: FINAL_REVIEW.md sec 4(d) under-claims after the remove leg
brief:
pri: LATER
size: S
deps: []
related: []
parent:
labels: [docs]
source: board
source_hash: ba590a695caa
created: 2026-08-16
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

`FINAL_REVIEW.md` §4(d) under-claims after the remove leg

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- that item's own dated note

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-10-13

Re-derived 2026-10-13 from the current `remove` constructor (session lane L2-AW1). The verdict is NO UNDER-CLAIM; the defect was an OVER-claim, now fixed in `formal/FINAL_REVIEW.md` §4(d).

First-hand READ (line numbers as of 2026-10-13):
- The `remove` constructor is identical on all three chains: `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean::ReachedByW3d2` (:430), `CascadeStrataSettle.lean::ReachedByW3d2C` (:3140) and `CascadeStrataAssemble.lean::ReachedByW3d2E` (:435). `formal/headline_definitions.txt` has `ReachedBy := ReachedByW3d2E`. Its guards are `RemoveAdmits σ T t` (`Cascade.lean::RemoveAdmits` := `t ∈ T`), `cascadeKeys S σ = []`, `StoreValidRules S T`, `BareStarStore T`, `TtuStarFree S T` and `htermT`. §4(d)'s scope ('in store, drained prior, pre-remove disciplines, never more') matches them hypothesis for hypothesis. Nothing is under-claimed.
- `FullScope.lean::GraphAdmission.storeValid` is `StoreValidRulesD S T` (:221, widened in leg 5 on 2026-08-05). `RulesSound.lean::StoreValidRules` (:201) is the plain W2 admission over `exprDirects`. `ReconcileCorrect.lean::StoreValidRulesD` (:1146) is the untainted/derived disjunction.
- In general the two are incomparable. Inside `W4Fragment`, `CascadeStrataSettle.lean::storeValidRulesD_of_storeValidRules_directArmsBare` (:595) gives plain ⇒ D, with `W4Fragment.directArmsBare` supplying its hypothesis. `FullScope.lean::W4WitnessDirect.outside_old_admission` (:1628) and `outside_old_admission4` (:2258) refute the converse. So the guard's `StoreValidRules` is strictly STRONGER than what `graph_correct` assumes.
- REASONED: `W4Fragment.noUnionDirects` (`FullScope.lean` :373) sets `exprDirects e = []` on every derived def. So plain `StoreValidRules` forbids ANY stored tuple on a derived key, which is why `removeGateB` fail-closes on `direct_arm_exclusion` (`_REMOVE_EXCLUDED`, row `P9`).

What changed: the sentence 'these are exactly the `W4Fragment` carries `graph_correct` already assumes' was false for the `StoreValidRules` conjunct. It now says that the last three disciplines ARE `W4Fragment` carries (`bareStar` / `ttuStarFree` / `term`) and that the first is strictly stronger than `GraphAdmission.storeValid`. The honest claim now reads 'from a drained state whose store holds no tuple on a derived key', with a pointer saying P9 owns the widening and that the sentence must be re-read when P9 lands. The ⚠ AW-1 paragraph is deleted. §4's index entry now reads '(d)'s scope wording → `AW-1` (DONE 2026-10-13)'. 'Plausibly subsumed by ZT-P3-4 / ZT-P3-5' was false: both are closed, and the sentence survived them.

What builds: prose only, so there is no Lean change and no new check, and nothing to sabotage. No verify.sh step or test pins this prose. `claim_rot` covers only CORRESPONDENCE.md, and FINAL_REVIEW.md is exempt from doc_counts' prose scan. What is red: `doc_counts --check` was rc=1 on 2026-10-13, but only on counts-block drift from other lanes' new tests (`tests/` collected 2283→2307). It is unrelated to this edit and is regenerated in the gate stage.

Next action: none. When P9 widens the guard to `StoreValidRulesD`, re-read §4(d).
