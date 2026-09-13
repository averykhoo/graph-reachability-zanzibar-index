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
    `w_any(c.type, c.pred)` node (lazily) and — **iff no copy of the bridge edge is
    already present** — add the bridge edge `c → w_any`, under the same cycle-rejection
    guard the core edge-add uses. A non-bridged node is left untouched. The caller
    ensures `c` is already a live node.

    ⚠ **The presence guard is `P6` step 2 (2026-09-13b) and it is a FIDELITY repair, not
    an optimization.** Until then this definition re-added the edge unconditionally, so it
    was idempotent on `NReaches` (membership, not multiplicity) and NOT idempotent on the
    edge MULTISET: `formal/probes/p6_step1_logged_bridge_2026-09-13.lean` measured
    `(0 calls, 1, 2, 3) = (0, 1, 2, 3)` bridge copies. That was inert only because no live
    chain called it (see `isSubjectWildcardUserset`'s note); increment B calls it **once per
    member of the leaf-routed list**, so copies would accumulate per write — the
    `_leak_accumulates` shape. Python does not: `index_v4/wildcard.py::WildcardIndex.
    _ensure_own_bridges` interns the `w_any` node and then guards with
    `if not self.idx.direct_edge_exists_by_id(node.id, w_any.id)` before `add_edge_by_id`.
    The guard order here is Python's: intern first (the node is added on every bridged
    branch, present edge included), test the edge second. The multiset statement is pinned
    by `ensureInBridges_idem` + `InBridgeIdemWitness` below — do not weaken either to a
    reachability-level claim, which is what let this through for a month. -/
def GraphState.ensureInBridges (σ : GraphState) (c : NodeKey) : GraphState :=
  if σ.bridgedInConcrete c then
    if (c, wAnyNode (c.type, c.pred)) ∈ σ.edges then
      σ.addNode (wAnyNode (c.type, c.pred))
    else if (σ.addNode (wAnyNode (c.type, c.pred))).admitEdge c (wAnyNode (c.type, c.pred)) then
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

/-- **The bridge-before-grant PROLOGUE of a leaf-routed write** — `P6` increment B,
    step 3. `GraphState.writeBridgedOne` below is the unlogged twin of
    `Cascade.lean::GraphState.writeLoggedOne`, and the per-member step
    `LeafRules.lean::GraphState.writeRulesRaw` folds. It is `writeDirect` with Python's
    bridge-before-grant prologue on BOTH endpoints
    (`index_v4/wildcard.py::WildcardIndex._add_tuple_trusted`'s `_ensure_bridges(subject)`
    then `_ensure_bridges(obj)`), and nothing else.

    ⚠ **Why this is NOT `writeUsStar`, which is one line above and would have been free.**
    That one also runs `ensureBridges` (the W1b OUT-bridges) and would have brought its
    whole existing theory with it — a real temptation. Rejected: out-bridges are the
    object-wildcard mechanism, `P6` is the SUBJECT-wildcard one, and widening the live
    write leg by a second mechanism in the same edit would make any resulting divergence
    unattributable. Python does run both (`_ensure_bridges` = `_ensure_own_bridges` +
    `_ensure_entity_middles`), so this is a deliberate NARROWING of the model, recorded as
    such: on this fragment the out-bridge arm is inert (no object wildcards, nothing
    crossable — the entity-middle boundary entry in `formal/CORRESPONDENCE.md` §7).

    ⚠ **The node prologue is NOT decoration.** `structInv_ensureInBridges` needs
    `c ∈ σ.nodes` — a bridge out of a node that does not exist breaks
    `StructInv.edgesClosed` — and Python resolves both endpoints with `create=True`
    BEFORE `_ensure_bridges`. So `addNode` first, bridge second, grant third, exactly as
    `writeUsStar` does it. The consequence for `LeafRules.lean::writeRulesRaw_untaintedSchema`
    is real and is step 3's to pay: the admission probe now reads the BRIDGED state, so
    this is no longer definitionally `writeDirect` even where no shape is bridged.

    **The rollback is Python's, not a modelling convenience.** A rejected grant returns
    `σ`, discarding the bridges: `_add_tuple_trusted` raises `AdmissionRejected` out of
    `add_edge_by_id` and the whole write aborts with its transaction, bridges included.
    `writeUsStar` already models the same thing the same way (`:251`).

    ⚠ **The prologue is a NAMED definition, not a `let`.** `writeUsStar` above binds its
    stages with `let`, which elaborates to `have` in a goal and then **blocks `split`** —
    every downstream proof has to `dsimp only` first. `writeLoggedOne`'s cone is far too
    large to pay that at every site, so the bridged pre-state gets a name here and the
    write stays a top-level `if` that `split` can see. -/
