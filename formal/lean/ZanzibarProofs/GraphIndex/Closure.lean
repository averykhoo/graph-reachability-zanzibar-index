import Mathlib.Data.Finset.Basic
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Order.Interval.Finset.Nat
import Mathlib.Data.List.Chain
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Tactic.Ring

/-!
# T4 — path-counting closure maintenance

`SEMANTICS.md` §7.2, `theory.md:26-61`. The graph index stores, per ordered pair,
the number of distinct directed paths `p(u,v)`. In a DAG a path uses each edge at
most once, so inserting a direct edge `(u,v)` adds `p̂(a,u)·p̂(v,b)` paths to every
pair `(a,b)`, where `p̂(x,x)=1` (the empty path). This is theorem **T4**.

**Phase 4 (this file): `pathCount` is now CONCRETE** — weighted-walk counting over a
`Fintype V`, total (no acyclicity needed to define). `pathsOfLength k` counts walks
of exactly length `k` (first-edge decomposition); `pathCount` sums lengths `1..|V|`
(in a DAG every path has length < |V|, so this equals the true count), and `phat`
adds the empty path.

Proved here: the **boundary sum-identity** (`phat_boundary`) — the exact first-edge
recurrence *with* the length-`|V|` boundary term, by pure `Finset.sum` manipulation,
NO acyclicity. What remains for the full counting theorem is (a) the vanishing lemma
`Acyclic → pathsOfLength |V| = 0` (a DAG has no walk of length |V| — pigeonhole), which
turns `phat_boundary` into the clean recurrence, and (b) the algebraic expansion for
`pathCount_addEdge`. Both are isolated as the two remaining `sorry`s.
-/

namespace Zanzibar

/-- A finite directed multigraph given by a direct-edge multiplicity function. -/
structure DirectGraph (V : Type) where
  dcount : V → V → Nat

variable {V : Type} [DecidableEq V] [Fintype V]

/-- Insert one direct edge `(u,v)` (increment its multiplicity). -/
def DirectGraph.addEdge (g : DirectGraph V) (u v : V) : DirectGraph V :=
  ⟨fun a b => g.dcount a b + (if a = u ∧ b = v then 1 else 0)⟩

/-- Remove one direct edge `(u,v)` (decrement, saturating at 0). -/
def DirectGraph.removeEdge (g : DirectGraph V) (u v : V) : DirectGraph V :=
  ⟨fun a b => g.dcount a b - (if a = u ∧ b = v then 1 else 0)⟩

/-- Number of weighted walks of exactly length `k` from `u` to `v` (first-edge
    decomposition: a length-`k+1` walk is a first edge `u→w` times a length-`k`
    walk `w→v`). -/
def pathsOfLength (g : DirectGraph V) : Nat → V → V → Nat
  | 0, u, v => if u = v then 1 else 0
  | k + 1, u, v => ∑ w : V, g.dcount u w * pathsOfLength g k w v

@[simp] theorem pathsOfLength_zero (g : DirectGraph V) (u v : V) :
    pathsOfLength g 0 u v = (if u = v then 1 else 0) := rfl

theorem pathsOfLength_succ (g : DirectGraph V) (k : Nat) (u v : V) :
    pathsOfLength g (k + 1) u v = ∑ w : V, g.dcount u w * pathsOfLength g k w v := rfl

/-- `p(u,v)`: number of distinct directed paths of length ≥ 1 (walks of length `1..|V|`;
    equals the true path count on a DAG, where no path is longer than `|V|-1`). -/
def pathCount (g : DirectGraph V) (u v : V) : Nat :=
  ∑ k ∈ Finset.Ico 1 (Fintype.card V + 1), pathsOfLength g k u v

/-- `p̂(u,v)` — path count with the empty path at coincident endpoints
    (`theory.md:32`). -/
def phat (g : DirectGraph V) (u v : V) : Nat :=
  pathCount g u v + (if u = v then 1 else 0)

