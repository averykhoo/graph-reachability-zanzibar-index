import ZanzibarProofs.GraphIndex.ObjStarWrite

/-!
# The bridge-materializing write model — userset-wildcard fragment (T2b, stage W1c)

`SEMANTICS.md` §7.2–7.5; `wildcard-materialization-spec.md` §1.1, §7;
ROADMAP "The staged T2 plan", sub-stage **W1c**; `index_v4/wildcard.py:120-259`,
`zanzibar_utils_v1.py:264-270`.

## What W1c adds vs W1a/W1b

* **W1a** (bare star *subject* grants `[user:*]`): ZERO bridges — a bare-concrete /
  bare-`w_any` node has no in-edges, so a bare-star grant is a pure *leading* hop that
  read-probe 2 absorbs.
* **W1b** (object wildcards `[T:*]`): `w_all → concrete` **out-bridges** — an
  object-wildcard grant flowing into a further userset hop needs to reach the concrete
  object node.
* **W1c** (userset star *subject* grants `[group:*#member]`): `concrete → w_any`
  **in-bridges** — a concrete userset node `⟨group,inst,member,plain⟩` bridges INTO the
  `w_any(group,member)` node, out of which the userset-star grant leaves. This
  materializes the §1.1 composition `concrete → w_any(shape) → objNode` and is the
  graph counterpart of `sem`'s `memberOfGranted` `instances`-branch: a userset-star
  grant expands over `instances T q group`, exactly the concrete group names that
  appear in the store (and hence have their in-bridge).

## Why bridged-IN shapes are the userset stars only (`bridged_in_shapes`)

`zanzibar_utils_v1.py:264-270`: `bridged_in_shapes = {s ∈ subject_wildcard_shapes |
s.predicate ≠ '...'}`. Bare shapes `(T,'...')` never need in-bridges (nothing in this
graph points into a `'...'`-predicate node, so a bare-shape hop can only be the
*leading* hop, which probe 2 covers virtually — this is exactly W1a). A subject-
wildcard shape `(T,P)` with `P ≠ BARE` comes from any `[T:*#P]` restriction in the
schema (`zanzibar_utils_v1.py:784-789`).

## The model (`wildcard.py:222-259`, `_ensure_bridges:120-134`)

`add_tuple` is **bridge-before-grant**: `_ensure_bridges` on each endpoint creates the
configured bridges (in-bridge for a bridged-in shape, out-bridge for a bridged-out
shape), then the grant edge under cycle-rejection. On this fragment (no object
wildcards) the out-bridges are inert, so `writeUsStar` = `writeWild` + the in-bridges.

## Attack-first (machine-checked, this session, no `native_decide`)

`GraphModel.check = sem` verified on 12 userset-star scenarios incl. the sharp
endpoint-exclusion cases: a group name is in `sem`'s `instances` iff it appears in a
TUPLE (not merely as a query endpoint), which is EXACTLY when the store-built graph
has its in-bridge — so the store-derived bridge set and `instances` agree. A
query-only name (`ghost`) is in neither. No refutation; the statement is worth
proving. The one *apparent* divergence found was an **admission-invalid tuple** (a
concrete userset `group:eng#member` grant against a `[group:*#member]`-only
restriction), confirming `restrictionMatches` (StoreValid) is load-bearing, exactly
as in the direct/objStar fragments.
-/

namespace Zanzibar

/-! ## Subject-wildcard userset shapes -/

/-- Is `(t, p)` a declared subject-wildcard *userset* shape — `p ≠ BARE` and some
    `[t:*#p]` restriction (`(t, p, true)`) occurs in the schema? These are exactly
    the `bridged_in_shapes` (`zanzibar_utils_v1.py:264-270, 784-789`); the graph
    materializes a `concrete → w_any(t,p)` in-bridge for every concrete node of such a
    shape. (The TTU-through-shape extension of `subject_wildcard_shapes`,
    `:795-803`, is out of scope for this TTU-free fragment.) -/
def Schema.isSubjectWildcardUserset (S : Schema) (t p : String) : Bool :=
  p != BARE && S.defs.any (fun d => (exprRestrictions d.2).contains (t, p, true))

/-! ## The bridged-in-concrete test and `ensureInBridges` -/

/-- `c` is a concrete *userset* node whose shape `(type, pred)` is a declared
    subject-wildcard userset shape — the nodes that need a `c → w_any` in-bridge
    (`wildcard.py:120-129`; bridged-in shapes, §5). Only concretes are bridged; the
    `pred ≠ BARE` guard is subsumed by `isSubjectWildcardUserset`. -/
def GraphState.bridgedInConcrete (σ : GraphState) (c : NodeKey) : Bool :=
  c.variant == Variant.plain && c.name != STAR && σ.schema.isSubjectWildcardUserset c.type c.pred

/-- **Ensure the in-bridge for a concrete userset endpoint** (`_ensure_bridges`,
    `wildcard.py:120-129`): if `c` is a concrete node of a bridged-in shape, create the
    `w_any(c.type, c.pred)` node (lazily) and add the bridge edge `c → w_any`, under the
    same cycle-rejection guard the core edge-add uses. Idempotence at the reachability
    level is automatic (`NReaches` is membership, not multiplicity); a non-bridged node
    is left untouched. The caller ensures `c` is already a live node. -/
