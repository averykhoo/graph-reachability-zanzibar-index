import ZanzibarProofs.GraphIndex.ReconcileWrite

/-!
# The derived reconcile — the `check_fn` ↔ `sem`-step reduction (ROADMAP W3a, read half — increment 1)

`Reconcile.lean` collapsed the derived read to the bare edge probe on a `ResidueEmpty`
state; `ReconcileWrite.lean` modelled the write (`reconcileKey` = a guarded `writeDirect`
fold materialising a derived edge per candidate iff `checkFn`). What remains for
`graph_correct_w3a` is the *correspondence*: the reconcile materialises a derived edge
for `s` **iff** `s` is a `sem`-member of the derived key.

This increment lands the first spine of that correspondence — the **`checkFn` ↔
`sem`-step reduction**. On the W3a fragment the derived def is a boolean tree
(`and`/`but not`/`or`) whose leaves are all `computed` references to (untainted,
single-stratum) sub-relations — captured by `ComputedOnly` below. On such a tree `evalE`
consults its node-recursion `rec` only at `(dt, on, ·)` (it never reaches a
`direct`/`ttu` leaf), so the graph-reading `checkFn` and one `sem` immediate-consequence
step of the derived key coincide **exactly when the graph read and the fuel-`f` `sem`
read agree on every `computed` operand** — `checkFn_eq_semStep`.

This isolates the remaining W3a blocker (PROOF_STATUS "W3 STARTED", point 1) to precisely
that per-relation agreement `graphRec σ s dt on r' = semAux S s T q f dt on r'`, an
untainted-relation graph↔`sem` fact the W2 correspondence supplies (restated per-relation
within the mixed schema) — and the T0a fuel-stability sidestep for the fuel index.
-/

namespace Zanzibar

/-- **`ComputedOnly e`** — the W3a derived-def shape: a boolean tree (`union` / `inter` /
    `excl`) whose leaves are all `computed` references. No `direct` / `ttu` leaves — those
    route onto leaf families and add the storage / rule-leaf split deferred past W3a. This
    is the "derived boolean over `computed` refs to untainted relations" fragment the
    attack-first `#eval` corpus confirmed. -/
def ComputedOnly : Expr → Prop
  | .computed _ => True
  | .union a b => ComputedOnly a ∧ ComputedOnly b
  | .inter a b => ComputedOnly a ∧ ComputedOnly b
  | .excl a b => ComputedOnly a ∧ ComputedOnly b
  | .direct _ => False
  | .ttu _ _ => False

/-- **`evalE` on a computed-only expr reads only `rec` at `(dt, on, ·)`.** Two `rec`s
    agreeing there evaluate the whole tree identically — independently of the subject,
    store, query and enclosing relation (a computed-only tree never reaches a
    `direct` / `ttu` leaf, the only places those are consulted). This is the congruence
    that lets `checkFn`'s graph node-recursion be swapped for `sem`'s fuel recursion. -/
