import ZanzibarProofs.GraphIndex.Write

/-!
# The bridge-materializing write model — object-wildcard fragment (T2b, stage W1b)

`SEMANTICS.md` §7.3–7.5; `wildcard-materialization-spec.md` §1.4, §3.4, §5, §7;
ROADMAP "The staged T2 plan", sub-stage **W1b**; `index_v4/wildcard.py:120-259`.

## Why W1b needs bridges (attack-first finding, machine-checked)

Stage W1a (bare star *subject* grants) needed **zero** bridges — a bare-star node
has no in-edges, so it is a pure *leading* hop that read-probe 2 (`w_any`) absorbs.
One might guess W1b (object wildcards `[T:*]`) is symmetric: a `w_all` node is never
a `subjNode` (only `plain`/`w_any` are), so it is never an edge *source*, and one
might hope read-probe 3 (`w_all`) absorbs it as a pure *trailing* hop, bridge-free.

**That guess is false, and it was machine-checked before this model was written.**
An object-wildcard grant that flows into a *further* userset hop needs the
wildcard membership to reach the **concrete** object node, which only a
`w_all → concrete` bridge provides. The refuting scenario (verified against the
real `GraphModel.check`/`sem`, no `native_decide`):

* schema: `viewer := [group#member, user]`, `editor := [doc#viewer]`,
  `member := [user]`; object-wildcard shape `(doc, viewer)`;
* store: `group:eng#member viewer doc:*` (object wildcard),
  `doc:readme#viewer editor doc:readme`, `user:alice member group:eng`;
* query `check(alice, editor, doc:readme)` — `sem = true` (alice ∈ group:eng ⇒
  viewer of *every* doc via the wildcard ⇒ viewer of `doc:readme` ⇒ editor), but
  the bridge-free `writeDirect` state answers **false**: `alice → group:eng#member
  → w_all(doc,viewer)` dead-ends (no out-edge), never reaching the concrete
  `doc:readme#viewer` node that `editor` routes through. Adding the single bridge
  `w_all(doc,viewer) → ⟨doc,readme,viewer,plain⟩` restores `true`.

So W1b materializes the §3.4 composition `subject → w_all(S) → concrete → …`: a
`w_all → concrete` out-bridge for every concrete node of a declared object-wildcard
shape. This file is the faithful write model.

## The model (`wildcard.py:222-259`)

`add_tuple` is **bridge-before-grant**: `_ensure_bridges(subject)` and
`_ensure_bridges(obj)` first (creating `w_all` lazily and the out-bridge for a
concrete endpoint of a bridged shape), then the grant edge under cycle-rejection.
A wildcard tuple whose object participates in its own shape would close a cycle and
is **rejected** at the grant edge (`wildcard.py:250-256`), so acyclicity is
preserved. A rejected write rolls the whole transaction back (bridges included).

Per-endpoint `ensureBridges` suffices to keep **bridge-completeness** (every
concrete of a bridged shape has its in-bridge from `w_all`) without a separate
`w_all`-arrival backfill: a concrete object node exists only as an edge endpoint,
so it self-bridges the first time it is touched.
-/

namespace Zanzibar

/-! ## The bridged-concrete test and `ensureBridges` -/

/-- `c` is a concrete node whose object-shape `(type, pred)` is a declared
    object-wildcard shape — the nodes that need a `w_all → c` out-bridge
    (`wildcard.py:120-134`; bridged-out shapes = the declared object wildcards,
    §5). Only concretes are bridged. -/
def GraphState.bridgedConcrete (σ : GraphState) (c : NodeKey) : Bool :=
  c.variant == Variant.plain && c.name != STAR && σ.schema.isObjectWildcard c.type c.pred

/-- **Ensure the out-bridge for a concrete endpoint** (`_ensure_bridges`,
    `wildcard.py:120-134`): if `c` is a concrete node of a bridged shape, create the
    `w_all(c.type, c.pred)` node (lazily) and add the bridge edge `w_all → c`, under
    the same cycle-rejection guard the core edge-add uses. Idempotence at the
    reachability level is automatic (`NReaches` is membership, not multiplicity);
    a non-bridged node is left untouched. The caller ensures `c` is already a live
    node (it is an endpoint of the grant being written). -/
