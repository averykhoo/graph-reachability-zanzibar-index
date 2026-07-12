import ZanzibarProofs.SetEngine.Correct
import ZanzibarProofs.GraphIndex.DirectCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.GraphIndex.UsStarClosure
import ZanzibarProofs.GraphIndex.RulesComplete
import ZanzibarProofs.GraphIndex.ReconcileComplete
import ZanzibarProofs.GraphIndex.ReconcileUposComplete
import ZanzibarProofs.GraphIndex.ReconcileStarsComplete
import ZanzibarProofs.GraphIndex.CascadeSettle
import ZanzibarProofs.GraphIndex.CascadeStrataResettle

/-!
# T3 / T6 — the historical per-stage corollary ladder

`SEMANTICS.md` §8 (T3, T6). T3 is the whole point of the shared-spec architecture:
prove each backend against `sem`, get backend-equivalence by transitivity in Lean.
T6 are the review's headline security properties, one-line consequences of T1/T2b.

**What this file is now.** The original (pre-2026-07-10) statements quantified
over a deleted abstract `ReachedBy` closure and were **false as stated** (junk
states satisfied every hypothesis while only the set engine computed `sem`). They
were restated over the operational closure at its then-current scope and re-proved
as REAL, axiom-clean theorems; the scope then widened stage by stage with the
write model (bridges → rule routing → reconcile → the scheduler chains). This file
hosts that per-stage corollary LADDER (`*_direct` … `*_w3d2`), each rung kept
exactly as proved at its stage. The FINAL full-scope statements — the unsuffixed
`backend_equivalence` / `exclusion_effective` / `no_ghost_grant` (with
`graph_correct` / `graph_reached_inv`) over `ReachedBy := ReachedByW3d2E` and the
`GraphAdmission`/`W4Fragment` provenance split — live in `FullScope.lean`. From
`*_w3a` onward T6a's exclusion case is non-vacuous (a derived `but not` genuinely
excludes); on the earlier pure-direct rungs its content is deny-propagation.

**Why the ladder is deliberately KEPT (not dead code), despite being superseded by
`FullScope.lean`.** Every rung here (`*_direct` … `*_w3d2`) is individually axiom-
audited in `Audit.lean` (its own `#print axioms` command), so the rungs are a
load-bearing part of the standing-axioms gate, not orphaned history: they document
that each staged scope was reached with the standard axioms only. Removing a rung
would drop its audit report and change the gate's expected report count, so the
whole ladder is retained by design. The verbatim-repeated hypothesis blocks are the
price of that per-stage record; the single source of truth for the CURRENT claim is
the unsuffixed `FullScope.lean` theorems.
-/

namespace Zanzibar

/-- **Historical milestone (W1a) — NOT subsumed by `FullScope.lean`: it sits on a
    different chain** (`ReachedByAdmitted`, plain admitted write folds) from the
    final closure `ReachedBy = ReachedByW3d2E`; kept as the W1 record.

    **T3 (equivalence), star-free pure-direct fragment scope.** On states
    operationally reached by writing exactly `T`, the two backends agree — by
    transitivity through `sem` (T1 ∘ T2b-fragment). (Renamed `*_direct` at W4:
    the unsuffixed names now live at full scope in `FullScope.lean`.) -/
theorem backend_equivalence_direct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid,
      graph_correct_direct S T σ q hWF hPD hSV hSF hqs hqo hReach]

/-!
## T6 — security corollaries

Stated as named theorems because they are the review's headline properties. Each
is a one-line consequence of T1/T2b + a spec lemma, at the fragment's scope.
-/

/-- **Historical milestone (W1a; different chain — see the
    `backend_equivalence_direct` tag).**

    **T6a (exclusion-effectiveness / deny-propagation), fragment scope.** Whenever
    the spec denies, both backends deny. At full scope this specializes to the
    exclusion property (`but not banned` always removes a banned subject); the
    pure-direct fragment has no exclusions, so here the content is the general
    soundness direction. -/
