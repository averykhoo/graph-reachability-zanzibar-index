import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.SetEngine.MemberSet

/-!
# The set-engine model — `check` (concrete, Phase 3)

`SEMANTICS.md` §6.3. The set engine evaluates the AST *set-at-a-time*: it expands a
node `(otype, oname, rel)` into the full `MemberSet` of subjects holding that
relation, then answers `check` by probing that set with `containsShape` at the query
subject. This mirrors `setengine/engine.py:expand` (`do`/`do_expr`/`direct_expand`/
`ttu_expand`) — the boolean folds are `union`/`intersect`/`subtract`, the leaves are
`singletonEntity`/`star`/flow-through recursion.

**Modeling choices (logged in PROOF_STATUS / ROADMAP T1).**
* `Id := SubjectRef`. A subject is its own id; its `shape` is `(type, predicate)` and
  its `name` distinguishes within a shape. (Gemini's `MemberSet String` model was
  unsound — `alice:user` and `alice:group` collide.)
* The **population is query-focused**: `popOf s σ = {s}` at `s`'s own shape, `∅`
  elsewhere. This is sound because `containsShape` **never reads `pop`** (only
  `pos`/`stars`/`neg`), and the distribution lemmas (`Contains.lean`) prove the probe
  answer is invariant across *any* population satisfying `PopFocus`/`WFp`/`Grounded`
  — which the real global population also satisfies. The focused population makes all
  three invariants hold definitionally (`popFocus_popOf`, `grounded_popOf`,
  `wfp_*`), discharging the confinement obligation the ROADMAP flagged.
