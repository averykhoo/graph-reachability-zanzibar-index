import ZanzibarProofs.Spec.WellDef

/-!
# T0a is FALSE without store validity — the machine-checked counterexample

Found 2026-07-10 while attacking the `semAux_fuel_stable_step` sorry. The original
statement (stratifiable schema, **arbitrary** store) is refutable inside Lean:

- `ttuLeaf` consults `rec` at the subject of every stored tupleset tuple with **no
  restriction check** (faithful to the oracle's `ttu_leaf`, which also has none —
  admission validity is enforced at *write* time by the real system, not at read).
- Taint/`depEdges` predict TTU consultations from the *declared* restriction types
  (`directTypes`). An admission-invalid tuple therefore creates a consultation edge
  invisible to stratification.
- Such an edge can close a cycle through an `excl` subtrahend. `semAux` (pure fuel
  recursion, no visited-set) then **oscillates forever**: below, with `S`/`T`/`q`,
  `semAux (n+2) = !(semAux n)` at the query atom, at *every* fuel.

The schema here is stratifiable (`(A,p)` is the only tainted key; `depEdges = []`
— the cycle runs through tuples the schema never declared), and the store violates
exactly the `StoreDeclared` clause the real admission gate enforces
(`engine.py:_validate` (2)): tuple `C:c#... ts A:o` matches no declared restriction
— `(A, ts)` is not even a declared relation.

Consequently `semAux_fuel_stable_step` / `sem_fuel_stable` (`Spec/WellDef.lean`)
carry `StoreDeclared S T`, the documented §8 "write-valid tuples" precondition.
-/

namespace Zanzibar
namespace T0aCounter

/-- `(A,p) := direct[user] BUT NOT ttu(q, ts)`; `(C,q) := ttu(p, ts)`. Note `(A,ts)`
    and `(C,ts)` are UNDECLARED — `ttuLeaf` reads stored `ts`-tuples regardless. -/
def S : Schema :=
  { defs :=
      [ (("A", "p"), .excl (.direct [("user", BARE, false)]) (.ttu "q" "ts"))
      , (("C", "q"), .ttu "p" "ts") ]
  , objectWildcards := [] }

/-- One valid base grant + the two `ts`-tuples that close the undeclared cycle
    `(A,p)@o → (C,q)@c → (A,p)@o` through the exclusion. -/
def T : Store :=
  [ ⟨⟨"user", "alice", BARE⟩, "p", ⟨"A", "o"⟩⟩
  , ⟨⟨"C", "c", BARE⟩, "ts", ⟨"A", "o"⟩⟩
  , ⟨⟨"A", "o", BARE⟩, "ts", ⟨"C", "c"⟩⟩ ]

def q : Query := ⟨⟨"user", "alice", BARE⟩, "p", ⟨"A", "o"⟩⟩

theorem stratifiable : Stratifiable S := by unfold Stratifiable; decide

/-- The store violates the admission gate: `C:c#... ts A:o` has no declared
    `(A, ts)` relation (the real system rejects this write). -/
theorem not_storeDeclared : ¬ StoreDeclared S T := by
  intro h
  obtain ⟨e, he, -⟩ := h ⟨⟨"C", "c", BARE⟩, "ts", ⟨"A", "o"⟩⟩ (by simp [T])
  simp [S, Schema.lookup] at he

/-- **The oscillation.** Two fuel levels flip the answer at the query atom, at every
    fuel: level 1 unfolds `(A,p)`'s `excl` (base grant `true`, subtrahend = the
    `ts`-consultation of `(C,q)@c`), level 2 unfolds `(C,q)`'s ttu back to
    `(A,p)@o`. Everything else is concrete and computes away. -/
theorem oscillates (n : Nat) :
    semAux S q.subject T q (n + 2) "A" "o" "p"
      = !(semAux S q.subject T q n "A" "o" "p") := by
  simp [semAux, step, S, T, q, Schema.lookup, evalE, directLeaf, ttuLeaf,
    memberOfGranted, grantsOf, restrictionMatches, matchingObjects, instances,
    universeOf, List.find?, List.filter, List.any_cons, List.any_nil, STAR, BARE]

/-- **The refutation**: the pre-2026-07-10 statement of `semAux_fuel_stable_step`
    (no store hypothesis) is false. From stability at `40`, `41`, `42` and the
    oscillation `a₄₂ = !a₄₀`, a Boolean self-negation. -/
theorem fuel_stable_step_false :
    ¬ (∀ (S : Schema) (T : Store) (q : Query), Stratifiable S →
        ∀ f, fuelBound S T ≤ f →
          semAux S q.subject T q f q.object.type q.object.name q.relation
            = semAux S q.subject T q (f + 1) q.object.type q.object.name q.relation) := by
  intro h
  have h40 : semAux S q.subject T q 40 "A" "o" "p" = semAux S q.subject T q 41 "A" "o" "p" :=
    h S T q stratifiable 40 (by decide)
  have h41 : semAux S q.subject T q 41 "A" "o" "p" = semAux S q.subject T q 42 "A" "o" "p" :=
    h S T q stratifiable 41 (by decide)
  have hosc : semAux S q.subject T q 42 "A" "o" "p"
      = !(semAux S q.subject T q 40 "A" "o" "p") := oscillates 40
  rw [← h41, ← h40] at hosc
  cases hval : semAux S q.subject T q 40 "A" "o" "p" <;> rw [hval] at hosc <;>
    simp at hosc

end T0aCounter
end Zanzibar