theorem exclusion_effective_direct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByAdmitted σ S T) (hValid : AllValid T)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid]; exact hDeny
  · rw [graph_correct_direct S T σ q hWF hPD hSV hSF hqs hqo hReach]; exact hDeny

/-- **Historical milestone (W1a; different chain — see the
    `backend_equivalence_direct` tag).**

    **T6b (no-ghost-grant), fragment scope.** If removing a tuple makes the spec
    deny, the graph backend denies after the removal — no stale grant survives the
    loss of its last support. (`T'` is the post-removal store; `σ'` its
    operationally reached state.) -/
theorem no_ghost_grant_direct (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T') (hSF : StarFreeStore T')
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByAdmitted σ' S T')
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_direct S T' σ' q hWF hPD hSV hSF hqs hqo hReach]; exact hDeny

/-! ## T3 / T6 widened to the W1b (object-wildcard) fragment

Per the shared-spec architecture these are one-line corollaries that widen with the
write model: `graph_correct_objStar` (T2b on the object-wildcard fragment) composed
with T1 (`setEngine_correct`, general) gives backend equivalence and the security
corollaries on stores with object wildcards `[T:*]` — a strictly wider scope than the
star-free `*_objStar`-free versions above. -/

/-- **Historical milestone (W1b) — superseded by the unsuffixed theorems in
    `FullScope.lean` EXCEPT for its store scope**: `w_all` object-wildcard tuples
    lie outside the W4 chain's `bareStar` carry (honest gap, ROADMAP "W4 — honest
    gaps"), and it sits on its own chain (`WildReachedAdmitted`).

    **T3 (equivalence), W1b (object-wildcard) scope.** Both backends agree on stores
    with object wildcards, by transitivity through `sem` (T1 ∘ `graph_correct_objStar`). -/
theorem backend_equivalence_objStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T)
    (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : WildReachedAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid,
      graph_correct_objStar S T σ q hWF hPD hSV hOS hOV hqs hqo hReach]

/-- **Historical milestone (W1b; retains object-wildcard store scope — see the
    `backend_equivalence_objStar` tag).**

    **T6a (deny-propagation), W1b scope.** Whenever the spec denies, both backends
    deny — now including object-wildcard stores. -/
theorem exclusion_effective_objStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T)
    (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : WildReachedAdmitted σ S T) (hValid : AllValid T)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid]; exact hDeny
  · rw [graph_correct_objStar S T σ q hWF hPD hSV hOS hOV hqs hqo hReach]; exact hDeny

/-- **Historical milestone (W1b; retains object-wildcard store scope — see the
    `backend_equivalence_objStar` tag).**

    **T6b (no-ghost-grant), W1b scope.** If removing a tuple makes the spec deny, the
    graph backend denies after the removal — no stale wildcard grant survives the loss
    of its last support. -/
theorem no_ghost_grant_objStar (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T')
    (hOS : ObjStarStore T') (hOV : ObjStarValid S T')
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : WildReachedAdmitted σ' S T')
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_objStar S T' σ' q hWF hPD hSV hOS hOV hqs hqo hReach]; exact hDeny

/-! ## W1c (userset-star) scope — the same corollaries via `graph_correct_usStar` -/

/-- **Historical milestone (W1c) — superseded by the unsuffixed theorems in
    `FullScope.lean` EXCEPT for its store scope**: userset-star tuples lie outside
    the W4 chain's `bareStar` carry (honest gap, ROADMAP "W4 — honest gaps"), and
    it sits on its own chain (`UsStarReachedAdmitted`).

    **T3 (equivalence), W1c (userset-star) scope.** Both backends agree on stores with
    userset-star subject grants (`[T:*#P]`), by transitivity through `sem`
    (T1 ∘ `graph_correct_usStar`). -/