def GraphState.bridgePre (σ : GraphState) (t : Tuple) : GraphState :=
  (((σ.addNode (subjNode t.subject)).addNode (objNode t.object t.relation)).ensureInBridges
    (subjNode t.subject)).ensureInBridges (objNode t.object t.relation)

/-- One leaf-routed write, bridged and UNLOGGED — see `GraphState.bridgePre` above for the
    full rationale (this is the guarded grant on top of that prologue). -/
def GraphState.writeBridgedOne (σ : GraphState) (t : Tuple) : GraphState :=
  if (σ.bridgePre t).admitEdge (subjNode t.subject) (objNode t.object t.relation)
  then (σ.bridgePre t).addEdge (subjNode t.subject) (objNode t.object t.relation)
  else σ

/-! ## Schema is fixed by the in-bridge machinery -/

@[simp] theorem ensureInBridges_schema (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridges c).schema = σ.schema := by
  unfold GraphState.ensureInBridges
  split
  · split
    · simp
    · split <;> simp
  · rfl

/-- Residues are untouched by the in-bridge machinery — it only ever adds a node and an
    edge. (Added by `P6` step 2 for `Cascade.lean::ensureInBridgesLogged_residue`; the
    `schema` twin above had been enough while nothing downstream needed `residue`.) -/
@[simp] theorem ensureInBridges_residue (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridges c).residue = σ.residue := by
  unfold GraphState.ensureInBridges
  split
  · split
    · simp
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
    · exact hk'
    · split
      · simpa using hk'
      · exact hk'
  · rw [if_neg hbr]; exact hk

/-! ## ★ The bridge multiplicity is at most one (`P6` step 2, 2026-09-13b)

The property the presence guard exists for, stated on the edge **multiset** — the level at
which the old definition was wrong and at which every reachability-shaped statement in this
file is blind. `ensureInBridges_count_le_one` is an INVARIANT, not a one-shot idempotence
claim: that is the form the step-3 fold needs, where `writeLoggedOne`'s leaf-routed list
calls the bridge once per member and the interesting state is the one after `k` calls, not
after two. -/

/-- The bridged edge is left alone when a copy is already present — the presence branch,
    isolated for reuse. Mirrors the short-circuit in `index_v4/wildcard.py::WildcardIndex.
    _ensure_own_bridges` (`if not …direct_edge_exists_by_id`): the `w_any` node is still
    interned, only the edge-add is skipped. -/
theorem ensureInBridges_edges_of_mem {σ : GraphState} {c : NodeKey}
    (h : (c, wAnyNode (c.type, c.pred)) ∈ σ.edges) :
    (σ.ensureInBridges c).edges = σ.edges := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr, if_pos h, addNode_edges]
  · rw [if_neg hbr]

/-- ★ **`ensureInBridges` never lets the bridge edge exceed multiplicity one.** With the
    presence guard this is an inductive invariant of the write leg: the bridged branch adds
    a copy only when `count = 0`. Without the guard it is FALSE — the measured
    `(0 calls, 1, 2, 3) = (0, 1, 2, 3)` of
    `formal/probes/p6_step1_logged_bridge_2026-09-13.lean` §9 is a counterexample at the
    second call — so this theorem is the positive pin for the P6-step-2 fidelity repair
    (`docs/sabotage-procedure.md` prefers a positive pin to an `xfail`, and a permanent
    statement to a probe). `InBridgeIdemWitness` below supplies the red-to-green arm. -/
theorem ensureInBridges_count_le_one {σ : GraphState} {c : NodeKey}
    (h : σ.edges.count (c, wAnyNode (c.type, c.pred)) ≤ 1) :
    (σ.ensureInBridges c).edges.count (c, wAnyNode (c.type, c.pred)) ≤ 1 := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr]
    by_cases hpres : (c, wAnyNode (c.type, c.pred)) ∈ σ.edges
    · rw [if_pos hpres, addNode_edges]; exact h
    · rw [if_neg hpres]
      have h0 : σ.edges.count (c, wAnyNode (c.type, c.pred)) = 0 :=
        List.count_eq_zero.mpr hpres
      split
      · rw [addEdge_edges, addNode_edges, List.count_cons_self, h0]
      · rw [addNode_edges]; exact h
  · rw [if_neg hbr]; exact h

