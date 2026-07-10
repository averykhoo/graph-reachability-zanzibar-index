import ZanzibarProofs.GraphIndex.RulesChain

/-!
# The untainted rule-routing COMPLETENESS groundwork (ROADMAP W2, read half — the `sem ⇒ reach` side)

`RulesChain.lean` closed the W2 *soundness* direction (`reach ⇒ sem`). This file builds
the operational groundwork for the *completeness* direction (`sem ⇒ reach`): the
**admitted** W2 write-closure `ReachedByRulesAdmitted`, on which every materialised
rewrite-closure edge is present (`reachedByRulesAdmitted_edge_complete`). This is the W2
analog of `admitted_edge_complete` (DirectCorrect) / the W1 admitted closures.

`writeRules` folds `writeDirect` over `rewriteClosure S t`; a `writeDirect` is a *guarded*
edge write (cycle-rejection), so edge-completeness needs every write in the fold to be
admitted. `FoldAdmits` records exactly that (faithful to the composed system: a rejected
write raises and rolls back, so a real store never holds a rejected tuple — here, a real
graph never drops an admitted closure edge). Edges are monotone under `writeDirect`, so an
admitted edge, once added, persists through the rest of the fold.

The completeness *core* (`sem ⇒ reach`) — which additionally needs closure-saturation for
the `computed` case (attack-first confirmed the `|keys|+1` bound is sound) — is the
deferred next increment.
-/

namespace Zanzibar

/-! ## Edge monotonicity of the `writeDirect` fold -/

/-- A single `writeDirect` only ever adds edges. -/
theorem writeDirect_edges_mono (σ : GraphState) (t : Tuple) :
    ∀ e ∈ σ.edges, e ∈ (σ.writeDirect t).edges := by
  intro e he
  rw [writeDirect_edges]
  split
  · exact List.mem_cons_of_mem _ he
  · exact he

/-- Folding `writeDirect` over a tuple list only ever adds edges. -/
theorem foldl_writeDirect_edges_mono (us : List Tuple) :
    ∀ {σ : GraphState}, ∀ e ∈ σ.edges,
      e ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).edges := by
  induction us with
  | nil => intro σ e he; exact he
  | cons t rest ih =>
    intro σ e he
    exact ih e (writeDirect_edges_mono σ t e he)

/-! ## The fold-admission predicate -/

/-- **`FoldAdmits σ us`** — folding `writeDirect` over `us` from `σ` admits every write
    (no cycle-rejection anywhere in the fold). The faithful admission condition for the
    rule-routed write: the composed system rolls back a rejected write, so a real graph
    materialises every closure edge. -/
def FoldAdmits : GraphState → List Tuple → Prop
  | _, [] => True
  | σ, u :: rest =>
      σ.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true ∧
      FoldAdmits (σ.writeDirect u) rest

/-- **Fold edge-completeness.** If every write in the fold is admitted, every tuple's
    materialised edge is present in the folded state — its own `writeDirect` adds it
    (admission), and the rest of the fold preserves it (edge monotonicity). -/
theorem foldl_writeDirect_edge_complete (us : List Tuple) :
    ∀ {σ : GraphState}, FoldAdmits σ us →
      ∀ u ∈ us, (subjNode u.subject, objNode u.object u.relation) ∈
        (us.foldl (fun acc u => acc.writeDirect u) σ).edges := by
  induction us with
  | nil => intro σ _ u hu; simp at hu
  | cons t rest ih =>
    intro σ hfa u hu
    obtain ⟨hadm, hrest⟩ := hfa
    rcases List.mem_cons.mp hu with rfl | hmem
    · -- u = t (t eliminated by subst): its edge is added by σ.writeDirect u (admitted),
      -- then preserved by the rest
      have hstep : (subjNode u.subject, objNode u.object u.relation) ∈ (σ.writeDirect u).edges := by
        rw [writeDirect_edges, if_pos hadm]; exact List.mem_cons_self
      exact foldl_writeDirect_edges_mono rest _ hstep
    · -- u ∈ rest: IH on the post-t fold state
      exact ih hrest u hmem

/-! ## The admitted W2 write-closure -/

/-- **`ReachedByRulesAdmitted σ S T`** — `σ` is reached from empty by rule-routed writes
    (`writeRules`) each of whose rewrite-closure fold was fully admitted. The W2 analog of
    `ReachedByAdmitted`; on it the edge set is complete for every materialised closure
    tuple (`reachedByRulesAdmitted_edge_complete`). -/
inductive ReachedByRulesAdmitted : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByRulesAdmitted (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hprev : ReachedByRulesAdmitted σ S T)
      (hadm : FoldAdmits σ (rewriteClosure S t)) :
      ReachedByRulesAdmitted (σ.writeRules S t) S (t :: T)

/-- Admitted rule-routed writes are a special case of the W2 write-closure. -/
theorem reachedByRules_of_admitted {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) : ReachedByRules σ S T := by
  induction h with
  | empty S => exact ReachedByRules.empty S
  | step t _ _ ih => exact ReachedByRules.step t ih

/-- **W2 edge-completeness.** Every tuple in the rewrite-closure of every stored write has
    its materialised edge present. By induction over the admitted write path: a fresh
    write's closure edges are complete via `foldl_writeDirect_edge_complete` (fold
    admission), and old edges are monotone (`foldl_writeDirect_edges_mono`). The
    completeness-half analog of `reachedByRules_edge_sound`. -/
theorem reachedByRulesAdmitted_edge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) :
    ∀ t ∈ T, ∀ u ∈ rewriteClosure S t,
      (subjNode u.subject, objNode u.object u.relation) ∈ σ.edges := by
  induction h with
  | empty S => intro t ht; simp at ht
  | @step σ S T t hprev hadm ih =>
    intro t' ht' u hu
    rcases List.mem_cons.mp ht' with rfl | hmem
    · -- t' = t (t eliminated by subst): the just-written closure's edges are complete
      exact foldl_writeDirect_edge_complete (rewriteClosure S t') hadm u hu
    · -- t' ∈ T: old edge, monotone through σ.writeRules S t
      exact foldl_writeDirect_edges_mono (rewriteClosure S t) _ (ih t' hmem u hu)

/-- **Every stored tuple's own edge is present** (the seed case of edge-completeness — the
    `direct`/`ttu` completeness cases consult exactly this). -/
theorem reachedByRulesAdmitted_seed_edge {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) :
    ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges := by
  intro t ht
  exact reachedByRulesAdmitted_edge_complete h t ht t (rewriteClosure_seed S t)

end Zanzibar
