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
  | reconcile dt on R e cands _hRne _hcands _hder _ ih =>
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

/-- An object node's type is its object's type (both variants keep it). -/
@[simp] theorem objNode_type (o : ObjectRef) (R : String) : (objNode o R).type = o.type := by
  unfold objNode; split <;> rfl

/-- A subject node's predicate is its subject's predicate (both variants keep it). -/
@[simp] theorem subjNode_pred (s : SubjectRef) : (subjNode s).pred = s.predicate := by
  unfold subjNode; split <;> rfl

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
  | reconcile dt on R e cands hRne _hcands _hder _ ih =>
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

/-! ## Discharging `hsrcbare` via `NoRuleOutputs` (ROADMAP W3a, read half — increment 4)

The reach-collapse (`reachedByW3a_reach_collapse`) needs `hsrcbare`: every in-edge source of
the derived object node `objNode ⟨dt,on⟩ R` is bare. This increment discharges it on the
W3a fragment where the derived def `e = lookup (dt, R)` is **`inter`/`excl`-rooted**
(`RootBoolean` — the analytic side condition found last session, the W3a analog of W2's
`TtuTuplesetsDirect`). The argument:

* No `schemaRewrites S` rule outputs `(dt, R)` (`NoRuleOutputs`) — a `RootBoolean` def emits
  no rewrite arms (`exprArms_rootBoolean`), so via `schemaRewrites_provenance` + `NodupKeys`
  no rule carries `(objectType, outRel) = (dt, R)`.
* No stored tuple sits on `(dt, R)` — a `RootBoolean` def has no `Direct` arm
  (`exprDirects_rootBoolean = []`), so `StoreValidRules` forbids a stored `(dt, R)` tuple.

Together these kill the **base** (rewrite-closure) leg of `reachedByW3a_edge_sound` on the
R-node: a closure tuple landing there is neither the raw seed (no stored `(dt,R)` tuple) nor
a rewrite output (`NoRuleOutputs`). So *every* in-edge of the R-node is a **reconcile** edge,
whose source is a candidate — bare by the reconcile constructor's `hcands`. Hence `hsrcbare`
holds unconditionally on the fragment, and the collapse fires (`reachedByW3a_reach_collapse_
root`). -/

/-- **`RootBoolean e`** — `e`'s root is a boolean operator (`inter`/`excl`). On the W3a
    fragment this is the shape that keeps the derived key off the rewrite-fanout: a
    boolean-rooted def emits no `computed`/`ttu` rewrite arms and carries no `Direct`
    storage arm. The W3a analog of `directsOnly`/`TtuTuplesetsDirect` for the *derived*
    relation itself. -/
def RootBoolean : Expr → Prop
  | .inter _ _ => True
  | .excl _ _  => True
  | _          => False

/-- A boolean-rooted expr emits no rewrite arms (`exprArms` walks into `union` but stops at
    `inter`/`excl`). -/
theorem exprArms_rootBoolean (ot rel : String) {e : Expr} (h : RootBoolean e) :
    exprArms ot rel e = [] := by
  cases e <;> first | rfl | exact h.elim

/-- A boolean-rooted expr carries no `Direct` storage arm. -/
theorem exprDirects_rootBoolean {e : Expr} (h : RootBoolean e) : exprDirects e = [] := by
  cases e <;> first | rfl | exact h.elim

/-- **`NoRuleOutputs S dt R`** — no schema rewrite rule outputs the derived key `(dt, R)`.
    On a boolean-rooted derived def this holds (`noRuleOutputs_of_root`), so W2's base
    rewrite-closure never lands a tuple on the R-node — the fragment condition behind the
    reach-collapse. -/
def NoRuleOutputs (S : Schema) (dt R : String) : Prop :=
  ∀ r ∈ schemaRewrites S, ¬(r.objectType = dt ∧ r.outRel = R)

/-- **Boolean-rooted ⇒ no rewrite outputs `(dt, R)`.** A rule with `(objectType, outRel) =
    (dt, R)` comes (via `schemaRewrites_provenance` + `NodupKeys`) from the def at key
    `(dt, R)` — which is `e`, boolean-rooted, hence emits no arms (`exprArms_rootBoolean`),
    a contradiction. -/