/-! ### ★ Red-to-green witness for the presence guard

The invariant above is provable from the guard and *unprovable without it*, but a reader
cannot see that from the statement. These pins are the executable half: the literal
`(0, 1, 2, 3)` measurement from the step-1 probe, re-run as `decide` against the shipped
definition, where it now reads `(0, 1, 1, 1)`. Delete the guard and `copies_2` / `copies_3`
red by `decide` with the observed multiplicities printed in the error.

⚠ **Non-vacuity, per arm** (`P6` step 0's lesson): `bridged_control` asserts the node is
actually bridge-eligible, and `unbridged_control` asserts the count stays `0` at a node of
the SAME store that is not — without both, a state where `ensureInBridges` is the identity
would satisfy `copies_*` and prove nothing.

**SWEPT, and the table is one file over**: these pins are swept together with the three
legs that consume them, in `GraphIndex/Cascade.lean`'s §"CONTROLLED — MUTATION SWEEP over
everything `P6` step 2 added". Dropping the guard (`M1`) reds `copies_2`, `copies_3`,
`edges_are_the_bridge_alone`, `ensureInBridges_count_le_one` **and**
`Cascade.lean::InBridgeLegWitness.logged_second_call_silent`; reversing it (`M2`) reds the
same set bar the schema/mono projections; `M11`/`M12` are the witness-side mutations that
earn the two controls their red. `copies_0` is never reddened and says so there. -/
namespace InBridgeIdemWitness

/-- The through-shape concrete of `ThroughShapeWitness.Sthru`. -/
def c0 : NodeKey := ⟨"folder", "f1", "viewer", Variant.plain⟩

/-- Its `w_any` bridge target. -/
def w0 : NodeKey := wAnyNode (c0.type, c0.pred)

/-- A node of the same store that is NOT of a bridged-in shape (`doc#parent` is not a
    subject-wildcard userset shape), used as the attribution control. -/
def cUn : NodeKey := ⟨"doc", "d1", "parent", Variant.plain⟩

/-- The caller's precondition: `c0` is live before the bridge is ensured. -/
def base : GraphState := (emptyState ThroughShapeWitness.Sthru).addNode c0

/-- `n` successive `ensureInBridges c0` calls — the shape a leaf-routed fold produces when
    the same subject appears in more than one routed member (the step-1 probe's `tSub`
    had two). -/
def callN : Nat → GraphState
  | 0     => base
  | n + 1 => (callN n).ensureInBridges c0

/-- **NON-VACUITY**: the subject really is bridge-eligible here. -/
theorem bridged_control : base.bridgedInConcrete c0 = true := by decide

/-- **ATTRIBUTION CONTROL**: an un-bridged node of the same store never gains the edge, so
    the counts below are the guard's doing and not a state that changes under every call. -/
theorem unbridged_control :
    ((base.ensureInBridges cUn).edges.count (cUn, wAnyNode (cUn.type, cUn.pred))) = 0 := by
  decide

theorem copies_0 : ((callN 0).edges.count (c0, w0)) = 0 := by decide
theorem copies_1 : ((callN 1).edges.count (c0, w0)) = 1 := by decide

/-- ★ **The pin that was FALSE before the guard** (measured `2`). -/
theorem copies_2 : ((callN 2).edges.count (c0, w0)) = 1 := by decide

/-- ★ **The pin that was FALSE before the guard** (measured `3`) — two calls could be an
    accident of `admitEdge`, three cannot. -/
theorem copies_3 : ((callN 3).edges.count (c0, w0)) = 1 := by decide

/-- The whole edge list stays a singleton, not merely the counted entry: a guard that
    dropped the duplicate but added some OTHER edge would satisfy `copies_*`. -/
theorem edges_are_the_bridge_alone : (callN 3).edges = [(c0, w0)] := by decide

end InBridgeIdemWitness

/-! ## Structural-invariant preservation -/

/-- **`ensureInBridges` preserves the structural invariant** (given the concrete
    endpoint is already live). On the non-bridged branch the state is unchanged; on
    the bridged branch the `w_any` node is encoding-valid (`nodeEnc_wAnyNode`) and the
    bridge edge is admitted by cycle-rejection, so `structInv_addNode` /
    `structInv_addEdge` apply. The P6-step-2 presence branch adds the node and no edge,
    so `structInv_addNode` alone discharges it. -/
theorem structInv_ensureInBridges {S : Schema} {σ : GraphState} (h : StructInv S σ)
    {c : NodeKey} (hc : c ∈ σ.nodes) : StructInv S (σ.ensureInBridges c) := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr]
    set w := wAnyNode (c.type, c.pred) with hw_def
    have h1 : StructInv S (σ.addNode w) :=
      structInv_addNode h (by rw [hw_def]; exact nodeEnc_wAnyNode (c.type, c.pred))
    -- the presence branch adds no edge at all (P6 step 2)
    by_cases hpres : (c, w) ∈ σ.edges
    · rw [if_pos hpres]; exact h1
    rw [if_neg hpres]
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