theorem backend_equivalence_usStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReachedAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid,
      graph_correct_usStar S T σ q hWF hPD hSV hUS hqs hqo hReach]

/-- **Historical milestone (W1c; retains userset-star store scope — see the
    `backend_equivalence_usStar` tag).**

    **T6a (deny-propagation), W1c scope.** Whenever the spec denies, both backends deny
    — now including userset-star stores. -/
theorem exclusion_effective_usStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReachedAdmitted σ S T) (hValid : AllValid T)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid]; exact hDeny
  · rw [graph_correct_usStar S T σ q hWF hPD hSV hUS hqs hqo hReach]; exact hDeny

/-- **Historical milestone (W1c; retains userset-star store scope — see the
    `backend_equivalence_usStar` tag).**

    **T6b (no-ghost-grant), W1c scope.** If removing a tuple makes the spec deny, the
    graph backend denies after the removal — no stale userset-star grant survives the
    loss of its last support. -/
theorem no_ghost_grant_usStar (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T') (hUS : UsStarStore T')
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReachedAdmitted σ' S T')
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_usStar S T' σ' q hWF hPD hSV hUS hqs hqo hReach]; exact hDeny

/-! ## W2 (untainted rule-routing) scope — the same corollaries via `graph_correct_rules`

The first fragment with `computed`/`ttu`/`union` (not just direct grants). `sem`'s
stratifiability comes from `stratifiable_untainted` (no tainted keys), and the graph
equivalence from `graph_correct_rules`. -/

/-- **Historical milestone (W2) — superseded in role by the unsuffixed theorems in
    `FullScope.lean`** (untainted schemas sit inside the full scope:
    `w4Fragment_of_untainted` + `drained_of_untainted`), **but with REAL residual
    generality**: no `hMatch` (`RewriteMatchDeclared`), no `hWSbare`, and the
    plain-fold chain `ReachedByRulesAdmitted` — cf. `graph_correct_rulesBS`
    (`RulesBareStar.lean`, the star-relaxed W2 form) and the ROADMAP W4 scope
    inventory.

    **T3 (equivalence), W2 (rule-routing) scope.** Both backends agree on untainted
    schemas with `computed`/`ttu`/`union` definitions, by transitivity through `sem`
    (T1 ∘ `graph_correct_rules`). -/
theorem backend_equivalence_rules (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByRulesAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_untainted hUT) hValid,
      graph_correct_rules S T σ q hWF hUT hTT hNK hR hSV hSF hqs hqo hReach]

/-- **Historical milestone (W2; residual generality — see the
    `backend_equivalence_rules` tag).**

    **T6a (deny-propagation), W2 scope.** Whenever the spec denies, both backends deny —
    now including untainted rule-routed schemas. -/
theorem exclusion_effective_rules (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByRulesAdmitted σ S T) (hValid : AllValid T)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF (stratifiable_untainted hUT) hValid]; exact hDeny
  · rw [graph_correct_rules S T σ q hWF hUT hTT hNK hR hSV hSF hqs hqo hReach]; exact hDeny

/-- **Historical milestone (W2; residual generality — see the
    `backend_equivalence_rules` tag).**

    **T6b (no-ghost-grant), W2 scope.** If removing a tuple makes the spec deny, the graph
    backend denies after the removal — no stale computed/ttu/union grant survives the loss
    of its supporting tuple. -/
theorem no_ghost_grant_rules (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T') (hSF : StarFreeStore T')
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByRulesAdmitted σ' S T')
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_rules S T' σ' q hWF hUT hTT hNK hR hSV hSF hqs hqo hReach]; exact hDeny

/-! ## W3a (star-free bare-subject derived booleans) scope — via `graph_correct_w3a`

