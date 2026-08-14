import ZanzibarProofs.GraphIndex.ObjStarWrite

/-!
# The bridge-materializing write model — userset-wildcard fragment (T2b, stage W1c)

`SEMANTICS.md` §7.2–7.5; `wildcard-materialization-spec.md` §1.1, §7;
ROADMAP "The staged T2 plan", sub-stage **W1c**;
`index_v4/wildcard.py::WildcardIndex._ensure_bridges` /
`::WildcardIndex.add_tuple` → `::WildcardIndex._add_tuple_trusted`;
`zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes`.

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

`zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes`:
`bridged_in_shapes = {s ∈ subject_wildcard_shapes | s.predicate ≠ '...'}`.
Bare shapes `(T,'...')` never need in-bridges (nothing in this
graph points into a `'...'`-predicate node, so a bare-shape hop can only be the
*leading* hop, which probe 2 covers virtually — this is exactly W1a). A subject-
wildcard shape `(T,P)` with `P ≠ BARE` comes from **either** loop of
`zanzibar_utils_v1.py::derive_schema_info`: the FIRST, any literal `[T:*#P]` restriction
in the schema; **or the SECOND, a star-tupleset TTU through-shape** — a TTU `P from ts`
whose tupleset relation carries a bare wildcard `[T:*]`, which the TTU rule rewrites into
a tuple of subject shape `(T,P)`. See `Schema.isStarTuplesetThrough` below.

⚠ **The second loop landed 2026-08-14** (part (i) of the `ttuStarFree` lift). Before that
this header said "the first loop" and meant it: the through-shape was declared out of
scope, and that declaration WAS the hole that made `graph_correct` machine-checked FALSE
without `W4Fragment.ttuStarFree`. Note the consequence for the W4 fragment specifically —
`W4Fragment.wsBare` forces every shape in `wildcardShapes S` to be `BARE`, and
`wildcardShapes` sweeps only LITERAL restrictions, so on W4 the first disjunct is
identically `false` and the in-bridge machinery was dead code. The through-shape disjunct
is *not* filtered by `wsBare`, and that asymmetry is the whole content of part (i).

## The model (`index_v4/wildcard.py::WildcardIndex._add_tuple_trusted` and
`::WildcardIndex._ensure_bridges`)

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

/-- **Star-tupleset TTU through-shape** — the twin of `zanzibar_utils_v1.py::
    derive_schema_info`'s SECOND loop. `(t, p)` is a through-shape when some definition
    `(dt, R) ↦ e` contains a TTU `p from ts` (`exprTtus`, the twin of `::_iter_ttus`) and
    the SAME object type's tupleset relation `(dt, ts)` carries a **bare** wildcard
    restriction `[t:*]`, i.e. `(t, BARE, true) ∈ exprRestrictions` of its body
    (`::_iter_directs` + `r.wildcard and r.predicate == '...'`).

    Python's own rationale, verbatim: *"a wildcard restriction [S:*] on a relation used as
    a TTU tupleset means the TTU rule will rewrite `S:* ts o` into a tuple whose subject
    shape is (S, target_rel) -- that through-shape must be declared or the graph rejects a
    schema-legal write the set engine accepts."*

    Deliberately **one pass, no fixpoint**: Python does not feed derived through-shapes
    back into this loop, and a fixpoint here would be model drift, not fidelity. -/
def Schema.isStarTuplesetThrough (S : Schema) (t p : String) : Bool :=
  S.defs.any (fun d =>
    (exprTtus d.2).any (fun tt =>
      tt.1 == p &&
        (match S.lookup (d.1.1, tt.2) with
         | some ts => (exprRestrictions ts).contains (t, BARE, true)
         | none    => false)))