theorem evalE_computedOnly {rec1 rec2 : Rec} {sub1 sub2 : SubjectRef}
    {T1 T2 : Store} {q1 q2 : Query} {dt on rel1 rel2 : String}
    (hag : ∀ r', rec1 dt on r' = rec2 dt on r') :
    ∀ e : Expr, ComputedOnly e →
      evalE rec1 sub1 T1 q1 dt on rel1 e = evalE rec2 sub2 T2 q2 dt on rel2 e := by
  intro e
  induction e with
  | computed r' => intro _; simp only [evalE]; exact hag r'
  | union a b iha ihb =>
    intro hco; simp only [evalE]; rw [iha hco.1, ihb hco.2]
  | inter a b iha ihb =>
    intro hco; simp only [evalE]; rw [iha hco.1, ihb hco.2]
  | excl a b iha ihb =>
    intro hco; simp only [evalE]; rw [iha hco.1, ihb hco.2]
  | direct rs => intro hco; exact hco.elim
  | ttu tr ts => intro hco; exact hco.elim

/-- **`checkFn` equals the derived key's `sem`-step, given per-relation agreement.**
    On the W3a fragment (`ComputedOnly` derived def `e = lookup (dt, R)`), the compiled
    `check_fn` for the fixed bare subject `s` — `evalE` with node-recursion reading the
    graph (`graphRec`) — coincides with one `sem` immediate-consequence step of the
    derived key, **provided** the graph read and the fuel-`f` `sem` read agree on every
    `computed` operand at `(dt, on, ·)`.

    This is the first spine of the W3a correspondence: it reduces `checkFn = sem`-membership
    (the reconcile guard) to exactly the per-relation agreement
    `graphRec σ s dt on r' = semAux S s T q f dt on r'`, which the untainted operands' W2
    correspondence supplies (restated per-relation within the mixed schema), plus the
    fuel-stability sidestep for the fuel index. -/
theorem checkFn_eq_semStep {S : Schema} {σ : GraphState} {T : Store} {q : Query}
    {s : SubjectRef} {dt on R : String} {e : Expr} {f : Nat}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hag : ∀ r', GraphModel.graphRec σ s dt on r' = semAux S s T q f dt on r') :
    σ.checkFn T s dt on R e = semAux S s T q (f + 1) dt on R := by
  have hrhs : semAux S s T q (f + 1) dt on R
      = evalE (semAux S s T q f) s T q dt on R e := by
    simp only [semAux, step, hlk]
  rw [hrhs]
  unfold GraphState.checkFn
  exact evalE_computedOnly hag e hco

/-! ## The reconcile edge characterization — structural groundwork for the reach-collapse

`reconcileKey` is a guarded `writeDirect` fold; every step either adds the single derived
edge `subjNode c → objNode ⟨dt,on⟩ R` (a candidate `c` with `checkFn`) or is the identity.
So its edge effect is: old edges persist (`reconcileKey_edges_mono`), and every *new* edge
is a derived edge from a candidate (`reconcileKey_edge_sound`). Lifting over the W3a write
path gives `reachedByW3a_edge_sound` — every edge of a W3a state is either a materialised
rewrite-closure tuple (the untainted base, via `reachedByRules_edge_sound`) or a reconcile
derived edge. This is the W3a analog of `reachedByDirect_edge_sound` / the W2 edge sound
groundwork, and the structural spine the (bare-subject) reach-collapse will classify each
last edge against. -/

/-- **The reconcile fold only ever adds edges.** Each guarded `writeDirect` step preserves
    existing edges (`writeDirect_edges_mono`) or is the identity. -/
theorem reconcileKey_edges_mono {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) :
    ∀ ab ∈ σ.edges, ab ∈ (σ.reconcileKey T dt on R e cands).edges := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => intro ab h; exact h
  | cons s rest ih =>
    intro ab h
    simp only [List.foldl_cons]
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc]
      exact ih ab (writeDirect_edges_mono σ ⟨s, R, ⟨dt, on⟩⟩ ab h)
    · rw [if_neg hc]
      exact ih ab h

/-- **Every edge of a reconciled state is an old edge or a candidate's derived edge.** The
    fold adds only `subjNode c → objNode ⟨dt,on⟩ R` for candidates `c ∈ cands` (guarded by
    `checkFn`); everything else was already present. -/
