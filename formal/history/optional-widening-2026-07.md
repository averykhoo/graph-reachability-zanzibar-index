# Optional assurance-widening — design briefs & resume points (2026-07-18)

**Purpose.** The formal-verification arc is COMPLETE (T1 + T2a/T2b + T3/T6 over
`ReachedBy`, Phase 6, conformance — all sorry-free, axiom-clean, gate green). What
remains is the OPTIONAL assurance-widening ranked in `FINAL_REVIEW.md §4`. This file
is the durable design + resume state for that work, so a fresh-context session can
pick up ANY of the four targets without re-doing recon. Read `formal/HANDOFF.md`
first, then the target's section here.

Each target was scoped by a read-only recon + (for #1) attack-first `#eval` probes.
House rules unchanged (honesty; attack-first; green `verify.sh`; commit per green
increment; subagents don't parallelize proof-closing — one Lean-editing leg at a time).

Working order chosen (2026-07-18): **interleave** — bank the tractable targets (#3
state/enum, #4 remove) then return to the deep grinds (#1 Direct-arm leg 4+, #1
TTU/userset, #2 strata). Ordering is the orchestrator's call; adjust freely.

---

## Target #1 — Leaf fragment widening (`W4Fragment.computedOnly` → Direct/TTU arms)

Goal: let derived (tainted/boolean) defs carry `Direct` and TTU operand leaves
(`PDerivedTTU`/`PDerivedUserset`), not just `computed`. `computedOnly` is STRUCTURAL —
it powers two workhorse lemmas that are literally FALSE for Direct/TTU leaves. Genuine
proof effort. Split **Direct-arm-first, then TTU/userset**.

Attack-first ground truth (all backends agree; NO live Python divergence):
- Tainting needs an exclusion/intersection ROOT or a reference to an already-derived
  relation — a plain `or` of a Direct/TTU arm compiles UNTAINTED. Real Direct-arm shape:
  `approver = [user] but not banned` (raw `excl (direct [user]) (computed banned)`).
- A Direct arm compiles to a `PClosureLeaf(storage=True)` family `<rel>.<index>`; a raw
  write on the public derived key is admission-accepted and routed onto that storage leaf
  (I5 preserved). So the write-half "no stored tuple on a derived key" must be reformulated.
- Python has NO 2-stratum cap; `twoStrata` is proof-scope only (see #2).

### Direct-arm sub-legs — progress
- **Leg 1 DONE (commit `98773d3`)** — read-half workhorse. Added (additive, `ReconcileCorrect.lean`):
  `ComputedOrDirect`, `DirectArmsBare`, `computedOnly_computedOrDirect`/`_directArmsBare`,
  `grantsOf_bare_subjects`, `memberOfGranted_of_bareGrants`, `directLeaf_bare_indep`,
  **`evalE_computedOrDirect`** (generalized READ congruence; subject/store/rel SHARED —
  varying-subject congruence is attack-refuted for `.direct` — query free).
- **Leg 2 DONE (commit `0dd8d7b`)** — write-half admission + diffing retraction crux.
  `ReconcileCorrect.lean`: `exprDirectsAll` (recurses inter/excl), `StoreValidRulesD`
  (isDerived partitions disjuncts; derived-key tuple must be BARE subject on an
  `exprDirectsAll` leaf), `storeValidRulesD_of_storeValidRules`, `reachedByW3a_*_d`
  (reach-collapse admits stored base seed edges, sources stay BARE).
  `ReconcileDiff.lean`: `reconcileKeyD_edge_char_cd`, **`reconcileKeyD_retracts_excluded`**
  (THE CRUX — excluded bare candidate's derived pair absent after the diffing pass even if
  it pre-existed as a stored base edge; attack-`#eval`-confirmed sound).
- **Leg 3 DONE (commit `8a9bee1`)** — base-equation WALL characterized (green checkpoint).
  Attack-first: the widened `graphRec_base_eq_d` is FALSE without a `NoStoreSubjectR`
  hypothesis (userset-over-derived flow → graph=true/sem=false), TRUE with it (faithfully
  available downstream via `reachedByW3d2E_toC`'s `hterm`). Landed additive
  `storeValidRules_untaintedFilter` (restrict-T entry). NOTE: `graphRec_base_eq` is at the
  ADMITTED base state where the derived-key seed edge is a harmless DEAD-END; item 1 leans
  on a dead-end/reach-invariance argument gated by `NoStoreSubjectR`, NOT on leg-2's
  drained-read retraction.
- **Leg 4 DONE (2026-07-19, this session — UNCOMMITTED at write time; verify.sh lean
  PASSED, audit 431/431, sorries=0, all new theorems standard-axioms-only).** The
  base-equation WALL is DISCHARGED. All in `RestrictBase.lean` (+ 6 Audit entries):
  - **`graphRec_base_eq_d` / `graphRec_base_eq_bs_d`** — the WIDENED base equations:
    admitted base over a `StoreValidRulesD` store (stored BARE Direct-arm tuples on
    derived keys ADMITTED), untainted operand read = `sem`, **NO `ComputedOnly`/`hCO`
    hypothesis**; instead the `hterm` bundle
    `∀ dt R, isDerived → NoTtuTarget S R ∧ NoStoreSubjectR T R` — the EXACT bundle every
    chain consumer already carries (so downstream threading needs no new fragment field).
  - **Design lemma A** = `rewriteClosure_derived_eq_seed`: a derived-key tuple's closure
    is `[t]`. SIMPLER than designed — no `exprRefs`-heredity/`TtuTuplesetsDirect` needed:
    a firing rule's match key would BE the derived key, but `RewriteMatchDeclared`
    (already a base-eq premise) says every match key is declared UNTAINTED. Recorded
    divergence from the design's lemma-A recipe; the compiler agreed.
  - **Design lemma B** = `probeNonDerived_untaintedFilter` (+ `untaintedFilter_extra_edge_derived`,
    `untaintedFilter_derivedNode_not_source`, generic `nreaches_extra_inert`): the ≤4-probe
    read agrees between the full-store admitted base and the untainted-filter rebuild
    (`exists_admitted_ofSubset` — the R5a tool, no new state-transfer needed). Extra edges
    are derived SEED edges; dead ends under `hterm` (never a source — `rewriteClosure_subject_pred_ne`,
    string-level); both probe targets carry the untainted `(dt, r')` key so they differ
    from every extra target by taint. Attack-first `#eval` (deleted): the agreement is
    (true, false)-REFUTED without `NoStoreSubjectR` — the leg-3 kill reproduced at lemma
    level — and confirmed on direct/ttu/userset-flow/bare-star/star-subject shapes.
  - **Design lemma C** = `sem_untaintedFilter` (+ `semAux_untaintedFilter`,
    `evalE_untaintedFilter`, `ttuLeaf_untaintedFilter`, `memberOfGranted_untaintedFilter`,
    `grantsOf_untaintedFilter`, `filter_absorb`/`any_filter_absorb`): `sem S T q =
    sem S (T↾U) q` on untainted reads. Route DIVERGES from the design (recorded): the
    store-congruence is proved over the untainted schema restriction `S↾U` at EVERY fuel
    and EVERY key (undeclared keys false on both stores ⇒ the rec-agreement IH needs no
    taint bookkeeping), then both ends close via `semAux_restrict` + T0a over `S↾U` —
    avoiding any `Stratifiable S` premise on the MIXED schema. Hypotheses: `NodupKeys`,
    `StoreDeclared S T` (⇐ new `storeDeclared_of_validRulesD` via new
    `directTypes_mem_of_exprDirectsAll`), `NoUsersetStar T`, `TtuStarFree S T` (both ⇐
    `StarFreeStore` in the plain variant; ⇐ `BareStarStore`+given in `_bs`) — the
    `instances` branches are the only store reads that don't filter by an untainted key,
    and they are dead. Attack-first: NO `NoStoreSubjectR` needed on the sem side
    (confirmed equal even on the kill store); a DERIVED query genuinely diverges
    ((true, false)) so the untainted-query scope is load-bearing.
  - **Refactor (audited statements UNCHANGED):** `graphRec_base_eq`/`_bs` are now 8-line
    wrappers deriving the no-stored-derived-key fact from `hCO` and delegating to the new
    hypothesis-factored cores `graphRec_base_eq_unt`/`_bs_unt` (`hStoreUnt` premise) —
    which leg-4 applies at the sub-store `T↾U` where `hStoreUnt` is free. Zero call-site
    churn; axiom audit re-verified both audited originals.

### Direct-arm — leg 5 PROGRESS (2026-07-19, this session — UNCOMMITTED; verify.sh lean PASSED, audit 434, sorries=0, standard axioms only)
**Sub-step 1 read-bridge foundation LANDED (additive, green).** Three `_d`/`_cd`
read-bridge lemmas, no fragment/conformance change (so lean-only gate):
- `checkFn_eq_semStep_cd` (`ReconcileCorrect.lean`, after `evalE_computedOrDirect`) — the
  `ComputedOrDirect ∧ DirectArmsBare` analog of `checkFn_eq_semStep`: `checkFn = semAux(f+1)`
  at a derived key whose def is a boolean tree of `computed` refs + BARE `Direct` arms,
  given operand agreement on `computedRefs e`. The `.direct` arm rides via
  `evalE_computedOrDirect` (bare arm is `rec`/query-independent), so no arm-side agreement.
- `checkFn_eq_sem_of_base_d` / `checkFn_eq_sem_d` (`ReconcileComplete.lean`, after
  `checkFn_eq_sem`) — the `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare` analogs of
  `checkFn_eq_sem_of_base`/`checkFn_eq_sem`, routing the operand read through
  `graphRec_base_eq_d` (the leg-4 widened base eq) + `checkFn_eq_semStep_cd`. Concrete bare
  subject scope (`hs : s.name ≠ STAR`).

**★ ATTACK-FIRST KILL (house rule 2) — the W3a-level vertical slice `graph_correct_w3a_d`
is FALSE.** Probed the natural "widen `graph_correct_w3a` under `StoreValidRulesD`" path
before proving it. `#eval` (deleted): schema `approver := excl (direct [user]) (computed
banned)`, `banned := direct [user]`; store `{(alice,approver,doc), (alice,banned,doc)}`
(valid under `StoreValidRulesD` — a stored BARE Direct-arm tuple on the derived `approver`
key). `sem(alice,approver,doc) = FALSE` (direct arm matches but alice is banned ⇒ excl =
true ∧ ¬true). BUT the stored seed tuple materialises a base seed edge `subjNode(alice) →
objNode(doc:doc,approver)` (leg-2 `reachedByW3a_*_d`), so the RAW W3a reconcile state has
`reach(alice→approver:doc) = true` — the residue-empty derived read (`check_derived_
ResidueEmpty`) returns `true ≠ sem`. Structural root: `graph_correct_w3a`'s soundness base
case (`reachedByW3aAdmitted_derived_edge_sound`, `ReconcileComplete.lean:432`) uses
`reachedByRules_derived_no_inedge` = "a derived key has NO base in-edge", which is FALSE
under `StoreValidRulesD` (a stored Direct-arm tuple IS an in-edge). The W3a reconcile model
runs NO diffing retraction; the excluded/banned stored seed persists. **So the read half
widens cleanly (landed) but the WRITE half of the Direct-arm widening must thread through
the W3d DIFFING pass** (`ReconcileDiff.lean` `reconcileKeyD` / leg-2's
`reconcileKeyD_retracts_excluded`, which retracts the excluded seed), i.e. the widened
correspondence lives at the W3d2 DRAINED state, NOT the W3a assembly. This refines sub-step
2 below: it is not only the STAR/coverage split — the base derived-edge soundness itself
requires the retraction, so there is no useful `graph_correct_w3a_d` milestone.

**Remaining leg-5 work (sub-steps 1-cont/2/3 below):** the read-bridge `_d` lemmas are the
reusable foundation for the W3d2 derived-read consumers; the W3a-assembly consumers
(`ReconcileComplete.lean:700` `graph_correct_w3a` derived path) are a DEAD END (above), so
skip them — thread `StoreValidRulesD` into the W3d2 diffing/settled consumers
(`CascadeStrataSettle.lean:884`, `CascadeStrataResettle.lean:1540`, and the diffing edge
char / retraction from leg 2) directly. The untainted-operand read consumers
(`ReconcileComplete.lean:128`/`779`, `ReconcileStarsComplete.lean:1058`,
`CascadeSettle.lean:1116`) can offer `_d` forms off `checkFn_eq_sem_of_base_d`/the base eqs
without the write-half wall. Then sub-steps 2 (coveredFn star/concrete split) + 3 (widen
`W4Fragment` + witness `W4WitnessDirect` + conformance) as below.

### Direct-arm — leg 5 sub-steps 1-cont./2 LANDED (2026-07-19, this session — UNCOMMITTED; verify.sh lean PASSED, audit 441, sorries=0, standard axioms only)
Additive, no fragment/conformance change (lean-only gate). Two banks:

**Sub-step 1 cont. — the STAR-RELAXED + ROUTED read spine** (foundation the settled
consumers migrate onto):
- `checkFn_eq_sem_of_base_bs_d` / `checkFn_eq_sem_bs_d` (`ReconcileComplete.lean`) — the
  `BareStarStore`+`TtuStarFree` star-relaxed `_d` analogs of leg-5a's `checkFn_eq_sem_of_base_d`/
  `_d`, routing the untainted operand read through `graphRec_base_eq_bs_d` (leg 4) +
  `checkFn_eq_semStep_cd`. These are what the `graphRec_base_eq_bs`/`checkFn_eq_sem_bs` consumers
  migrate onto under `StoreValidRulesD`.
- `checkFnR_eq_semStep_cd` (`CascadeStrataSettle.lean`, after `checkFnR_eq_semStep`) — the ROUTED
  (`graphRecR`, via `evalE_computedOrDirect`) `cd` step bridge; the routed foundation for a
  `_d` clone of `checkFnR_eq_sem_settled`.

**Sub-step 2 — the coveredFn star/concrete SPLIT** (attack-first, house rule 2):
- **★ KILL CONFIRMED (`#eval`, deleted).** Naive-widened `checkFn_eq_coveredFn_of_no_extra` under
  `ComputedOrDirect`/`DirectArmsBare` is FALSE: schema `approver := excl (direct [user]) banned`,
  store `{(alice,approver,doc)}` ⇒ `checkFn alice = true ≠ coveredFn * = false` (bare-concrete
  match disjunct fires at alice, absent from the star branch). Probe also CONFIRMED the fix both
  ways: a subject with NO concrete grant AGREES with its star under `[user:*]` coverage (and stays
  agreeing under an UNRELATED concrete grant); a subject with its OWN concrete grant DIVERGES.
- **The corrected split (landed).** `NoConcDirect T s dt on rel e` (`ReconcileStars.lean`): `s`
  has no concrete Direct-arm grant on any Direct arm of `e`. Under it, `directLeaf` at `s` = at
  `starSubj s.shape` (`directLeaf_star_of_noConc`; both reduce to the shape's bare-STAR coverage
  read — `memberOfGranted` dead on bare grants, concrete disjunct dead by the gate). The tree
  transports via `evalE_star_of_noConc` (generic in `rec1`/`rec2`, so it serves BOTH the unrouted
  `graphRec` and routed `graphRecR` reads). Split lemmas:
  `checkFn_eq_coveredFn_of_no_extra_cd` (`CascadeEnum.lean`, unrouted) +
  `checkFnR_eq_star_of_not_enum_cd` (`CascadeStrataEnum.lean`, routed). (`+ any_congr_mem` helper,
  `concMatch`.) The third cited site, `checkFn_agree_of_graphRec` (`ReconcileStars:483`), needs NO
  new lemma — its `_cd` (cross-state, subject-shared) already landed in **leg 2**
  (`ReconcileDiff.lean:834` `checkFn_agree_of_graphRec_cd`).

### Direct-arm — leg 5 FINAL SLICE — the ENUM HALF + read-bridge `_d` clones LANDED (2026-07-19, this session — UNCOMMITTED; verify.sh lean PASSED, audit 441 → 446, sorries=0, standard axioms only)
Additive, no fragment/conformance change (lean-only gate). ATTACK-FIRST (`#eval`, house rule 2 —
**NO KILL**): a stored BARE Direct-arm subject lives in the FIXED store `T` (`grantsOf T rs dt on R`),
NOT in any mutating operand residue, so — unlike the 12h kill (a fresh grant appearing only in a
dirty operand's FUTURE residue) — it is enumerable at EVERY cascade state directly from `T`; the
`NoConcDirect`-failing subject IS its own grant's subject, hence in `storedDirectSubjects`. (Also
confirmed the ghost direction: a wildcard arm with NO bare-STAR grant reads `false` at the star.)

**Landed this slice (all additive):**
- **Foundational (`ReconcileStarsComplete.lean`):** `mem_exprRestrictions_of_directsAll`,
  `directArmsBare_mem`, **`graphRec_star_declared_d`** (the star-reach no-ghost core over
  `StoreValidRulesD`, seed classification via the `exprDirects`∨`exprDirectsAll` disjunction),
  `evalE_computedOrDirect_true_leaf` (a true `ComputedOrDirect` tree has a true computed leaf OR a
  true `Direct` arm), `directArm_star_declared` (a true `Direct` arm at the star ⇒ a bare-STAR grant
  ⇒ a wildcard-flagged restriction ⇒ declared), **`coveredFn_declared_d`** (the linchpin, widened).
  `computedOnly_directArmsBare` already existed (`ReconcileCorrect.lean`).
- **Read bridges:** **`checkFnR_eq_sem_settled_d`** (`CascadeStrataSettle.lean`, after the ComputedOnly
  original) — routed stratum-staged bridge over a Direct-arm def (arm via `checkFnR_eq_semStep_cd`,
  operands still ComputedOnly via `graphRec_base_eq_bs_d`/`coveredFn_declared_d`/`checkFn_eq_sem_bs_d`);
  **`checkFnR_star_declared_d`** (`CascadeStrataEnum.lean`) — routed no-ghost-coverage (untainted leaf
  via `graphRec_star_declared_d`, derived leaf via the settled `stars` row, `Direct` arm via
  `directArm_star_declared`).
- **Enum half (`CascadeStrataEnum.lean`):** `directLeaf_star_userset_bare` + **`evalE_star_bareArms`**
  (star transport over `ComputedOrDirect`/`DirectArmsBare`, BOTH subject kinds — bare via
  `directLeaf_star_of_noConc` gated on `NoConcDirect`, userset via `directLeaf_star_userset_bare`,
  no gate), `storedDirectSubjects` (= `exprDirectsAll e` grants' subjects, read from `T`),
  `noConcDirect_of_not_mem`, `enum2BaseD`/`enumJob2D` (= `enum2Base ∪ storedDirectSubjects`),
  `checkFnR_eq_star_of_not_baseD`, **`w3dJobCoverage_enumJob2D`** (the coverage discharge), and
  **`w3d2_leg_context_d`** (packages the routed bridge + declaredness). Audit: the 5 correspondence
  ones (`coveredFn_declared_d`, `checkFnR_eq_sem_settled_d`, `checkFnR_star_declared_d`,
  `w3dJobCoverage_enumJob2D`, `w3d2_leg_context_d`) added to `Audit.lean`.

### Direct-arm — RESUME (the state-level `_d` clones need the `_d` CHAIN; then sub-step 3)
**★ WALL / DESIGN REFINEMENT (this session).** The read-bridge + coverage-discharge `_d` clones are
DONE and are exactly the hypothesis-factored cores the design promised — they take the shadow (`h0 :
ReachedByRulesAdmitted σ0 S T`, `hsh : UntaintedShadow`) as INPUTS, so they need NO `_d` chain. BUT the
design's expectation that the settled-consumer clones "just need `coveredFn_declared_d` + enum" was
INCOMPLETE: the STATE-LEVEL correspondence theorems — `w3c_row_char` (`ReconcileStarsComplete.lean:291`),
`graph_correct_w3d2` (`CascadeStrataResettle.lean:1436`, DERIVES the shadow at `:1456` via
`reachedByW3d2_shadow hW3d2 hNK hCO hSV hterm`), and `w3dJobCoverage_enumJob2_state`
(`CascadeStrataEnum.lean`) — DERIVE their base/shadow/master from the CHAIN via
`reachedByW3c_master` / `reachedByW3d2_shadow` / `reachedByW3d2C_settled`, each **gated on `hCO : ∀
ComputedOnly` + `hSV : StoreValidRules`** (`CascadeStrataSettle.lean:577-582` for the shadow). So a full
`_d` clone of those needs a **`_d` CHAIN**: `reachedByW3d2_shadow_d` / `reachedByW3c_master_d` /
`reachedByW3d2C_settled_d` (+ the underlying W3c/W3d2 write-model reconcile passes) re-proven admitting
`StoreValidRulesD` + a `ComputedOrDirect ∧ DirectArmsBare` derived def. That is genuine chain-level
proof effort — the SAME machinery sub-step 3's fragment widening needs — NOT an additive
hypothesis-factored clone. **NEXT LEG (call it 5c / sub-step-3 groundwork):**
1. **The `_d` chain.** Re-prove the W3d2 chain plumbing under `StoreValidRulesD` + a Direct-arm def:
   `reachedByW3d2_shadow_d` (the shadow admits Direct-arm derived keys — the reconcile write pass
   materialises the stored BARE Direct-arm seed edges via leg-2's `reachedByW3a_*_d`, then the W3d
   diffing pass `reconcileKeyD_retracts_excluded` retracts the excluded seeds; correspondence lives at
   the W3d2 DRAINED state per leg-5a's KILL), `reachedByW3d2C_settled_d` (the settledness invariant),
   and `reachedByW3c_master_d` (the canonical-row master). These consume the enum half + read bridges
   THIS slice landed (`w3d2_leg_context_d` / `w3dJobCoverage_enumJob2D` / `checkFnR_eq_sem_settled_d`).
   Then the state-level `_d` clones (`graph_correct_w3d2_d`, `w3c_row_char_d`) fall out.
2. **Then sub-step 3:** widen `W4Fragment.computedOnly` → `ComputedOrDirect ∧ DirectArmsBare`; re-prove
   `w4_within_scope` (`FullScope.lean:165-174`; `directsOnly_of_computedOnly` needs a `directsOnly (excl
   …) = false` variant); add witness `W4WitnessDirect` (`approver := excl (direct [user]) (computed
   banned)` + a store granting `user:alice`) to `Audit.lean`; conformance: move a Direct-arm corpus INTO
   `GRAPH_FRAGMENT` (`corpus.py`) + a state pin (conf phases required). Keep derived-TTU-userset shapes
   OUT of the graph leg.

### TTU/userset half — NOT STARTED (deeper; after Direct arm)
`PDerivedTTU` (TTU arm, store-state dependent, +1 stratum) and `PDerivedUserset`
(cross-object `upos`/`_leaf_concretes` lift — the X4 shape fixed Python-side 2026-07-13,
NEVER modeled in Lean). Hardest sub-lemma: completeness for the userset/TTU-arm read (analog
of `checkFn_eq_semStep`/`evalE_computedOrDirect` for a tree with a `ttu`/userset leaf,
including from-chain userset + cross-object-membership lift). Expect the userset half to
dominate. `computedRefs`/`ComputedOrDirect` `.ttu ↦ False` must be lifted; `evalE`
congruence must account for the TTU parent tuples (store-dependent) and the residue lift.

---

## Target #2 — Strata widening (>2 derived strata)

Goal: lift the `twoStrata`/`hLU2` cap (scheduler `runCascade2`, rounds=2) to N strata.
Attack-confirmed: Python has NO cap and is correct at ≥3 strata; the Lean round-2 reject
FIRES at 3 strata (`CascadeStrata.lean:419-429` attack schema `a:=b∨y, b:=c∨x, c:=x∖y`).
So `twoStrata` is proof-scope only, not a Python invariant. Recon verdict: a **partial
scheduler re-architecture then a clean-ish induction**; ~8–12 lemmas have intrinsically
two-round proof content (438 mechanical `runCascade2`/`jobs1 jobs2` occurrences follow the
fold once the core changes); Python known-correct at N ⇒ no algorithmic discovery risk.

Key files (all `GraphIndex/`): `CascadeStrata.lean` (scheduler + T5),
`CascadeStrataSettle/Resettle/Enum/Assemble.lean`, `CascadeStrataInv/Edge.lean`,
`Exec.lean:58` (driver wires `runCascade2`+`enumJobs2R1/R2`).

### Design / resume
- **`runCascade2`** (`CascadeStrata.lean:361-369`) bakes in "2" four ways: fixed 2-deep
  `reconcileJobsLR` nesting, two job-list params, a two-step frontier cursor chain, one
  post-round-2 leftover/reject check. Generalize to `runCascadeN S T σ (jobss : List (List
  W3cJob))` as a `foldl` over `(state, cursor)` threading the cursor computed on each
  round's PRE-apply state (preserve the advance-cursor-then-apply order EXACTLY or the
  leftover check moves). `enumJobs2R1/R2` (`CascadeStrataAssemble.lean:309-317`) → an
  indexed `enumJobs2At` per round.
- **`hLU2`** (`CascadeStrata.lean:740-743`): every computed operand of a derived def is
  untainted OR a derived key whose own computed operands are ALL untainted (chain stops
  after 1 hop). Generalize to `hLUN` — every derived-dependency chain length ≤ N, most
  cleanly via `stratify` producing ≤ N strata (T0b topological order) rather than an
  N-deep quantifier nest.
- **REUSES cleanly (stratum-agnostic):** the conditional-coverage design
  (`W3dJobOpsSettled` + `covg_of_opsSettled`, `CascadeStrataSettle.lean:1461-1495` — the
  kill-#6 "coverage must stay conditional" absorption), per-stratum read-inertness
  (`check_reconcileStarsKeyDR_other`, "whatever its stratum"), `settledComplete_jobsLR_targeted`.
- **HARD-CODED to 2 (need real re-proof, ~8-12):** `runCascade2` (def), `runCascade2_no_abort`
  (whole two-level case split `:762-889`), `cascade2_drains`, `round2_key_reads_derived`
  (`CascadeStrataSettle.lean:883-891`, one-hop), `settledComplete_cascade2_targeted`
  (binary Case A/B `CascadeStrataResettle.lean:855-869`), `writeLeg_sem_stable2`,
  `reachedByW3d2C_settled`, and the assembly quartet `enumJobs2R1`/`enumJobs2R2`/
  `ReachedByW3d2E`/`reachedByW3d2E_toC` + T2a re-assembly (`reachedByW3d2E_inv`,
  `graph_reached_inv` edge legs).
- **Proof strategy:** two nested inductions — outer on the `ReachedBy` chain (unchanged),
  inner on the round index (fold prefix). Prefer round-index induction over well-founded
  recursion on the DAG (matches the `foldl`/cursor definitionally). **Hardest lemma:** the
  N-round stratum fence / no-abort induction — generalize one-hop `round2_key_reads_derived`
  + `hLU2` to "a row above cursor cur_k came from a round-≤k emission ⇒ its reader is at
  stratum k+1", discharging `runCascadeN_no_abort`. Attack probes: within-round order at 3
  strata; a stratum-k→k−2 skip edge (kill-#6 at depth 3 — coverage must stay CONDITIONAL);
  future-residue re-read at depth 3; cursor monotonicity under out-of-order outbox ids;
  `hLUN` exactly-N-dead / N+1-live boundary.

---

## Target #3 — State/enum conformance bounds widening (mostly Python; land FIRST)

Goal (`FINAL_REVIEW.md §4(e)`): widen the exhaustive small-scope enumeration
`formal/conformance/test_conformance_enum.py` (currently k≤3, 2 names/type, 4 boolean
shapes, 527 stores; spec×oracle×set-engine pointwise over a shared grid, store-counts
asserted; ~90s, runs in the `conf-rest` phase). Four axes: (a) graph backend inside the
enumeration, (b) k=4, (c) userset/TTU shape, (d) state-level gate over enumerated stores.
Reusable driver `graphindex_answers` ALREADY EXISTS (`formal/conformance/backends.py:94-105`,
mirrors `tests/test_matrix.py::GraphBackend`; I5 leaf-routing + cascade).

### Recommended order (each an independent green increment)
1. **(c) userset/TTU shape** — ✅ **DONE (2026-07-18b, commit pending push at write time).**
   `_POOL` +`group`/`folder`; `_SHAPES` +`wildcard_group_member` (10-tuple space, 176
   stores — the existing acyclic `viewer:[group#member]`+`user:*` shape) +`ttu`
   (`viewer: viewer from parent`, 8-tuple space, 93 stores), asserted counts empirical.
   **Attack-first finding:** the brief's `group_userset` (self-referential
   `member:[user,group#member]`) is admission-INVALID for the set engine on 132/299 stores
   (cycle guard `engine.py:770`) — an admission-domain difference, not a check divergence;
   NOT used (docstring records it). Spec==oracle==set-engine on every enumerated store; no
   graph leg (that's (a)). Gate green incl. conf phases (290 conf, +2 params).
2. **(a) graph-in-enum, answer level** — ✅ **DONE (2026-07-18c).** All six enum shapes are
   in `GRAPH_FRAGMENT`, so ALL get the graph leg (none skipped; `run_graph = name in
   GRAPH_FRAGMENT`). Added `_graph_query_filter` (mirrors `test_conformance_graph.
   _graph_queries_for`: concrete objects, star subjects bare) + a per-store
   `graphindex_answers` == spec (== oracle == set engine) assert. **Attack-first: graph ==
   sem on EVERY in-fragment enumerated store (796 × graph grid), NO `ValueError`, NO
   divergence** — no P6/stale-fanout-class event this run. Enum file ~5 min standalone
   (conf-rest); no shapes/queries dropped. No new test params (rides inside the 6 enum
   tests) ⇒ conf still 290, 0 skip.
3. **(b) k=4** — ✅ **DONE (2026-07-18d).** Lever (1): `_SHAPES` now carries a PER-SHAPE K
   `(space, K, count)`. Four shapes reach K=4 (`boolean_exclusion`/`boolean_intersection`
   163, `boolean_star_exclusion` 57, `ttu` 163); the two dominators stay K=3
   (`two_stratum_cascade` 299 — 12-tuple space; `wildcard_group_member` 176 — 10-tuple).
   Measured: with only `two_stratum` capped the enum was ~7.6 min (conf-rest ~9.2, too
   tight against the graph-leg-inflated cap); capping BOTH large spaces → enum ~6.4 min,
   conf-rest ~7.9 min (≥2 min margin). Caps documented in the docstring (no silent caps);
   counts asserted empirically. **Attack-first: graph == sem on every in-fragment store at
   K=4, no `ValueError`, no divergence** (the four K=4 shapes + `wildcard` at K=4 during the
   measurement run were all clean). Total 1021 stores (naive all-six K=4 = 1726 would blow
   the cap). No verify.sh phase-structure change needed.
4. **(d) state gate over enumerated stores** — ✅ **DONE (2026-07-18e) — TARGET #3 COMPLETE.**
   New file `test_conformance_enum_state.py`: for a deterministic stride-4 SAMPLE (257 of
   1021 stores, ~25%, spread across every store size; per-shape sample sizes asserted) it
   compares the Lean graph model's canonical final state (zcli `"graph-state"`) vs the real
   Python graph index's extracted `EdgeV4`/`ResidueV1` state under `extractor.py`'s P1–P6
   projections UNCHANGED. All six shapes covered (none excluded — all in `GRAPH_FRAGMENT`,
   zero Lean admission/drain errors). **Attack-first: state match on every sampled store
   under P1–P6, ZERO mismatches** (this is the exact run class that originally found the P6
   leaf-family + 2026-07-17 stale-fanout divergences — none this run). ~180 ms/store; +47s
   → conf-rest 8:34 (within cap). +6 params → conf 296, 0 skip. The other ~75% of stores
   stay answer-pinned by increment (a).

**Findings, not failures (house rule 2).** Exhaustively driving the real graph index over
all sub-stores exercises write-order/partial-store interleavings never before driven —
the class that found the P6 leaf-family and 2026-07-17 stale-fanout divergences. A store
where graph `check` ≠ `sem` on an in-fragment shape is a genuine adjudication event —
record it, never edit oracle/golden.

---

## Target #4 — Remove legs in Lean (bounded — Route 1 confluence)

Goal (`FINAL_REVIEW.md §4 item 2`, "biggest lift, highest ceiling"): the Lean chain
`ReachedBy = ReachedByW3d2E` (`CascadeStrataAssemble.lean:325-333`) is ADD-ONLY
(`empty`/`write`/`cascade`); model chain-level REMOVE. Per-key retraction ALREADY exists
(`ReconcileDiff.lean` `reconcileStarsKeyD`; T4 `pathCount_removeEdge` `Closure.lean:473`;
`removeEdgePair` `ReconcileDiff.lean:52`; `structInv_removeEdgePair` `CascadeInv.lean:48`;
`reconcileStarsKeyD_edge_char` `:922-942`). Python remove paths already pinned empirically
(`test_conformance_remove.py`). OPEN = the Lean CHAIN-level legs only.

### RECON + ATTACK-FIRST PROBE — DONE (2026-07-18f). Verdict: **Route 1 GO**, with a KILL.
Read-only recon + the five design probes ran against the real Python backends / model.

**★ KILL (house rule 2 — the design's step 2 was a FALSE statement).** The original
step 2 ("fold `removeEdgePair`" = filter-ALL-copies) is UNSOUND in-fragment. `#eval`
refutation (untainted `viewer = editor or manager`, alice granted both ⇒ `alice → viewer:doc:1`
has `direct_edge_count = 2`): removing `(alice,editor)` decrements rc 2→1, the edge SURVIVES,
`check` stays True (via manager) == `sem` == fresh rebuild of `{(alice,manager,doc:1)}`. A
filter-all `removeEdgePair` would drop the edge → `check=False` → divergence. Reachable
inside `W4Fragment`/`twoStrata` (plain untainted union; also boolean-operand leaves at rc≥2).
The faithful op is **`List.erase (a,b)` — decrement ONE occurrence** (mirror of Python
`_add_direct_edge_unsafe(..., -1)`, `core.py:686-704`). `removeEdgePair` stays valid ONLY
where I5 guarantees rc≡1 (the diffing pass `reconcileStarsKeyD`), NEVER the chain-level
untainted fold.

**★ NO `GraphState` ripple (the pivotal positive finding).** `GraphState.edges :
List (NodeKey × NodeKey)` is ALREADY a multiset — `addEdge = (a,b) :: σ.edges` prepends
unconditionally (`State.lean:742`), `admitEdge` only checks `a≠b ∧ ¬reach b a` (`Write.lean:69`),
so a parallel copy of an acyclic rewrite edge is always admitted and the list multiplicity
== Python `direct_edge_count`. Reads (`reachB`/`NReaches`) test only membership, so
multiplicity is read-inert: **multiset for writes (ref-count), set for reads.** `List.erase`
(remove one) is therefore the exact faithful mirror with NO new field. Probes 2–6 all clean
(remove-readd symbolic-state identical, extractor P5 doesn't compare nodes so node-GC is
already modeled-away/read-safe; cross-stratum retraction `check==sem`; I6 residue diff
clean; non-present remove raises `ValueError` ⇒ `RemoveAdmits` faithful).

### Corrected leg breakdown — Route 1 (sequential, one Lean-editing leg each)
- **Leg R1 — erase-one primitive + invariants. ✅ DONE (2026-07-18g).** Landed additive
  (96 insertions, 0 deletions), verify.sh lean 415/415 sorries=0. `ReconcileDiff.lean`:
  `GraphState.removeEdgeOne σ a b := { σ with edges := σ.edges.erase (a,b) }` (cited to
  `core.py:704`/`686-704`; header comment records the KILL) + 6 `@[simp]` accessors +
  `removeEdgeOne_edges_subset` (`List.mem_of_mem_erase`) + `mem_removeEdgeOne_edges` /
  `mem_removeEdgeOne_edges_of_ne` (`List.mem_erase_of_ne`) + `count_removeEdgeOne_self`
  (`List.count_erase_self`, the `count-1` decrement seeding R3) / `count_removeEdgeOne_of_ne`
  + `edgesClosed_removeEdgeOne`. `CascadeInv.lean`: `structInv_removeEdgeOne` (line-for-line
  analog of `structInv_removeEdgePair` via the subset acyclicity). No kill this leg (erase-
  first-occurrence == decrement-one confirmed). **`removeLoggedRules`/`removeLoggedOne` +
  retraction deltas DEFERRED to R2** (delta wiring wants the constructor's context; a
  fold-without-deltas now would be an unfaithful half-primitive).
- **Leg R2 — standalone retraction substrate + consumer-surface map. ✅ DONE (2026-07-18h).**
  Landed additive (140 ins, 0 del, verify.sh lean 415/415). `Cascade.lean`:
  `GraphState.removeLoggedOne` (guarded erase-one + retraction `pushDelta` iff a copy was
  present — mirror `writeLoggedOne`; Python mirrors `apply.py:48-68` routes ADD+REMOVE through
  the SAME `ruleset.apply` fan-out, `core.py:686-704` `_remove_edge_locked` → `-1`,
  `core.py:278` `_emit("REMOVED")`), `GraphState.removeLoggedRules S t` (fold over the SAME
  `rewriteClosure S t`), `RemoveAdmits σ T t := t ∈ T` (mirror `source.py:104-112`) + schema/
  nodes/watermark `@[simp]` mirrors. `CascadeInv.lean`: `structInv_removeLoggedOne/_Rules`.
  **Delta-faithfulness finding:** `removeLoggedRules` mirrors the UNTAINTED routed retraction
  (dual of `writeLoggedRules`), NOT the processor's derived diffing removal (already modeled
  by `removeEdgePair`); emission is per-actual-erase (multiset shrink), exact dual of the
  write's per-admitted-add — write/remove paths mirror-symmetric, no asymmetry.
  **CRITICAL: the `remove` CONSTRUCTOR is NOT here** — adding it to `ReachedByW3d2E` breaks
  every downstream induction until each remove case is discharged (needs R4), so per the
  green gate the constructor moves to the FINAL leg R5. R2 is pure additive substrate.
- **Leg R3 — the occurrence-count invariant. ✅ UNTAINTED ARM DONE (2026-07-18i); derived arm
  KILLED as false.** New additive file `RemoveOccCount.lean` (+ 3-line aggregator import),
  verify.sh lean 415/415. Headline `reachedByW3d2E_untOccCount`: over every `ReachedByW3d2E`
  state, for an untainted `(a,b)` (`isDerived S (b.type,b.pred) = false`),
  `σ.edges.count (a,b) = untOccCount S T a b` where `untOccCount := ((T.flatMap (rewriteClosure
  S)).map edgeOfTuple).count (a,b)` — the ref-count made concrete (edges is a multiset ⇒
  `List.count` IS `direct_edge_count`). Supporting (all R4-reusable): `count_foldl_writeDirect`
  (admitted `writeDirect` fold = occurrence count, keyed off the write ctor's own `FoldAdmits`
  hyp — NO acyclicity argument needed, the admitEdge-passes question dissolved),
  `count_writeLoggedRules`, and the cascade-preserves-untainted-count stack
  (`count_reconcileKeyDR_of_ne` → `…StarsKeyDR…` → `…applyLoggedR…` → `…reconcileJobsLR…` →
  `count_runCascade2_of_ne`; every enumerated job is at a DERIVED R-node via
  `enumJobs2At_keyFacts`, so untainted `(a,b)` differs by `objNode_type/_pred`).
  - **★ KILL (house rule 2): the design's DERIVED arm `count ∈ {0,1}` is MODEL-FALSE.** `#eval`
    `viewer := a but not b` (write alice@a→cascade→write bob@a→cascade): `count(alice→viewer)`
    = 1 then **4**. The diffing pass `reconcileKeyD` (`ReconcileDiff.lean:212`) writes on
    `checkFn ∧ ¬covered` and does NOT probe `¬has_edge` like Python (`processor.py:359-367`),
    so it STACKS duplicate derived copies (the documented `ReconcileDiff` header decision,
    compensated by filter-all `removeEdgePair`). The faithful derived-side property is
    MEMBERSHIP (filter-all zeroes the pair), NOT a count bound — R4 must consume that, not
    `∈{0,1}`.
  - **Faithfulness nuance (reported, benign):** Lean `rewriteClosure` doesn't dedupe; Python
    `RuleSet.apply` does — on a reconvergent diamond the model over-counts (count 2 vs Python
    `direct_edge_count` 1). Read-invisible (reads test membership) + remove-consistent
    (`removeLoggedRules` folds the SAME closure) ⇒ doesn't affect the membership-level R4/R5
    target; extends the pre-existing `RulesWrite.lean:100` "duplicates harmless — reachability
    not counts" note to the remove path. The theorem characterizes the MODEL ref-count in
    terms of MODEL `rewriteClosure` occurrences (the design's exact phrasing), not a
    Python-count claim in reconvergent schemas.
- **Leg R4 — the confluence lemma. ✅ UNTAINTED ARM + `ReadEq` ASSEMBLY DONE (part 1 2026-07-19a,
  part 2 2026-07-19b); the DERIVED-membership + residue arms are chain-bound ⇒ R5.** New additive
  file `RemoveConfluence.lean` (verify.sh lean 415/415 sorries=0, additive ⇒ conf unchanged 296).
  Attack-first CONFIRMED the full confluence at answer level (`check(drain(remove)) = sem S (T.erase
  t)`, zero mismatch over rc≥2-survival + derived-exclusion probes).
  - **UNTAINTED side ✅ (part 1)** fed by R3's `untOccCount`: `count_removeLoggedRules` (retraction
    count-shrink, dual of R3's write growth, unconditional Nat sub) + `untOccCount_erase`
    (`t∈T ⇒ untOccCount S T = untOccCount S (T.erase t) + t-occ`, via `List.perm_cons_erase`) ⇒
    `drain_removeLoggedRules_untOccCount` (drained untainted multiplicity = `untOccCount S (T.erase
    t)` = R3 on a fresh rebuild) + `mem_drain_removeLoggedRules_untainted` (`count>0 ↔ mem`). The
    two-round drain is untainted-count-inert (R3's `count_runCascade2_of_ne`).
  - **`ReadEq` ASSEMBLY ✅ (part 2, deliverable iii)** — the membership-level read-agreement
    relation + full read-congruence, the transport vehicle R5 needs. `structure ReadEq` (schema eq +
    nodes eq + residue eq + edge-SET membership eq `∀ e, e∈σ'.edges ↔ e∈σ.edges`) + `refl`/`symm`/
    `trans` + `EvalEq.toReadEq` (LIST-eq ⇒ SET-eq). Congruence suite: `any_congr_of_mem` (`List.any`
    is order/multiplicity-blind — the base fact) → `reachB_congr_of_mem` (fuel induction; `reachB`
    reads edges ONLY via `.any` ⇒ edge-SET congruent) → `reach_readEq`/`reachB_readEq` →
    `probeNonDerived_readEq` / `probeDerived_readEq` → **`check_readEq`** (the headline; R5 transports
    `check(post-remove)=sem` through a `ReadEq` to a rebuild). Confirmed why `ReadEq` not `EvalEq`:
    the add-chain vs remove+drain fold orders give equal edge SETS but UNEQUAL lists (stacked derived
    dups + untainted-count order artifact), so `EvalEq`'s LIST equality is FALSE — `ReadEq` is
    satisfiable AND congruent for the whole read surface. Also landed the UNTAINTED half of the
    cross-state `edgeMem` clause: `untEdgeMem_drain_removeLoggedRules_rebuild` (drained-remove vs ANY
    rebuild `σr` over `T.erase t` agree on every untainted edge's membership — both `↔ 0 <
    untOccCount S (T.erase t)`, off R3 for `σr` + the untainted arm).
  - **★ FINDING (attack-first, negative — house rule 2): the DERIVED-membership + residue arms are
    NOT additively separable from the constructor.** The design's (i)/(ii) — derived-pair presence +
    residue = `sem S (T.erase t)` at the drained-remove state — are CHAIN-BOUND. Traced every route:
    `graph_correct_w3d2` (`ReachedByW3d2C` hyp), `reachedByW3d2C_settled` (`ReachedByW3d2C`),
    `settledComplete_cascade2_targeted` (**needs `ReachedByW3d2 σ S T`** for the two-round drain), and
    `settledComplete_jobsLR_targeted` (shadow-based but SINGLE-round only + wants operand keys already
    settled). No add-only rebuild-existence TERM exists (only the `ReachedByW3d2E` inductive + the
    `graphRun`/`graphRun_reached` driver), so no witness can be supplied additively for the
    drained-remove state. These arms close in R5: the `remove` constructor makes the drained state a
    `ReachedByW3d2E`, at which the EXISTING `graph_correct_w3d2E` gives `check=sem` for ALL queries
    (untainted AND derived) in one shot — the derived/residue equality is then free, not a separate
    additive lemma. So part 2 lands the reusable `ReadEq`+congruence (transport vehicle) + the
    untainted arm; the derived/residue `edgeMem`/`residue` clauses are R5's, discharged against the
    constructor — documented, not faked (a green infrastructure landing over a fragile forced close).
  - **Audit:** kept `ReadEq`+congruence OUT of `Audit.lean` (infrastructure, matching part 1's
    untainted arm and the peer `check_evalEq` congruence — neither audited); count stays 415/415.
- **Leg R5a — rebuild-existence (build-FROM-store admitted witness). ✅ DONE (2026-07-19d).**
  Landed additive in `RemoveConfluence.lean` (verify.sh lean 415/415 sorries=0, audit
  standard-axioms-only; additive ⇒ conf unchanged 296). The build-FROM-store admitted term both
  R5b routes need, as the **STORE-restriction dual of `exists_admitted_restrict`** (which restricts
  the SCHEMA). Three lemmas:
  - `exists_admitted_ofAcyclicTarget` (the core): given a FIXED acyclic target `Ef` containing
    every materialised closure edge of a store `T'`, folds `∃ σ0', ReachedByRulesAdmitted σ0' S T'
    ∧ edges ⊆ Ef` by induction on `T'` — each `writeDirect` fold admits via `foldAdmits_of_acyclic`
    (`RestrictBase.lean:392`), `σp.edges ⊆ Ef` recovered per-step from `reachedByRules_edge_sound`.
  - `exists_admitted_ofSubset` (route-agnostic): `ReachedByRulesAdmitted σ0 S T → T' ⊆ T →
    ∃ σ0', ReachedByRulesAdmitted σ0' S T' ∧ edges ⊆ σ0.edges`. Target `Ef := σ0.edges`, acyclic by
    `Inv.acyclic`, complete by `reachedByRulesAdmitted_edge_complete`.
  - `exists_admitted_erase` (the R5b tool): `ReachedByRulesAdmitted σ0 S T → ∀ t, ∃ σ0',
    ReachedByRulesAdmitted σ0' S (T.erase t) ∧ edges ⊆ σ0.edges` (via `List.erase_subset`). This is
    exactly what route (a)'s `reachedByW3d2_shadow` remove case consumes (IH hands the admitted
    chain over `T`; erase yields the rebuild over `T.erase t`). **Route (b) note:** the E-chain
    drained rebuild `∃ σ, ReachedByW3d2E σ S (T.erase t) ∧ Drained` is NOT provided (no add-only
    lift exists as a one-liner) — but route (a) is the recommendation and consumes only the
    admitted term, so R5b is unblocked as-is; its untainted-core shadow reduces to this term.
  - **The new ingredient (closure-acyclicity) is INHERITED, not proved from scratch.** Acyclicity
    of the admission target comes from the larger admitted store's `Inv.acyclic` — a sub-store's
    materialised graph is a subgraph of an acyclic one. **★ Attack-first SCOPING KILL (house rule
    2):** rebuild-existence over an ARBITRARY store is FALSE even under `RewriteRanked` — the
    userset 2-cycle store `{⟨group:g1#member, member, group:g2⟩, ⟨group:g2#member, member,
    group:g1⟩}` (no rewrite rules, so `RewriteRanked` vacuous) materialises
    `objNode(g1,member)⇄objNode(g2,member)`, which `admitEdge` (`a≠b ∧ ¬reach b a`) rejects on the
    2nd write — no `ReachedByRulesAdmitted` chain exists (Python rolls the cyclic write back
    identically). So from-scratch admissibility is NOT free; it is free only over a SUB-store of an
    admitted store — the only shape R5b needs. This SHAPES R5b: derive the erased store's
    admissibility FROM the pre-remove store's (as `exists_admitted_erase` does), never assert it.
  - **What R5b now has:** `exists_admitted_erase h0 t` (the admitted rebuild over `T.erase t` +
    edge ⊆) for `reachedByW3d2_shadow`'s remove case; the R4 `ReadEq`/`check_readEq` transport +
    untainted arm; the Group-A structural substrate (`residueHygienic_/residueDeclared_/
    structInv_removeLoggedRules` + `mem_removeLoggedRules_edges`). Remaining R5b work: add the
    `remove` constructor to `ReachedByW3d2`/`C`/`E` (route a — mirror `write`), build the
    settledness duals + `reachedByW3d2_shadow`/`reachedByW3d2C_settled` remove cases, `toC` trivial.
- **Leg R5b — RE-SEQUENCED into three additive sub-legs (2026-07-19e RECON+WALL).** The 2026-07-19d
  "unblocked as-is" was optimistic: a full read-only trace (tree left GREEN, no edits) found TWO
  obstructions the recon missed — a design correction + a module-DAG inversion. **R5b is NOT a
  one-session landing; sequence it R5b-i → R5b-ii → R5b-iii.**
  - **★ DESIGN CORRECTION — the `remove` constructor MUST carry `hdrain : cascadeKeys S σ = []`
    (drained prior).** `cascadeKeys` is NON-MONOTONE under a retraction (`affectedObjects` filters by
    reach-cone, which SHRINKS when `removeLoggedRules` shrinks the edge multiset), so a remove from an
    UNDRAINED state can un-dirty a STALE key without re-settling it ⇒ `reachedByW3d2C_settled`'s invariant
    is violated. The write case dodges this via monotonicity (`cascadeKeys_writeLeg_mono`), which has NO
    retraction dual. With `hdrain`, the IH gives all-keys-settled at the prior state (dirty disjuncts
    vacuous) and the remove case mirrors the write case's unmapped subcase exactly. FAITHFUL — Python
    drains between every applied log row (`advance_index`/`catch_up`), so remove-from-undrained never
    occurs; `hdrain` is a restriction strictly inside Python behaviour. So route (a)'s constructor is
    `(σ, T) → (σ.removeLoggedRules S t, T.erase t)` with `RemoveAdmits σ T t` AND `hdrain : cascadeKeys S σ = []`.
  - **★ WALL — MODULE-DAG INVERSION.** Import order bottom→top: `CascadeStrata` (`ReachedByW3d2`) →
    `…Settle` (`ReachedByW3d2C`, `reachedByW3d2_shadow`) → `…Resettle` (`reachedByW3d2C_settled`) →
    `…Assemble` (`ReachedByW3d2E`) → `CascadeStrataInv` → `RemoveOccCount` (R3) → `RemoveConfluence`
    (R4 + R5a). The constructor forces remove-case discharges INSIDE the LOW inductives, but their
    content is HIGH. The mechanical relocations (count arithmetic → RemoveOccCount; residue/edge substrate
    → CascadeInv; `exists_admitted_erase` → below RestrictBase) are easy. The HARD wall is
    `reachedByW3d2_shadow`'s remove case (in the low `…Settle`): building `UntaintedShadow S σ_rem σ0'`
    (edge-SET agreement between the multiset-erased `σp` and R5a's fresh rebuild `σ0'`) needs a
    COUNT/multiplicity characterisation of `σp`'s untainted edges (= R3's `untOccCount` over `T`) — which
    is TOP-level and tied to `ReachedByW3d2E`, unavailable and un-importable at the shadow's low level.
    Breaking it requires **re-deriving R3's untainted-count invariant at the `ReachedByW3d2` level in
    `CascadeStrata`/`…Settle`** (relocate the RemoveOccCount count stack DOWN + re-state
    `untOccCount`/`reachedByW3d2_untOccCount` there). Genuine new low content, high-risk relocation.
  - **The settledness-dual stack (~10 theorems)** for `reachedByW3d2C_settled`'s remove case are duals of
    the write-leg stack (`CascadeStable.lean:432/471/980/1020`, `CascadeStrataSettle.lean:1064/1106/1149/1193`),
    buildable below Resettle once the shadow works: `untaintedShadow_removeLeg`, `removeLeg_graphRec_/checkFn_stable`,
    `removeLeg_derived_inedges_eq` (retraction erases ONLY untainted edges — `noRuleOutputs_of_derived`, no
    closure member targets a DerNode), `removeLeg_sem_stable/_sh/_stable2`, `settledKey_/completeKey_removeLeg_sem`
    (residue-inert via the landed `removeLoggedRules_residue`). `cascadeKeys_writeLeg_mono` has NO dual
    (that is what `hdrain` sidesteps).
  - **R5b sub-legs (each additive, green before the next):** **R5b-i** relocate the count/residue/edge/
    existence substrate DOWN to respect the future DAG (pure move, no proof change). **R5b-ii** the low
    untainted-count invariant `reachedByW3d2_untOccCount` + `untaintedShadow_removeLeg` (the crux; new
    content). **R5b-iii** the constructor (route a, WITH `hdrain`) + 18 mechanical discharges + shadow
    (off R5b-ii) + settled (off the dual stack) + `toC`/`toW3d2` trivial; audit the `graph_correct`
    remove path.
  - **★ No kill** (the confluence stays TRUE per R4). The findings SHAPE R5b; the target is not refuted.

- **Leg R5b — RE-SCOPED (2026-07-19c): the constructor is MONOLITHIC and gated on the (now-landed
  R5a) rebuild-existence.** The design's "lands green in ONE commit armed with R4" is FALSE — traced
  end-to-end this session (tree left green; T2a Group-A structural discharges landed additively in
  `RemoveConfluence.lean`; constructor NOT added). Full trace in `history/PROOF_STATUS.md`
  2026-07-19c. The corrected picture:
  - **Monolithic, no partial landing.** `graph_correct_w3d2E` is ∀-quantified over `ReachedByW3d2E`
    and consumed by `FullScope.graph_correct` + `Exec.graphRun_check_eq_sem`, so adding the
    constructor FORCES its T2b remove case (`check = sem` post-remove) immediately.
  - **Both routes need REBUILD-EXISTENCE over `T.erase t`** — a term `∃ σ, ReachedByW3d2E σ S T' ∧
    Drained` (route b, for the `ReadEq` transport target) or `∃ σ0, ReachedByRulesAdmitted σ0 S T'`
    (route a, for `reachedByW3d2_shadow`'s remove case). ABSENT in the tree (every `∃ σ,
    ReachedByRules…` is shadow-FROM-chain, never build-FROM-store). This is what R4-part-2's "no
    add-only rebuild-existence TERM exists" was pointing at; it is load-bearing for BOTH routes.
  - **REACHABLE though:** `foldAdmits_of_acyclic` (`RestrictBase.lean:392`) discharges `FoldAdmits`
    from target-relation acyclicity; `exists_admitted_restrict` (`:434`) is the build-from-a-chain
    template. Building it FROM A STORE needs closure-acyclicity from `RewriteRanked`/`Stratifiable`.
  - **Leg R5a (do FIRST, additive):** prove rebuild-existence — `∃ σ0, ReachedByRulesAdmitted σ0 S T`
    (untainted) and/or `∃ σ, ReachedByW3d2E σ S T ∧ Drained S σ` (full) from a store, via
    `foldAdmits_of_acyclic` + closure-acyclicity. A self-contained additive sub-leg.
  - **Leg R5b (the constructor, armed with R5a).** RECOMMEND **route (a) — undrained `remove`**
    (mirror `write`: `(σ, t::T) → (σ.removeLoggedRules S t, T.erase t)`, NO bundled drain — the
    existing `cascade` constructor drains), added to ALL THREE inductives `ReachedByW3d2`/`C`/`E`.
    Then `removeLoggedRules σ t` IS a `ReachedByW3d2` (via `ReachedByW3d2.remove`), so
    `settledComplete_cascade2_targeted` applies verbatim and `toC`'s remove case is trivial
    (`ReachedByW3d2C.remove`) — the design's fix-(iii) obstruction DISSOLVES (it was an artefact of
    the BUNDLED/drained constructor, where σ_rem is not a C-cascade state). Discharge the STRUCTURAL
    Group-A cases with this session's substrate (`residueHygienic_/residueDeclared_/structInv_removeLoggedRules`
    + `mem_removeLoggedRules_edges`); build the settledness duals `removeLeg_sem_stable2` /
    `settledKey_removeLeg` / `cascadeKeys_removeLeg_mono` / `removeLeg_derived_inedges_eq` (semantic
    duals of the writeLeg stack `CascadeStrataSettle.lean:1064-1207`, `CascadeStable.lean:471/980/1020`);
    `reachedByW3d2_shadow`'s remove case off R5a; `reachedByW3d2C_settled`'s remove case (mirror its
    write case, `CascadeStrataResettle.lean:1210-1253`).
  - **T2a structural substrate LANDED this session (green, additive):** `removeLoggedOne_residue`,
    `removeLoggedRules_residue`, `mem_removeLoggedRules_edges`, `residueHygienic_removeLoggedRules`,
    `residueDeclared_removeLoggedRules` (`RemoveConfluence.lean`). These + R2's `structInv_removeLoggedRules`
    ARE the `reachedByW3d2E_{structInv,residueHygienic,residueDeclared,edgeHyg1}` remove-case bodies.

  Original R5 plan (superseded by the R5a/R5b split above), for reference — add the 4th `remove`
  constructor to `ReachedByW3d2E` and discharge the ripple surface mapped in R2:
  - **Group A (direct `induction h`, each MUST get a remove case):** `reachedByW3d2E_edgeHyg1`
    (`CascadeStrataEdge.lean:237`), `reachedByW3d2E_structInv` (`CascadeStrataInv.lean:122`),
    `_residueHygienic` (`:223`), `_residueDeclared` (`:323`) — all four conclusions
    (`EdgeHyg1`/`StructInv`/`ResidueHygienic`/`ResidueDeclared`) are MEMBERSHIP-READ ⇒
    EvalEq-invariant ⇒ remove case = R4 confluence → theorem@rebuild → EvalEq-transport. NOTE
    #3-5 actually delegate to the NON-E `reachedByW3d2_*` inductions (`CascadeStrataInv.lean:
    109/211/285`, `Assemble:164/75`) — those may need remove cases too (check whether the
    constructor is added to `ReachedByW3d2` as well, or the E-chain projects).
  - **Group B (ride automatically):** `graph_correct_w3d2E`, `reachedByW3d2E_edgeHygienic`,
    `reachedByW3d2E_inv`, `graph_correct`/`graph_reached_inv` (`FullScope.lean:183/241`),
    T3/T6 (`Equiv.lean`) — no own induction; ride once Group A closes.
  - **★ The one obstruction — `reachedByW3d2E_toC` (`CascadeStrataAssemble.lean:342`).** Its
    codomain `ReachedByW3d2C` is an OPERATIONAL stateful inductive (pins outbox/watermark/edge
    MULTIPLICITY), NOT membership-read ⇒ NOT EvalEq-invariant ⇒ R4 does NOT discharge its
    remove case. **Recommended fix (iii):** RETIRE `toC` from the remove path — its only 3
    callers (`graph_correct_w3d2E:494`, `edgeHyg1:281`, `edgeHygienic:347`) are all in the
    surface; restructure them to induct on `ReachedByW3d2E` directly (empty/write/cascade via
    the existing route; remove via R4→rebuild→EvalEq-invariance of the membership-read
    conclusion). Alternatives (i) cascade the constructor down `ReachedByW3d2C`/`ReachedByW3d2`
    (more inductive surgery) or (ii) an `EvalEq`-transport for `ReachedByW3d2C` (likely
    intractable) are the fallbacks.
  - **Group C (driver, optional):** `graphRunAux`/`graphRun_reached` (`Exec.lean:65-106`)
    CONSTRUCT the constructors; extend the input type + fold with a `.remove` branch ONLY if
    the zcli graph driver is to exercise removes (additive; not required for the theorems).

- Route 2 (direct preservation — `remove` case in each chain-inducting proof, touches
  `CascadeStrataEdge/Inv/Assemble.lean`) is the fallback if R3 proves intractable; strictly
  MORE work (same erase-one op + same multiplicity reasoning, done locally everywhere).

**Lift:** as predicted, ~one W3d sub-stage — but R3 (occurrence-count invariant) is GENUINE
new content; R1/R2 clone-and-mirror; R4 the confluence; R5 the one non-additive assembly
(green in one commit, with the `toC` retire as its trickiest piece). **RESUME: Leg R5** — the
`remove` constructor + consumer-surface discharge (the ONE non-additive leg). R4 is now fully
scoped: part 1 (untainted arm) + part 2 (`ReadEq` relation + `check`/`reachB` congruence +
untainted `edgeMem`) LANDED; the derived-membership + residue arms were attack-pinned CHAIN-BOUND
(no additive rebuild witness) and MOVE INTO R5, where the constructor lets `graph_correct_w3d2E`
discharge `check=sem` for all queries directly. R5 transports through `ReadEq` (`check_readEq`) for
the Group-A membership-read invariants and retires `reachedByW3d2E_toC` from the remove path
(fix iii). `RemoveConfluence.lean` (2026-07-19a/b) is the template + the transport toolkit.