def GraphState.ensureBridges (σ : GraphState) (c : NodeKey) : GraphState :=
  if σ.bridgedConcrete c then
    if (σ.addNode (wAllNode c.type c.pred)).admitEdge (wAllNode c.type c.pred) c then
      (σ.addNode (wAllNode c.type c.pred)).addEdge (wAllNode c.type c.pred) c
    else σ.addNode (wAllNode c.type c.pred)
  else σ

/-- **The bridge-materializing single-tuple write** (`add_tuple`,
    `wildcard.py:222-259`): add both endpoint nodes, ensure the out-bridges of each
    concrete endpoint (bridge-before-grant), then add the grant edge
    `subjNode s → objNode o R` under cycle-rejection. A rejected grant rolls back
    the whole write (bridges included), leaving the state unchanged. -/
def GraphState.writeWild (σ : GraphState) (t : Tuple) : GraphState :=
  let a := subjNode t.subject
  let b := objNode t.object t.relation
  let σ0 := (σ.addNode a).addNode b
  let σ1 := (σ0.ensureBridges a).ensureBridges b
  if σ1.admitEdge a b then σ1.addEdge a b else σ

/-! ## Schema is fixed by the bridge machinery -/

@[simp] theorem ensureBridges_schema (σ : GraphState) (c : NodeKey) :
    (σ.ensureBridges c).schema = σ.schema := by
  unfold GraphState.ensureBridges
  split
  · split <;> simp
  · rfl

/-! ## `w_all` nodes are encoding-valid -/

/-- A `w_all` node always satisfies the node-encoding clause. -/
theorem nodeEnc_wAllNode (T R : String) :
    (wAllNode T R).name = STAR ↔ (wAllNode T R).variant ≠ Variant.plain := by
  have hv : (wAllNode T R).variant = Variant.wAll := rfl
  have hn : (wAllNode T R).name = STAR := rfl
  rw [hv, hn]
  exact ⟨fun _ => by decide, fun _ => rfl⟩

/-- Nodes only grow under `ensureBridges` (it adds a `w_all` node or nothing). -/
theorem ensureBridges_mono {σ : GraphState} {c k : NodeKey} (hk : k ∈ σ.nodes) :
    k ∈ (σ.ensureBridges c).nodes := by
  unfold GraphState.ensureBridges
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr]
    have hk' : k ∈ (σ.addNode (wAllNode c.type c.pred)).nodes := List.mem_cons_of_mem _ hk
    split
    · simpa using hk'
    · exact hk'
  · rw [if_neg hbr]; exact hk

/-! ## Structural-invariant preservation -/

/-- **`ensureBridges` preserves the structural invariant** (given the concrete
    endpoint is already live). On the non-bridged branch the state is unchanged; on
    the bridged branch the `w_all` node is encoding-valid (`nodeEnc_wAllNode`) and
    the bridge edge is admitted by cycle-rejection, so `structInv_addNode` /
    `structInv_addEdge` apply. -/
theorem structInv_ensureBridges {S : Schema} {σ : GraphState} (h : StructInv S σ)
    {c : NodeKey} (hc : c ∈ σ.nodes) : StructInv S (σ.ensureBridges c) := by
  unfold GraphState.ensureBridges
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr]
    set w := wAllNode c.type c.pred with hw_def
    have h1 : StructInv S (σ.addNode w) :=
      structInv_addNode h (by rw [hw_def]; exact nodeEnc_wAllNode c.type c.pred)
    by_cases hadmit : (σ.addNode w).admitEdge w c = true
    · rw [if_pos hadmit]
      unfold GraphState.admitEdge at hadmit
      simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true'] at hadmit
      obtain ⟨hne, hreach⟩ := hadmit
      have hback : ¬ NReaches (σ.addNode w).edges c w := by
        intro hr
        have := reach_complete h1.edgesClosed hr
        rw [this] at hreach; exact Bool.noConfusion hreach
      refine structInv_addEdge h1 ?_ ?_ hback hne
      · exact List.mem_cons_self
      · exact List.mem_cons_of_mem _ hc
    · rw [if_neg hadmit]; exact h1
  · rw [if_neg hbr]; exact h

/-- **`writeWild` preserves the structural invariant.** Add the two endpoint nodes,
    thread `StructInv` through both `ensureBridges` (endpoints are now live), then
    add the cycle-admitted grant edge. A rejected grant returns the original state. -/
