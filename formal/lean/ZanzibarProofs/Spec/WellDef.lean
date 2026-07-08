import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify

/-!
# T0 — well-definedness of the spec

`SEMANTICS.md` §8, rows T0a/T0b.

- **T0a** (`sem_fuel_stable`): the fuel-bounded evaluator is stable above
  `fuelBound` — running with more fuel than the bound gives the same answer, so
  `sem` is well-defined. (For a stratifiable schema the immediate-consequence
  iteration reaches its fixpoint by `fuelBound`; the non-monotone exclusion makes
  this a genuine theorem, not mere monotonicity — hence it rests on `Stratifiable`.)
- **T0b** (`stratify_sound`): `stratify` computes a topological layering exactly
  when there is no derived-dependency cycle.

Both are stated here; proofs are Phase-1 targets (currently `sorry`). See
PROOF_STATUS ledger.
-/

namespace Zanzibar

/-- Transitive reachability along a finite edge list (nonempty paths). -/
inductive Reaches (edges : List (Key × Key)) : Key → Key → Prop
  | step {a b} : (a, b) ∈ edges → Reaches edges a b
  | trans {a b c} : Reaches edges a b → Reaches edges b c → Reaches edges a c

/-- A derived-dependency cycle exists. -/
def HasDerivedCycle (S : Schema) : Prop := ∃ k, Reaches (depEdges S) k k

/-- **T0a.** `sem` is well-defined: fuel above the bound does not change the
    answer. Requires stratifiability (non-monotone exclusion). -/
theorem sem_fuel_stable (S : Schema) (T : Store) (q : Query)
    (_hStrat : Stratifiable S) :
    ∀ f, fuelBound S T ≤ f →
      semAux S q.subject T q f q.object.type q.object.name q.relation = sem S T q := by
  sorry

/-- **T0b (part 1).** `stratify` fails exactly on a derived-dependency cycle. -/
theorem stratify_none_iff_cycle (S : Schema) :
    stratify S = none ↔ HasDerivedCycle S := by
  sorry

/-- **T0b (part 2).** When it succeeds, the layers partition the derived keys and
    every dependency edge points to an earlier-or-equal layer (topological). -/
theorem stratify_topological (S : Schema) (L : List (List Key)) (_h : stratify S = some L) :
    (∀ e ∈ depEdges S, ∀ i j, e.1 ∈ L.getD i [] → e.2 ∈ L.getD j [] → j ≤ i) := by
  sorry

end Zanzibar