/-! ## ★ `writeBridgedOne` preservation — `P6` increment B, step 3 (2026-09-13d)

The fold family `LeafRules.lean::writeRulesRaw` used to inherit for free from
`RulesWrite.lean`'s `∀ (ts : List Tuple)` lemmas about `writeDirect` (scope doc §11.1's
"fork the TUPLE, not the write path"). Composing the bridge forks the write path after
all, so the five preservation facts are re-proved here for the bridged step and re-folded.
Each one mirrors its `writeUsStar` twin above, minus the out-bridge layer. -/

/-- The in-bridge machinery never touches the outbox (it only adds a node and an edge) —
    needed for `quiescent_writeBridgedOne`. -/
@[simp] theorem ensureInBridges_outbox (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridges c).outbox = σ.outbox := by
  unfold GraphState.ensureInBridges
  split
  · split
    · rfl
    · split <;> rfl
  · rfl

/-- …nor the watermark. -/
@[simp] theorem ensureInBridges_watermark (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridges c).watermark = σ.watermark := by
  unfold GraphState.ensureInBridges
  split
  · split
    · rfl
    · split <;> rfl
  · rfl

/-- The bridged leaf-routed step preserves the structural invariant — the same argument as
    `structInv_writeUsStar`, with the out-bridge layer removed. -/
theorem structInv_writeBridgedOne {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeBridgedOne t) := by
  unfold GraphState.writeBridgedOne GraphState.bridgePre
  set a := subjNode t.subject with ha_def
  set b := objNode t.object t.relation with hb_def
  have h0a : StructInv S (σ.addNode a) :=
    structInv_addNode h (by rw [ha_def]; exact nodeEnc_subjNode t.subject)
  have h0 : StructInv S ((σ.addNode a).addNode b) :=
    structInv_addNode h0a (by rw [hb_def]; exact nodeEnc_objNode t.object t.relation)
  have haσ0 : a ∈ ((σ.addNode a).addNode b).nodes :=
    List.mem_cons_of_mem _ List.mem_cons_self
  have hbσ0 : b ∈ ((σ.addNode a).addNode b).nodes := List.mem_cons_self
  have h2a : StructInv S (((σ.addNode a).addNode b).ensureInBridges a) :=
    structInv_ensureInBridges h0 haσ0
  have hbσ2a : b ∈ (((σ.addNode a).addNode b).ensureInBridges a).nodes :=
    ensureInBridges_mono hbσ0
  have h2 : StructInv S ((((σ.addNode a).addNode b).ensureInBridges a).ensureInBridges b) :=
    structInv_ensureInBridges h2a hbσ2a
  set σ2 := (((σ.addNode a).addNode b).ensureInBridges a).ensureInBridges b with hσ2_def
  have haσ2 : a ∈ σ2.nodes := ensureInBridges_mono (ensureInBridges_mono haσ0)
  have hbσ2 : b ∈ σ2.nodes := ensureInBridges_mono hbσ2a
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

/-- The bridged step keeps the schema fixed. -/
@[simp] theorem writeBridgedOne_schema (σ : GraphState) (t : Tuple) :
    (σ.writeBridgedOne t).schema = σ.schema := by
  unfold GraphState.writeBridgedOne GraphState.bridgePre
  split <;> simp

/-- The bridged step leaves the outbox alone (it is the UNLOGGED twin — that is the whole
    difference between it and `Cascade.lean::writeLoggedOne`). -/
@[simp] theorem writeBridgedOne_outbox (σ : GraphState) (t : Tuple) :
    (σ.writeBridgedOne t).outbox = σ.outbox := by
  unfold GraphState.writeBridgedOne GraphState.bridgePre
  split <;> simp [GraphState.addEdge, GraphState.addNode]