theorem noRuleOutputs_of_root {S : Schema} {dt R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hNK : NodupKeys S) (hroot : RootBoolean e) :
    NoRuleOutputs S dt R := by
  intro r hr hcon
  obtain ⟨d, hd, hkey, hrarm⟩ := schemaRewrites_provenance hr
  have hkey' : d.1 = (dt, R) := by rw [hkey, hcon.1, hcon.2]
  have hld : S.lookup d.1 = some d.2 := lookup_of_mem hNK hd
  rw [hkey', hlk, Option.some.injEq] at hld
  rw [← hld, exprArms_rootBoolean _ _ hroot] at hrarm
  simp at hrarm

/-- **Every in-edge source of the derived R-node is bare** on the W3a fragment. By induction
    over the write path: the base (rewrite-closure) leg landing on `objNode ⟨dt,on⟩ R` is
    impossible — the closure tuple would be a stored `(dt,R)` tuple (none, by
    `exprDirects_rootBoolean` + `StoreValidRules`) or a rewrite output `(dt,R)` (none, by
    `noRuleOutputs_of_root`); so every in-edge is a reconcile edge, whose source is a
    candidate, bare by `hcands`. Discharges the `hsrcbare` hypothesis of the reach-collapse. -/
theorem reachedByW3a_Rnode_source_bare {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hlk : S.lookup (dt, R) = some e) (hroot : RootBoolean e)
    (h : ReachedByW3a σ S T) :
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
  induction h with
  | base hr =>
    intro x hx
    obtain ⟨t, ht, u, hu, _hasub, hbobj⟩ := reachedByRules_edge_sound hr x _ hx
    exfalso
    have htype : dt = u.object.type := by
      simpa [objNode_type] using congrArg NodeKey.type hbobj
    have hrel : R = u.relation := by
      simpa [objNode_pred] using congrArg NodeKey.pred hbobj
    rcases rewriteClosure_produced hu with heq | ⟨r, hr', hro, hrout⟩
    · rw [heq] at htype hrel
      obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t ht
      rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
      rw [← hlk', exprDirects_rootBoolean hroot] at hrs
      simp at hrs
    · exact noRuleOutputs_of_root hlk hNK hroot r hr'
        ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
  | reconcile dt' on' R' e' cands _hRne hcands _hder _ ih =>
    intro x hx
    rcases reconcileKey_edge_sound _ dt' on' R' e' cands x _ hx with hold | ⟨c, hc, hxc, _⟩
    · exact ih hSV hNK hlk x hold
    · rw [hxc, subjNode_pred]; exact hcands c hc

/-- **The reach-collapse, fully discharged on the boolean-rooted W3a fragment.** Given the
    derived def `e = lookup (dt, R)` is `inter`/`excl`-rooted (`RootBoolean`), any path to the
    derived object node `objNode ⟨dt,on⟩ R` is a *single* reconcile edge — no `hsrcbare` left
    free. This is the last structural link: `reach (subjNode s) (objNode ⟨dt,on⟩ R) ↔ [a
    reconcile pass wrote s's edge]`, ready to compose with `checkFn_eq_semStep` for
    `graph_correct_w3a`. -/
theorem reachedByW3a_reach_collapse_root {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr} {u : NodeKey}
    (hWF : WF S) (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hlk : S.lookup (dt, R) = some e) (hroot : RootBoolean e)
    (h : ReachedByW3a σ S T)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges :=
  reachedByW3a_reach_collapse hWF hSV h
    (reachedByW3a_Rnode_source_bare hSV hNK hlk hroot h) hr

/-! ## Reconcile-edge reachability inertness (ROADMAP W3a, read half — increment 5)

The remaining W3a correspondence blocker (PROOF_STATUS point 2, `hag`) restates W2's
`graph_correct_rules` *per untainted operand relation* `r'` within the mixed W3a schema.
That restatement needs the reconcile-materialised derived edges to be **reachability-inert
for the operand read** — the graph read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full
W3a `σ` must equal the read on the untainted base, so that the W2 argument transfers.

**The flagged subtlety (PROOF_STATUS "R-node-source"): is the derived R-node ever an edge
SOURCE?** A reconcile edge is `subjNode c → objNode ⟨dt,on⟩ R` (bare source, R-node target).
Its bare source is never a target (`reachedByW3a_bareNode_no_inedge`), so it can only *start*
a path; the path then continues out of the R-node. If the R-node has an out-edge, a reconcile
edge can extend a path to a *further* node — NOT inert. A base (W2) edge source is
`subjNode u.subject`; for a **userset** subject `⟨dt,on⟩#R` over the derived relation `R` this
IS the R-node, so a stored/rewrite-closure operand tuple with such a subject would give the
R-node an out-edge.

**Resolution.** On the single-stratum W3a fragment the derived boolean `R` is *terminal*: it
is neither a stored subject predicate (`NoStoreSubjectR`) nor a TTU target relation
(`NoTtuTarget` — the Python `PDerivedTTU`/`PDerivedTuplesetTTU` "target from tupleset with
derived target" shapes are deferred past W3a). A rewrite-closure tuple's subject predicate is
the seed's (computed rewrites keep the subject) or a TTU rule's `tr` (ttu re-userset-s onto
`tr`); under both conditions neither is `R`, so **no graph edge is ever sourced at an
`R`-userset node** (`reachedByW3a_edge_source_ne_R`). The R-node has no out-edge, and a
reconcile edge onto it is a pure trailing hop — inert for any read whose target is not that
R-node (`reconcileKey_reach_inert`). -/

/-- **Generic single-new-edge inertness.** If the target `b` of a prepended edge `(a,b)` is
    never itself a *source* in the old edges, then for any `v ≠ b` a path in `(a,b) :: edges`
    to `v` is already a path in `edges` — the new edge, if used, would have to be exited out
    of `b` (impossible: `b` is not a source) or be the final hop (impossible: its target `b`
    ≠ `v`). Axiom-free; via `nreaches_cons_split`. -/
theorem nreaches_cons_inert {edges : List (NodeKey × NodeKey)} {a b u v : NodeKey}
    (hbns : ∀ y, (b, y) ∉ edges) (hv : v ≠ b)
    (h : NReaches ((a, b) :: edges) u v) : NReaches edges u v := by
  rcases nreaches_cons_split h with hl | ⟨_, hbv⟩
  · exact hl
  · rcases hbv with heq | hr
    · exact absurd heq.symm hv
    · cases hr with
      | edge hbw => exact absurd hbw (hbns _)
      | head hbw _ => exact absurd hbw (hbns _)

/-- **`NoTtuTarget S R`** — no schema rewrite rule re-userset-s a subject onto `R` (no TTU
    rule has target relation `R`). On the single-stratum W3a fragment the derived boolean `R`
    is terminal — the "target from a tupleset" shapes that would output an `R`-userset subject
    are deferred (Python `PDerivedTTU`/`PDerivedTuplesetTTU`). -/
def NoTtuTarget (S : Schema) (R : String) : Prop :=
  ∀ r ∈ schemaRewrites S, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ R

/-- **`NoStoreSubjectR T R`** — no stored tuple carries a subject that is a userset over the
    derived relation `R`. On W3a the derived boolean is a top-level permission, never itself a
    userset subject of a raw write. -/
def NoStoreSubjectR (T : Store) (R : String) : Prop :=
  ∀ t ∈ T, t.subject.predicate ≠ R

/-- One rewrite step keeps a subject off predicate `R`: `computed` preserves the subject; a
    `ttu tr` sets it to `tr ≠ R` by `NoTtuTarget`. -/
theorem rewriteStep_subject_pred_ne {S : Schema} {R : String} (hnt : NoTtuTarget S R)
    {t u : Tuple} (ht : t.subject.predicate ≠ R) (h : u ∈ rewriteStep S t) :
    u.subject.predicate ≠ R := by
  unfold rewriteStep at h
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp h
  obtain ⟨ot, mr, or, kind⟩ := r
  unfold applyRRule at hap
  split at hap
  · cases kind with
    | computed => simp only [Option.some.injEq] at hap; rw [← hap]; exact ht
    | ttu tr => simp only [Option.some.injEq] at hap; rw [← hap]; exact hnt _ hr tr rfl
  · simp at hap

/-- Subject-predicate avoidance across the bounded closure. -/
theorem rewriteClosureAux_subject_pred_ne {S : Schema} {R : String} (hnt : NoTtuTarget S R) :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, w.subject.predicate ≠ R) →
      ∀ u ∈ rewriteClosureAux S n cur, u.subject.predicate ≠ R := by
  intro n
  induction n with
  | zero => intro cur hcur u hu; exact hcur u hu
  | succ m ih =>
    intro cur hcur u hu
    rw [rewriteClosureAux, List.mem_append] at hu
    rcases hu with hin | hrec
    · exact hcur u hin
    · refine ih _ ?_ u hrec
      intro w hw
      rw [List.mem_flatMap] at hw
      obtain ⟨x, hx, hwx⟩ := hw
      exact rewriteStep_subject_pred_ne hnt (hcur x hx) hwx

/-- **No rewrite-closure tuple of an `R`-avoiding seed has subject predicate `R`.** The seed
    avoids `R` (`NoStoreSubjectR`); each rewrite hop keeps it off `R` (`rewriteStep_subject_
    pred_ne`). -/
theorem rewriteClosure_subject_pred_ne {S : Schema} {R : String} (hnt : NoTtuTarget S R)
    {t u : Tuple} (ht : t.subject.predicate ≠ R) (hu : u ∈ rewriteClosure S t) :
    u.subject.predicate ≠ R := by
  unfold rewriteClosure at hu
  exact rewriteClosureAux_subject_pred_ne hnt _ _
    (fun w hw => by rw [List.mem_singleton.mp hw]; exact ht) _ hu

/-- **No W3a edge is sourced at an `R`-userset node.** A base edge's source is
    `subjNode u.subject` for a closure tuple `u` (predicate ≠ `R` by
    `rewriteClosure_subject_pred_ne`); a reconcile edge's source is a bare candidate
    (predicate `BARE ≠ R`). By induction over the write path. Resolves the flagged
    R-node-source subtlety: the derived R-node (predicate `R`) has no out-edge. -/
theorem reachedByW3a_edge_source_ne_R {σ : GraphState} {S : Schema} {T : Store}
    {R : String} (hnt : NoTtuTarget S R) (hns : NoStoreSubjectR T R) (hRne : R ≠ BARE)
    (h : ReachedByW3a σ S T) :
    ∀ a b, (a, b) ∈ σ.edges → a.pred ≠ R := by
  induction h with
  | base hr =>
    intro a b hab
    obtain ⟨t, ht, u, hu, hasub, _⟩ := reachedByRules_edge_sound hr a b hab
    rw [hasub, subjNode_pred]
    exact rewriteClosure_subject_pred_ne hnt (hns t ht) hu
  | reconcile dt on R' e cands _hRne hcands _hder _ ih =>
    intro a b hab
    rcases reconcileKey_edge_sound _ dt on R' e cands a b hab with hold | ⟨c, hc, hac, _⟩
    · exact ih hnt hns a b hold
    · rw [hac, subjNode_pred, hcands c hc]; exact hRne.symm

/-- **The derived R-node is never an edge source** (`hk : k.pred = R`) — the direct
    consequence of `reachedByW3a_edge_source_ne_R`. So a reconcile edge onto the R-node is a
    trailing hop: no path exits the R-node. -/
theorem reachedByW3a_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {R : String} (hnt : NoTtuTarget S R) (hns : NoStoreSubjectR T R) (hRne : R ≠ BARE)
    (h : ReachedByW3a σ S T) {k : NodeKey} (hk : k.pred = R) :
    ∀ y, (k, y) ∉ σ.edges := by
  intro y hky
  exact reachedByW3a_edge_source_ne_R hnt hns hRne h k y hky hk

/-- **One reconcile pass is reachability-inert for a non-R-node read.** If the derived R-node
    `objNode ⟨dt,on⟩ R'` is not a source in `σ` (its candidates are bare, `R' ≠ BARE`), then
    reconciling key `(dt,R')` adds no reachability to any `v ≠` that R-node: every new edge is
    a trailing hop onto the R-node. Peels the guarded `writeDirect` fold one candidate at a
    time via `nreaches_cons_inert`, maintaining "R-node not a source" (each new edge's bare
    source has predicate `BARE ≠ R'`). This is the per-pass inertness the multi-pass `hag`
    transfer folds over the W3a write path. -/
theorem reconcileKey_reach_inert {σ0 : GraphState} (T : Store)
    (dt on R' : String) (e : Expr) (cands0 : List SubjectRef) (hR'ne : R' ≠ BARE)
    {u v : NodeKey} (hv : v ≠ objNode ⟨dt, on⟩ R')
    (hcb0 : ∀ c ∈ cands0, c.predicate = BARE)
    (hRns0 : ∀ y, (objNode ⟨dt, on⟩ R', y) ∉ σ0.edges)
    (h0 : NReaches (σ0.reconcileKey T dt on R' e cands0).edges u v) :
    NReaches σ0.edges u v := by
  suffices H : ∀ (cs : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cs, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R', y) ∉ σ.edges) →
      NReaches (σ.reconcileKey T dt on R' e cs).edges u v →
      NReaches σ.edges u v from H cands0 σ0 hcb0 hRns0 h0
  intro cs
  induction cs with
  | nil =>
    intro σ _ _ h
    unfold GraphState.reconcileKey at h
    simpa using h
  | cons s rest ih =>
    intro σ hcb hRns h
    unfold GraphState.reconcileKey at h
    simp only [List.foldl_cons] at h
    by_cases hc : σ.checkFn T s dt on R' e = true
    · rw [if_pos hc] at h
      have hsbare : s.predicate = BARE := hcb s List.mem_cons_self
      have hRns' : ∀ y, (objNode ⟨dt, on⟩ R', y) ∉ (σ.writeDirect ⟨s, R', ⟨dt, on⟩⟩).edges := by
        intro y hy
        rw [writeDirect_edges] at hy
        split at hy
        · rcases List.mem_cons.mp hy with heq | hmem
          · have h1 := (Prod.ext_iff.mp heq).1
            have h2 : R' = s.predicate := by
              have hp := congrArg NodeKey.pred h1
              simpa [objNode_pred, subjNode_pred] using hp
            rw [hsbare] at h2
            exact hR'ne h2
          · exact hRns y hmem
        · exact hRns y hy
      have hstep := ih (σ.writeDirect ⟨s, R', ⟨dt, on⟩⟩)
        (fun c hcm => hcb c (List.mem_cons_of_mem _ hcm)) hRns' h
      rw [writeDirect_edges] at hstep
      split at hstep
      · exact nreaches_cons_inert hRns hv hstep
      · exact hstep
    · rw [if_neg hc] at h
      exact ih σ (fun c hcm => hcb c (List.mem_cons_of_mem _ hcm)) hRns h

/-! ## Multi-pass reconcile inertness — the reachability transfer to the untainted base
    (ROADMAP W3a, read half — increment 6)

`reconcileKey_reach_inert` shows one reconcile pass adds no reachability to a non-R-node.
This increment **folds that over the whole W3a write path**: every reconcile pass is peeled
off, transferring reachability into an *untainted-key* node all the way down to the
`ReachedByRules` base. This is the reachability half of the `hag` reduction (PROOF_STATUS
point 2): the operand read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full W3a state agrees
with the read on the untainted base, so W2's per-relation correctness transfers.

The target-key condition is `isDerived S (v.type, v.pred) = false` — an *untainted* node.
Each reconcile pass writes only into `objNode ⟨dt,on⟩ R` with `isDerived S (dt, R) = true`
(the constructor's `hder`); an untainted node has `isDerived` `false` at its own key, so it is
distinct from every reconcile target (equal keys share `isDerived`) — exactly
`reconcileKey_reach_inert`'s `v ≠` hypothesis. The per-pass R-node-not-a-source premise comes
from `reachedByW3a_Rnode_not_source` on the pre-pass sub-derivation, using the schema-level
terminal hypothesis `hterm` (every derived key is `NoTtuTarget`/`NoStoreSubjectR` — faithful:
W3a defers the non-terminal `PDerivedTTU`/`PDerivedUserset` shapes). -/

/-- **Every reconcile pass is reachability-inert for untainted-key reads — folded to the
    base.** For a W3a state `σ`, there is an untainted base `σ0` (`ReachedByRules σ0 S T`,
    the rewrite-closure of the store) such that reachability into any *untainted-key* node
    `v` (`isDerived S (v.type, v.pred) = false`) agrees between `σ` and `σ0`. By induction
    over the write path: the base leg is the identity; each reconcile leg peels one
    `reconcileKey_reach_inert` (the pass writes only into its derived R-node, distinct from
    the untainted target since equal keys share `isDerived`), then applies the IH.

    This transfers W2's per-relation untainted correctness through the mixed W3a schema: the
    operand reads `hag` consults see only the base edges, so the reconcile-materialised
    derived edges are inert for them. `hterm` is the faithful W3a fragment condition (every
    derived relation is terminal — no TTU target, no stored userset subject). -/
theorem reachedByW3a_reach_inert {σ : GraphState} {S : Schema} {T : Store}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3a σ S T) :
    ∃ σ0, ReachedByRules σ0 S T ∧
      ∀ {u v : NodeKey}, isDerived S (v.type, v.pred) = false →
        NReaches σ.edges u v → NReaches σ0.edges u v := by
  induction h with
  | base hr => exact ⟨_, hr, fun _ hn => hn⟩
  | reconcile dt on R e cands hRne hcands hder h' ih =>
    obtain ⟨σ0, hσ0, htrans⟩ := ih hterm
    refine ⟨σ0, hσ0, ?_⟩
    intro u v hv hreach
    obtain ⟨hnt, hns⟩ := hterm dt R hder
    have hRns0 := reachedByW3a_Rnode_not_source hnt hns hRne h' (objNode_pred ⟨dt, on⟩ R)
    have hvne : v ≠ objNode ⟨dt, on⟩ R := by
      intro heq
      rw [heq, objNode_type, objNode_pred, hder] at hv
      exact absurd hv (by decide)
    have hstep := reconcileKey_reach_inert _ dt on R e cands hRne hvne hcands hRns0 hreach
    exact htrans hv hstep

end Zanzibar
