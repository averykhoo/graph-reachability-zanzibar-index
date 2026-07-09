import ZanzibarProofs.Core.Store
import ZanzibarProofs.Spec.Stratify
import ZanzibarProofs.GraphIndex.Closure

/-!
# The graph-index model — state, invariant, read (CONCRETE, Phase 4)

`SEMANTICS.md` §7. Phase 1 stubbed the state, read, invariant, reachability,
quiescence, and scope predicate as `opaque` placeholders so the T2/T5 statements
could compile. **This file replaces all seven with concrete definitions** — the
"concretize + partial proofs" pass. The deep theorems (`graph_correct`,
the `Inv` half of `graph_reached_inv`) remain tracked `sorry`s in `Correct.lean`;
`cascade_converges` and the `Quiescent` half of `graph_reached_inv` are *closed*
here off the concrete `ReachedBy` (the model bakes the in-transaction cascade into
each write — §7.8 / ambiguity A1, user-approved).

## Modeling choices (logged here + PROOF_STATUS)

* **Reads read reachability, not path counts.** The Python index stores `p(u,v)`
  (the path count) for O(1) reads and for the counting-IVM (T4). Semantically,
  `check` only needs *reachability* `p(u,v) > 0`, which is the transitive closure of
  the direct edges. So `GraphState` tracks the **direct edges** and `check` probes
  reachability via a fuel-bounded closure (`reachB`). The path-*counting* layer is a
  separate concern, modeled and proven in `Closure.lean` (T4); factoring it out
  avoids threading a `Fintype NodeKey` (the key space is infinite) through the read
  proof. `Inv.acyclic` pins the DAG property the counting theorem needs.
* **The schema is baked into the state.** `check : GraphState → Query → Bool` takes
  no schema (the compiled artifacts — taint classification, declared shapes — are
  part of the persisted index), so `GraphState` carries `schema` and `Inv S σ`
  pins `σ.schema = S`.
* **`WriteStep` is a minimal operational spec.** It records only the necessary
  postconditions this pass exercises (schema fixed, nodes monotone, the cascade
  drained in-txn). The full add-edge + bridge + reconcile realization is the
  deferred T2a operational content; `graph_reached_inv`'s `Inv` conjunct stays
  `sorry` because those clauses are *not* free from this thin step.
-/

namespace Zanzibar

/-! ## §7.4 — nodes -/

/-- Node variant: an ordinary concrete/userset node, the ∃-wildcard node `w_any`
    (concretes bridge **in**, wildcard-*subject* grants leave), or the ∀-wildcard
    node `w_all` (wildcard-*object* grants arrive, bridges leave) — `SEMANTICS.md`
    §7.4, `models.py:32-36`. -/
inductive Variant where
  | plain | wAny | wAll
deriving DecidableEq, Repr, Inhabited

/-- A materialized graph node key `(type, name, predicate, variant)` (§7.4). The
    Python key's `store` component is dropped (single-store model). The node
    encoding invariant `name == '*' ⟺ variant ≠ plain` lives in `Inv`. -/
structure NodeKey where
  type : String
  name : String
  pred : String
  variant : Variant
deriving DecidableEq, Repr, Inhabited

/-! ## §7.6 — residues -/

/-- A persisted residue `ResidueV1` for a derived `(object node, relation)`
    (§7.6, `models.py:80-107`): the star-covered shapes, the concrete subjects that
    are star-covered-but-excluded (`neg`), and the edge-free userset members
    (`upos`). Membership is `edges ∪ upos ∪ (⋃_{σ∈stars} pop(σ) ∖ neg)`. -/
structure Residue where
  stars : List Shape
  neg   : List SubjectRef
  upos  : List SubjectRef
deriving DecidableEq, Repr, Inhabited

/-- The empty residue (default for a node with no persisted residue). -/
def Residue.empty : Residue := ⟨[], [], []⟩

/-- A delta-outbox row (§7.8, `outbox.py`) — an id plus the `(node, relation)` it
    dirties. Enough structure to state outbox-drain quiescence (I10). -/
structure Delta where
  id : Nat
  node : NodeKey
  relation : String
deriving DecidableEq, Repr, Inhabited

/-! ## §7.1 — the materialized state -/