The first fragment with a DERIVED (`and`/`but not`) relation actually maintained by the delta
processor: one `RootBoolean` derived key per untainted operand cone. `sem`'s stratifiability is the
carried `Stratifiable S` (mixed schema); the graph equivalence is `graph_correct_w3a`. Scope:
bare-subject star-free queries (userset subjects on derived keys are W3b's `upos` residue). T6a here
carries the first REAL exclusion content — a derived `but not` actually excluding. -/

/-- **Historical milestone (W3a) — superseded by the unsuffixed theorems in
    `FullScope.lean`**, which lift the bare-subject query restriction, widen stores
    to bare-star (`BareStarStore`) and strata to two (`hLU2` ⊋ `hLU`), over the
    canonical operational closure; the one-shot batch closure `W3aComplete`
    survives only as this stage record.

    **T3 (equivalence), W3a scope.** Both backends agree on the star-free bare-subject derived
    boolean fragment, by transitivity through `sem` (T1 ∘ `graph_correct_w3a`). -/
theorem backend_equivalence_w3a (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3aComplete S T σ) (hValid : AllValid T)
    (hqbare : q.subject.predicate = BARE) (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct_w3a q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqbare hqs hqo]

/-- **Historical milestone (W3a; see the `backend_equivalence_w3a` tag).**

    **T6a (deny-propagation), W3a scope.** Whenever the spec denies, both backends deny — now
    including a derived `but not` that genuinely excludes (the first real exclusion content). -/
theorem exclusion_effective_w3a (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3aComplete S T σ) (hValid : AllValid T)
    (hqbare : q.subject.predicate = BARE) (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]; exact hDeny
  · rw [graph_correct_w3a q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqbare hqs hqo]
    exact hDeny

/-- **Historical milestone (W3a; see the `backend_equivalence_w3a` tag).**

    **T6b (no-ghost-grant), W3a scope.** If removing a tuple makes the spec deny, the graph backend
    denies after the removal — no stale derived-boolean grant survives the loss of its support. -/
theorem no_ghost_grant_w3a (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T') (hSF : StarFreeStore T')
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T' R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3aComplete S T' σ')
    (hqbare : q.subject.predicate = BARE) (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_w3a q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqbare hqs hqo]
  exact hDeny

/-! ## W3b (userset subjects on derived keys — the `upos` residue) scope — via `graph_correct_w3b`

The W3a bare-subject restriction is LIFTED: the graph's edge-free `upos` residue now answers userset
subjects on derived keys (blind-audit P4), so the corollaries hold for **every** star-free query.
The schema fragment is unchanged (one `RootBoolean` derived stratum over untainted operands). -/

/-- **Historical milestone (W3b) — superseded by the unsuffixed theorems in
    `FullScope.lean`**, which widen stores to bare-star (`BareStarStore`), admit
    star-BARE query subjects, and take two strata (`hLU2` ⊋ `hLU`), over the
    canonical operational closure; the batch closure `W3bComplete` survives only
    as this stage record.

    **T3 (equivalence), W3b scope.** Both backends agree on the star-free derived boolean fragment
    for bare AND userset subjects (T1 ∘ `graph_correct_w3b`). -/
theorem backend_equivalence_w3b (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T σ) (hValid : AllValid T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct_w3b q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqs hqo]

/-- **Historical milestone (W3b; see the `backend_equivalence_w3b` tag).**

    **T6a (deny-propagation), W3b scope.** Whenever the spec denies, both backends deny — now
    including a userset subject excluded by a derived `but not` (the P4 non-leak: a userset's
    `upos` grant never bleeds past a member's own exclusion, and vice versa). -/
theorem exclusion_effective_w3b (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T σ) (hValid : AllValid T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]; exact hDeny
  · rw [graph_correct_w3b q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqs hqo]
    exact hDeny

/-- **Historical milestone (W3b; see the `backend_equivalence_w3b` tag).**

    **T6b (no-ghost-grant), W3b scope.** If removing a tuple makes the spec deny, the graph backend
    denies after the removal — no stale `upos` entry or derived edge survives its support. -/
theorem no_ghost_grant_w3b (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T') (hSF : StarFreeStore T')
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T' R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T' σ')
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_w3b q hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU h hqs hqo]
  exact hDeny

/-! ## W3c (star-carrying stores — the `stars`/`neg` residue) scope — via `graph_correct_w3c`

The store may now hold bare `T:*` subject-wildcard grants (`BareStarStore` + `TtuStarFree`
replace `StarFreeStore`), and the query subject may be a bare-star (`user:*`) subject. The
graph answers covered subjects wholesale from the `stars` ∖ `neg` residue — the space rule —
so T6a's exclusion content now includes a concrete subject excluded FROM UNDER a wildcard
grant (`neg`), the headline W3c behaviour. `hWSbare` pins the decision-15 scope: only
bare-subject wildcard shapes are declared. -/

/-- **Historical milestone (W3c) — superseded by the unsuffixed theorems in
    `FullScope.lean`**: the same hypothesis surface but TWO strata (`hLU2` ⊋
    `hLU`), over the canonical operational closure; the batch closure
    `W3cComplete` survives only as this stage record.

    **T3 (equivalence), W3c scope.** Both backends agree on the derived boolean fragment
    over star-carrying stores, for bare, star-BARE, and userset subjects
    (T1 ∘ `graph_correct_w3c`). -/
theorem backend_equivalence_w3c (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : W3cComplete S T σ) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct_w3c q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
        hWSbare h hqs hqo]

