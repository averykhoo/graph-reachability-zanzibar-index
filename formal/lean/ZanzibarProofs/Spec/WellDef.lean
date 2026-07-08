import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify

/-!
# T0 — well-definedness of the spec

`SEMANTICS.md` §8, rows T0a/T0b.

- **T0a** (`sem_fuel_stable`): the fuel-bounded evaluator is stable above
  `fuelBound`. This file now PROVES it from a single step lemma
  (`semAux_fuel_stable_step`, the pigeonhole argument) — the reduction is a clean
  induction, so only the pigeonhole core remains `sorry`.
- **T0b** (`stratify_none_iff_cycle`, `stratify_topological`): `stratify` computes a
  topological layering exactly when there is no derived-dependency cycle.

Design note (adopting a Gemini review suggestion, corrected): isolating the
graph-theory / pigeonhole cores as their own lemmas keeps the `sem`-evaluation
reduction provable now and the hard combinatorics separately dischargeable.
-/

namespace Zanzibar

/-- Transitive reachability along a finite edge list (nonempty paths). -/
inductive Reaches (edges : List (Key × Key)) : Key → Key → Prop
  | step {a b} : (a, b) ∈ edges → Reaches edges a b
  | trans {a b c} : Reaches edges a b → Reaches edges b c → Reaches edges a c

/-- A derived-dependency cycle exists. -/
def HasDerivedCycle (S : Schema) : Prop := ∃ k, Reaches (depEdges S) k k

/-! ### T0a — fuel stability -/

/-- **The pigeonhole core.** At or above `fuelBound`, one more unit of fuel does not
    change the answer: the evaluation's distinct `(otype, oname, rel)` states number
    at most `fuelBound`, so any acyclic recursion has already bottomed out and the
    extra level is never reached (for a stratifiable schema, where the only
    recursion the fuel could still cut is acyclic). Discharged in a later pass. -/
theorem semAux_fuel_stable_step (S : Schema) (T : Store) (q : Query)
    (_hStrat : Stratifiable S) :
    ∀ f, fuelBound S T ≤ f →
      semAux S q.subject T q f q.object.type q.object.name q.relation
        = semAux S q.subject T q (f + 1) q.object.type q.object.name q.relation := by
  sorry

/-- **T0a.** `sem` is well-defined: fuel above the bound does not change the answer.
    PROVED from `semAux_fuel_stable_step` by induction from the bound. -/
theorem sem_fuel_stable (S : Schema) (T : Store) (q : Query)
    (hStrat : Stratifiable S) :
    ∀ f, fuelBound S T ≤ f →
      semAux S q.subject T q f q.object.type q.object.name q.relation = sem S T q := by
  intro f hf
  induction f, hf using Nat.le_induction with
  | base => rfl
  | succ n hn ih =>
      rw [← semAux_fuel_stable_step S T q hStrat n hn]; exact ih

/-! ### T0b — stratification soundness -/

/-- **T0b (part 1).** `stratify` fails exactly on a derived-dependency cycle (Kahn's
    ready-node filter peels every node iff there is no SCC). Discharged in a later
    pass. -/
theorem stratify_none_iff_cycle (S : Schema) :
    stratify S = none ↔ HasDerivedCycle S := by
  sorry

/-- **T0b (part 2).** When it succeeds, every dependency edge points to an
    earlier-or-equal layer (topological). Discharged in a later pass. -/
theorem stratify_topological (S : Schema) (L : List (List Key)) (_h : stratify S = some L) :
    (∀ e ∈ depEdges S, ∀ i j, e.1 ∈ L.getD i [] → e.2 ∈ L.getD j [] → j ≤ i) := by
  sorry

end Zanzibar