/-- The materialized graph-index state (§7.1, §7.6, §7.8). Concrete replacement for
    the Phase-1 opaque placeholder. Edges are the direct multigraph edges (as a
    list; reachability is their transitive closure); `residue` maps a derived
    `(object node, relation)` to its residue; `outbox`/`watermark` model the delta
    stream and its drain frontier. -/
structure GraphState where
  schema : Schema
  edges : List (NodeKey × NodeKey)
  nodes : List NodeKey
  residue : NodeKey → String → Option Residue
  outbox : List Delta
  watermark : Nat

/-! ## Node constructors from query endpoints (§7.4, §7.5) -/

/-- The node for a subject reference: a `'*'` subject is its own `w_any` (∃) node;
    a concrete/userset subject is a plain node. -/
def subjNode (s : SubjectRef) : NodeKey :=
  if s.name = STAR then ⟨s.type, STAR, s.predicate, Variant.wAny⟩
  else ⟨s.type, s.name, s.predicate, Variant.plain⟩

/-- The `w_any` (∃) node of a shape `(type, predicate)`. -/
def wAnyNode (sh : Shape) : NodeKey := ⟨sh.1, STAR, sh.2, Variant.wAny⟩

/-- The userset node carrying relation `R` on object `o`: a `'*'` object is its own
    `w_all` (∀) node; a concrete object is a plain node. -/
def objNode (o : ObjectRef) (R : String) : NodeKey :=
  if o.name = STAR then ⟨o.type, STAR, R, Variant.wAll⟩
  else ⟨o.type, o.name, R, Variant.plain⟩

/-- The `w_all` (∀) node for object-wildcard of type `t`, relation `R`. -/
def wAllNode (t R : String) : NodeKey := ⟨t, STAR, R, Variant.wAll⟩

/-! ## Reachability (transitive closure of the direct edges) -/

/-- Fuel-bounded reachability: is there a directed path `u → v` of length `1..fuel`?
    A length-`(k+1)` path is a first edge `u→w` then a length-`k` path `w→v`. -/
def reachB (edges : List (NodeKey × NodeKey)) : Nat → NodeKey → NodeKey → Bool
  | 0, _, _ => false
  | fuel + 1, u, v => edges.any (fun e => e.1 == u && (e.2 == v || reachB edges fuel e.2 v))

/-- The read-side reachability probe `p(u,v) > 0`: a path exists within the node
    count (any longer walk in a DAG would repeat a node). -/
def GraphState.reach (σ : GraphState) (u v : NodeKey) : Bool :=
  reachB σ.edges (σ.nodes.length + 1) u v

/-! ## Fuel-free reachability — the invariant / write-path layer

`GraphState.reach` above is the *executable* probe: a fuel-capped closure whose
fuel is tied to `nodes.length`. For the state invariant and the write-path proofs
it is far cleaner to reason about reachability as a **fuel-free relation**
`NReaches` — the transitive closure of the direct edges (≥ 1 hop). This sidesteps
the `nodes.length`-fuel bookkeeping (adding a node changes the fuel, which would
otherwise perturb a capped probe out from under an acyclicity argument). The bridge
`reach ↔ NReaches` — that the fuel `nodes.length + 1` is always enough — is a
stabilization (pigeonhole) fact needed only by the read theorem T2b, and is
factored there. `Inv` below is stated over `NReaches`. -/

/-- Fuel-free directed reachability: a path of ≥ 1 edge from `u` to `v`. -/
inductive NReaches (edges : List (NodeKey × NodeKey)) : NodeKey → NodeKey → Prop where
  | edge {u v} : (u, v) ∈ edges → NReaches edges u v
  | head {u w v} : (u, w) ∈ edges → NReaches edges w v → NReaches edges u v

/-- Reflexive closure of `NReaches` (a path of ≥ 0 edges). -/
def NReachesR (edges : List (NodeKey × NodeKey)) (u v : NodeKey) : Prop :=
  u = v ∨ NReaches edges u v

/-- Extend a path by one trailing edge. -/
theorem NReaches.tail {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h : NReaches edges u w) (e : (w, v) ∈ edges) : NReaches edges u v := by
  induction h with
  | edge huw => exact NReaches.head huw (NReaches.edge e)
  | head huw _ ih => exact NReaches.head huw (ih e)

/-- `NReaches` is transitive. -/
theorem NReaches.trans {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h1 : NReaches edges u w) (h2 : NReaches edges w v) : NReaches edges u v := by
  induction h1 with
  | edge huw => exact NReaches.head huw h2
  | head huw _ ih => exact NReaches.head huw (ih h2)