/-- **Historical milestone (W3c; see the `backend_equivalence_w3c` tag).**

    **T6a (deny-propagation), W3c scope.** Whenever the spec denies, both backends deny —
    now including a concrete subject excluded from under a `T:*` wildcard grant (the
    `neg` residue: the space rule's exclusion actually excludes). -/
theorem exclusion_effective_w3c (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : W3cComplete S T σ) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]; exact hDeny
  · rw [graph_correct_w3c q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
      hWSbare h hqs hqo]
    exact hDeny

/-- **Historical milestone (W3c; see the `backend_equivalence_w3c` tag).**

    **T6b (no-ghost-grant), W3c scope.** If removing a tuple makes the spec deny, the
    graph backend denies after the removal — no stale `stars` coverage, `upos` entry, or
    derived edge survives its support. -/
theorem no_ghost_grant_w3c (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T')
    (hBS : BareStarStore T') (hTS : TtuStarFree S T')
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T' R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : W3cComplete S T' σ')
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_w3c q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
    hWSbare h hqs hqo]
  exact hDeny

/-! ## W3d (the interleaved scheduler chain) scope — via `graph_correct_w3d`

The graph state is no longer a one-shot batch build: it is any state of the
`ReachedByW3dC` closure — logged write transactions interleaved with `runCascade`
runs, in any order — read at a fully-drained point (`cascadeKeys = []`, which every
accepted cascade produces: `cascade_drains` + `cascadeKeys_nil_of_quiescent`). The
scheduler itself (outbox rows, delta→key fan-out, the drain loop, stale-edge
retraction between transactions) is now inside the verified perimeter. -/

/-- **Historical milestone (W3d-1) — superseded by the unsuffixed theorems in
    `FullScope.lean`**: single-stratum `hLU` (vs the final `hLU2`) and the
    hypothesis-carrying coverage chain `ReachedByW3dC` (vs the fully-operational
    `ReachedBy = ReachedByW3d2E`, whose coverage is derived from state).

    **T3 (equivalence), W3d scope.** Both backends agree at every fully-drained state
    of the interleaved scheduler chain (T1 ∘ `graph_correct_w3d`). -/
theorem backend_equivalence_w3d (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3dC σ S T) (hq : cascadeKeys S σ = []) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct_w3d q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
        hWSbare h hq hqs hqo]

/-- **Historical milestone (W3d-1; see the `backend_equivalence_w3d` tag).**

    **T6a (deny-propagation), W3d scope.** Whenever the spec denies, both backends deny
    — at every fully-drained scheduler state, including a subject whose grant was
    retracted by a LATER transaction's cascade (the stale-edge retraction is what
    keeps this true across transactions). -/
