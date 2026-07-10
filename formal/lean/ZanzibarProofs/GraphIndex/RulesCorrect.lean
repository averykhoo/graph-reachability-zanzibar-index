import ZanzibarProofs.GraphIndex.RulesWrite
import ZanzibarProofs.GraphIndex.State

/-!
# The untainted rule-routing read correspondence (ROADMAP W2, read half — IN PROGRESS)

`SEMANTICS.md` §7.5. The W2 write half (`RulesWrite.lean`) materializes a raw write's
rewrite-closure as ordinary direct edges. This file builds the read correspondence
`check = sem` on the **untainted** fragment (`computed`/`union`/`ttu`, no `and`/`but
not`). This increment lands the **read-routing** reduction: on an untainted schema no
key is derived, so `GraphModel.check` routes to `probeNonDerived` (pure reachability) —
the same read path W1's `graph_correct_*` theorems glue against.

The remaining, genuinely-new content — `TupleChain over the rewrite-closure ↔ sem over
the raw store` (the rewrite-closure realizing `evalE`'s computed/ttu/union recursion) —
is the deferred next increment (see PROOF_STATUS "W2 STARTED").
-/

namespace Zanzibar

/-! ## The untainted fragment predicate -/

/-- **`UntaintedSchema S`** — no definition uses a boolean operator (`and`/`but not`),
    i.e. every def is built from `direct`/`computed`/`ttu`/`union`. This is exactly the
    W2 scope: on it, taint never propagates, so every relation is read via the
    reachability probes (never the residue path). -/
def UntaintedSchema (S : Schema) : Prop := ∀ p ∈ S.defs, containsBool p.2 = false

/-! ## Taint collapses on the untainted fragment -/

/-- On an untainted schema, no key is base-tainted (whatever the lookup outcome). -/
theorem baseTaint_untainted {S : Schema} (h : UntaintedSchema S) (k : Key) :
    baseTaint S k = false := by
  unfold baseTaint Schema.lookup
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rfl
  | some p =>
    simp only [Option.map_some]
    exact h p (List.mem_of_find?_eq_some hf)

/-- One taint round from `∅` stays `∅`: nothing is base-tainted and nothing references
    a currently-tainted key (there are none). -/
theorem taintStep_nil_untainted {S : Schema} (h : UntaintedSchema S) :
    taintStep S [] = [] := by
  unfold taintStep
  have hp : ∀ k, (baseTaint S k ||
      (refsOf S k).any (fun r => ([] : List Key).contains r)) = false := by
    intro k
    rw [baseTaint_untainted h k]
    simp
  simp only [hp, List.filter_false]

/-- Iterating a `[]`-fixed function from `[]` stays `[]`. -/
theorem iterate_nil_fixed {α : Type} (f : List α → List α) (hf : f [] = []) :
    ∀ n, iterate f n [] = [] := by
  intro n
  induction n with
  | zero => rfl
  | succ m ih =>
    show iterate f m (f []) = []
    rw [hf]; exact ih

/-- **The tainted set is empty on the untainted fragment.** -/
theorem taintedKeys_untainted {S : Schema} (h : UntaintedSchema S) :
    taintedKeys S = [] := by
  unfold taintedKeys
  exact iterate_nil_fixed (taintStep S) (taintStep_nil_untainted h) _

/-- **No key is derived on the untainted fragment.** -/
theorem isDerived_untainted {S : Schema} (h : UntaintedSchema S) (k : Key) :
    isDerived S k = false := by
  unfold isDerived
  rw [taintedKeys_untainted h]
  rfl

/-! ## The read routes to `probeNonDerived` -/

/-- **On the untainted fragment the graph read is pure reachability.** Since no key is
    derived, `check` never takes the residue path — it reduces to the ≤4-probe
    `probeNonDerived`, the same read `graph_correct_direct`/`_bareStar`/`_objStar`/
    `_usStar` glue against. This is the routing half of the W2 correspondence. -/
theorem check_eq_probeNonDerived {σ : GraphState} {S : Schema}
    (hsc : σ.schema = S) (h : UntaintedSchema S) (q : Query) :
    GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
  unfold GraphModel.check
  rw [hsc, isDerived_untainted h]
  simp

end Zanzibar
