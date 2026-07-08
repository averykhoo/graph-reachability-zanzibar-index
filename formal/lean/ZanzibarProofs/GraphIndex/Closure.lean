import Mathlib.Data.Finset.Basic

/-!
# T4 — path-counting closure maintenance

`SEMANTICS.md` §7.2, `theory.md:26-61`. The graph index stores, per ordered pair,
the number of distinct directed paths `p(u,v)`. In a DAG a path uses each edge at
most once, so inserting a direct edge `(u,v)` adds `p̂(a,u)·p̂(v,b)` paths to every
pair `(a,b)`, where `p̂(x,x)=1` (the empty path). This is theorem **T4** — the
basis of exact incremental maintenance (deletion is the exact inverse in `(ℤ,+)`).

Modeled abstractly over an id type `V`. `pathCount` is `opaque` for Phase 1 (its
concrete DAG definition + the counting proof are Phase 4).
-/

namespace Zanzibar

/-- A finite directed multigraph given by a direct-edge multiplicity function. -/
structure DirectGraph (V : Type) where
  dcount : V → V → Nat

variable {V : Type} [DecidableEq V]

/-- Insert one direct edge `(u,v)` (increment its multiplicity). -/
def DirectGraph.addEdge (g : DirectGraph V) (u v : V) : DirectGraph V :=
  ⟨fun a b => g.dcount a b + (if a = u ∧ b = v then 1 else 0)⟩

/-- Remove one direct edge `(u,v)` (decrement, saturating at 0). -/
def DirectGraph.removeEdge (g : DirectGraph V) (u v : V) : DirectGraph V :=
  ⟨fun a b => g.dcount a b - (if a = u ∧ b = v then 1 else 0)⟩

/-- `p(u,v)`: number of distinct directed paths of length ≥ 1 from `u` to `v`.
    Opaque for Phase 1; Phase 4 defines it (bounded DAG path enumeration over a
    `Fintype V`, total without needing acyclicity, equal to the true count on DAGs)
    and proves the counting theorems below.

    **Phase-4 proof strategy** (a corrected Gemini suggestion — as a *lemma* to be
    proved from the definition, NOT an axiom, so the C4 axiom audit stays clean):
    once defined, `pathCount` satisfies the first-edge recurrence
    `phat g u v = (if u = v then 1 else 0) + ∑ w, g.dcount u w * phat g w v`
    (paths grouped by their first hop). `pathCount_addEdge` then follows by
    algebraic expansion of this recurrence. Introducing the recurrence as an
    `axiom` about the *opaque* constant was rejected: it pollutes the axiom set and
    the plan's C4 gate forbids custom axioms. -/
opaque pathCount (g : DirectGraph V) (u v : V) : Nat

/-- `p̂(u,v)` — path count with the empty path at coincident endpoints
    (`theory.md:32`). -/
def phat (g : DirectGraph V) (u v : V) : Nat :=
  pathCount g u v + (if u = v then 1 else 0)

/-- Acyclicity: no positive-length path from a node to itself
    (`theory.md:57-61` — the counting theorem's precondition). -/
def Acyclic (g : DirectGraph V) : Prop := ∀ v, pathCount g v v = 0

/-- **T4 (insert).** In a DAG, inserting `(u,v)` updates every pair by the
    path-count product (`theory.md:35`). The DAG hypothesis on the *result* is
    what the code's reverse-reachability cycle pre-check enforces (§7.3). -/
theorem pathCount_addEdge (g : DirectGraph V) (u v : V)
    (_hdag : Acyclic (g.addEdge u v)) (a b : V) :
    pathCount (g.addEdge u v) a b = pathCount g a b + phat g a u * phat g v b := by
  sorry

/-- **T4 (delete).** Deletion is the exact inverse: removing `(u,v)` subtracts the
    same product computed over the graph *without* `(u,v)` (`theory.md:40-46` — the
    "remove direct edge first" ordering). -/
theorem pathCount_removeEdge (g : DirectGraph V) (u v : V)
    (_hdag : Acyclic g) (_hpos : 0 < g.dcount u v) (a b : V) :
    pathCount g a b
      = pathCount (g.removeEdge u v) a b + phat (g.removeEdge u v) a u * phat (g.removeEdge u v) v b := by
  sorry

end Zanzibar