/-- `NReachesR` is transitive. -/
theorem NReachesR.trans {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h1 : NReachesR edges u w) (h2 : NReachesR edges w v) : NReachesR edges u v := by
  rcases h1 with rfl | r1
  · exact h2
  · rcases h2 with rfl | r2
    · exact Or.inr r1
    · exact Or.inr (r1.trans r2)

/-- The empty edge set reaches nothing. -/
theorem nreaches_nil (u v : NodeKey) : ¬ NReaches [] u v := by
  intro h; cases h <;> simp_all

/-- Adding an edge never removes reachability. -/
theorem NReaches.mono {edges : List (NodeKey × NodeKey)} {e : NodeKey × NodeKey}
    {u v : NodeKey} (h : NReaches edges u v) : NReaches (e :: edges) u v := by
  induction h with
  | edge huv => exact NReaches.edge (List.mem_cons_of_mem _ huv)
  | head huw _ ih => exact NReaches.head (List.mem_cons_of_mem _ huw) ih

/-- **First-use decomposition.** A path in `(a,b) :: edges` either avoids the new
    edge entirely (a path in the old edges) or factors through it as
    `u →* a → b →* v` (the reflexive-closure legs use only old edges). -/
theorem nreaches_cons_split {edges : List (NodeKey × NodeKey)} {a b u v : NodeKey}
    (h : NReaches ((a, b) :: edges) u v) :
    NReaches edges u v ∨ (NReachesR edges u a ∧ NReachesR edges b v) := by
  induction h with
  | @edge u v huv =>
    rcases List.mem_cons.mp huv with heq | hmem
    · obtain ⟨hu, hv⟩ := Prod.ext_iff.mp heq
      exact Or.inr ⟨Or.inl hu, Or.inl hv.symm⟩
    · exact Or.inl (NReaches.edge hmem)
  | @head u w v huw _ ih =>
    rcases List.mem_cons.mp huw with heq | hmem
    · obtain ⟨hu, hw⟩ := Prod.ext_iff.mp heq
      subst hu; subst hw
      refine Or.inr ⟨Or.inl rfl, ?_⟩
      rcases ih with hl | ⟨_, hr⟩
      · exact Or.inr hl
      · exact hr
    · rcases ih with hl | ⟨hwa, hbv⟩
      · exact Or.inl (NReaches.head hmem hl)
      · refine Or.inr ⟨?_, hbv⟩
        rcases hwa with rfl | hwa'
        · exact Or.inr (NReaches.edge hmem)
        · exact Or.inr (NReaches.head hmem hwa')

/-- **Cycle-rejection preserves acyclicity.** Adding a direct edge `(a,b)` to an
    acyclic edge set keeps it acyclic provided there is no back-path `b →* a` and
    `a ≠ b` — exactly the admission check the write path performs (I2 / §7.7). -/
theorem acyclic_addEdge {edges : List (NodeKey × NodeKey)} {a b : NodeKey}
    (hac : ∀ v, ¬ NReaches edges v v)
    (hback : ¬ NReaches edges b a) (hne : a ≠ b) :
    ∀ v, ¬ NReaches ((a, b) :: edges) v v := by
  intro v hv
  rcases nreaches_cons_split hv with hl | ⟨hva, hbv⟩
  · exact hac v hl
  · have hba : NReachesR edges b a := hbv.trans hva
    rcases hba with heq | hr
    · exact hne heq.symm
    · exact hback hr

/-! ## §7.5, §7.6 — the read `GraphModel.check` -/

namespace GraphModel

/-- Non-derived read: the ≤4 candidate probes (§7.5, `wildcard.py:354-374`).
    `(s,o)`, `(w_any(shape s), o)`, `(s, w_all(o.type,R))`, `(w_any, w_all)`,
    each `p>0`, OR-combined. A literal `'*'` endpoint IS its own variant node and so
    skips its own extra probe (the `!= STAR` guards). A key whose node is absent
    contributes `reach = false` (ghost coverage) automatically. -/
def probeNonDerived (σ : GraphState) (q : Query) : Bool :=
  let s := q.subject
  let o := q.object
  let R := q.relation
  let sN := subjNode s
  let oN := objNode o R
  σ.reach sN oN
  || (s.name != STAR && σ.reach (wAnyNode s.shape) oN)
  || (o.name != STAR && σ.reach sN (wAllNode o.type R))
  || (s.name != STAR && o.name != STAR && σ.reach (wAnyNode s.shape) (wAllNode o.type R))

/-- Derived read: the residue path (§7.6, `wildcard.py:398-432`). An object wildcard
    on a derived relation is rejected (decision-15) ⇒ `False`. A `'*'` subject checks
    shape-star coverage. A userset subject is edge-free: in `upos` ⇒ True, else
    shape not covered ⇒ False, else not excluded. A bare subject probes its derived
    edge first (an edge hit returns True **without** consulting `neg` — the I6
    disjointness), else falls back to `stars ∖ neg`. -/
def probeDerived (σ : GraphState) (q : Query) : Bool :=
  let s := q.subject
  let o := q.object
  let R := q.relation
  if o.name == STAR then false
  else
    let oN := objNode o R
    let res := (σ.residue oN R).getD Residue.empty
    if s.name == STAR then
      res.stars.contains s.shape
    else if s.predicate != BARE then
      if res.upos.contains s then true
      else if !res.stars.contains s.shape then false
      else !res.neg.contains s
    else
      σ.reach (subjNode s) oN || (res.stars.contains s.shape && !res.neg.contains s)

/-- The graph-index `check` (§7.5–7.6): route by whether the queried relation is
    derived (tainted). The schema is read off the baked-in `σ.schema`. -/
def check (σ : GraphState) (q : Query) : Bool :=
  if isDerived σ.schema (q.object.type, q.relation) then
    probeDerived σ q
  else
    probeNonDerived σ q

end GraphModel

/-! ## §8 — the graph scope predicate `GraphAccepts` (decision-15) -/

/-- All `Direct` restrictions occurring anywhere in an expression. -/
def exprRestrictions : Expr → List Restriction
  | .direct rs => rs
  | .computed _ => []
  | .ttu _ _ => []
  | .union a b => exprRestrictions a ++ exprRestrictions b
  | .inter a b => exprRestrictions a ++ exprRestrictions b
  | .excl a b => exprRestrictions a ++ exprRestrictions b

/-- All TTU nodes `(targetRel, tuplesetRel)` occurring anywhere in an expression. -/
def exprTtus : Expr → List (String × String)
  | .direct _ => []
  | .computed _ => []
  | .ttu tr ts => [(tr, ts)]
  | .union a b => exprTtus a ++ exprTtus b
  | .inter a b => exprTtus a ++ exprTtus b
  | .excl a b => exprTtus a ++ exprTtus b

/-- **`GraphAccepts S`** — the decision-15 scope predicate (`SEMANTICS.md` §8,
    `boolean-ivm-spec §1.15`): (1) no object-wildcard shape on a derived relation;
    (2) no wildcard *userset* restriction referencing a derived relation; (3) no TTU
    whose tupleset relation is derived. Outside this scope the graph rejects the
    schema at compile. -/
def GraphAccepts (S : Schema) : Prop :=
  (∀ tr ∈ S.objectWildcards, isDerived S tr = false)
  ∧ (∀ d ∈ S.defs, ∀ r ∈ exprRestrictions d.2,
       r.2.2 = true → r.2.1 ≠ BARE → isDerived S (r.1, r.2.1) = false)
  ∧ (∀ d ∈ S.defs, ∀ tt ∈ exprTtus d.2, isDerived S (d.1.1, tt.2) = false)

/-! ## §7.8 — cascade quiescence -/

/-- **`Quiescent σ`** (I9 / §7.8): the outbox is fully drained — no delta sits above
    the watermark, i.e. `run_cascade` has advanced the frontier past every dirtied
    row. This is the in-transaction fixpoint condition the model bakes into each
    write; the full "a second reconcile changes nothing" characterization is the
    deferred T5 content. -/
def Quiescent (σ : GraphState) : Prop :=
  ∀ d ∈ σ.outbox, d.id ≤ σ.watermark

/-! ## §7.7 — the state invariant `Inv` -/

/-- **`Inv S σ`** — the concretely-expressible core of the I-series (§7.7,
    `invariants.py`). Named clauses so a proof can use exactly the piece it needs:

    * `schemaEq` — the state was built for `S`.
    * `nodeEnc` — node encoding (`:83-87`): `name == '*' ⟺ variant ≠ plain`.
    * `edgesClosed` — I1 endpoint existence (`:89-101`): both ends of a direct edge
      are live nodes.
    * `acyclic` — I2 (`:103-128`): the direct-edge graph is a DAG (no self-reach).
    * `negStarCovered` / `negEdgeFree` / `uposEdgeFree` / `uposNegDisjoint` — I6
      residue hygiene (`:220-273`): `neg ⊆ star-covered`, `neg ∩ edge-holders = ∅`
      (the load-bearing disjointness the bare edge-hit relies on), `upos ∩
      edge-holders = ∅`, `upos ∩ neg = ∅`.

    The path-count algebra (I1's `p ≥ d`), refcounts (I13), and the full bridge
    completeness (I3) are counting/structural facts factored to `Closure.lean` (T4)
    and the deferred T2a; they are not restated here. -/
structure Inv (S : Schema) (σ : GraphState) : Prop where
  schemaEq : σ.schema = S
  nodeEnc : ∀ k ∈ σ.nodes, (k.name = STAR ↔ k.variant ≠ Variant.plain)
  edgesClosed : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes
  acyclic : ∀ v, ¬ NReaches σ.edges v v
  negStarCovered : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.neg, res.stars.contains n.shape = true
  negEdgeFree : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.neg, ¬ NReaches σ.edges (subjNode n) k
  uposEdgeFree : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.upos, ¬ NReaches σ.edges (subjNode n) k
  uposNegDisjoint : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.upos, res.neg.contains n = false

/-! ## §7.8 — reachable states -/

/-- The empty index state for schema `S` (the `build_index` seed). -/
def emptyState (S : Schema) : GraphState :=
  { schema := S, edges := [], nodes := [], residue := fun _ _ => none,
    outbox := [], watermark := 0 }

/-- **`WriteStep S σ σ' t`** — one accepted write incorporating tuple `t` (§7.8).
    A minimal *operational spec*: the schema is fixed, existing nodes persist, and
    the in-transaction cascade leaves the outbox drained (§7.8 / A1 — the model bakes
    the cascade into every write). The full edge/bridge/reconcile realization (and
    hence the preservation of the remaining `Inv` clauses) is the deferred T2a
    content, so this step deliberately does *not* assert `Inv`. -/
structure WriteStep (S : Schema) (σ σ' : GraphState) (t : Tuple) : Prop where
  schemaEq : σ'.schema = σ.schema
  monoNodes : ∀ k ∈ σ.nodes, k ∈ σ'.nodes
  drained : ∀ d ∈ σ'.outbox, d.id ≤ σ'.watermark

/-- **`ReachedBy σ S T`** — `σ` is reached by applying `T`'s writes (each with its
    in-transaction cascade) from the empty state, under schema `S`. The transitive
    closure of `WriteStep` from `emptyState`. -/
inductive ReachedBy : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedBy (emptyState S) S []
  | step {σ σ' : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      ReachedBy σ S T → WriteStep S σ σ' t → ReachedBy σ' S (t :: T)

/-! ## Partial results (this pass) -/

/-- Reachability in the empty edge set is always `false`. -/
theorem reachB_nil (f : Nat) (u v : NodeKey) : reachB [] f u v = false := by
  cases f <;> rfl

/-- The empty state reaches nothing. -/
theorem reach_empty (S : Schema) (u v : NodeKey) : (emptyState S).reach u v = false := by
  unfold GraphState.reach emptyState
  exact reachB_nil _ _ _

/-- The empty state satisfies `Inv` (the `build_index` base case). -/
theorem inv_empty (S : Schema) : Inv S (emptyState S) where
  schemaEq := rfl
  nodeEnc := by intro k hk; simp [emptyState] at hk
  edgesClosed := by intro e he; simp [emptyState] at he
  acyclic := fun v => nreaches_nil v v
  negStarCovered := by intro k r res h; simp [emptyState] at h
  negEdgeFree := by intro k r res h; simp [emptyState] at h
  uposEdgeFree := by intro k r res h; simp [emptyState] at h
  uposNegDisjoint := by intro k r res h; simp [emptyState] at h

/-- The empty state is quiescent. -/
theorem quiescent_empty (S : Schema) : Quiescent (emptyState S) := by
  intro d hd; simp [emptyState] at hd

end Zanzibar
