import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.Spec.WellDef

/-!
# T2 / T5 — the graph index computes `sem`, and its cascade converges

`SEMANTICS.md` §8 (T2a, T2b, T5). Phase 4.

**Status (concretize + partial pass).** The graph model is now concrete
(`State.lean`): `GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`,
`GraphAccepts` are real definitions, not `opaque` placeholders. Off the concrete
`ReachedBy` (which bakes the in-transaction cascade into each write, §7.8 / A1):

* **`cascade_converges` (T5) is CLOSED** — outbox-drain quiescence is a `WriteStep`
  postcondition, so it holds at every reachable state by induction.
* **`graph_reached_inv` (T2a)**: its `Quiescent` conjunct is closed the same way; the
  `Inv` conjunct stays a tracked `sorry` (it needs the full operational write path —
  edge/bridge/reconcile — to be realized, the deferred T2a content).
* **`graph_correct` (T2b)** stays a tracked `sorry` — the read = `sem` completeness
  argument (≤4-probe reachability decomposition + residue algebra), resting on T4
  (edges = path counts) and the T1 MemberSet lemmas.
-/

namespace Zanzibar

/-- **T5 (cascade convergence).** Every reachable state is cascade-quiescent: the
    in-transaction cascade drains the outbox on every write, so the drain frontier
    covers all deltas at any state reached from empty. Each `but not` operand settles
    before any consumer reads it (encoded by `Quiescent` + the stratum order). -/
theorem cascade_converges (S : Schema) (T : Store) (σ : GraphState)
    (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S) (hReach : ReachedBy σ S T) :
    Quiescent σ := by
  induction hReach with
  | empty S => exact quiescent_empty S
  | step t _hprev hstep _ih => exact hstep.drained

/-- **T2a (invariant preservation).** Every reachable graph state satisfies the
    I-series invariant and is cascade-quiescent (materialization = recompute from
    scratch). The `Quiescent` conjunct is `cascade_converges`; the `Inv` conjunct
    still needs the concrete write path (edge/bridge/reconcile maintenance) that
    `WriteStep` abstracts — tracked `sorry`. -/
theorem graph_reached_inv (S : Schema) (T : Store) (σ : GraphState)
    (_hWF : WF S) (hStrat : Stratifiable S) (hAcc : GraphAccepts S)
    (hReach : ReachedBy σ S T) :
    Inv S σ ∧ Quiescent σ := by
  refine ⟨?_, cascade_converges S T σ hStrat hAcc hReach⟩
  sorry

/-! ## T2b base case — the empty store / empty state

The `ReachedBy.empty` case of `graph_correct`, discharged end-to-end and axiom-clean.
Both sides are constantly `false`: the empty store grants nothing (`sem_empty_store`),
and the empty index reaches nothing / persists no residue (`check_empty`). This is
the genuine base of the eventual `graph_correct` induction — no `sorry`. -/

/-- On the empty store every `Direct`/`TTU` leaf is empty and `computed` recurses into
    a uniformly-`false` `rec`, so structural evaluation of any expression is `false`. -/
theorem evalE_empty_store {rec : Rec} {subject : SubjectRef} {q : Query}
    {otype oname rel : String} (hrec : ∀ ot nm r, rec ot nm r = false) :
    ∀ e : Expr, evalE rec subject [] q otype oname rel e = false := by
  intro e
  induction e with
  | union a b iha ihb => simp [evalE, iha, ihb]
  | inter a b iha ihb => simp [evalE, iha, ihb]
  | excl a b iha _ => simp [evalE, iha]
  | computed r => simpa [evalE] using hrec otype oname r
  | direct rs => simp [evalE, directLeaf, grantsOf, memberOfGranted]
  | ttu tr ts => simp [evalE, ttuLeaf]

/-- The fuel-bounded evaluator is constantly `false` on the empty store, at every
    fuel and state (induction on fuel, feeding the fuel-IH as the `rec` to
    `evalE_empty_store`). -/
theorem semAux_empty_store (S : Schema) (subject : SubjectRef) (q : Query) :
    ∀ (fuel : Nat) (ot nm r : String), semAux S subject [] q fuel ot nm r = false := by
  intro fuel
  induction fuel with
  | zero => intro ot nm r; rfl
  | succ f ih =>
    intro ot nm r
    simp only [semAux, step]
    cases hlk : S.lookup (ot, r) with
    | none => rfl
    | some e => exact evalE_empty_store ih e

/-- **`sem` on the empty store is `false`.** Nothing is granted, so no query holds. -/
theorem sem_empty_store (S : Schema) (q : Query) : sem S [] q = false := by
  unfold sem
  exact semAux_empty_store S q.subject q _ _ _ _

/-- The non-derived read is `false` on the empty index: every reachability probe
    misses (`reach_empty`). -/
theorem probeNonDerived_empty (S : Schema) (q : Query) :
    GraphModel.probeNonDerived (emptyState S) q = false := by
  unfold GraphModel.probeNonDerived
  simp [reach_empty]

/-- The derived read is `false` on the empty index: no persisted residue (so `stars`
    covers nothing) and no reachable derived edge. -/
theorem probeDerived_empty (S : Schema) (q : Query) :
    GraphModel.probeDerived (emptyState S) q = false := by
  have hres : ∀ oN R, (emptyState S).residue oN R = none := fun _ _ => rfl
  unfold GraphModel.probeDerived
  simp only [hres, Option.getD_none, Residue.empty, List.contains_nil, reach_empty,
    Bool.false_and, Bool.or_false]
  split <;> simp

/-- The empty index answers `false` to every query (both read paths). -/
theorem check_empty (S : Schema) (q : Query) :
    GraphModel.check (emptyState S) q = false := by
  unfold GraphModel.check
  split
  · exact probeDerived_empty S q
  · exact probeNonDerived_empty S q

/-- **T2b, base case.** On the empty index / empty store the graph read matches the
    specification (`ReachedBy.empty`): both are constantly `false`. -/
theorem graph_correct_empty (S : Schema) (q : Query) :
    GraphModel.check (emptyState S) q = sem S [] q := by
  rw [check_empty, sem_empty_store]

/-- **T2b (read correctness).** On any invariant-satisfying reachable state the
    graph read answers exactly the specification. Tracked `sorry`: the completeness
    argument (every semantic path decomposes as leading-hop · materialized-closure ·
    trailing-hop for the ≤4 probes; the residue fold reproduces the star×boolean
    table) resting on T4 + the T1 MemberSet lemmas. The `ReachedBy.empty` base case
    is `graph_correct_empty` above. -/
theorem graph_correct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S)
    (_hInv : Inv S σ) (_hReach : ReachedBy σ S T) :
    GraphModel.check σ q = sem S T q := by
  sorry

end Zanzibar