/-- …and the watermark. -/
@[simp] theorem writeBridgedOne_watermark (σ : GraphState) (t : Tuple) :
    (σ.writeBridgedOne t).watermark = σ.watermark := by
  unfold GraphState.writeBridgedOne GraphState.bridgePre
  split <;> simp [GraphState.addEdge, GraphState.addNode]

/-- The bridged step never touches a residue (untainted fragment; bridges are nodes and
    edges only). -/
@[simp] theorem writeBridgedOne_residue (σ : GraphState) (t : Tuple) :
    (σ.writeBridgedOne t).residue = σ.residue := by
  unfold GraphState.writeBridgedOne GraphState.bridgePre
  split <;> simp

/-- The bridged step never drops a residue. -/
theorem residueEmpty_writeBridgedOne {σ : GraphState} (t : Tuple) (h : ResidueEmpty σ) :
    ResidueEmpty (σ.writeBridgedOne t) := by
  intro k r
  rw [writeBridgedOne_residue]
  exact h k r

/-- The bridged step preserves the full `Inv` on the residue-free fragment — structural
    clauses from `structInv_writeBridgedOne`, residue clauses vacuous under
    `ResidueEmpty`. -/
theorem inv_writeBridgedOne {S : Schema} {σ : GraphState} (h : Inv S σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S (σ.writeBridgedOne t) := by
  have hstruct := structInv_writeBridgedOne h.toStruct t
  have hre' := residueEmpty_writeBridgedOne t hre
  exact
    { schemaEq := hstruct.schemaEq
      nodeEnc := hstruct.nodeEnc
      edgesClosed := hstruct.edgesClosed
      acyclic := hstruct.acyclic
      negStarCovered := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      negEdgeFree := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      uposEdgeFree := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      uposNegDisjoint := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res) }

/-- The bridged step preserves cascade-quiescence (outbox/watermark untouched). -/
theorem quiescent_writeBridgedOne {σ : GraphState} (hq : Quiescent σ) (t : Tuple) :
    Quiescent (σ.writeBridgedOne t) := by
  intro d hd
  rw [writeBridgedOne_outbox] at hd
  rw [writeBridgedOne_watermark]
  exact hq d hd

/-! ### The fold family — the drop-in replacements for `RulesWrite.lean`'s
`*_foldl_writeDirect` at `LeafRules.lean`'s five corollaries. -/