theorem structInv_writeWild {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeWild t) := by
  unfold GraphState.writeWild
  dsimp only
  set a := subjNode t.subject with ha_def
  set b := objNode t.object t.relation with hb_def
  -- add the two endpoint nodes
  have h0a : StructInv S (σ.addNode a) :=
    structInv_addNode h (by rw [ha_def]; exact nodeEnc_subjNode t.subject)
  have h0 : StructInv S ((σ.addNode a).addNode b) :=
    structInv_addNode h0a (by rw [hb_def]; exact nodeEnc_objNode t.object t.relation)
  -- a, b are live after adding the endpoint nodes
  have haσ0 : a ∈ ((σ.addNode a).addNode b).nodes :=
    List.mem_cons_of_mem _ List.mem_cons_self
  have hbσ0 : b ∈ ((σ.addNode a).addNode b).nodes := List.mem_cons_self
  -- ensure bridges for a, then b
  have h1a : StructInv S (((σ.addNode a).addNode b).ensureBridges a) :=
    structInv_ensureBridges h0 haσ0
  have hbσ1a : b ∈ (((σ.addNode a).addNode b).ensureBridges a).nodes :=
    ensureBridges_mono hbσ0
  have h1 : StructInv S ((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b) :=
    structInv_ensureBridges h1a hbσ1a
  -- a, b are live in the fully-bridged state
  have haσ1 : a ∈ ((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b).nodes :=
    ensureBridges_mono (ensureBridges_mono haσ0)
  have hbσ1 : b ∈ ((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b).nodes :=
    ensureBridges_mono hbσ1a
  -- add the guarded grant edge
  split
  · rename_i hadmit
    unfold GraphState.admitEdge at hadmit
    simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true'] at hadmit
    obtain ⟨hne, hreach⟩ := hadmit
    have hback : ¬ NReaches ((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b).edges b a := by
      intro hr
      have := reach_complete h1.edgesClosed hr
      rw [this] at hreach; exact Bool.noConfusion hreach
    exact structInv_addEdge h1 haσ1 hbσ1 hback hne
  · exact h

/-! ## Write-effect projections -/

/-- The schema is fixed by the bridge-materializing write. -/
theorem writeWild_schema (σ : GraphState) (t : Tuple) :
    (σ.writeWild t).schema = σ.schema := by
  unfold GraphState.writeWild
  dsimp only
  split
  · simp
  · rfl

/-- Existing nodes persist across the write (nodes are only ever added). -/
theorem writeWild_monoNodes (σ : GraphState) (t : Tuple) :
    ∀ k ∈ σ.nodes, k ∈ (σ.writeWild t).nodes := by
  intro k hk
  unfold GraphState.writeWild
  dsimp only
  have hk0 : k ∈ ((σ.addNode (subjNode t.subject)).addNode
      (objNode t.object t.relation)).nodes :=
    List.mem_cons_of_mem _ (List.mem_cons_of_mem _ hk)
  have hk1 : k ∈ ((((σ.addNode (subjNode t.subject)).addNode
      (objNode t.object t.relation)).ensureBridges (subjNode t.subject)).ensureBridges
      (objNode t.object t.relation)).nodes :=
    ensureBridges_mono (ensureBridges_mono hk0)
  split
  · simpa using hk1
  · exact hk

/-! ## The bridge-model write-closure and its structural invariant -/

/-- **`WildReached σ S T`** — `σ` is reached from the empty state by applying `T`'s
    writes as bridge-materializing writes (`writeWild`). The operational
    reachable-state closure at the object-wildcard fragment's scope (the W1b analog
    of `ReachedByDirect`). -/
inductive WildReached : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : WildReached (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      WildReached σ S T → WildReached (σ.writeWild t) S (t :: T)

/-- **The structural invariant holds at every W1b-reachable state.** By induction
    over the bridge-materializing write path (`structInv_writeWild`): node encoding,
    endpoint closure, and acyclicity (preserved through both the bridge edges and
    the cycle-rejected grant) all survive. The residue clauses and bridge-
    completeness are the deferred content of the correspondence increment. -/
theorem wildReached_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReached σ S T) : StructInv S σ := by
  induction h with
  | empty S => exact structInv_empty S
  | step t _ ih => exact structInv_writeWild ih t

end Zanzibar
