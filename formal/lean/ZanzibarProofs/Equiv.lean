import ZanzibarProofs.SetEngine.Correct
import ZanzibarProofs.GraphIndex.DirectCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.GraphIndex.UsStarClosure

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

/-- **T3 (equivalence), fragment scope.** On states operationally reached by
    writing exactly `T`, the two backends agree — by transitivity through `sem`
    (T1 ∘ T2b-fragment). -/
theorem backend_equivalence (S : Schema) (T : Store) (σ : GraphState) (q : Query)
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
theorem exclusion_effective (S : Schema) (T : Store) (σ : GraphState) (q : Query)
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
theorem no_ghost_grant (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
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

/-- **T6c (wildcard scoping).** A `Direct` restriction (in particular a `T:*` grant)
    matches a stored tuple only when the tuple's subject type is one of the
    restriction types — so a `T:*` grant can never leak to a subject of another type.
    A real proved theorem via `restrictionMatches_type`. Both backends inherit the
    property through T1/T2b + the shared leaf structure. -/
theorem wildcard_scoping (rs : List Restriction) (tup : Tuple)
    (h : restrictionMatches rs tup = true) : ∃ r ∈ rs, tup.subject.type = r.1 :=
  restrictionMatches_type rs tup h

end Zanzibar