/-- Acyclicity: no positive-length path from a node to itself
    (`theory.md:57-61` — the counting theorem's precondition). -/
def Acyclic (g : DirectGraph V) : Prop := ∀ v, pathCount g v v = 0

/-- Sum-shift identity: `(∑_{k=1}^{M} f k) + f (M+1) = f 1 + ∑_{k=1}^{M} f (k+1)`
    (both equal `∑_{k=1}^{M+1} f k`). Pure `Nat` combinatorics, by induction. -/
private theorem sum_Ico_shift_boundary (f : Nat → Nat) (M : Nat) :
    (∑ k ∈ Finset.Ico 1 (M + 1), f k) + f (M + 1)
      = f 1 + ∑ k ∈ Finset.Ico 1 (M + 1), f (k + 1) := by
  induction M with
  | zero => simp
  | succ m ih =>
      rw [Finset.sum_Ico_succ_top (Nat.le_add_left 1 m),
          Finset.sum_Ico_succ_top (Nat.le_add_left 1 m)]
      omega

/-- **Boundary first-edge recurrence** (no acyclicity). Summing the first-edge
    decomposition over lengths, the length-`|V|` walks form the boundary term:
    `phat u v + ∑_w dcount u w · pathsOfLength |V| w v
       = [u=v] + ∑_w dcount u w · phat w v`.
    Under `Acyclic` the boundary term vanishes (no length-`|V|` walk in a DAG),
    yielding the clean recurrence `phat = [u=v] + ∑_w dcount·phat`. -/
theorem phat_boundary (g : DirectGraph V) (u v : V) :
    phat g u v + ∑ w : V, g.dcount u w * pathsOfLength g (Fintype.card V) w v
      = (if u = v then 1 else 0) + ∑ w : V, g.dcount u w * phat g w v := by
  have succ : ∀ k, (∑ w : V, g.dcount u w * pathsOfLength g k w v) = pathsOfLength g (k + 1) u v :=
    fun k => (pathsOfLength_succ g k u v).symm
  -- transform the RHS sum: split phat, evaluate the two pieces
  have e1 : (∑ w : V, g.dcount u w * pathCount g w v)
      = ∑ k ∈ Finset.Ico 1 (Fintype.card V + 1), pathsOfLength g (k + 1) u v := by
    simp only [pathCount, Finset.mul_sum]
    rw [Finset.sum_comm]
    exact Finset.sum_congr rfl (fun k _ => succ k)
  have e2 : (∑ w : V, g.dcount u w * (if w = v then 1 else 0)) = pathsOfLength g 1 u v := by
    have h := succ 0
    simp only [pathsOfLength_zero] at h
    exact h
  have rhs : (∑ w : V, g.dcount u w * phat g w v)
      = (∑ k ∈ Finset.Ico 1 (Fintype.card V + 1), pathsOfLength g (k + 1) u v)
        + pathsOfLength g 1 u v := by
    calc (∑ w : V, g.dcount u w * phat g w v)
        = (∑ w : V, g.dcount u w * pathCount g w v)
          + (∑ w : V, g.dcount u w * (if w = v then 1 else 0)) := by
            rw [← Finset.sum_add_distrib]
            exact Finset.sum_congr rfl (fun w _ => by unfold phat; exact Nat.left_distrib _ _ _)
      _ = _ := by rw [e1, e2]
  rw [succ (Fintype.card V), rhs]
  simp only [phat, pathCount]
  have hshift := sum_Ico_shift_boundary (fun k => pathsOfLength g k u v) (Fintype.card V)
  omega

/-- **First-edge recurrence** — PROVED from `phat_boundary`, taking the DAG
    "no length-`|V|` walk" property (`hvanish`) as an explicit hypothesis:
    `phat u v = [u=v] + ∑_w dcount u w · phat w v`.

    `hvanish` is exactly the remaining combinatorial obligation (`Acyclic g →
    hvanish`, a pigeonhole: a length-`|V|` walk repeats a vertex ⇒ closed sub-walk ⇒
    positive `pathCount x x` ⇒ ¬Acyclic). Stated as a hypothesis rather than a
    separate `sorry` so this recurrence is a complete proof and the count stays on
    the two genuine T4 obligations (`pathCount_addEdge/removeEdge`). See ROADMAP. -/
theorem phat_recurrence (g : DirectGraph V) (u v : V)
    (hvanish : ∀ w : V, pathsOfLength g (Fintype.card V) w v = 0) :
    phat g u v = (if u = v then 1 else 0) + ∑ w : V, g.dcount u w * phat g w v := by
  have hb := phat_boundary g u v
  have hzero : ∑ w : V, g.dcount u w * pathsOfLength g (Fintype.card V) w v = 0 := by
    apply Finset.sum_eq_zero
    intro w _
    rw [hvanish w, Nat.mul_zero]
  rw [hzero, Nat.add_zero] at hb
  exact hb

/-! ### Walk API — bridging `pathsOfLength` positivity to concrete vertex lists

To discharge `hvanish` (`Acyclic → pathsOfLength |V| = 0`) we need the combinatorial
content: a positive-weight length-`k` walk is a vertex list `l` of length `k+1` whose
consecutive pairs are positive edges (`IsChain` over `edgeRel`). Then pigeonhole on a
length-`|V|` walk (which has `|V|+1` vertices) gives a repeated vertex, hence a closed
sub-walk, hence `pathCount x x > 0`, contradicting acyclicity. -/

/-- The positive-edge relation of `g`: `a → b` present iff its multiplicity is nonzero. -/
def edgeRel (g : DirectGraph V) (a b : V) : Prop := 0 < g.dcount a b

/-- **Walk correspondence.** `pathsOfLength g k u v` is positive exactly when there is a
    vertex list of length `k+1` from `u` to `v` all of whose steps are positive edges. -/
theorem pathsOfLength_pos_iff (g : DirectGraph V) :
    ∀ (k : Nat) (u v : V), 0 < pathsOfLength g k u v ↔
      ∃ l : List V, l.length = k + 1 ∧ l.head? = some u ∧ l.getLast? = some v
        ∧ List.IsChain (edgeRel g) l := by
  intro k
  induction k with
  | zero =>
      intro u v
      simp only [pathsOfLength_zero]
      constructor
      · intro h
        have huv : u = v := by by_contra hne; simp [hne] at h
        exact ⟨[u], rfl, rfl, by simp [huv], List.IsChain.singleton u⟩
      · rintro ⟨l, hlen, hhd, hlast, _⟩
        match l, hlen, hhd, hlast with
        | [x], _, hhd, hlast =>
            simp only [List.head?_cons, Option.some.injEq] at hhd
            simp only [List.getLast?_singleton, Option.some.injEq] at hlast
            subst hhd; subst hlast; simp
  | succ k ih =>
      intro u v
      rw [pathsOfLength_succ]
      constructor
      · intro h
        -- some term of the sum is positive
        have : ∃ w : V, 0 < g.dcount u w * pathsOfLength g k w v := by
          by_contra hc
          simp only [not_exists, Nat.pos_iff_ne_zero, not_not] at hc
          have : ∑ w : V, g.dcount u w * pathsOfLength g k w v = 0 :=
            Finset.sum_eq_zero (fun w _ => hc w)
          omega
        obtain ⟨w, hw⟩ := this
        have hpos := (mul_ne_zero_iff.mp (Nat.pos_iff_ne_zero.mp hw))
        have huw : edgeRel g u w := Nat.pos_of_ne_zero hpos.1
        have hwv : 0 < pathsOfLength g k w v := Nat.pos_of_ne_zero hpos.2
        obtain ⟨l', hlen', hhd', hlast', hchain'⟩ := (ih w v).mp hwv
        have hne' : l' ≠ [] := by intro h; rw [h] at hlen'; simp at hlen'
        refine ⟨u :: l', by simp [hlen'], rfl, ?_, ?_⟩
        · rw [List.getLast?_cons_of_ne_nil hne']; exact hlast'
        · refine hchain'.cons ?_
          intro y hy; rw [hhd'] at hy; simp only [Option.mem_def, Option.some.injEq] at hy
          subst hy; exact huw
      · rintro ⟨l, hlen, hhd, hlast, hchain⟩
        match l, hlen, hhd, hlast, hchain with
        | u' :: l', hlen, hhd, hlast, hchain =>
            simp only [List.head?_cons, Option.some.injEq] at hhd
            subst hhd
            have hne' : l' ≠ [] := by
              intro h; rw [h] at hlen; simp at hlen
            obtain ⟨w, hw⟩ : ∃ w, l'.head? = some w := by
              cases l' with
              | nil => exact absurd rfl hne'
              | cons x xs => exact ⟨x, rfl⟩
            have huw : edgeRel g u' w := hchain.rel_head? hw
            have hchain' : List.IsChain (edgeRel g) l' := hchain.tail
            have hlast' : l'.getLast? = some v := by
              rwa [List.getLast?_cons_of_ne_nil hne'] at hlast
            have hlen' : l'.length = k + 1 := by simpa using hlen
            have hwv : 0 < pathsOfLength g k w v := (ih w v).mpr ⟨l', hlen', hw, hlast', hchain'⟩
            have hterm : 0 < g.dcount u' w * pathsOfLength g k w v := Nat.mul_pos huw hwv
            rcases Nat.eq_zero_or_pos (∑ w' : V, g.dcount u' w' * pathsOfLength g k w' v) with hz | hp
            · exfalso
              rw [Finset.sum_eq_zero_iff] at hz
              have := hz w (Finset.mem_univ w); omega
            · exact hp

/-- **Pigeonhole vanishing lemma.** In an acyclic graph there is no walk of length
    `|V|`: such a walk has `|V|+1` vertices, so two coincide (pigeonhole), giving a
    closed sub-walk `x → x` of length `1..|V|`, i.e. `pathCount x x > 0` — contradicting
    `Acyclic`. This discharges the `hvanish` hypothesis of `phat_recurrence`. -/
theorem pathsOfLength_card_vanish (g : DirectGraph V) (hAcyc : Acyclic g) :
    ∀ w v : V, pathsOfLength g (Fintype.card V) w v = 0 := by
  intro w v
  by_contra hne
  have hpos : 0 < pathsOfLength g (Fintype.card V) w v := Nat.pos_of_ne_zero hne
  obtain ⟨l, hlen, _hhd, _hlast, hchain⟩ :=
    (pathsOfLength_pos_iff g (Fintype.card V) w v).mp hpos
  -- l has |V|+1 vertices ⇒ it is not Nodup
  have hnd : ¬ l.Nodup := by
    intro hnd; have := hnd.length_le_card; omega
  rw [List.nodup_iff_pairwise_ne, List.pairwise_iff_getElem] at hnd
  push_neg at hnd
  obtain ⟨i, j, hi, hj, hij, heq⟩ := hnd
  -- the closed sub-walk (l.drop i).take (k+1): a walk l[i] → l[i] of length k = j - i
  set k := j - i with hk
  have hk1 : 1 ≤ k := by omega
  have hkN : k ≤ Fintype.card V := by omega
  have hlent : ((l.drop i).take (k + 1)).length = k + 1 := by
    rw [List.length_take, List.length_drop, hlen]; omega
  have hschain : List.IsChain (edgeRel g) ((l.drop i).take (k + 1)) :=
    (hchain.drop i).take (k + 1)
  have hshead : ((l.drop i).take (k + 1)).head? = some (l[i]) := by
    rw [List.head?_eq_getElem?, List.getElem?_take_of_lt (by omega), List.getElem?_drop,
        Nat.add_zero, List.getElem?_eq_getElem hi]
  have hslast : ((l.drop i).take (k + 1)).getLast? = some (l[i]) := by
    rw [List.getLast?_eq_getElem?, hlent, Nat.add_sub_cancel, List.getElem?_take_of_succ,
        List.getElem?_drop, show i + k = j by omega, List.getElem?_eq_getElem hj]
    exact congrArg some heq.symm
  -- so there is a positive closed walk l[i] → l[i] of length k, hence pathCount > 0
  have hclosed : 0 < pathsOfLength g k (l[i]) (l[i]) :=
    (pathsOfLength_pos_iff g k (l[i]) (l[i])).mpr
      ⟨(l.drop i).take (k + 1), hlent, hshead, hslast, hschain⟩
  have hac := hAcyc (l[i])
  rw [pathCount, Finset.sum_eq_zero_iff] at hac
  have := hac k (by rw [Finset.mem_Ico]; omega)
  omega

/-! ### Algebraic ingredients for the counting theorem -/

/-- Monotonicity of walk counts in the edge multiplicities. -/
theorem pathsOfLength_mono {g₁ g₂ : DirectGraph V}
    (h : ∀ a b, g₁.dcount a b ≤ g₂.dcount a b) :
    ∀ (k : Nat) (u v : V), pathsOfLength g₁ k u v ≤ pathsOfLength g₂ k u v := by
  intro k
  induction k with
  | zero => intro u v; simp
  | succ k ih =>
      intro u v
      simp only [pathsOfLength_succ]
      exact Finset.sum_le_sum (fun w _ => Nat.mul_le_mul (h u w) (ih w v))

/-- **Last-edge decomposition** (dual to `pathsOfLength_succ`): a length-`k+1` walk is a
    length-`k` walk `u → w` followed by a final edge `w → v`. -/
theorem pathsOfLength_succ_last (g : DirectGraph V) :
    ∀ (k : Nat) (u v : V),
      pathsOfLength g (k + 1) u v = ∑ w : V, pathsOfLength g k u w * g.dcount w v := by
  intro k
  induction k with
  | zero =>
      intro u v
      simp only [pathsOfLength_succ, pathsOfLength_zero, mul_ite, mul_one, mul_zero,
        ite_mul, one_mul, zero_mul, Finset.sum_ite_eq, Finset.sum_ite_eq', Finset.mem_univ, if_true]
  | succ k ih =>
      intro u v
      rw [pathsOfLength_succ]
      calc ∑ a : V, g.dcount u a * pathsOfLength g (k + 1) a v
          = ∑ a : V, ∑ w : V, g.dcount u a * (pathsOfLength g k a w * g.dcount w v) := by
            refine Finset.sum_congr rfl (fun a _ => ?_)
            rw [ih a v, Finset.mul_sum]
        _ = ∑ w : V, ∑ a : V, g.dcount u a * (pathsOfLength g k a w * g.dcount w v) :=
            Finset.sum_comm
        _ = ∑ w : V, pathsOfLength g (k + 1) u w * g.dcount w v := by
            refine Finset.sum_congr rfl (fun w _ => ?_)
            rw [pathsOfLength_succ, Finset.sum_mul]
            refine Finset.sum_congr rfl (fun a _ => ?_)
            ring

/-- The edge multiplicity only grows under `addEdge`. -/
theorem addEdge_dcount_ge (g : DirectGraph V) (u v a b : V) :
    g.dcount a b ≤ (g.addEdge u v).dcount a b := by
  simp only [DirectGraph.addEdge]; omega

/-- **L1.** Acyclicity is inherited by subgraphs: if `addEdge u v` is acyclic so is `g`. -/
theorem acyclic_of_addEdge (g : DirectGraph V) (u v : V)
    (h : Acyclic (g.addEdge u v)) : Acyclic g := by
  intro x
  have := pathsOfLength_mono (addEdge_dcount_ge g u v)
  have hle : pathCount g x x ≤ pathCount (g.addEdge u v) x x :=
    Finset.sum_le_sum (fun k _ => this k x x)
  have := h x; omega

/-- **Closed form of the affine recurrence.** Any `X` solving `X a = c a + ∑_w dcount a w · X w`
    in an acyclic graph equals the finite matrix series `∑_{m<|V|} ∑_w pathsOfLength m a w · c w`.
    The `X`-dependent tail of the `n`-step unrolling vanishes at `n = |V|`
    (`pathsOfLength_card_vanish`), leaving only the `c`-terms. -/
theorem rec_closed_form (g : DirectGraph V) (hAcyc : Acyclic g) (c X : V → Nat)
    (hX : ∀ a, X a = c a + ∑ w : V, g.dcount a w * X w) :
    ∀ a, X a = ∑ m ∈ Finset.range (Fintype.card V), ∑ w : V, pathsOfLength g m a w * c w := by
  have unroll : ∀ n a, X a = (∑ m ∈ Finset.range n, ∑ w : V, pathsOfLength g m a w * c w)
      + ∑ w : V, pathsOfLength g n a w * X w := by
    intro n
    induction n with
    | zero =>
        intro a
        simp only [Finset.range_zero, Finset.sum_empty, pathsOfLength_zero, ite_mul, one_mul,
          zero_mul, Finset.sum_ite_eq, Finset.mem_univ, if_true, zero_add]
    | succ n ih =>
        intro a
        have key : (∑ w : V, pathsOfLength g n a w * X w)
            = (∑ w : V, pathsOfLength g n a w * c w)
              + ∑ w : V, pathsOfLength g (n + 1) a w * X w := by
          have e1 : ∀ w, pathsOfLength g n a w * X w
              = pathsOfLength g n a w * c w
                + pathsOfLength g n a w * (∑ x : V, g.dcount w x * X x) := by
            intro w; rw [hX w]; ring
          rw [Finset.sum_congr rfl (fun w _ => e1 w), Finset.sum_add_distrib]
          congr 1
          rw [Finset.sum_congr rfl (fun w _ => Finset.mul_sum _ _ _), Finset.sum_comm]
          refine Finset.sum_congr rfl (fun x _ => ?_)
          rw [pathsOfLength_succ_last, Finset.sum_mul]
          refine Finset.sum_congr rfl (fun w _ => ?_)
          ring
        rw [ih a, Finset.sum_range_succ, key]; ring
  intro a
  rw [unroll (Fintype.card V) a]
  have : (∑ w : V, pathsOfLength g (Fintype.card V) a w * X w) = 0 := by
    apply Finset.sum_eq_zero
    intro w _; rw [pathsOfLength_card_vanish g hAcyc a w]; ring
  rw [this, add_zero]

/-- **Recurrence uniqueness.** Two solutions of the same affine recurrence in an acyclic
    graph coincide (both equal the closed form). -/
theorem rec_unique (g : DirectGraph V) (hAcyc : Acyclic g) (c X Y : V → Nat)
    (hX : ∀ a, X a = c a + ∑ w : V, g.dcount a w * X w)
    (hY : ∀ a, Y a = c a + ∑ w : V, g.dcount a w * Y w) :
    ∀ a, X a = Y a := by
  intro a
  rw [rec_closed_form g hAcyc c X hX a, rec_closed_form g hAcyc c Y hY a]

/-- The `addEdge u v` multiplicity of `(u,v)` is one more than in `g`. -/
theorem addEdge_dcount_self (g : DirectGraph V) (u v : V) :
    (g.addEdge u v).dcount u v = g.dcount u v + 1 := by simp [DirectGraph.addEdge]

/-- **L2 — the new edge cannot close a cycle.** If `addEdge u v` is acyclic then `g` has no
    path (not even the empty one) `v → u`; otherwise composing it with the new edge `u → v`
    would give a positive closed walk `u → u` in `g'`, contradicting acyclicity. -/
theorem no_back_path (g : DirectGraph V) (u v : V)
    (hAcyc' : Acyclic (g.addEdge u v)) : phat g v u = 0 := by
  have hAcyc : Acyclic g := acyclic_of_addEdge g u v hAcyc'
  by_contra hne
  have hpos : 0 < phat g v u := Nat.pos_of_ne_zero hne
  rcases eq_or_ne v u with hvu | hvu
  · -- v = u: the new edge is a self-loop, an immediate cycle
    subst hvu
    have hstep : 0 < pathsOfLength (g.addEdge v v) 1 v v := by
      rw [pathsOfLength_succ]
      have hterm : 0 < (g.addEdge v v).dcount v v * pathsOfLength (g.addEdge v v) 0 v v := by
        refine Nat.mul_pos ?_ ?_
        · rw [addEdge_dcount_self]; omega
        · simp
      rcases Nat.eq_zero_or_pos
          (∑ w : V, (g.addEdge v v).dcount v w * pathsOfLength (g.addEdge v v) 0 w v) with hz | hp
      · exfalso; rw [Finset.sum_eq_zero_iff] at hz; have := hz v (Finset.mem_univ v); omega
      · exact hp
    have hcard : 1 ≤ Fintype.card V := Fintype.card_pos_iff.mpr ⟨v⟩
    have hac := hAcyc' v
    rw [pathCount, Finset.sum_eq_zero_iff] at hac
    have := hac 1 (by rw [Finset.mem_Ico]; omega); omega
  · -- v ≠ u: extract a positive walk v → u of length m ∈ [1, |V|-1]
    have hpc : 0 < pathCount g v u := by
      have : phat g v u = pathCount g v u := by simp [phat, hvu]
      omega
    rw [pathCount] at hpc
    obtain ⟨m, hm, hmne0⟩ :=
      Finset.exists_ne_zero_of_sum_ne_zero (Nat.pos_iff_ne_zero.mp hpc)
    rw [Finset.mem_Ico] at hm
    have hmpos : 0 < pathsOfLength g m v u := Nat.pos_of_ne_zero hmne0
    have hmne : m ≠ Fintype.card V := by
      intro h; rw [h, pathsOfLength_card_vanish g hAcyc] at hmpos; omega
    have hstep : 0 < pathsOfLength (g.addEdge u v) (m + 1) u u := by
      rw [pathsOfLength_succ]
      have hterm : 0 < (g.addEdge u v).dcount u v * pathsOfLength (g.addEdge u v) m v u := by
        refine Nat.mul_pos ?_ ?_
        · rw [addEdge_dcount_self]; omega
        · exact lt_of_lt_of_le hmpos (pathsOfLength_mono (addEdge_dcount_ge g u v) m v u)
      rcases Nat.eq_zero_or_pos
          (∑ w : V, (g.addEdge u v).dcount u w * pathsOfLength (g.addEdge u v) m w u) with hz | hp
      · exfalso; rw [Finset.sum_eq_zero_iff] at hz; have := hz v (Finset.mem_univ v); omega
      · exact hp
    have hac := hAcyc' u
    rw [pathCount, Finset.sum_eq_zero_iff] at hac
    have := hac (m + 1) (by rw [Finset.mem_Ico]; omega); omega

/-- **T4 (insert).** In a DAG, inserting `(u,v)` updates every pair by the
    path-count product (`theory.md:35`). Follows by algebraic expansion of
    `phat_recurrence` on the edge-augmented graph. -/
theorem pathCount_addEdge (g : DirectGraph V) (u v : V)
    (hdag : Acyclic (g.addEdge u v)) (a b : V) :
    pathCount (g.addEdge u v) a b = pathCount g a b + phat g a u * phat g v b := by
  have hAcyc : Acyclic g := acyclic_of_addEdge g u v hdag
  have hL2 : phat g v u = 0 := no_back_path g u v hdag
  have hvanG : ∀ w y, pathsOfLength g (Fintype.card V) w y = 0 := pathsOfLength_card_vanish g hAcyc
  -- `phat g'` and the target formula both solve g''s affine recurrence (c a = [a=b]);
  -- by uniqueness they coincide.
  have hX : ∀ a', phat (g.addEdge u v) a' b = (if a' = b then 1 else 0)
      + ∑ w : V, (g.addEdge u v).dcount a' w * phat (g.addEdge u v) w b :=
    fun a' => phat_recurrence (g.addEdge u v) a' b
      (fun w => pathsOfLength_card_vanish (g.addEdge u v) hdag w b)
  have hY : ∀ a', phat g a' b + phat g a' u * phat g v b = (if a' = b then 1 else 0)
      + ∑ w : V, (g.addEdge u v).dcount a' w
          * (phat g w b + phat g w u * phat g v b) := by
    intro a'
    have recb := phat_recurrence g a' b (fun w => hvanG w b)
    have recu := phat_recurrence g a' u (fun w => hvanG w u)
    -- split the g'-sum: g-part + new-edge indicator term
    have hsplit : ∀ w : V, (g.addEdge u v).dcount a' w * (phat g w b + phat g w u * phat g v b)
        = g.dcount a' w * (phat g w b + phat g w u * phat g v b)
          + (if a' = u ∧ w = v then (phat g w b + phat g w u * phat g v b) else 0) := by
      intro w; simp only [DirectGraph.addEdge]; split_ifs <;> ring
    rw [Finset.sum_congr rfl (fun w _ => hsplit w), Finset.sum_add_distrib]
    have hind : (∑ w : V, if a' = u ∧ w = v then (phat g w b + phat g w u * phat g v b) else 0)
        = if a' = u then (phat g v b + phat g v u * phat g v b) else 0 := by
      by_cases hau : a' = u
      · subst hau; simp [Finset.sum_ite_eq']
      · simp [hau]
    rw [hind]
    have hgsum : ∑ w : V, g.dcount a' w * (phat g w b + phat g w u * phat g v b)
        = (∑ w : V, g.dcount a' w * phat g w b)
          + (∑ w : V, g.dcount a' w * phat g w u) * phat g v b := by
      rw [Finset.sum_mul, ← Finset.sum_add_distrib]
      exact Finset.sum_congr rfl (fun w _ => by ring)
    rw [hgsum, recb, recu, hL2]
    split_ifs <;> ring
  have main : phat (g.addEdge u v) a b = phat g a b + phat g a u * phat g v b :=
    rec_unique (g.addEdge u v) hdag (fun a' => if a' = b then 1 else 0)
      (fun a' => phat (g.addEdge u v) a' b)
      (fun a' => phat g a' b + phat g a' u * phat g v b) hX hY a
  have lhs : phat (g.addEdge u v) a b = pathCount (g.addEdge u v) a b + (if a = b then 1 else 0) :=
    rfl
  have rhs : phat g a b = pathCount g a b + (if a = b then 1 else 0) := rfl
  rw [lhs, rhs] at main
  omega

/-- **T4 (delete).** Deletion is the exact inverse of insertion: since re-inserting the
    removed edge reconstructs `g` (`(g.removeEdge u v).addEdge u v = g` when the edge is
    present), the delete identity is `pathCount_addEdge` applied to `g.removeEdge u v`. -/
theorem pathCount_removeEdge (g : DirectGraph V) (u v : V)
    (hdag : Acyclic g) (hpos : 0 < g.dcount u v) (a b : V) :
    pathCount g a b
      = pathCount (g.removeEdge u v) a b + phat (g.removeEdge u v) a u * phat (g.removeEdge u v) v b := by
  have heq : (g.removeEdge u v).addEdge u v = g := by
    cases g with
    | mk d =>
      simp only [DirectGraph.addEdge, DirectGraph.removeEdge, DirectGraph.mk.injEq]
      funext a' b'
      split_ifs with h
      · obtain ⟨ha, hb⟩ := h; rw [ha, hb]
        have h1 : 0 < d u v := hpos; omega
      · omega
  have key := pathCount_addEdge (g.removeEdge u v) u v (by rw [heq]; exact hdag) a b
  rw [heq] at key
  exact key

end Zanzibar
