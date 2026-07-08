import ZanzibarProofs.Core.Schema

/-!
# The tuple store and the query universe

`SEMANTICS.md` §2.2, §5.2. A `Store` is a list of write-valid tuples (dedup is a
model-boundary concern — §11-A4). The `universe`/`instances` helpers implement the
oracle's per-query name sets (`tests/oracle.py:314-351`).
-/

namespace Zanzibar

/-- The tuple store. A `List` for executable evaluation; the spec treats it up to
    the multiset of its elements. -/
abbrev Store := List Tuple

/-- A query `(subject, relation, object)`. -/
structure Query where
  subject : SubjectRef
  relation : String
  object : ObjectRef
deriving DecidableEq, Repr, Inhabited

/-- Concrete `type`-`t` names appearing in any tuple position of `T`, together
    with the query-endpoint names of type `t` when `includeEndpoints`. Mirrors
    `_universe` (endpoints in) / `instances` (endpoints out) — `oracle.py:314-351`.
    The `STAR` sentinel is never a universe member. -/
def universeOf (T : Store) (q : Query) (t : String) (includeEndpoints : Bool) : List String :=
  let fromTuples := T.foldr (fun tup acc =>
    let acc := if tup.subject.type = t ∧ tup.subject.name ≠ STAR then tup.subject.name :: acc else acc
    if tup.object.type = t ∧ tup.object.name ≠ STAR then tup.object.name :: acc else acc) []
  let endpoints :=
    if includeEndpoints then
      (if q.subject.type = t ∧ q.subject.name ≠ STAR then [q.subject.name] else []) ++
      (if q.object.type = t ∧ q.object.name ≠ STAR then [q.object.name] else [])
    else []
  (fromTuples ++ endpoints).dedup

/-- `_universe(t, query_names)` — endpoints included (shape/marker matching).
    (`universe` is a reserved keyword in Lean, hence `universeNames`.) -/
def universeNames (T : Store) (q : Query) (t : String) : List String :=
  universeOf T q t true

/-- `instances(t)` — endpoints excluded; the ∃-witness population for strict
    ∀⇒∃ (`oracle.py:346-351`, blind-audit O3). -/
def instances (T : Store) (q : Query) (t : String) : List String :=
  universeOf T q t false

/-- An upper bound on recursion depth for the fuel-based spec (§5.1): the number
    of distinct declared `(type, relation)` nodes reachable, over-approximated by
    `|schema keys| + 2·|tuples| + 4` (the `+4` covers the query endpoints). Any
    value ≥ the true fixpoint depth gives the same answer (fuel-monotonicity, T0a). -/
def fuelBound (S : Schema) (T : Store) : Nat :=
  S.keys.length + T.length * 2 + 4

end Zanzibar
