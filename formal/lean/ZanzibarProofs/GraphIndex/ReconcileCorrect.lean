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
  | reconcile dt on R e cands _ ih =>
    intro a b hab
    rcases reconcileKey_edge_sound _ dt on R e cands a b hab with hold | ⟨c, _, hac, hbc⟩
    · exact ih a b hold
    · exact Or.inr ⟨dt, on, R, c, hac, hbc⟩

end Zanzibar