theorem exclusion_effective_w3d (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3dC σ S T) (hq : cascadeKeys S σ = []) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]; exact hDeny
  · rw [graph_correct_w3d q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
      hWSbare h hq hqs hqo]
    exact hDeny

/-- **Historical milestone (W3d-1; see the `backend_equivalence_w3d` tag).**

    **T6b (no-ghost-grant), W3d scope.** If the spec denies on the chain's own store,
    the graph denies at any fully-drained state — no stale derived edge, `stars`
    coverage, or `upos` entry survives a later transaction that removed its support. -/
theorem no_ghost_grant_w3d (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T')
    (hBS : BareStarStore T') (hTS : TtuStarFree S T')
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T' R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3dC σ' S T') (hq : cascadeKeys S σ' = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_w3d q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
    hWSbare h hq hqs hqo]
  exact hDeny

/-! ## W3d-2 (two strata) scope — via `graph_correct_w3d2`

Derived defs may now read other derived defs one stratum down (`hLU2`, strictly
wider than W3d-1's all-untainted-operands `hLU`): the scheduler runs TWO rounds per
cascade, round 1 re-settling stratum-1 keys and its emissions re-dirtying their
stratum-2 readers for round 2. -/

/-- **Historical milestone (W3d-2, coverage-chain form) — superseded by the
    unsuffixed theorems in `FullScope.lean`**, which discharge this statement's
    `ReachedByW3d2C` coverage hypotheses from state (`reachedByW3d2E_toC`); the C
    form remains the wider scaffolding statement for externally-audited states.

    **T3 (equivalence), W3d-2 scope.** Both backends agree at every fully-drained
    state of the two-stratum interleaved scheduler chain (T1 ∘ `graph_correct_w3d2`). -/
theorem backend_equivalence_w3d2 (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2C σ S T) (hq : cascadeKeys S σ = []) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct_w3d2 q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO
        hLU2 hWSbare h hq hqs hqo]

/-- **Historical milestone (W3d-2; see the `backend_equivalence_w3d2` tag).**

    **T6a (deny-propagation), W3d-2 scope.** Whenever the spec denies, both backends
    deny — including a stratum-2 grant whose stratum-1 support was retracted (the
    round-2 re-settle is what keeps this true). -/
theorem exclusion_effective_w3d2 (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2C σ S T) (hq : cascadeKeys S σ = []) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]
    exact hDeny
  · rw [graph_correct_w3d2 q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO
      hLU2 hWSbare h hq hqs hqo]
    exact hDeny

/-- **Historical milestone (W3d-2; see the `backend_equivalence_w3d2` tag).**

    **T6b (no-ghost-grant), W3d-2 scope.** If the spec denies on the chain's own
    store, the graph denies at any fully-drained state — a stale stratum-2 edge left
    by round 1 is retracted by its round-2 re-settle before the drain completes. -/
theorem no_ghost_grant_w3d2 (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T')
    (hBS : BareStarStore T') (hTS : TtuStarFree S T')
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T' R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2C σ' S T') (hq : cascadeKeys S σ' = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct_w3d2 q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO
    hLU2 hWSbare h hq hqs hqo]
  exact hDeny

/-- **T6c (wildcard scoping).** A `Direct` restriction (in particular a `T:*` grant)
    matches a stored tuple only when the tuple's subject type is one of the
    restriction types — so a `T:*` grant can never leak to a subject of another type.
    A real proved theorem via `restrictionMatches_type`. Both backends inherit the
    property through T1/T2b + the shared leaf structure. -/
theorem wildcard_scoping (rs : List Restriction) (tup : Tuple)
    (h : restrictionMatches rs tup = true) : ∃ r ∈ rs, tup.subject.type = r.1 :=
  restrictionMatches_type rs tup h

end Zanzibar