def GraphState.ensureInBridges (σ : GraphState) (c : NodeKey) : GraphState :=
  if σ.bridgedInConcrete c then
    if (σ.addNode (wAnyNode (c.type, c.pred))).admitEdge c (wAnyNode (c.type, c.pred)) then
      (σ.addNode (wAnyNode (c.type, c.pred))).addEdge c (wAnyNode (c.type, c.pred))
    else σ.addNode (wAnyNode (c.type, c.pred))
  else σ

/-- **The userset-star bridge-materializing single-tuple write** (`add_tuple`,
    `wildcard.py:222-259`): add both endpoint nodes, ensure the out-bridges (W1b —
    inert on this object-wildcard-free fragment) and then the in-bridges of each
    concrete endpoint (bridge-before-grant), then the grant edge
    `subjNode s → objNode o R` under cycle-rejection. A rejected grant rolls back the
    whole write (bridges included), leaving the state unchanged. -/
def GraphState.writeUsStar (σ : GraphState) (t : Tuple) : GraphState :=
  let a := subjNode t.subject
  let b := objNode t.object t.relation
  let σ0 := (σ.addNode a).addNode b
  let σ1 := (σ0.ensureBridges a).ensureBridges b
  let σ2 := (σ1.ensureInBridges a).ensureInBridges b
  if σ2.admitEdge a b then σ2.addEdge a b else σ

/-! ## Schema is fixed by the in-bridge machinery -/

@[simp] theorem ensureInBridges_schema (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridges c).schema = σ.schema := by
  unfold GraphState.ensureInBridges
  split
  · split <;> simp
  · rfl

/-! ## `w_any` nodes are encoding-valid -/

/-- A `w_any` node always satisfies the node-encoding clause. -/
theorem nodeEnc_wAnyNode (sh : Shape) :
    (wAnyNode sh).name = STAR ↔ (wAnyNode sh).variant ≠ Variant.plain := by
  have hv : (wAnyNode sh).variant = Variant.wAny := rfl
  have hn : (wAnyNode sh).name = STAR := rfl
  rw [hv, hn]
  exact ⟨fun _ => by decide, fun _ => rfl⟩

/-- Nodes only grow under `ensureInBridges` (it adds a `w_any` node or nothing). -/
theorem ensureInBridges_mono {σ : GraphState} {c k : NodeKey} (hk : k ∈ σ.nodes) :
    k ∈ (σ.ensureInBridges c).nodes := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr]
    have hk' : k ∈ (σ.addNode (wAnyNode (c.type, c.pred))).nodes := List.mem_cons_of_mem _ hk
    split
    · simpa using hk'
    · exact hk'
  · rw [if_neg hbr]; exact hk

/-! ## Structural-invariant preservation -/

/-- **`ensureInBridges` preserves the structural invariant** (given the concrete
    endpoint is already live). On the non-bridged branch the state is unchanged; on
    the bridged branch the `w_any` node is encoding-valid (`nodeEnc_wAnyNode`) and the
    bridge edge is admitted by cycle-rejection, so `structInv_addNode` /
    `structInv_addEdge` apply. -/
theorem structInv_ensureInBridges {S : Schema} {σ : GraphState} (h : StructInv S σ)
    {c : NodeKey} (hc : c ∈ σ.nodes) : StructInv S (σ.ensureInBridges c) := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr]
    set w := wAnyNode (c.type, c.pred) with hw_def
    have h1 : StructInv S (σ.addNode w) :=
      structInv_addNode h (by rw [hw_def]; exact nodeEnc_wAnyNode (c.type, c.pred))
    by_cases hadmit : (σ.addNode w).admitEdge c w = true
    · rw [if_pos hadmit]
      unfold GraphState.admitEdge at hadmit
      simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true'] at hadmit
      obtain ⟨hne, hreach⟩ := hadmit
      have hback : ¬ NReaches (σ.addNode w).edges w c := by
        intro hr
        have := reach_complete h1.edgesClosed hr
        rw [this] at hreach; exact Bool.noConfusion hreach
      refine structInv_addEdge h1 ?_ ?_ hback hne
      · exact List.mem_cons_of_mem _ hc
      · exact List.mem_cons_self
    · rw [if_neg hadmit]; exact h1
  · rw [if_neg hbr]; exact h

/-- **`writeUsStar` preserves the structural invariant.** Add the two endpoint nodes,
    thread `StructInv` through both `ensureBridges` (out-bridges, W1b) and both
    `ensureInBridges` (in-bridges, W1c) — endpoints stay live throughout — then add the
    cycle-admitted grant edge. A rejected grant returns the original state. -/