theorem reconcileKey_edge_sound {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) :
    ∀ a b, (a, b) ∈ (σ.reconcileKey T dt on R e cands).edges →
      (a, b) ∈ σ.edges ∨ ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => intro a b h; exact Or.inl h
  | cons s rest ih =>
    intro a b h
    simp only [List.foldl_cons] at h
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc] at h
      rcases ih a b h with hprev | ⟨c, hc', hac, hbc⟩
      · -- an edge of `σ.writeDirect ⟨s,R,⟨dt,on⟩⟩`: the new derived edge or an old one
        rw [writeDirect_edges] at hprev
        split at hprev
        · rcases List.mem_cons.mp hprev with heq | hmem
          · obtain ⟨h1, h2⟩ := Prod.ext_iff.mp heq
            exact Or.inr ⟨s, List.mem_cons_self, h1, h2⟩
          · exact Or.inl hmem
        · exact Or.inl hprev
      · exact Or.inr ⟨c, List.mem_cons_of_mem _ hc', hac, hbc⟩
    · rw [if_neg hc] at h
      rcases ih a b h with hprev | ⟨c, hc', hac, hbc⟩
      · exact Or.inl hprev
      · exact Or.inr ⟨c, List.mem_cons_of_mem _ hc', hac, hbc⟩

/-- **W3a edge soundness.** Every edge of a W3a-reached state is either a materialised
    rewrite-closure tuple of a stored tuple (the untainted base structure — W2) or a
    reconcile derived edge `subjNode c → objNode ⟨dt,on⟩ R` on some derived key. By
    induction over the write path (base = `reachedByRules_edge_sound`, reconcile =
    `reconcileKey_edge_sound`). The derived-edge disjunct's source is a candidate subject
    node — the fact the bare-subject reach-collapse turns into a single-hop path. -/
theorem reachedByW3a_edge_sound {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3a σ S T) :
    ∀ a b, (a, b) ∈ σ.edges →
      (∃ t ∈ T, ∃ u ∈ rewriteClosure S t,
          a = subjNode u.subject ∧ b = objNode u.object u.relation)
      ∨ (∃ (dt on R : String) (c : SubjectRef),
          a = subjNode c ∧ b = objNode ⟨dt, on⟩ R) := by
  induction h with
  | base hr => intro a b hab; exact Or.inl (reachedByRules_edge_sound hr a b hab)
  | reconcile dt on R e cands _hRne _ ih =>
    intro a b hab
    rcases reconcileKey_edge_sound _ dt on R e cands a b hab with hold | ⟨c, _, hac, hbc⟩
    · exact ih a b hold
    · exact Or.inr ⟨dt, on, R, c, hac, hbc⟩

/-! ## The bare-subject reach-collapse (ROADMAP W3a, read half — increment 3)

The W3a assembly reads a derived query by routing to `probeDerived`, collapsing to the
bare edge probe `reach (subjNode s) (objNode ⟨dt,on⟩ R)` (`check_derived_ResidueEmpty`),
and then classifying that reachability. This increment lands the **reach-collapse spine**:
on a bare-subject query the reachability to a derived object node is a *single* edge — no
multi-hop path exists — so `reach ↔ [the reconcile wrote s's edge]`, the last link before
`checkFn ↔ sem`.

