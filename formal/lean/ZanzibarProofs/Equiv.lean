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
# T3 / T6 — equivalence and the security corollaries

`SEMANTICS.md` §8 (T3, T6). T3 is the whole point of the shared-spec architecture:
prove each backend against `sem`, get backend-equivalence by transitivity in Lean.
T6 are the review's headline security properties, one-line consequences of T1/T2b.

**Restatement (2026-07-10).** The original statements quantified over the deleted
abstract `ReachedBy` closure and were **false as stated** (junk states satisfied
every hypothesis while only the set engine computed `sem`). They are now stated
over the operational closure at its current scope — the star-free pure-direct
fragment (`ReachedByAdmitted`, T2b = `graph_correct_direct`) — and are REAL,
axiom-clean theorems, no `sorry`. Their scope widens with the write model
(bridges → rule routing → reconcile, ROADMAP order); at full `GraphAccepts`
scope the exclusion case of T6a becomes non-vacuous (the current fragment has no
`but not`, so T6a's content here is deny-propagation).
-/

namespace Zanzibar

/-- **T3 (equivalence), star-free pure-direct fragment scope.** On states
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

/-- **T6a (exclusion-effectiveness / deny-propagation), fragment scope.** Whenever
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

/-- **T6b (no-ghost-grant), fragment scope.** If removing a tuple makes the spec
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

/-- **T3 (equivalence), W1b (object-wildcard) scope.** Both backends agree on stores
    with object wildcards, by transitivity through `sem` (T1 ∘ `graph_correct_objStar`). -/
theorem backend_equivalence_objStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T)
    (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : WildReachedAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid,
      graph_correct_objStar S T σ q hWF hPD hSV hOS hOV hqs hqo hReach]

/-- **T6a (deny-propagation), W1b scope.** Whenever the spec denies, both backends
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

/-- **T6b (no-ghost-grant), W1b scope.** If removing a tuple makes the spec deny, the
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

/-- **T3 (equivalence), W1c (userset-star) scope.** Both backends agree on stores with
    userset-star subject grants (`[T:*#P]`), by transitivity through `sem`
    (T1 ∘ `graph_correct_usStar`). -/
theorem backend_equivalence_usStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReachedAdmitted σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF (stratifiable_pureDirect hPD) hValid,
      graph_correct_usStar S T σ q hWF hPD hSV hUS hqs hqo hReach]

/-- **T6a (deny-propagation), W1c scope.** Whenever the spec denies, both backends deny
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

/-- **T6b (no-ghost-grant), W1c scope.** If removing a tuple makes the spec deny, the
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

/-- **T3 (equivalence), W2 (rule-routing) scope.** Both backends agree on untainted
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

/-- **T6a (deny-propagation), W2 scope.** Whenever the spec denies, both backends deny —
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

/-- **T6b (no-ghost-grant), W2 scope.** If removing a tuple makes the spec deny, the graph
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

/-- **T3 (equivalence), W3a scope.** Both backends agree on the star-free bare-subject derived
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

/-- **T6a (deny-propagation), W3a scope.** Whenever the spec denies, both backends deny — now
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

/-- **T6b (no-ghost-grant), W3a scope.** If removing a tuple makes the spec deny, the graph backend
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

/-- **T3 (equivalence), W3b scope.** Both backends agree on the star-free derived boolean fragment
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

/-- **T6a (deny-propagation), W3b scope.** Whenever the spec denies, both backends deny — now
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

/-- **T6b (no-ghost-grant), W3b scope.** If removing a tuple makes the spec deny, the graph backend
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

/-- **T3 (equivalence), W3c scope.** Both backends agree on the derived boolean fragment
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

/-- **T6a (deny-propagation), W3c scope.** Whenever the spec denies, both backends deny —
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

/-- **T6b (no-ghost-grant), W3c scope.** If removing a tuple makes the spec deny, the
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

/-- **T3 (equivalence), W3d scope.** Both backends agree at every fully-drained state
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

/-- **T6a (deny-propagation), W3d scope.** Whenever the spec denies, both backends deny
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

/-- **T6b (no-ghost-grant), W3d scope.** If the spec denies on the chain's own store,
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

/-- **T3 (equivalence), W3d-2 scope.** Both backends agree at every fully-drained
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

/-- **T6a (deny-propagation), W3d-2 scope.** Whenever the spec denies, both backends
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

/-- **T6b (no-ghost-grant), W3d-2 scope.** If the spec denies on the chain's own
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
