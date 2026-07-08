import ZanzibarProofs.Core.Refs

/-!
# Schema AST, lookup, well-formedness

`SEMANTICS.md` §4. The AST mirrors `tests/oracle.py:78-109`.

**Modeling choice (logged in PROOF_STATUS variations):** the production/oracle
AST has *n-ary* `Union`/`Intersection`; we model them as **binary**. This is
faithful: union/intersection are associative and commutative, and well-formedness
guarantees arity ≥ 2 (`set-engine-spec.md §2.2`), so no empty-fold degeneracy
(`all [] = true` fail-open) can arise. An n-ary `or`/`and` chain is the left fold
of the binary node.
-/

namespace Zanzibar

/-- A `Direct` restriction `[t]`, `[t#p]`, `[t:*]`, `[t:*#p]` as
    `(type, predicate, wildcard)` (`tests/oracle.py:144-166`). -/
abbrev Restriction := String × String × Bool

/-- The rewrite/expression AST (binary boolean nodes; see modeling note). -/
inductive Expr where
  | direct   : List Restriction → Expr
  | computed : String → Expr
  | ttu      : (targetRel : String) → (tuplesetRel : String) → Expr
  | union    : Expr → Expr → Expr
  | inter    : Expr → Expr → Expr
  | excl     : (base : Expr) → (subtract : Expr) → Expr
deriving Repr, DecidableEq, Inhabited

/-- A schema: an association list of `(type, relation) ↦ Expr` definitions plus
    the object-wildcard shape set (which has no DSL syntax and enters via a
    constructor argument — `SEMANTICS.md` §11-A7 / CLAUDE.md). -/
structure Schema where
  defs : List ((String × String) × Expr)
  objectWildcards : List (String × String)
deriving Repr, Inhabited

/-- Definition lookup: `(type, relation) ↦ Expr?`. An undefined reference is
    `none` and evaluates to "constantly empty" in `sem` (`oracle.py:360-363`;
    `SEMANTICS.md` §11-A3). -/
def Schema.lookup (S : Schema) (key : String × String) : Option Expr :=
  (S.defs.find? (fun p => p.1 = key)).map (·.2)

/-- The declared `(type, relation)` keys of a schema. -/
def Schema.keys (S : Schema) : List (String × String) := S.defs.map (·.1)

/-- Is `(objectType, relation)` a declared object-wildcard shape? -/
def Schema.isObjectWildcard (S : Schema) (t r : String) : Bool :=
  S.objectWildcards.contains (t, r)

/-!
## Well-formedness `WF S` (`SEMANTICS.md` §4.2)

Stated as a structure of the individual rules so downstream proofs can use
exactly the piece they need. The concrete predicates are placeholders to be
filled in Phase 1 against the compiler's real checks (ambiguity A3); the shape is
fixed now so theorem statements can reference `WF`.
-/

/-- `"."` reserved in a declared relation name (`parse_schema_ast:697-702`). -/
def relNameOK (name : String) : Prop := ¬ name.contains '.'

/-- Placeholder well-formedness predicate. Refined in Phase 1 (A3). Currently
    records: declared relation names contain no `.`. Arity ≥ 2 is structural
    (binary nodes), and reference-declared-ness is handled by the "undefined ⇒
    empty" convention, so they are not extra `WF` clauses. -/
structure WF (S : Schema) : Prop where
  relNames : ∀ p ∈ S.defs, relNameOK p.1.2

end Zanzibar