theorem structInv_writeUsStar {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeUsStar t) := by
  unfold GraphState.writeUsStar
  dsimp only
  set a := subjNode t.subject with ha_def
  set b := objNode t.object t.relation with hb_def
  -- add the two endpoint nodes
  have h0a : StructInv S (σ.addNode a) :=
    structInv_addNode h (by rw [ha_def]; exact nodeEnc_subjNode t.subject)
  have h0 : StructInv S ((σ.addNode a).addNode b) :=
    structInv_addNode h0a (by rw [hb_def]; exact nodeEnc_objNode t.object t.relation)
  have haσ0 : a ∈ ((σ.addNode a).addNode b).nodes :=
    List.mem_cons_of_mem _ List.mem_cons_self
  have hbσ0 : b ∈ ((σ.addNode a).addNode b).nodes := List.mem_cons_self
  -- out-bridges (W1b) for a, then b
  have h1a : StructInv S (((σ.addNode a).addNode b).ensureBridges a) :=
    structInv_ensureBridges h0 haσ0
  have hbσ1a : b ∈ (((σ.addNode a).addNode b).ensureBridges a).nodes :=
    ensureBridges_mono hbσ0
  have h1 : StructInv S ((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b) :=
    structInv_ensureBridges h1a hbσ1a
  set σ1 := (((σ.addNode a).addNode b).ensureBridges a).ensureBridges b with hσ1_def
  have haσ1 : a ∈ σ1.nodes := ensureBridges_mono (ensureBridges_mono haσ0)
  have hbσ1 : b ∈ σ1.nodes := ensureBridges_mono hbσ1a
  -- in-bridges (W1c) for a, then b
  have h2a : StructInv S (σ1.ensureInBridges a) := structInv_ensureInBridges h1 haσ1
  have hbσ2a : b ∈ (σ1.ensureInBridges a).nodes := ensureInBridges_mono hbσ1
  have h2 : StructInv S ((σ1.ensureInBridges a).ensureInBridges b) :=
    structInv_ensureInBridges h2a hbσ2a
  set σ2 := (σ1.ensureInBridges a).ensureInBridges b with hσ2_def
  have haσ2 : a ∈ σ2.nodes := ensureInBridges_mono (ensureInBridges_mono haσ1)
  have hbσ2 : b ∈ σ2.nodes := ensureInBridges_mono hbσ2a
  -- add the guarded grant edge
  split
  · rename_i hadmit
    unfold GraphState.admitEdge at hadmit
    simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true'] at hadmit
    obtain ⟨hne, hreach⟩ := hadmit
    have hback : ¬ NReaches σ2.edges b a := by
      intro hr
      have := reach_complete h2.edgesClosed hr
      rw [this] at hreach; exact Bool.noConfusion hreach
    exact structInv_addEdge h2 haσ2 hbσ2 hback hne
  · exact h

/-! ## Write-effect projections -/

/-- The schema is fixed by the userset-star write. -/
theorem writeUsStar_schema (σ : GraphState) (t : Tuple) :
    (σ.writeUsStar t).schema = σ.schema := by
  unfold GraphState.writeUsStar
  dsimp only
  split
  · simp
  · rfl

/-- Existing nodes persist across the write (nodes are only ever added). -/
theorem writeUsStar_monoNodes (σ : GraphState) (t : Tuple) :
    ∀ k ∈ σ.nodes, k ∈ (σ.writeUsStar t).nodes := by
  intro k hk
  unfold GraphState.writeUsStar
  dsimp only
  have hk0 : k ∈ ((σ.addNode (subjNode t.subject)).addNode
      (objNode t.object t.relation)).nodes :=
    List.mem_cons_of_mem _ (List.mem_cons_of_mem _ hk)
  have hk1 : k ∈ ((((((σ.addNode (subjNode t.subject)).addNode
      (objNode t.object t.relation)).ensureBridges (subjNode t.subject)).ensureBridges
      (objNode t.object t.relation)).ensureInBridges (subjNode t.subject)).ensureInBridges
      (objNode t.object t.relation)).nodes :=
    ensureInBridges_mono (ensureInBridges_mono (ensureBridges_mono (ensureBridges_mono hk0)))
  split
  · simpa using hk1
  · exact hk

/-! ## The userset-star write-closure and its structural invariant -/

/-- **`UsStarReached σ S T`** — `σ` is reached from the empty state by applying `T`'s
    writes as userset-star bridge-materializing writes (`writeUsStar`). The operational
    reachable-state closure at the userset-wildcard fragment's scope (the W1c analog of
    `WildReached`). -/
inductive UsStarReached : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : UsStarReached (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      UsStarReached σ S T → UsStarReached (σ.writeUsStar t) S (t :: T)

/-- **The structural invariant holds at every W1c-reachable state.** By induction over
    the bridge-materializing write path (`structInv_writeUsStar`): node encoding,
    endpoint closure, and acyclicity (preserved through both bridge families and the
    cycle-rejected grant) all survive. Bridge-completeness and the read correspondence
    are the deferred content of the correspondence increment. -/
theorem usStarReached_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) : StructInv S σ := by
  induction h with
  | empty S => exact structInv_empty S
  | step t _ ih => exact structInv_writeUsStar ih t

/-- The schema is fixed along the whole W1c write-closure. -/
theorem usStarReached_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) : σ.schema = S :=
  (usStarReached_structInv h).schemaEq

end Zanzibar