* Like `sem` (and unlike the real engine's Tarjan-lowlink memo), the model is **pure
  fuel recursion** — agreement with the memoized engine is asserted by conformance,
  not by matching control flow (PROOF_STATUS variations).
-/

namespace Zanzibar
namespace SetEngineModel

open MemberSet

/-- The query-focused population: at the fixed query subject `s`, shape `σ` has
    population `{s}` when `σ = s.shape`, else `∅`. See the file header for why this
    is sound despite ignoring other members. -/
def popOf (s : SubjectRef) : Shape → Finset SubjectRef :=
  fun σ => if σ = s.shape then {s} else ∅

/-- Fold a list of member sets with `union` (the set-engine accumulator, §6.3). -/
def unionFold (s : SubjectRef) (l : List (MemberSet SubjectRef)) : MemberSet SubjectRef :=
  l.foldr (MemberSet.union (popOf s)) MemberSet.empty

/-- The `MemberSet` contributed by one `Direct`-leaf grant tuple `g`, under the
    recursive expander `rc` (`direct_expand`, `engine.py:675-705`). A concrete/bare
    grant contributes its entity; a bare wildcard a `star` shape; a userset grant
    the token itself PLUS its flow-through expansion; a wildcard userset the shape
    `star` PLUS the union of flow-throughs over `instances`. -/
def grantMS (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (g : Tuple) : MemberSet SubjectRef :=
  let sub := g.subject
  if sub.name == STAR then
    if sub.predicate == BARE then MemberSet.star (sub.type, BARE)
    else MemberSet.union (popOf s) (MemberSet.star (sub.type, sub.predicate))
      (unionFold s ((instances T q sub.type).map (fun inst => rc sub.type inst sub.predicate)))
  else
    if sub.predicate == BARE then MemberSet.singletonEntity sub
    else MemberSet.union (popOf s) (MemberSet.singletonEntity sub) (rc sub.type sub.name sub.predicate)

/-- The "token/star match" part of a grant's contribution, probed at subject `s`
    (subject-kind-uniform; equals `directLeaf`'s per-branch match disjunct). -/
def grantMatch (s : SubjectRef) (g : Tuple) : Bool :=
  if g.subject.name == STAR then
    (if g.subject.predicate == BARE then decide (s.shape = (g.subject.type, BARE))
     else decide (s.shape = (g.subject.type, g.subject.predicate)))
  else decide (s = g.subject)

/-- The flow-through part of a grant's contribution — exactly `memberOfGranted`'s
    per-grant body (`Semantics.lean`). -/
def grantFlow (rec : String → String → String → Bool) (T : Store) (q : Query) (g : Tuple) : Bool :=
  if g.subject.predicate == BARE then false
  else if g.subject.name != STAR then rec g.subject.type g.subject.name g.subject.predicate
  else (instances T q g.subject.type).any (fun inst => rec g.subject.type inst g.subject.predicate)

/-- `Direct`-leaf expansion: the `union` over all matching grants. -/
def expandDirect (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (rs : List Restriction) (otype oname rel : String) : MemberSet SubjectRef :=
  unionFold s ((grantsOf T rs otype oname rel).map (grantMS s T q rc))

/-- The stored tupleset (parent) tuples a TTU ranges over (`ttu_expand` guard). -/
def ttuParents (T : Store) (tuplesetRel otype oname : String) : List Tuple :=
  T.filter (fun tup =>
    tup.relation == tuplesetRel && tup.object.type == otype &&
    (matchingObjects oname).contains tup.object.name)

/-- The `MemberSet` contributed by one TTU parent tuple (`ttu_expand`,
    `engine.py:707-724`): the target-relation members of the parent, plus the
    from-chain userset token; a wildcard parent contributes the shape `star` plus
    the flow-throughs over `instances`. -/
def parentMS (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (targetRel : String) (tup : Tuple) : MemberSet SubjectRef :=
  let pt := tup.subject.type
  let pn := tup.subject.name
  if pn == STAR then
    MemberSet.union (popOf s) (MemberSet.star (pt, targetRel))
      (unionFold s ((instances T q pt).map (fun inst => rc pt inst targetRel)))
  else
    MemberSet.union (popOf s) (MemberSet.singletonEntity ⟨pt, pn, targetRel⟩)
      (rc pt pn targetRel)

/-- TTU-leaf expansion: the `union` over all matching parent tuples. -/
def expandTtu (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (targetRel tuplesetRel otype oname : String) : MemberSet SubjectRef :=
  unionFold s ((ttuParents T tuplesetRel otype oname).map (parentMS s T q rc targetRel))

/-- Structural expansion of one `Expr` into a `MemberSet` (`do_expr`), mirroring
    `evalE`: boolean nodes fold with `union`/`intersect`/`subtract`, `computed`
    re-expands the same object at another relation, leaves call the leaf expanders. -/
def expandE (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (otype oname rel : String) : Expr → MemberSet SubjectRef
  | .union a b => MemberSet.union (popOf s)
      (expandE S s T q rc otype oname rel a) (expandE S s T q rc otype oname rel b)
  | .inter a b => MemberSet.intersect (popOf s)
      (expandE S s T q rc otype oname rel a) (expandE S s T q rc otype oname rel b)
  | .excl b sub => MemberSet.subtract (popOf s)
      (expandE S s T q rc otype oname rel b) (expandE S s T q rc otype oname rel sub)
  | .computed r => rc otype oname r
  | .direct rs => expandDirect s T q rc rs otype oname rel
  | .ttu tr ts => expandTtu s T q rc tr ts otype oname

/-- One immediate-consequence expansion step (`do`), mirroring `step`: an undefined
    relation expands to `empty`. -/
def expandStep (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (otype oname rel : String) : MemberSet SubjectRef :=
  match S.lookup (otype, rel) with
  | none => MemberSet.empty
  | some e => expandE S s T q rc otype oname rel e

/-- The fuel-bounded expander, primitive-recursive on `fuel` (mirrors `semAux`). -/
def expandAux (S : Schema) (s : SubjectRef) (T : Store) (q : Query) :
    Nat → String → String → String → MemberSet SubjectRef
  | 0, _, _, _ => MemberSet.empty
  | fuel + 1, otype, oname, rel =>
      expandStep S s T q (expandAux S s T q fuel) otype oname rel

/-- The set-engine `check`: expand the query node, probe with `containsShape` at the
    query subject and its own shape (`SEMANTICS.md` §6.3). -/
def check (S : Schema) (T : Store) (q : Query) : Bool :=
  containsShape
    (expandAux S q.subject T q (fuelBound S T) q.object.type q.object.name q.relation)
    q.subject q.subject.shape

end SetEngineModel
end Zanzibar