**Attack-first (analytic) finding — the single-edge collapse needs a NoRuleOutputs side
condition (the W3a analog of W2's `TtuTuplesetsDirect`).** The collapse rests on: *every*
edge into the derived R-node has a **bare** source node (predicate `BARE`), and a bare node
is never an edge *target* (`reachedByW3a_edge_target_ne_bare`), so no hop can precede that
source. The reconcile derived edges have bare sources by construction. But if the derived
def `e = lookup (dt,R)` has a **top-level `union`** exposing a `computed` arm (e.g.
`member or (admin but not suspended)`), `exprArms` emits a `computed` rewrite rule
`… ↦ R`, so W2's base rewrite-closure *also* lands tuples on the R-node — and a `computed`
rewrite carries the operand chain's subject, which for a ttu-derived operand is a **userset**
(non-bare) node that CAN be an edge target. Then the R-node's in-edge sources are not all
bare and the collapse fails (the path is genuinely ≥ 2 hops, `subjNode s → g#x →
objNode R`). It holds exactly when no rewrite rule outputs `R` — i.e. the derived def is
`inter`/`excl`-rooted (`exprArms … = []`). This session states the collapse over that
gap as the isolated hypothesis `hsrcbare` (every R-node in-edge source is bare); the
`NoRuleOutputs`-discharge of `hsrcbare` is the next increment. -/

/-- An object node's predicate is its relation (both variants encode it in `pred`). -/
@[simp] theorem objNode_pred (o : ObjectRef) (R : String) : (objNode o R).pred = R := by
  unfold objNode; split <;> rfl

/-- **Generic single-edge collapse.** If every source of an edge into `v` has itself no
    in-edge, then any path to `v` is a single edge: its last-edge source `x` (from
    `nreaches_last`) would otherwise carry an in-edge (the prefix `u →* x`'s last edge),
    contradicting the hypothesis — so the prefix is empty and `(u,v)` is that edge. -/
theorem nreaches_collapse_of_source_notarget {edges : List (NodeKey × NodeKey)}
    {u v : NodeKey}
    (H : ∀ x, (x, v) ∈ edges → ∀ y, (y, x) ∉ edges)
    (h : NReaches edges u v) : (u, v) ∈ edges := by
  obtain ⟨x, hux, hxv⟩ := nreaches_last h
  rcases hux with rfl | hux
  · exact hxv
  · obtain ⟨z, _, hzx⟩ := nreaches_last hux
    exact absurd hzx (H x hxv z)

/-- **Every W3a edge target has a non-`BARE` predicate.** A base edge lands on
    `objNode u.object u.relation` (predicate `u.relation ≠ BARE`, `rewriteClosure_rel_ne_
    bare`); a reconcile derived edge lands on `objNode ⟨dt,on⟩ R` (predicate `R ≠ BARE`,
    the reconcile constructor's declared-relation side condition). By induction over the
    write path, using `reconcileKey_edge_sound` to classify the reconcile-pass edges. -/
theorem reachedByW3a_edge_target_ne_bare {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (h : ReachedByW3a σ S T) :
    ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE := by
  induction h with
  | base hr =>
    intro a b hab
    obtain ⟨t, ht, u, hu, _, hbobj⟩ := reachedByRules_edge_sound hr a b hab
    rw [hbobj, objNode_pred]; exact rewriteClosure_rel_ne_bare hWF hSV ht hu
  | reconcile dt on R e cands hRne _ ih =>
    intro a b hab
    rcases reconcileKey_edge_sound _ dt on R e cands a b hab with hold | ⟨c, _, _, hbc⟩
    · exact ih hWF hSV a b hold
    · rw [hbc, objNode_pred]; exact hRne

/-- **A `BARE`-predicate node is never an edge target** in a W3a state — the structural
    fact behind the reach-collapse (a bare candidate node has no in-edges, so no hop can
    precede it). Immediate from `reachedByW3a_edge_target_ne_bare`. -/
theorem reachedByW3a_bareNode_no_inedge {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (h : ReachedByW3a σ S T)
    {k : NodeKey} (hk : k.pred = BARE) : ∀ x, (x, k) ∉ σ.edges := by
  intro x hxk
  exact reachedByW3a_edge_target_ne_bare hWF hSV h x k hxk hk

/-- **The bare-subject reach-collapse.** On a W3a state, if every source of an edge into
    the derived object node `objNode ⟨dt,on⟩ R` is a bare node (`hsrcbare` — the
    `NoRuleOutputs` gap, discharged next increment), then any path to that node is a
    *single* edge. Combines the generic collapse with `reachedByW3a_bareNode_no_inedge`
    (a bare source is never itself a target). This is the last structural link before
    `reach ↔ [reconcile wrote s's edge] ↔ checkFn ↔ sem`. -/
theorem reachedByW3a_reach_collapse {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (h : ReachedByW3a σ S T)
    {dt on R : String} {u : NodeKey}
    (hsrcbare : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv
  exact reachedByW3a_bareNode_no_inedge hWF hSV h (hsrcbare x hxv)

end Zanzibar