/-- Is `(t, p)` a subject-wildcard *userset* shape — `p ≠ BARE` and either **(a)** some
    literal `[t:*#p]` restriction (`(t, p, true)`) occurs in the schema
    (`::derive_schema_info`'s FIRST loop), or **(b)** `(t, p)` is a star-tupleset TTU
    through-shape (`::derive_schema_info`'s SECOND loop, `isStarTuplesetThrough`)?
    Together with the outer `p != BARE` — which is `::SchemaInfo.bridged_in_shapes`'s
    final `s[1] != '...'` filter, applied to BOTH disjuncts as in Python — these are
    exactly `zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes`. The graph materializes a
    `concrete → w_any(t,p)` in-bridge for every concrete node of such a shape.

    ⚠ **The outer `p != BARE` must stay OUTERMOST.** `UsStarCorrect.lean::
    bridgedInConcrete_elim` (audited) recovers its `c.pred ≠ BARE` conjunct by
    `Bool.and_eq_true` on this `&&`; pushing the guard inside the disjunction breaks it and,
    through it, the `UsStarReach.inbridge` constructor's `hcp` field.

    **Disjunct (b) landed 2026-08-14** as part (i) of the `ttuStarFree` lift. It is inert
    on its own — no live chain calls `ensureInBridges` yet (`writeRules`/`writeLoggedRules`
    are bridge-free folds), so part (ii) is what materializes the edge. The `#guard`s below
    are therefore this change's ONLY red-to-green evidence; do not delete them. -/
def Schema.isSubjectWildcardUserset (S : Schema) (t p : String) : Bool :=
  p != BARE &&
    (S.defs.any (fun d => (exprRestrictions d.2).contains (t, p, true))
     || S.isStarTuplesetThrough t p)

/-! ## The bridged-in-concrete test and `ensureInBridges` -/

/-- `c` is a concrete *userset* node whose shape `(type, pred)` is a declared
    subject-wildcard userset shape — the nodes that need a `c → w_any` in-bridge
    (the `bridged_in_shapes` arm of `index_v4/wildcard.py::WildcardIndex._ensure_bridges`;
    §5). Only concretes are bridged; the
    `pred ≠ BARE` guard is subsumed by `isSubjectWildcardUserset`. -/
def GraphState.bridgedInConcrete (σ : GraphState) (c : NodeKey) : Bool :=
  c.variant == Variant.plain && c.name != STAR && σ.schema.isSubjectWildcardUserset c.type c.pred

/-! ### Non-vacuity pins for the through-shape disjunct (part (i), 2026-08-14)

★ **These are the ONLY red-to-green evidence that disjunct (b) does anything.** Part (i) is
inert on a live chain until part (ii) composes `ensureInBridges` into `writeRules` /
`writeLoggedRules`, so the narrowest plausible sabotage — *"`isStarTuplesetThrough` returns
`false`"*, the one-line "simplification" a future reader would reach for — reddens NOTHING
else in the tree. It reddens these pins, by `decide`.

**SABOTAGE-VERIFIED 2026-08-14, literal observed output.** Short-circuiting the definition
to `false && S.defs.any …` (the whole rest of the body kept, so the edit stays plausible):

```
error: ZanzibarProofs/GraphIndex/UsStarWrite.lean:146:66: Tactic `decide` proved that the proposition
  Sthru.isSubjectWildcardUserset "folder" "viewer" = true
is false
error: ZanzibarProofs/GraphIndex/UsStarWrite.lean:166:2: Tactic `decide` proved that the proposition
  (emptyState Sthru).bridgedInConcrete { type := "folder", name := "f1", pred := "viewer", variant := Variant.plain } =
    true
is false
```

★ **The red is ATTRIBUTABLE**: under that sabotage the four controls below
(`literal_disjunct_is_false`, `control_one_char_delta_is_not_bridged_in`,
`bare_pred_still_excluded`, `concrete_node_control`) all stay GREEN. A sabotage that
reddened everything would not distinguish "disjunct (b) is load-bearing" from "the file is
broken" — which is the instrument-control half of `docs/sabotage-procedure.md`.

The schema is the 2026-08-10 attack-first counterexample that machine-checked
`graph_correct` FALSE without `W4Fragment.ttuStarFree` (`history/PROOF_STATUS.md`
2026-08-10). ⚠ It carries **no object wildcard** — this is not the I14 bug. -/
namespace ThroughShapeWitness

/-- `viewer: [user]` · `parent: [folder, folder:*]` · `viewer: [user] or viewer from parent`. -/
def Sthru : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent"))], []⟩

/-- **CONTROL — a one-character delta**: `folder:*` → `folder:f1` on `doc#parent`, i.e. the
    wildcard restriction is dropped. Same control the 2026-08-10 probe used. -/
def Sctrl : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent"))], []⟩

/-- **THE SUBJECT.** Was `false` before part (i); the through-shape is now bridged-in. -/
theorem through_shape_is_bridged_in :
    Sthru.isSubjectWildcardUserset "folder" "viewer" = true := by decide

/-- **ATTRIBUTION.** The LITERAL-`[t:*#p]` disjunct (a) is false here, so the subject above
    is carried by disjunct (b) alone and cannot pass for the pre-existing reason. -/
theorem literal_disjunct_is_false :
    Sthru.defs.any (fun d => (exprRestrictions d.2).contains ("folder", "viewer", true)) = false := by
  decide

/-- **THE CONTROL fires**: without the wildcard restriction there is no through-shape. -/
theorem control_one_char_delta_is_not_bridged_in :
    Sctrl.isSubjectWildcardUserset "folder" "viewer" = false := by decide

/-- **SUBSUMPTION.** `BARE` predicates stay out under the outer guard, on both disjuncts —
    the `bridged_in_shapes` filter Python applies after the union. -/
theorem bare_pred_still_excluded :
    Sthru.isSubjectWildcardUserset "folder" BARE = false := by decide

/-- The pin one layer down: the concrete node really does become bridge-eligible. -/
theorem concrete_node_is_bridged :
    (emptyState Sthru).bridgedInConcrete ⟨"folder", "f1", "viewer", Variant.plain⟩ = true := by
  decide

/-- …and under the control it is not. -/
theorem concrete_node_control :
    (emptyState Sctrl).bridgedInConcrete ⟨"folder", "f1", "viewer", Variant.plain⟩ = false := by
  decide

end ThroughShapeWitness

/-- **Ensure the in-bridge for a concrete userset endpoint**
    (`index_v4/wildcard.py::WildcardIndex._ensure_bridges`, `bridged_in_shapes` arm):
    if `c` is a concrete node of a bridged-in shape, create the
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

/-- **The userset-star bridge-materializing single-tuple write**
    (`index_v4/wildcard.py::WildcardIndex.add_tuple` →
    `::WildcardIndex._add_tuple_trusted`): add both endpoint nodes, ensure the
    out-bridges (W1b —
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
