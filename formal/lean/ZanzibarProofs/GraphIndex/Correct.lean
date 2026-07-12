import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.Spec.WellDef

/-!
# T2 / T5 — the graph index computes `sem`, and its cascade converges

`SEMANTICS.md` §8 (T2a, T2b, T5). Phase 4.

**Restatement (2026-07-10).** The original statements here quantified over an
abstract `WriteStep`/`ReachedBy` closure whose three thin postconditions never
tied the graph state to the store — they admitted junk states, making
`graph_correct` and `graph_reached_inv` **false as stated** (and
`cascade_converges` true only by assertion). That layer was deleted; the false
statements were deleted WITH it, not proved. The T-theorems are now stated over
the **operational** write-closure at its current scope, and their scope widens
with the write model:

* **T2a (`graph_reached_inv_direct`)** and **T5 (`cascade_converges_direct`)** —
  below, over `ReachedByDirect` (the untainted direct fragment), proved by
  induction over the concrete write path.
* **T2b (`graph_correct_direct`)** — `DirectCorrect.lean`, over
  `ReachedByAdmitted` on the star-free pure-direct fragment, proved end-to-end.
* The full-`GraphAccepts`-scope statements return when the write model covers
  wildcard bridges, rule routing, and the derived reconcile (ROADMAP order).

The empty-store base case (`graph_correct_empty` and its supporting lemmas) is
scope-independent and lives here.
-/

namespace Zanzibar

/-- **T5 (cascade convergence), untainted-fragment scope.** Every state reached
    by the operational write path is cascade-quiescent. On this fragment writes
    produce no deltas, so the outbox is trivially drained. (Renamed from
    `cascade_converges` at cleanup: this is the W1 untainted-chain quiescence;
    the CONTENTFUL T5 — the scheduler draining a non-empty outbox — is
    `runCascade_no_abort`/`cascade_drains` (`Cascade.lean`) and
    `runCascade2_no_abort`/`cascade2_drains` (`CascadeStrata.lean`).) -/
theorem cascade_converges_direct {S : Schema} {T : Store} {σ : GraphState}
    (hReach : ReachedByDirect σ S T) : Quiescent σ :=
  (reachedByDirect_inv hReach).2.2

/-- **T2a (invariant preservation), untainted-fragment scope.** Every state
    reached by the operational write path satisfies the I-series invariant and
    is cascade-quiescent — by induction over the concrete writes
    (`reachedByDirect_inv`), never postulated. The derived-relation half (residue
    reconcile re-establishing I6 across reachability-affected keys) is the
    remaining T2a content and arrives with the reconcile model. -/
theorem graph_reached_inv_direct {S : Schema} {T : Store} {σ : GraphState}
    (hReach : ReachedByDirect σ S T) : Inv S σ ∧ Quiescent σ :=
  ⟨(reachedByDirect_inv hReach).1, (reachedByDirect_inv hReach).2.2⟩

/-! ## T2b base case — the empty store / empty state

Discharged end-to-end and axiom-clean, independent of any write-model scope.
Both sides are constantly `false`: the empty store grants nothing
(`sem_empty_store`), and the empty index reaches nothing / persists no residue
(`check_empty`). Every operational closure starts here. -/

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
    specification: both are constantly `false`. The base of every operational
    closure's read-correctness induction. -/
theorem graph_correct_empty (S : Schema) (q : Query) :
    GraphModel.check (emptyState S) q = sem S [] q := by
  rw [check_empty, sem_empty_store]

end Zanzibar
