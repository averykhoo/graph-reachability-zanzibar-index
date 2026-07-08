import ZanzibarProofs.Core.Store

/-!
# The specification `sem` — pointwise stratified evaluation

`SEMANTICS.md` §5. This is the normative reference the two backends are proven to
compute. It is a faithful transcription of the reference oracle
(`tests/oracle.py:309-487`).

**Design (logged in PROOF_STATUS variations, refines §11-A2).** The evaluator is
*primitive-recursive on a fuel bound*: `semAux (fuel+1)` is defined purely in
terms of `semAux fuel` via one application of the immediate-consequence operator
`step`. This mirrors the oracle's depth-bounded, provisional-False recursion
(fuel exhaustion = the oracle's "in-progress revisit returns False") while being
total and structurally terminating. All the boolean/leaf logic lives in `step`,
which is parameterized by the sub-node answer function `rec` and so needs no
termination reasoning of its own. `sem` runs `semAux` at `fuelBound S T`.

`T0a` (well-definedness) will state fuel-monotonicity above the bound.
-/

namespace Zanzibar

/-- The node-recursion answer function: `(objectType, objectName, relation) ↦
    Bool`, supplied at fuel `n` to compute fuel `n+1`. -/
abbrev Rec := String → String → String → Bool

/-- Objects a query object-name matches: a concrete name also absorbs `T:*`
    object-wildcard grants; a `'*'` object is intensional (`oracle.py:393-396`). -/
def matchingObjects (oname : String) : List String :=
  if oname = STAR then [STAR] else [oname, STAR]

/-- Does a stored tuple's subject match one of a `Direct` leaf's restrictions?
    (`oracle.py:402-407`). -/
def restrictionMatches (rs : List Restriction) (tup : Tuple) : Bool :=
  rs.any (fun r =>
    tup.subject.type == r.1 && tup.subject.predicate == r.2.1 &&
    ((tup.subject.name == STAR) == r.2.2))

/-- The grants of a `Direct` leaf on `(otype, oname, rel)`: stored tuples on this
    relation/object whose subject matches a restriction (`oracle.py:409-411`). -/
def grantsOf (T : Store) (rs : List Restriction) (otype oname rel : String) : List Tuple :=
  T.filter (fun tup =>
    tup.relation == rel && tup.object.type == otype &&
    (matchingObjects oname).contains tup.object.name && restrictionMatches rs tup)

/-- `_member_of_granted` (`oracle.py:450-462`): is the fixed `subject` a transitive
    member of any granted *userset* in `grants`? Star usersets expand over the
    ∃-witness population `instances`. -/
def memberOfGranted (rec : Rec) (T : Store) (q : Query) (grants : List Tuple) : Bool :=
  grants.any (fun g =>
    if g.subject.predicate == BARE then false
    else if g.subject.name != STAR then
      rec g.subject.type g.subject.name g.subject.predicate
    else
      (instances T q g.subject.type).any (fun inst => rec g.subject.type inst g.subject.predicate))

/-- `direct_leaf` (`oracle.py:398-448`): membership of the fixed `subject` in a
    `Direct` leaf, by query-subject kind (star / bare-concrete / userset). -/
def directLeaf (rec : Rec) (subject : SubjectRef) (T : Store) (q : Query)
    (rs : List Restriction) (otype oname : String) (rel : String) : Bool :=
  let grants := grantsOf T rs otype oname rel
  let s := subject
  if s.name == STAR then
    -- star subject: matching star tuple of the exact shape, OR flow-through (D1)
    grants.any (fun g =>
      g.subject.name == STAR && g.subject.type == s.type && g.subject.predicate == s.predicate)
    || memberOfGranted rec T q grants
  else if s.predicate == BARE then
    -- bare concrete entity u
    grants.any (fun g =>
      (g.subject.name != STAR && g.subject.predicate == BARE
        && g.subject.type == s.type && g.subject.name == s.name)
      || (g.subject.name == STAR && g.subject.predicate == BARE && g.subject.type == s.type))
    || memberOfGranted rec T q grants
  else
    -- userset subject (s_type, s_name, s_pred)
    grants.any (fun g =>
      (g.subject.name != STAR && g.subject.predicate != BARE
        && g.subject.type == s.type && g.subject.name == s.name && g.subject.predicate == s.predicate)
      || (g.subject.name == STAR && g.subject.predicate != BARE
        && g.subject.type == s.type && g.subject.predicate == s.predicate))
    || memberOfGranted rec T q grants

/-- `ttu_leaf` (`oracle.py:464-485`): the stored-parent tupleset-to-userset rule.
    Parents come only from STORED tupleset tuples (`SEMANTICS.md` §5.5). -/
def ttuLeaf (rec : Rec) (subject : SubjectRef) (T : Store) (q : Query)
    (targetRel tuplesetRel : String) (otype oname : String) : Bool :=
  let objs := matchingObjects oname
  let s := subject
  T.any (fun tup =>
    if tup.relation == tuplesetRel && tup.object.type == otype && objs.contains tup.object.name then
      let pt := tup.subject.type
      let pn := tup.subject.name
      if pn != STAR then
        (s.type == pt && s.name == pn && s.predicate == targetRel)
        || rec pt pn targetRel
      else
        (s.type == pt && s.predicate == targetRel)
        || (instances T q pt).any (fun inst => rec pt inst targetRel)
    else false)

/-- Structural evaluation of one `Expr` on the fixed object `(otype, oname)` under
    enclosing relation `rel`, using `rec` for node-changing steps
    (`oracle.py:377-391`). A `Direct` leaf's grants are keyed on the enclosing
    relation `rel`, threaded here. -/
def evalE (rec : Rec) (subject : SubjectRef) (T : Store) (q : Query)
    (otype oname rel : String) : Expr → Bool
  | .union a b => evalE rec subject T q otype oname rel a || evalE rec subject T q otype oname rel b
  | .inter a b => evalE rec subject T q otype oname rel a && evalE rec subject T q otype oname rel b
  | .excl b s  => evalE rec subject T q otype oname rel b && !evalE rec subject T q otype oname rel s
  | .computed r => rec otype oname r
  | .direct rs => directLeaf rec subject T q rs otype oname rel
  | .ttu tr ts => ttuLeaf rec subject T q tr ts otype oname

/-- One immediate-consequence step: answer node `(otype, oname, rel)` given the
    sub-node answers `rec` (`sat`/`sat_expr`, `oracle.py:353-391`). An undefined
    relation is `false` (§11-A3). -/
def step (S : Schema) (subject : SubjectRef) (T : Store) (q : Query)
    (rec : Rec) (otype oname rel : String) : Bool :=
  match S.lookup (otype, rel) with
  | none => false
  | some e => evalE rec subject T q otype oname rel e

/-- The fuel-bounded evaluator, primitive-recursive on `fuel`. -/
def semAux (S : Schema) (subject : SubjectRef) (T : Store) (q : Query) :
    Nat → String → String → String → Bool
  | 0, _, _, _ => false
  | fuel + 1, otype, oname, rel =>
      step S subject T q (semAux S subject T q fuel) otype oname rel

/-- The specification: is `q` true in the stratified perfect model of `(S, T)`?
    Runs `semAux` at `fuelBound` (§5.1). -/
def sem (S : Schema) (T : Store) (q : Query) : Bool :=
  semAux S q.subject T q (fuelBound S T) q.object.type q.object.name q.relation

end Zanzibar
