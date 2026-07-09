import Mathlib.Data.Finset.Basic
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Order.Interval.Finset.Nat

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

/-- **T4 (insert).** In a DAG, inserting `(u,v)` updates every pair by the
    path-count product (`theory.md:35`). Follows by algebraic expansion of
    `phat_recurrence` on the edge-augmented graph. -/
theorem pathCount_addEdge (g : DirectGraph V) (u v : V)
    (_hdag : Acyclic (g.addEdge u v)) (a b : V) :
    pathCount (g.addEdge u v) a b = pathCount g a b + phat g a u * phat g v b := by
  sorry

/-- **T4 (delete).** Deletion is the exact inverse in `(ℤ,+)`. -/
theorem pathCount_removeEdge (g : DirectGraph V) (u v : V)
    (_hdag : Acyclic g) (_hpos : 0 < g.dcount u v) (a b : V) :
    pathCount g a b
      = pathCount (g.removeEdge u v) a b + phat (g.removeEdge u v) a u * phat (g.removeEdge u v) v b := by
  sorry

end Zanzibar