theorem structInv_foldl_writeBridgedOne {S : Schema} (ts : List Tuple) :
    ∀ {σ : GraphState}, StructInv S σ →
      StructInv S (ts.foldl (fun acc u => acc.writeBridgedOne u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (structInv_writeBridgedOne h t)

theorem residueEmpty_foldl_writeBridgedOne (ts : List Tuple) :
    ∀ {σ : GraphState}, ResidueEmpty σ →
      ResidueEmpty (ts.foldl (fun acc u => acc.writeBridgedOne u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (residueEmpty_writeBridgedOne t h)

theorem inv_foldl_writeBridgedOne {S : Schema} (ts : List Tuple) :
    ∀ {σ : GraphState}, Inv S σ → ResidueEmpty σ →
      Inv S (ts.foldl (fun acc u => acc.writeBridgedOne u) σ) := by
  induction ts with
  | nil => intro σ h _; exact h
  | cons t rest ih =>
    intro σ h hre
    exact ih (inv_writeBridgedOne h hre t) (residueEmpty_writeBridgedOne t hre)

theorem quiescent_foldl_writeBridgedOne (ts : List Tuple) :
    ∀ {σ : GraphState}, Quiescent σ →
      Quiescent (ts.foldl (fun acc u => acc.writeBridgedOne u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (quiescent_writeBridgedOne h t)

theorem schema_foldl_writeBridgedOne (ts : List Tuple) :
    ∀ {σ : GraphState},
      (ts.foldl (fun acc u => acc.writeBridgedOne u) σ).schema = σ.schema := by
  induction ts with
  | nil => intro σ; rfl
  | cons t rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih]; exact writeBridgedOne_schema σ t

/-! ### ★ Red-to-green witnesses for the bridged step (`P6` step 3a, 2026-09-13d)

`writeBridgedOne` is ADDITIVE: `writeRulesRaw` still folds `writeDirect`, so the whole
ten-phase gate stays green if every definition above is wrong. That is the same position
part (i) of `ttuStarFree` sat in for a month (`:112`), and the response is the same one:
`decide` pins are the ONLY evidence, and each carries its own non-vacuity or attribution
control (`docs/sabotage-procedure.md`).

The store is `ThroughShapeWitness.Sthru`, so a reader comparing these with
`InBridgeIdemWitness` and `Cascade.lean::InBridgeLegWitness` sees ONE scenario throughout.
⚠ `control_agrees_with_writeDirect` is the load-bearing control: without it,
`bridged_creates_the_bridge` would be satisfied by a `writeBridgedOne` that differs from
`writeDirect` *everywhere*, which would say nothing about the bridge. -/
namespace BridgedWriteWitness

/-- The TTU-rewritten member this whole item exists for: the through-shape subject
    `folder:f1#viewer` granting `doc:d1#viewer`. -/
def tThru : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "viewer", ⟨"doc", "d1"⟩⟩

/-- The SAME subject, a second object — the shape a leaf-routed fold produces when two
    routed members share a subject (the step-1 probe's `tSub` had exactly two). -/
def tThru2 : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "viewer", ⟨"doc", "d2"⟩⟩

/-- **CONTROL member**: neither endpoint is of a bridged-in shape (`(folder, BARE)` is
    filtered by the outer `p ≠ BARE`; `(doc, parent)` is not a through-shape — `doc#parent`
    carries `[folder:*]`, not `[doc:*]`). -/
def tCtrl : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

/-- A grant whose two endpoints are the SAME node, so admission refuses it — the arm that
    shows the rollback is real. -/
def tSelf : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "viewer", ⟨"folder", "f1"⟩⟩

def base : GraphState := emptyState ThroughShapeWitness.Sthru

/-- The bridge target of `tThru`'s subject. -/
def w0 : NodeKey := wAnyNode ("folder", "viewer")

/-- **NON-VACUITY**: the subject endpoint really is bridge-eligible at this store, so the
    bridged branch of `bridgePre` is the one being exercised. -/
theorem subject_is_bridged_in :
    base.bridgedInConcrete (subjNode tThru.subject) = true := by decide

/-- **NON-VACUITY**: the OBJECT endpoint is not, so these pins are about the subject
    bridge and a future reader cannot mistake which `ensureInBridges` call fired. -/
theorem object_is_not_bridged_in :
    base.bridgedInConcrete (objNode tThru.object tThru.relation) = false := by decide

/-- ★ **THE POINT OF `P6` (ii): the bridged step materialises the in-bridge.** -/
theorem bridged_creates_the_bridge :
    (subjNode tThru.subject, w0) ∈ (base.writeBridgedOne tThru).edges := by decide

/-- ★ **…and `writeDirect` — what the live leg still folds until step 3b — does not.**
    This is the divergence from `index_v4/wildcard.py::WildcardIndex._ensure_own_bridges`,
    exhibited rather than described. -/
theorem writeDirect_misses_the_bridge :
    (subjNode tThru.subject, w0) ∉ (base.writeDirect tThru).edges := by decide

/-- The grant survives the prologue: bridging does not cost the edge the write was for. -/
theorem bridged_keeps_the_grant :
    (subjNode tThru.subject, objNode tThru.object tThru.relation)
      ∈ (base.writeBridgedOne tThru).edges := by decide

/-- ★ **ATTRIBUTION CONTROL**: at a member with no bridged-in endpoint the bridged step
    and `writeDirect` agree on the edges. So the two pins above are the BRIDGE's doing,
    not "the two definitions differ everywhere". -/
theorem control_agrees_with_writeDirect :
    (base.writeBridgedOne tCtrl).edges = (base.writeDirect tCtrl).edges := by decide

/-- ★ **The presence guard survives COMPOSITION** — the property step 3b makes live, and
    the reason `ensureInBridges_count_le_one` is an invariant rather than a two-call
    idempotence claim. Folding the bridged step over two members that share a subject
    leaves exactly ONE copy of the bridge; before the step-2 guard this read `2`. -/
theorem fold_keeps_one_bridge_copy :
    (([tThru, tThru2].foldl (fun acc u => acc.writeBridgedOne u) base).edges.count
      (subjNode tThru.subject, w0)) = 1 := by decide

/-- A member whose **OBJECT** endpoint is of a bridged-in shape: `user:u1` granted
    `folder:f1#viewer`, whose object node IS the through-shape concrete.

    ⚠ **This arm exists because the sweep asked for it.** With only `tThru`, mutation `M2`
    — *bridge the SUBJECT only, dropping Python's `_ensure_bridges(obj)` call* — reddened
    `structInv_writeBridgedOne` and NOTHING ELSE: a broken PROOF, not a broken claim, and
    a future rewrite of that proof would have retired the only evidence. The arms below
    are the behavioural pin, and they are the reason
    `object_is_not_bridged_in` above states which endpoint `tThru` exercises. -/
def tObj : Tuple := ⟨⟨"user", "u1", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩

/-- **NON-VACUITY**: `tObj`'s object endpoint really is bridge-eligible… -/
theorem object_endpoint_is_bridged_in :
    base.bridgedInConcrete (objNode tObj.object tObj.relation) = true := by decide

/-- …and its SUBJECT endpoint is not (a `BARE` predicate is filtered by the outer guard),
    so the pin below is the object-side `ensureInBridges` call and cannot be passed off as
    the subject-side one. -/
theorem tObj_subject_is_not_bridged_in :
    base.bridgedInConcrete (subjNode tObj.subject) = false := by decide

/-- ★ **Python bridges BOTH endpoints, and so does this**: the object-side bridge fires. -/
theorem object_bridge_fires :
    (objNode tObj.object tObj.relation, w0) ∈ (base.writeBridgedOne tObj).edges := by decide

/-- …and `writeDirect` misses it, exactly as it misses the subject-side one. -/
theorem writeDirect_misses_the_object_bridge :
    (objNode tObj.object tObj.relation, w0) ∉ (base.writeDirect tObj).edges := by decide

/-- A wildcard-userset grant whose OBJECT is the very concrete its own bridge points out
    of: `folder:*#viewer viewer folder:f1`. The bridge `folder:f1#viewer → w_any` closes a
    cycle with it.

    ⚠ **This arm also exists because the sweep asked for it**: mutation `M5` — *probe
    admission on the UNBRIDGED state* — reddened only `structInv_writeBridgedOne`, so
    "bridge-before-grant" had no behavioural pin. It has one now, and the pair below is
    what makes the ORDER observable rather than a stated preference. -/
def tCycle : Tuple := ⟨⟨"folder", STAR, "viewer"⟩, "viewer", ⟨"folder", "f1"⟩⟩

/-- ★ **Bridge-before-grant REFUSES it** — Python's order, where "cycle errors then attach
    to the grant (the offending write)". -/
theorem bridged_probe_refuses_the_cycle :
    (base.bridgePre tCycle).admitEdge (subjNode tCycle.subject)
      (objNode tCycle.object tCycle.relation) = false := by decide

/-- ★ **ATTRIBUTION**: the UNBRIDGED probe ADMITS the same grant. So the refusal above is
    the bridge's doing, and a model that probed admission before bridging would accept a
    write the shipped index rejects. -/
theorem unbridged_probe_admits_the_cycle :
    base.admitEdge (subjNode tCycle.subject)
      (objNode tCycle.object tCycle.relation) = true := by decide

/-- ★ **…so the write materialises NOTHING** — bridge and grant roll back together. This
    is the arm that actually observes the ORDER through `writeBridgedOne`: the two pins
    above sit on `bridgePre` and `admitEdge` directly, and the sweep showed (`M5`) that a
    definition probing the unbridged state leaves both of them green. -/
theorem cycle_write_materialises_nothing :
    (base.writeBridgedOne tCycle).edges = base.edges := by decide

/-- **NON-VACUITY for the rollback arm**: the self-grant really is refused. -/
theorem self_grant_is_refused :
    (base.bridgePre tSelf).admitEdge (subjNode tSelf.subject)
      (objNode tSelf.object tSelf.relation) = false := by decide

/-- ★ **The rollback is Python's**: a refused grant discards the bridges with it, so a
    write the index rejects leaves no edge behind. Were the else-branch `σ₂` instead of
    `σ`, this would hold the bridge. -/
theorem refused_write_leaves_no_bridge :
    (base.writeBridgedOne tSelf).edges = base.edges := by decide

end BridgedWriteWitness

/-! ### ★ CONTROLLED — MUTATION SWEEP over everything `P6` step 3a added (2026-09-13d)

Eleven mutations, run against the whole `Cascade` target (so both files are covered by one
run, as step 2's sweep was). Harness: `.scratch/p6-step3/sweep.py`, anchors read with
`newline=''` and asserted to occur EXACTLY once — the step-2 lesson, where ten of fourteen
anchors matched zero times on a CRLF/LF mismatch and the run read like a clean module.
Literal observed output, restored baseline `rc=0`:

```text
M0   RED  flip `subject_is_bridged_in`'s own claim   -> UsStarWrite::subject_is_bridged_in
M1   RED  drop BOTH bridges from `bridgePre`         -> structInv_writeBridgedOne,
          bridged_creates_the_bridge, fold_keeps_one_bridge_copy, object_bridge_fires,
          bridged_probe_refuses_the_cycle
M2   RED  bridge the SUBJECT only                    -> structInv_writeBridgedOne,
          object_bridge_fires, bridged_probe_refuses_the_cycle
M3   RED  bridge the OBJECT twice, never the subject -> structInv_writeBridgedOne,
          bridged_creates_the_bridge, fold_keeps_one_bridge_copy
M4   RED  keep bridges when the grant is REFUSED     -> structInv_writeBridgedOne,
          cycle_write_materialises_nothing, refused_write_leaves_no_bridge
M5   RED  probe admission on the UNBRIDGED state     -> structInv_writeBridgedOne,
          cycle_write_materialises_nothing
M6   RED  drop the step-2 PRESENCE GUARD             -> ensureInBridges_edges_of_mem,
          ensureInBridges_count_le_one, copies_2, copies_3, edges_are_the_bridge_alone,
          structInv_ensureInBridges, fold_keeps_one_bridge_copy
M7   RED  logged prologue made UNLOGGED              -> Cascade::bridgePreLogged_evalEq,
          Cascade::prologue_emits, Cascade::prologue_outboxes_differ
M8   RED  release the OBJECT endpoint only           -> Cascade::epilogue_fires
M9   RED  release epilogue made the IDENTITY         -> Cascade::epilogue_fires
M10  INERT release without the bridged-in guard
```

★ **`M6` is the row that justifies step 3a as a unit.** Dropping the step-2 presence guard
now reds `fold_keeps_one_bridge_copy` — a COMPOSED pin — as well as step 2's own
single-call ones, so the guard and the composition are pinned together, which is what
`ensureInBridges_count_le_one`'s invariant form was chosen for.

⚠ **Attribution lists for a mutation of THIS file are TRUNCATED, and the harness cannot
help it.** `Cascade` imports `UsStarWrite`, so when `M1`–`M6` red a declaration here the
build never compiles `Cascade` and no `Cascade::` pin is ever evaluated. Read those rows
as "reds at least these", never as "reds only these" — in particular `M6` very likely reds
`Cascade::prologue_second_member_silent` too, and this sweep did **not** observe that.
`M7`–`M10` mutate `Cascade` itself and so carry complete lists.

⚠ **Two arms of this file exist only because the sweep asked for them, and that is the
point of sweeping instead of sabotaging once.** On the first run `M2` and `M5` reddened
`structInv_writeBridgedOne` and **nothing else** — a broken PROOF, not a broken claim, so
rewriting that proof would have retired the only evidence that the model bridges BOTH
endpoints and bridges BEFORE the grant. `BridgedWriteWitness.tObj` and `::tCycle` are the
behavioural pins added in response; `M2`/`M5` red them now. Note also that `tCycle`'s first
two pins were NOT enough: they sit on `bridgePre`/`admitEdge` directly, and `M5` mutates
`writeBridgedOne`, so `cycle_write_materialises_nothing` — which reads the write — is the
arm that actually observes the order.

⚠ **`M10` is INERT and says so rather than being deleted or dressed up.** Dropping
`bridgedInConcrete` from `Cascade.lean::inBridgeOnly` changes no observation, because the
release then fires at nodes with no bridge edge to erase and `removeEdgeOne` on an absent
edge is the identity. This is the SAME row step 2's sweep recorded as `M6`; the conjunct is
defensive. Do not delete it on the strength of that, and do not cite it as load-bearing.

⚠ **What this sweep does NOT cover, stated so the next session does not mistake silence
for coverage.** Every definition above is ADDITIVE — `writeRulesRaw` still folds
`writeDirect` and `writeLoggedOne` is still bridge-free — so the ten-phase gate is blind to
all of it, and these `decide` pins are the entire net. In particular no conformance test,
no hypothesis campaign and no golden can see a regression here until `P6` step 3b
re-points the live legs. -/

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
