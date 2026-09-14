import ZanzibarProofs.GraphIndex.ReconcileDiff
-- Step 4c-ii, THE FLIP: the live logged write leg is now leaf-routed, so this module
-- needs `Leaf.lean::rawWriteTuples`, `LeafRules.lean::rewriteClosureL` and
-- `LeafRules.lean::GraphState.writeRulesRaw`. (⚠ The three line numbers this comment
-- carried until 2026-09-14 were ALL stale — `:762`/`:214`/`:255` against live
-- `:793`/`:229`/`:336`. Symbols only from here on; grep, do not trust a number.)
-- **Cycle-checked by transitive
-- closure**: `LeafRules`' import cone is `Leaf` → {`Write`, `RulesWrite`,
-- `Spec.Stabilize`} plus `RulesSound`'s 29-module cone, and no module in it is a
-- `Cascade*` module, so no cycle is created and no new module is added to the build.
import ZanzibarProofs.GraphIndex.LeafRules
-- `P6` step 2 (increment B, the in-bridge on the leaf-routed write path): this module
-- needs `GraphState.ensureInBridges` / `::bridgedInConcrete` (`UsStarWrite.lean:213`,
-- `:127`) to define their LOGGED and RELEASE counterparts next to `pushDelta` /
-- `removeEdgeOne`, which is where step 3 composes them into `writeLoggedOne` /
-- `removeLoggedOne`. **Cycle-checked by transitive closure, as the `LeafRules` note
-- above was**: `UsStarWrite`'s 18-module cone is Mathlib + `Core.*` + {`GraphIndex.
-- State`, `Write`, `Closure`, `ObjStarWrite`} + `Spec.Stratify`, and contains no
-- `Cascade*` module and no `Reconcile*` module, so the edge `Cascade → UsStarWrite` is
-- acyclic and adds no module to the build (all 18 are already in `Cascade`'s own cone
-- except `ObjStarWrite`/`UsStarWrite` themselves). Measured 2026-09-13b.
import ZanzibarProofs.GraphIndex.UsStarWrite

/-!
# The cascade scheduling layer — logged writes, delta→key mapping, the drain loop (ROADMAP W3d-1a)

`index_v4/processor.py::DeltaProcessor.run_cascade` (a thin `_node_cache_scope()`
wrapper) → `::DeltaProcessor._run_cascade` (the modeled body),
`::DeltaProcessor._map_deltas_to_keys`, `::DeltaProcessor._fan_out`;
`index_v4/core.py::ReachabilityIndex._emit` (buffered) + `::ReachabilityIndex._flush_outbox`;
`index_v4/outbox.py`; `connectedstore/apply.py::advance_index`; boolean spec §5.1–5.2.
Design + faithfulness notes: ROADMAP "W3d — the multi-stratum cascade".

W3a–W3c treated a reconcile pass as an externally-scheduled batch job. **W3d models the
scheduler**: writes emit outbox deltas inside the transaction, `_run_cascade` maps the
frontier's deltas to affected derived keys, reconciles each, and advances the watermark
— with Python's final leftover check (the `raise InvariantViolation` on non-quiescence
at the tail of `index_v4/processor.py::DeltaProcessor._run_cascade`) modeled as a
REJECT branch, and T5 = the reject provably never
fires on the fragment (`runCascade_no_abort`) so the watermark advance is justified,
never asserted (`cascade_drains`).

Modeling decisions (ROADMAP W3d, decisions 1–6):
1. **One outbox row per accepted ROUTED edge** (not per raw write — a computed rewrite
   lands sibling-family tuples with no graph edge from the seed's object node, so the
   seed's reach cone would miss the sibling operand key). Python emits one row per
   materialized closure-pair flip; the row set's object ends `{y : b ⇝ y}` are
   recovered at cascade time as the reach cone of the routed edge's object node
   (add-only ⇒ superset ⇒ at worst extra idempotent reconciles).
2. **Fresh ids** `max maxOutboxId watermark + 1` — strictly above both existing rows
   and the drain frontier (never mint a born-drained row).
3. **Processor emission modeled**: one row per reconcile pass at its derived key — the
   coalescing of the pass's per-flip rows, which all share that object end by R-node
   terminality (re-proved over the interleaved closure:
   `reconcileJobsL_Rnode_not_source`).
4. **The key mapping** `affectedKeys` =
   `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`'s LeafFamily own-key
   branch + `::DeltaProcessor._fan_out`'s `via='computed'` arm, restricted to the
   fragment (`hLU`: operands
   are same-object untainted computed refs; the ttu/userset/tupleset-ttu dependent
   branches are out of fragment by `hterm`/`hCO`). The subject-level cheap path is
   NOT modeled (the model always full-object reconciles — Python's general path; the
   cheap path is an optimization with its own §5.4 escalations to full).
5. **The loop** at one stratum: one round, then the leftover check as the
   accept/reject branch of `runCascade`.
6. **Add-only STORE**: no store removes; the remove-side hazards (operand-removal
   re-reconcile, `neg` pruning after node GC, REMOVED deltas) are out of scope for
   W3d-1.
7. **The pass is the DIFFING audit** (`reconcileStarsKeyD`, 2026-07-11f): W3d's store
   grows between cascades, so a derived guard can flip DOWN (`excl` operand add) and
   the pass must RETRACT the stale derived edge — exactly the removal arm of
   `index_v4/processor.py::DeltaProcessor._reconcile_subject`'s bare-entity tail
   (`_write_derived(..., add=False)`). The add-only pass
   model was refuted by `#eval` at a cascaded state (see `ReconcileDiff.lean` header);
   W3a–W3c keep the add-only pass, where fixed-store guard stability makes the
   removal branch provably dead.

The W3c read-correspondence transfer (via `EvalEq` + the W3d analog of the coverage
clauses) is W3d-1b/1c — see ROADMAP. NB the W3a SHADOW does not extend over diffing
passes (a removal is not a W3a reconcile leg), so W3d-1b re-derives its read bridge
over the interleaved closure directly.

**Attack-first (2026-07-11e, machine-checked `#eval` vs the real `check`/`sem`,
scratch deleted).** Corpus `viewer := member ∖ banned` (`member` admitting `user`,
`user:*`, `group#mem`), 5 logged writes: the frontier's 5 rows mapped to the viewer
key (via direct, star, userset and group-flow cones); `runCascade` with one covering
job took the ACCEPT branch (watermark 0→6), the state was `Quiescent`, and the full
18-query grid matched `sem` (bare incl. a ghost concrete-under-star, star, userset
subjects). **The cross-key hazard**: a post-cascade `banned` write re-mapped the
EXISTING viewer key through the `banned` operand cone — and until that second cascade
ran, the derived read was STALE (`check = true ≠ sem = false` for the newly-banned
subject), confirming the model claim scope: reads are correct at CASCADED states
(Python: `DeltaProcessor.run_cascade` runs inside every writing transaction). The second cascade's
own pass row mapped to `[]` (the no-abort content) while the write's row mapped to
the key; an empty-frontier cascade was a no-op accept. No refutation. -/

namespace Zanzibar

/-! ## Outbox primitives -/

/-- The highest outbox id (0 if empty) — `index_v4/outbox.py::outbox_watermark`. -/
def GraphState.maxOutboxId (σ : GraphState) : Nat :=
  σ.outbox.foldl (fun m d => max m d.id) 0

/-- Fold-max dominates its initial accumulator. -/
theorem foldl_max_init_le (l : List Delta) :
    ∀ a : Nat, a ≤ l.foldl (fun m d => max m d.id) a := by
  induction l with
  | nil => intro a; exact Nat.le_refl a
  | cons d rest ih =>
    intro a
    exact le_trans (Nat.le_max_left a d.id) (ih (max a d.id))

/-- Fold-max dominates every member's id. -/
theorem mem_le_foldl_max (l : List Delta) :
    ∀ (a : Nat), ∀ d ∈ l, d.id ≤ l.foldl (fun m d => max m d.id) a := by
  induction l with
  | nil => intro a d hd; cases hd
  | cons e rest ih =>
    intro a d hd
    rcases List.mem_cons.mp hd with rfl | hmem
    · exact le_trans (Nat.le_max_right a d.id) (foldl_max_init_le rest _)
    · exact ih _ d hmem

/-- Every outbox row's id is bounded by `maxOutboxId`. -/
theorem mem_outbox_le_maxOutboxId (σ : GraphState) :
    ∀ d ∈ σ.outbox, d.id ≤ σ.maxOutboxId :=
  mem_le_foldl_max σ.outbox 0

/-- Fold-max splits off its accumulator. -/
theorem foldl_max_comm (l : List Delta) :
    ∀ a : Nat, l.foldl (fun m d => max m d.id) a
      = max a (l.foldl (fun m d => max m d.id) 0) := by
  induction l with
  | nil => intro a; simp
  | cons d rest ih =>
    intro a
    simp only [List.foldl_cons]
    rw [ih (max a d.id), ih (max 0 d.id)]
    omega

/-- The next fresh delta id: strictly above both the existing rows and the drain
    watermark (decision 2 — a plain `maxId+1` could mint a born-drained row). -/
def GraphState.nextDeltaId (σ : GraphState) : Nat :=
  max σ.maxOutboxId σ.watermark + 1

/-- Append one delta row (`index_v4/core.py::ReachabilityIndex._emit` — since perf N16
    the row is STAGED in `self._outbox_buffer` and bulk-inserted by
    `::ReachabilityIndex._flush_outbox` at the end of the driving
    `::ReachabilityIndex._add_direct_edge_unsafe`, still inside the writing
    transaction; the autoincrement id is the cursor). `leaf` records the row's
    provenance (Python LeafFamily vs DerivedFamily, see `Delta`): reconcile emissions
    default to `false`; raw leaf-routed writes/removes pass `true`. Only `affectedKeys`
    reads it, so every other observation is `leaf`-agnostic (the simp lemmas quantify
    over it). -/
def GraphState.pushDelta (σ : GraphState) (k : NodeKey) (r : String)
    (leaf : Bool := false) : GraphState :=
  { σ with outbox := ⟨σ.nextDeltaId, k, r, leaf⟩ :: σ.outbox }

@[simp] theorem pushDelta_schema (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).schema = σ.schema := rfl
@[simp] theorem pushDelta_edges (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).edges = σ.edges := rfl
@[simp] theorem pushDelta_nodes (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).nodes = σ.nodes := rfl
@[simp] theorem pushDelta_residue (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).residue = σ.residue := rfl
@[simp] theorem pushDelta_watermark (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).watermark = σ.watermark := rfl
@[simp] theorem pushDelta_outbox (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).outbox = ⟨σ.nextDeltaId, k, r, b⟩ :: σ.outbox := rfl

/-- Pushing a row moves `maxOutboxId` to exactly the fresh id. -/
theorem pushDelta_maxOutboxId (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).maxOutboxId = σ.nextDeltaId := by
  show (⟨σ.nextDeltaId, k, r, b⟩ :: σ.outbox).foldl (fun m d => max m d.id) 0
    = σ.nextDeltaId
  rw [List.foldl_cons, foldl_max_comm]
  show max (max 0 σ.nextDeltaId) σ.maxOutboxId = σ.nextDeltaId
  have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
  omega

/-! ## ★ The in-bridge, LOGGED — `P6` increment B, step 2 (2026-09-13b)

**These definitions are ADDITIVE and nothing calls them yet.** Step 3 of the `P6` plan
composes `ensureInBridgesLogged` into `writeLoggedOne` below (and `ensureInBridges` into
the unlogged `RulesWrite.lean::writeRules` twin, so `EvalEq` survives) and
`releaseInBridgesLogged` into `removeLoggedOne`. They live HERE, rather than beside
`ensureInBridges` in `UsStarWrite.lean`, because they need `pushDelta` (`:142` above) and
`removeEdgeOne` (`ReconcileDiff.lean:143`), neither of which `UsStarWrite` can see — and
because this is their final home, so step 3 is a pure composition edit with no file move.
The `Cascade → UsStarWrite` import that makes it possible is the one added at the top of
this file; it was measured free (whole-tree build green, job count unchanged, 2026-09-13b).

**Why logged.** Python's bridges go through `index_v4/core.py::ReachabilityIndex.
add_edge_by_id` / `::remove_edge_by_id`, which record reachability flips in the delta
outbox (`:1101-1107`) — so the LOGGED variant is the faithful one, and the step-1 probe
measured what that buys: with the bridge UNLOGGED, tier-1 stability (`uReachStable` /
`uGraphRecStable` / `uCheckFnStable`) is **false** at 3 unmapped keys; with it LOGGED all
three are true, because the delta moves those keys out of `hunmapped` and into
`cascadeKeys`, which is `CascadeStable.lean:367`'s premise doing its job. That is what
keeps all 23 at-risk stability theorems' STATEMENTS at step 3
(`formal/probes/p6_step1_logged_bridge_2026-09-13.lean` §6).

⚠ **The delta's KEY (`wAnyNode`, the bridge TARGET) is a free choice, not a measured one.**
The step-1 probe ran SRC and TGT arms and they were INDISTINGUISHABLE on every number it
reported. TGT is chosen for symmetry with `writeLoggedOne`, which emits at the edge's
object node. Do not cite that probe as evidence for the choice; if step 3 ever needs SRC,
nothing measured here forbids it. -/

/-- **Ensure the in-bridge and log it.** `ensureInBridges` (`UsStarWrite.lean:213`) plus a
    delta row at the bridge TARGET, emitted **iff the direct-edge multiset actually grew** —
    the same "emit on an actual flip" rule `writeLoggedOne` uses, stated directly on the
    edges so it stays correct under the presence guard (an `ensureInBridges` that finds the
    bridge already there is not a flip and must not emit; Python's `_emit` sits inside
    `add_edge_by_id`, which that call never reaches). -/
def GraphState.ensureInBridgesLogged (σ : GraphState) (c : NodeKey) : GraphState :=
  if (σ.ensureInBridges c).edges = σ.edges then σ.ensureInBridges c
  else (σ.ensureInBridges c).pushDelta (wAnyNode (c.type, c.pred)) c.pred true

/-- **Is `c` now nothing but its own in-bridge?** The guard of
    `index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges` (`:363-386`) — "implicit and
    `reference_count == bridge degree`" — as a predicate on the edge list: `c` is of a
    bridged-in shape and carries no incident edge other than `c → w_any(c)`. The Python
    guard also defers to `::_sync_entity_middles` for CROSSING middles (a shape bridged in
    AND out); this fragment has no object wildcards, so nothing is crossable and that arm is
    inert — see the entity-middle boundary entry in `formal/CORRESPONDENCE.md` §7. -/
def GraphState.inBridgeOnly (σ : GraphState) (c : NodeKey) : Bool :=
  σ.bridgedInConcrete c &&
    (σ.edges.filter (fun e =>
      (e.1 == c || e.2 == c) && !(e.1 == c && e.2 == wAnyNode (c.type, c.pred)))).isEmpty

/-- **Release a dead in-bridge** — the retract dual of `ensureInBridges`, and the second of
    the two mechanisms Wall 2 turned out to need. Erase ONE copy of the bridge edge (the
    ref-counted `-1`, as `removeEdgeOne` is everywhere on this leg) when `c` has become
    bridge-only, so the write-then-remove round trip returns the edge multiset to its
    pre-write value. The step-1 probe measured the residue this collects: `W2-DOM-TGT`
    leaves `residue := 1` without it and `releaseFixes := true` with it, and it declines
    correctly on a node that is still live.

    ⚠ **The NODE is deliberately left behind, and that is a MODEL/Python gap, not a
    decision.** Python's implicit GC deletes the stripped node once its reference count
    reaches zero. This model has no node GC anywhere — `removeEdgeOne_nodes` is `σ.nodes`
    on every leg — and inventing one here would break `StructInv.edgesClosed` for the
    general case rather than mirror anything. The consequence is bounded and is exactly the
    consequence of every other node the model never collects: `reach`'s fuel
    (`nodes.length + 1`) stays larger than Python's, which can only over-approximate, and
    no read consults `nodes` otherwise. -/
def GraphState.releaseInBridges (σ : GraphState) (c : NodeKey) : GraphState :=
  if σ.inBridgeOnly c then σ.removeEdgeOne c (wAnyNode (c.type, c.pred)) else σ

/-- **Release the in-bridge and log it** — the retract mirror of `ensureInBridgesLogged`,
    emitting iff the direct-edge multiset actually SHRANK, exactly as `removeLoggedOne`
    emits iff a copy was present to remove. Delta at the same `wAnyNode` key the write side
    uses, so a bridge that comes and goes leaves a balanced pair of rows. -/
def GraphState.releaseInBridgesLogged (σ : GraphState) (c : NodeKey) : GraphState :=
  if (σ.releaseInBridges c).edges = σ.edges then σ.releaseInBridges c
  else (σ.releaseInBridges c).pushDelta (wAnyNode (c.type, c.pred)) c.pred true

/-! ### ★ Red-to-green witnesses for the bridge legs (`P6` step 2)

A definition nothing calls is INERT: the whole gate stays green if these three are wrong,
which is exactly the position part (i) of `ttuStarFree` was in for a month
(`UsStarWrite.lean:130`). So, as there, `decide` pins are the only evidence, and as there
each one carries its own non-vacuity/attribution control. The store is
`ThroughShapeWitness.Sthru` and the concrete is `InBridgeIdemWitness.c0` —
the same subject the multiset pins use, so a reader comparing the two sees one scenario.

⚠ `logged_second_call_silent` is the load-bearing one. It couples the two step-2 changes:
without the presence guard in `ensureInBridges` the second call adds a second edge copy,
the multiset GROWS, and this leg emits a SECOND delta row — so a future "simplification"
that drops the guard reddens the outbox pin as well as `InBridgeIdemWitness.copies_2`.
A delta per redundant call is worse than a duplicate edge: it dirties a key per routed
member and the cascade re-reconciles it. -/
namespace InBridgeLegWitness

/-! The three names shared with `UsStarWrite.lean::InBridgeIdemWitness` are ALIASED here
rather than `open`ed, and that is not a style choice: `formal/conformance/statement_pin.py`
reads any `open` at column 0 as the hosting FILE's ambient context
(`AMBIENT_RE = ^(?:variable|open)`), with no notion of the enclosing namespace's `end`. So
a convenience `open` inside this witness would have registered as a new
`ambient:…/Cascade.lean` row in the headline DEFINITION pin — the gate caught exactly that
on 2026-09-13c and refused, correctly: the pin cannot tell a scoped `open` from one that
changes how every bare name in a central module resolves. Aliases are definitionally
transparent, so the `decide` pins below are unaffected. -/

/-- `UsStarWrite.lean::InBridgeIdemWitness.c0` — the through-shape concrete. -/
def c0 : NodeKey := InBridgeIdemWitness.c0

/-- `UsStarWrite.lean::InBridgeIdemWitness.w0` — its `w_any` bridge target. -/
def w0 : NodeKey := InBridgeIdemWitness.w0

/-- `UsStarWrite.lean::InBridgeIdemWitness.base` — `c0` live over `Sthru`. -/
def base : GraphState := InBridgeIdemWitness.base

/-- A second endpoint, so the "still live" arm has an incident edge that is not the
    bridge. -/
def other : NodeKey := ⟨"doc", "d1", "viewer", Variant.plain⟩

/-- The bridge, materialised and logged once. -/
def logged1 : GraphState := base.ensureInBridgesLogged c0

/-- The same leg run a second time on the already-bridged state. -/
def logged2 : GraphState := logged1.ensureInBridgesLogged c0

/-- **NON-VACUITY**: the leg FIRES — one row, at the bridge TARGET, carrying the concrete's
    predicate and the leaf flag `writeLoggedOne` uses. Pin the whole row, not its length:
    a row at the wrong key would keep a length pin green. -/
theorem logged_emits : logged1.outbox = [⟨1, w0, "viewer", true⟩] := by decide

/-- ★ **The presence guard, observed through the OUTBOX**: a redundant call is not a flip,
    so it emits nothing. Reds if the guard in `UsStarWrite.lean::ensureInBridges` is
    removed. -/
theorem logged_second_call_silent : logged2.outbox = logged1.outbox := by decide

/-- **ATTRIBUTION**: at a node of a shape that is NOT bridged-in, the leg is silent from
    the start — so `logged_emits` is the bridge firing, not "this leg always emits". -/
theorem logged_unbridged_silent :
    (base.ensureInBridgesLogged InBridgeIdemWitness.cUn).outbox = [] := by decide

/-- The bridged state whose ONLY incident edge at `c0` is its bridge. -/
def bridgedOnly : GraphState := base.ensureInBridges c0

/-- The same, plus a live grant `c0 → doc:d1#viewer`. -/
def stillLive : GraphState := ((base.addNode other).addEdge c0 other).ensureInBridges c0

/-- **NON-VACUITY**: the release FIRES on a dead bridge — the edge multiset returns to
    empty, which is the `releaseFixes := true` the step-1 probe measured. -/
theorem release_fires : (bridgedOnly.releaseInBridges c0).edges = [] := by decide

/-- ★ **THE CONTROL that makes the release safe**: at a node that still carries a real
    edge the release DECLINES, leaving the bridge in place. A GC that fired here would
    silently revoke a grant — `_maybe_remove_bridges`'s `reference_count == degree` guard
    is what forbids it. -/
theorem release_declines : (stillLive.releaseInBridges c0).edges = stillLive.edges := by
  decide

/-- …and the two arms really are different states, so the pair above is not one scenario
    read twice. -/
theorem release_arms_differ : bridgedOnly.edges ≠ stillLive.edges := by decide

/-- The logged release emits exactly one row when it fires, at the same key the write side
    uses — so a bridge that comes and goes leaves a balanced pair. -/
theorem release_logged_emits :
    (bridgedOnly.releaseInBridgesLogged c0).outbox = [⟨1, w0, "viewer", true⟩] := by decide

/-- **ATTRIBUTION**: and nothing at all when it declines. -/
theorem release_logged_silent_when_declined :
    (stillLive.releaseInBridgesLogged c0).outbox = stillLive.outbox := by decide

end InBridgeLegWitness

/-! ### ★ CONTROLLED — MUTATION SWEEP over everything `P6` step 2 added (2026-09-13b)

Covers BOTH halves of step 2 in one run — the presence guard and its multiset pins in
`UsStarWrite.lean::InBridgeIdemWitness`, and the three new legs and their pins here — since
`logged_second_call_silent` is precisely the pin that couples them. Rule applied: every pin
must be reddened by at least one mutation, or it is inert and says so out loud
(`docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations").

`M0` is the INSTRUMENT CONTROL: it flips `copies_1`'s own claim and the sweep must
attribute the red to exactly `copies_1`. `P6` step 0's first sweep had an inverted
error-location regex, reported `<unattributed>` for every mutation, and therefore listed
the whole module as candidate-inert — a broken harness that reads like a finding. The
step-2 sweep's own instrument failure was different and M0 did not catch it: the multi-line
anchors matched **zero** times because the sources are CRLF and the anchors were LF, so
ten of fourteen mutations came back `ANCHOR MISS` — which is at least loud. `M12`'s first
form was a third kind of instrument failure, an edit that does not change the property
under test (`doc#viewer` is no more bridged-in than `doc#parent`), and it read as `INERT`.

```text
M0  INSTRUMENT CONTROL: flip copies_1's own claim 1 -> 0     | RED: copies_1
M1  ensureInBridges: DROP the presence guard (the
      pre-step-2 definition)                                 | RED: ensureInBridges_schema,
      ensureInBridges_residue, ensureInBridges_mono, ensureInBridges_edges_of_mem,
      ensureInBridges_count_le_one, copies_2, copies_3, edges_are_the_bridge_alone,
      structInv_ensureInBridges
M2  ensureInBridges: guard tests the REVERSED pair (w_any,c) | RED: ensureInBridges_edges_of_mem,
      ensureInBridges_count_le_one, copies_2, copies_3, edges_are_the_bridge_alone,
      structInv_ensureInBridges
M3  ensureInBridgesLogged: emit unconditionally              | RED: logged_second_call_silent,
      logged_unbridged_silent, ensureInBridgesLogged_edges, ensureInBridgesLogged_nodes,
      ensureInBridgesLogged_schema, ensureInBridgesLogged_residue, ensureInBridgesLogged_evalEq
M4  ensureInBridgesLogged: log at the SOURCE, not the TARGET | RED: logged_emits
M5  ensureInBridgesLogged: emit with leaf := false           | RED: logged_emits
M6  inBridgeOnly: drop the bridgedInConcrete conjunct        | INERT (nothing reddened)
M7  inBridgeOnly: stop excluding the bridge edge itself      | RED: release_fires,
      release_logged_emits
M8  inBridgeOnly: ignore incident edges (fire whenever
      bridged)                                               | RED: release_declines,
      release_logged_silent_when_declined
M9  releaseInBridges: erase the bridge the wrong way round   | RED: release_fires,
      release_logged_emits, releaseInBridges_edges_subset
M10 ensureInBridges_count_le_one: weaken the bound 1 -> 2    | RED: ensureInBridges_count_le_one
M11 witness: c0's predicate viewer -> parent (a shape Sthru
      does NOT bridge in)                                    | RED: bridged_control, copies_1,
      copies_2, copies_3, edges_are_the_bridge_alone
M12 witness: the un-bridged control node cUn becomes c0      | RED: unbridged_control
M13 witness: stillLive loses its non-bridge edge             | RED: release_declines,
      release_arms_differ, release_logged_silent_when_declined
```

**M10 is the one that says the count pin is TIGHT.** Weakening its bound from `1` to `2`
reddens it — the proof genuinely needs `count = 0` on the add branch — so the theorem is not
a bound that happens to hold with slack.

**M6 is INERT, and that is honest rather than a hole.** Dropping `bridgedInConcrete` from
`inBridgeOnly` changes no observation here because the release then fires at nodes that have
no bridge edge to erase, and `removeEdgeOne` on an absent edge is the identity — no edge
moves, so no delta either. The conjunct is defensive: it keeps the predicate's MEANING
("this node is bridge-only") rather than guarding a reachable state. Do not delete it on the
strength of this row; do not cite it as load-bearing either. Note the contrast with `M7`,
where the *other* half of the same definition is load-bearing twice over.

**`copies_0` is never reddened by any mutation above, and cannot be.** It reads the state
BEFORE any call, so it is the baseline of the `(0, 1, 1, 1)` sequence rather than a pin on
the guard — it is there so the sequence is legible next to the probe's `(0, 1, 2, 3)`.

The sweep script is throwaway and gitignored (`.scratch/p6_step2_mutation_sweep.py`); this
table is the evidence. Baseline and restored builds were both green in the same run.
-/

/-! ### Projections and `EvalEq` for the bridge legs

The logged legs differ from their unlogged cores in the OUTBOX and nothing else, which is
precisely what `EvalEq` was introduced to say. Step 3 needs these to carry the
logged/unlogged correspondence (`writeLoggedRules_evalEq`) through a bridged write leg. -/

@[simp] theorem ensureInBridgesLogged_edges (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridgesLogged c).edges = (σ.ensureInBridges c).edges := by
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

@[simp] theorem ensureInBridgesLogged_nodes (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridgesLogged c).nodes = (σ.ensureInBridges c).nodes := by
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

@[simp] theorem ensureInBridgesLogged_schema (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridgesLogged c).schema = σ.schema := by
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

@[simp] theorem ensureInBridgesLogged_residue (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridgesLogged c).residue = σ.residue := by
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

@[simp] theorem releaseInBridges_schema (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridges c).schema = σ.schema := by
  unfold GraphState.releaseInBridges
  split <;> simp

@[simp] theorem releaseInBridges_nodes (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridges c).nodes = σ.nodes := by
  unfold GraphState.releaseInBridges
  split <;> simp

@[simp] theorem releaseInBridges_residue (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridges c).residue = σ.residue := by
  unfold GraphState.releaseInBridges
  split <;> simp

/-- Releasing only ever removes edges — the retract-side counterpart of
    `UsStarClosure.lean::ensureInBridges_edges_mono`, and what an acyclicity argument
    needs (`NReaches` can only shrink). -/
theorem releaseInBridges_edges_subset (σ : GraphState) (c : NodeKey) :
    ∀ e ∈ (σ.releaseInBridges c).edges, e ∈ σ.edges := by
  unfold GraphState.releaseInBridges
  split
  · exact fun e he => removeEdgeOne_edges_subset σ c (wAnyNode (c.type, c.pred)) e he
  · exact fun _ he => he

@[simp] theorem releaseInBridgesLogged_edges (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridgesLogged c).edges = (σ.releaseInBridges c).edges := by
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

@[simp] theorem releaseInBridgesLogged_nodes (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridgesLogged c).nodes = σ.nodes := by
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

@[simp] theorem releaseInBridgesLogged_schema (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridgesLogged c).schema = σ.schema := by
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

/-! ## Logged writes (decision 1) -/

/-- ★ **The bridge-before-grant PROLOGUE of a logged leaf-routed write** — `P6` increment
    B, **step 3a** (2026-09-13d), ADDITIVE: nothing calls it yet. Step 3b re-points
    `GraphState.writeLoggedOne` below onto it, which is the composition the whole item
    exists for; that is the cone payment and it is deliberately NOT taken here.

    Mirrors `index_v4/wildcard.py::WildcardIndex._add_tuple_trusted`: resolve both
    endpoints with `create=True` (the `addNode` pair), then `_ensure_bridges(subject)` and
    `_ensure_bridges(obj)`, and only then `add_edge_by_id`. The unlogged twin is
    `UsStarWrite.lean::GraphState.bridgePre` — same prologue, no delta rows — and
    `bridgePreLogged_evalEq` below is the pair's hinge: it is what will let step 3b bridge
    the logged leg AND its unlogged `writeRulesRaw` twin and still carry
    `writeLoggedRules_evalEq` with its statement unchanged.

    ⚠ **The prologue is a NAMED definition, not a `let`** — see
    `UsStarWrite.lean::GraphState.bridgePre`, whose note explains why (a `let` elaborates
    to `have` in the goal and blocks `split` at every one of `writeLoggedOne`'s downstream
    sites, and that cone is 20 modules). -/
def GraphState.bridgePreLogged (σ : GraphState) (t : Tuple) : GraphState :=
  (((σ.addNode (subjNode t.subject)).addNode
    (objNode t.object t.relation)).ensureInBridgesLogged
    (subjNode t.subject)).ensureInBridgesLogged (objNode t.object t.relation)

/-- One logged routed-edge write: materialize the guarded edge and, iff it was
    admitted, emit its delta row (`_emit` fires on actual flips; a rejected write
    inserts nothing).

    ★ **`P6` step 3b RE-POINT #1 LANDED 2026-09-14**, exactly as measured 2026-09-13d:
    `σ → σ.bridgePreLogged t` in the two probe positions, plus `writeDirect → addEdge`.

    ⚠ **`addEdge`, NOT `writeDirect`, and the difference is load-bearing.** The admission
    guard moves OUT to the `if`, where it probes the BRIDGED state. Leaving `writeDirect`
    in the then-branch would re-probe `admitEdge` on the UNBRIDGED `σ` inside it and so
    double-guard against the wrong state — a write the shipped index rejects for a cycle
    through a fresh bridge would be admitted here. The order is Python's: bridge first,
    then probe, then grant (`index_v4/wildcard.py::WildcardIndex._ensure_own_bridges` ahead
    of `add_edge_by_id`), and it is behaviourally pinned at
    `UsStarWrite.lean::BridgedWriteWitness.{bridged_probe_refuses_the_cycle,
    unbridged_probe_admits_the_cycle, cycle_write_materialises_nothing}`.

    **The body below is character-for-character the LHS of `writeBridgedOne_logged_evalEq`**
    (step 3a, below), which is why the flip is a re-point and not a new proof. -/
def GraphState.writeLoggedOne (σ : GraphState) (t : Tuple) : GraphState :=
  if (σ.bridgePreLogged t).admitEdge (subjNode t.subject) (objNode t.object t.relation)
  then ((σ.bridgePreLogged t).addEdge (subjNode t.subject)
    (objNode t.object t.relation)).pushDelta (objNode t.object t.relation) t.relation true
  else σ

/-- **The logged rule-routed write**: the LEAF-ROUTED fold with a delta row per accepted
    rewrite-closure member (`RuleSet.apply` + per-triple `add_tuple`, each `add_edge`
    emitting its flips).

    **RE-POINTED by step 4c-ii (THE FLIP)**: the seed list is `Leaf.lean::rawWriteTuples`
    (stage 1, `RuleSet.apply`'s re-addressing of the raw write onto its storage leaves) and
    the closure is `LeafRules.lean::rewriteClosureL` (stage 2, the closure under
    `schemaRewritesL = schemaRewrites ++ leafRewrites`). Its unlogged twin is therefore
    `LeafRules.lean::GraphState.writeRulesRaw`, NOT `RulesWrite.lean::GraphState.writeRules`;
    see `writeLoggedRules_evalEq` below.

    ⚠ **STALE SENTENCE REMOVED 2026-09-14 (`P6` step 3b).** This read "on an untainted
    schema the two coincide definitionally (`writeRulesRaw_untaintedSchema`)", naming
    `writeRules`. After re-point #2 that is FALSE — and false for the FUEL reason, not the
    bridging reason, so no premise repairs it (`LeafRules.lean::writeRulesRaw_untaintedSchema`
    carries the full argument). The untainted fact that survives is the LIST equation
    `LeafRules.lean::rewriteClosureL_rawWriteTuples_untaintedSchema`. -/
def GraphState.writeLoggedRules (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl (fun acc u => acc.writeLoggedOne u) σ

/-! ## `EvalEq` — the read-relevant core, and the logged/unlogged correspondence -/

/-- **`EvalEq σ' σ`** — agreement on everything the READ consults: schema, edges,
    nodes, residue. The W3d projection relation (`CoreEq` is too strong once the
    outbox/watermark genuinely differ between the logged chain and its unlogged
    twin). -/
structure EvalEq (σ' σ : GraphState) : Prop where
  schema : σ'.schema = σ.schema
  edges : σ'.edges = σ.edges
  nodes : σ'.nodes = σ.nodes
  residue : σ'.residue = σ.residue

theorem EvalEq.refl (σ : GraphState) : EvalEq σ σ := ⟨rfl, rfl, rfl, rfl⟩

/-- **`StructInv` transports along `EvalEq`.** ★ ADDITIVE, `P6` step 3b (2026-09-14).
    `State.lean::StructInv` reads only schema, nodes and edges — the outbox and watermark are
    not among its clauses — so it is exactly the kind of fact an `EvalEq` carries. This turns
    every logged leg's `StructInv` obligation into its unlogged twin's, instead of a second
    copy of the same acyclicity argument: `CascadeInv.lean::structInv_writeLoggedOne` is now
    one line over the audited `UsStarWrite.lean::structInv_writeBridgedOne`. -/
theorem structInv_of_evalEq {S : Schema} {σ' σ : GraphState} (h : EvalEq σ' σ)
    (hs : StructInv S σ) : StructInv S σ' where
  schemaEq := by rw [h.schema]; exact hs.schemaEq
  nodeEnc := by rw [h.nodes]; exact hs.nodeEnc
  edgesClosed := by rw [h.edges, h.nodes]; exact hs.edgesClosed
  acyclic := by rw [h.edges]; exact hs.acyclic

theorem EvalEq.trans {σ₁ σ₂ σ₃ : GraphState} (h₁ : EvalEq σ₁ σ₂) (h₂ : EvalEq σ₂ σ₃) :
    EvalEq σ₁ σ₃ :=
  ⟨h₁.schema.trans h₂.schema, h₁.edges.trans h₂.edges, h₁.nodes.trans h₂.nodes,
   h₁.residue.trans h₂.residue⟩

/-- `admitEdge` is `EvalEq`-congruent (it probes reachability over edges with
    node-count fuel). -/
theorem admitEdge_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (a b : NodeKey) :
    σ'.admitEdge a b = σ.admitEdge a b := by
  unfold GraphState.admitEdge GraphState.reach
  rw [h.edges, h.nodes]

/-- **The logged in-bridge is `EvalEq` to its unlogged core** (`P6` step 2): the outbox is
    the only difference, which is what lets step 3 bridge BOTH the logged leg and its
    unlogged `RulesWrite.lean::writeRules` twin and still carry
    `writeLoggedRules_evalEq`. -/
theorem ensureInBridgesLogged_evalEq (σ : GraphState) (c : NodeKey) :
    EvalEq (σ.ensureInBridgesLogged c) (σ.ensureInBridges c) := by
  refine ⟨by simp, by simp, by simp, ?_⟩
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

/-- The logged release is `EvalEq` to its unlogged core — the retract mirror. -/
theorem releaseInBridgesLogged_evalEq (σ : GraphState) (c : NodeKey) :
    EvalEq (σ.releaseInBridgesLogged c) (σ.releaseInBridges c) := by
  refine ⟨by simp, by simp, by simp, ?_⟩
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

/-- `writeDirect` is `EvalEq`-congruent (it reads and writes only edges/nodes). -/
theorem writeDirect_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.writeDirect t) (σ.writeDirect t) := by
  unfold GraphState.writeDirect
  dsimp only
  rw [admitEdge_evalEq h]
  by_cases hb : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · rw [if_pos hb, if_pos hb]
    exact ⟨h.schema, by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
  · rw [if_neg hb, if_neg hb]
    exact h

/-- **`ensureInBridges` is `EvalEq`-congruent** (`P6` step 3): its branch conditions read
    only the schema, the edges and the reachability probe, and its effects are an `addNode`
    and an `addEdge` — so two `EvalEq` states bridge to two `EvalEq` states. This is what
    lets the logged write leg and its unlogged twin carry a bridge prologue each and stay
    `EvalEq`. -/
theorem ensureInBridges_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (c : NodeKey) :
    EvalEq (σ'.ensureInBridges c) (σ.ensureInBridges c) := by
  have hbr : σ'.bridgedInConcrete c = σ.bridgedInConcrete c := by
    unfold GraphState.bridgedInConcrete; rw [h.schema]
  have hnode : EvalEq (σ'.addNode (wAnyNode (c.type, c.pred)))
      (σ.addNode (wAnyNode (c.type, c.pred))) :=
    ⟨by simp [h.schema], by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
  have hadm := admitEdge_evalEq hnode c (wAnyNode (c.type, c.pred))
  unfold GraphState.ensureInBridges
  rw [hbr, h.edges, hadm]
  split
  · split
    · exact hnode
    · split
      · exact ⟨by simp [h.schema], by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
      · exact hnode
  · exact h

/-- The logged bridge of one state is `EvalEq` to the unlogged bridge of any `EvalEq`
    state — `ensureInBridgesLogged_evalEq` composed with the congruence above. -/
theorem ensureInBridgesLogged_evalEq_congr {σ' σ : GraphState} (h : EvalEq σ' σ)
    (c : NodeKey) : EvalEq (σ'.ensureInBridgesLogged c) (σ.ensureInBridges c) :=
  EvalEq.trans (ensureInBridgesLogged_evalEq σ' c) (ensureInBridges_evalEq h c)

/-- **The logged bridge prologue is `EvalEq` to the unlogged one** — the step-3 hinge.
    `UsStarWrite.lean::GraphState.bridgePre` and `GraphState.bridgePreLogged` differ only
    in the outbox rows the latter emits. -/
theorem bridgePreLogged_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.bridgePreLogged t) (σ.bridgePre t) := by
  unfold GraphState.bridgePreLogged GraphState.bridgePre
  have h0 : EvalEq ((σ'.addNode (subjNode t.subject)).addNode (objNode t.object t.relation))
      ((σ.addNode (subjNode t.subject)).addNode (objNode t.object t.relation)) :=
    ⟨by simp [h.schema], by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
  exact ensureInBridgesLogged_evalEq_congr
    (ensureInBridgesLogged_evalEq_congr h0 (subjNode t.subject)) (objNode t.object t.relation)

/-- The UNLOGGED bridge prologue is `EvalEq`-congruent. ★ ADDITIVE, `P6` step 3b step 14
    (2026-09-14): needed because `FoldAdmitsBridged` probes `σ.bridgePre u`, so transporting
    that predicate along an `EvalEq` — which `untaintedShadow_foldAdmits` does at every fold
    step — needs the congruence at the prologue, not just at the grant. -/
theorem bridgePre_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.bridgePre t) (σ.bridgePre t) := by
  unfold GraphState.bridgePre
  have h0 : EvalEq ((σ'.addNode (subjNode t.subject)).addNode (objNode t.object t.relation))
      ((σ.addNode (subjNode t.subject)).addNode (objNode t.object t.relation)) :=
    ⟨by simp [h.schema], by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
  exact ensureInBridges_evalEq (ensureInBridges_evalEq h0 _) _

/-- …and so is the bridged write step itself. -/
theorem writeBridgedOne_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.writeBridgedOne t) (σ.writeBridgedOne t) := by
  have hp := bridgePre_evalEq h t
  unfold GraphState.writeBridgedOne
  rw [admitEdge_evalEq hp]
  split
  · exact ⟨by simp [hp.schema], by simp [hp.edges], by simp [hp.nodes], by simp [hp.residue]⟩
  · exact h

/-- ★ **The BRIDGED logged step is `EvalEq` to the bridged unlogged step** — `P6` step 3a,
    and the theorem step 3b re-points `writeLoggedOne_evalEq` onto. Stated on the bridged
    pair now, while it is additive, so that the flip is a re-point and not a new proof:
    once `writeLoggedOne` is `bridgePreLogged` + grant + delta and `writeRulesRaw` folds
    `writeBridgedOne`, this IS `writeLoggedOne_evalEq`, and `writeLoggedRules_evalEq` keeps
    its statement. -/
theorem writeBridgedOne_logged_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq
      (if (σ'.bridgePreLogged t).admitEdge (subjNode t.subject) (objNode t.object t.relation)
        then ((σ'.bridgePreLogged t).addEdge (subjNode t.subject)
          (objNode t.object t.relation)).pushDelta (objNode t.object t.relation) t.relation true
        else σ')
      (σ.writeBridgedOne t) := by
  have hp := bridgePreLogged_evalEq h t
  unfold GraphState.writeBridgedOne
  rw [admitEdge_evalEq hp]
  split
  · exact ⟨by simp [hp.schema], by simp [hp.edges], by simp [hp.nodes], by simp [hp.residue]⟩
  · exact h

/-- One logged write step is `EvalEq` to the unlogged step.

    ★ **STATEMENT MOVED by `P6` step 3b re-point #1 (2026-09-14)**: the RHS was
    `σ.writeDirect t` and is now `σ.writeBridgedOne t`. Both sides moved in the same step,
    so the correspondence itself is unchanged in content — and the whole proof collapses to
    the step-3a lemma, which was stated on the bridged pair in advance precisely so this
    would be a re-point rather than a re-proof. -/
theorem writeLoggedOne_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.writeLoggedOne t) (σ.writeBridgedOne t) := by
  unfold GraphState.writeLoggedOne
  exact writeBridgedOne_logged_evalEq h t

/-- **The logged fold's core is the plain `writeDirect` fold, at ANY list.** The
    list-generic form of `writeLoggedRules_evalEq` below — extracted by step 4c-ii because
    the post-flip shadow leg pairs the logged fold on the LEAF-ROUTED list against a plain
    fold on the untainted one, and so needs the correspondence at a list that is not
    `rewriteClosureL S (rawWriteTuples S t)`
    (`CascadeStable.lean::untaintedShadow_writeLegL`).

    ★ **STATEMENT MOVED by `P6` step 3b re-point #1 (2026-09-14)**: the second fold's body
    was `acc.writeDirect u` and is now `acc.writeBridgedOne u`. The PROOF BODY is
    untouched — it was already `exact ih (writeLoggedOne_evalEq h u)`, so re-pointing the
    one-step lemma re-points this one for free. -/
theorem foldl_writeLoggedOne_evalEq : ∀ (us : List Tuple) {σ' σ : GraphState}, EvalEq σ' σ →
    EvalEq (us.foldl (fun acc u => acc.writeLoggedOne u) σ')
      (us.foldl (fun acc u => acc.writeBridgedOne u) σ) := by
  intro us
  induction us with
  | nil => intro σ' σ h; exact h
  | cons u rest ih =>
    intro σ' σ h
    simp only [List.foldl_cons]
    exact ih (writeLoggedOne_evalEq h u)

/-- **The logged routed write's core is the unlogged `writeRulesRaw`.** All W2 edge/node
    facts about the leaf-routed fold transfer to `writeLoggedRules` through this.

    **RE-POINTED by step 4c-ii (THE FLIP)** from `RulesWrite.lean::GraphState.writeRules` to
    `LeafRules.lean::GraphState.writeRulesRaw` — both sides fold over the same
    list `rewriteClosureL S (rawWriteTuples S t)`.

    ★ **`P6` step 3b, 2026-09-14 — THIS STATEMENT DID NOT MOVE, and that is what makes every
    downstream `CascadeStable` repair a lemma substitution rather than a restatement.** Both
    sides of the `EvalEq` were re-pointed in the same step (`writeLoggedOne` onto the bridged
    prologue, `writeRulesRaw` onto `writeBridgedOne`), so the correspondence is preserved
    verbatim and every consumer's `rw [(writeLoggedRules_evalEq …).edges]` still fires. -/
theorem writeLoggedRules_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (S : Schema)
    (t : Tuple) : EvalEq (σ'.writeLoggedRules S t) (σ.writeRulesRaw S t) :=
  foldl_writeLoggedOne_evalEq (rewriteClosureL S (rawWriteTuples S t)) h

/-- The logged in-bridge leaves the watermark untouched (`P6` step 3 — the bridge
    prologue must not move the drain cursor). -/
@[simp] theorem ensureInBridgesLogged_watermark (σ : GraphState) (c : NodeKey) :
    (σ.ensureInBridgesLogged c).watermark = σ.watermark := by
  unfold GraphState.ensureInBridgesLogged
  split <;> simp

/-- …and so does the whole logged bridge prologue. -/
@[simp] theorem bridgePreLogged_watermark (σ : GraphState) (t : Tuple) :
    (σ.bridgePreLogged t).watermark = σ.watermark := by
  unfold GraphState.bridgePreLogged
  simp [GraphState.addNode]

/-- The bridge prologue is schema-inert, and so is the whole re-pointed write step.

    ★ ADDITIVE, `P6` step 3b step 8 (2026-09-14). Needed because the shadow's bridge
    obligations are stated on `σ.schema` — `GraphState.bridgedInConcrete` reads the STATE's
    schema, not a free `S` — so a fold-level lemma has to carry them from accumulator to
    accumulator, and that is exactly a schema-invariance argument. -/
@[simp] theorem bridgePreLogged_schema (σ : GraphState) (t : Tuple) :
    (σ.bridgePreLogged t).schema = σ.schema := by
  unfold GraphState.bridgePreLogged
  simp [GraphState.addNode]

@[simp] theorem writeLoggedOne_schema (σ : GraphState) (t : Tuple) :
    (σ.writeLoggedOne t).schema = σ.schema := by
  unfold GraphState.writeLoggedOne
  split
  · rw [pushDelta_schema, addEdge_schema]
    exact bridgePreLogged_schema σ t
  · rfl

/-! ### ★ The write-side bridge legs' OUTBOX facts (`P6` step 3b, 2026-09-13g)

ADDITIVE: new statements about the step-2/3a definitions above, nothing re-pointed. Step 7
of the `P6` plan needs them so `CascadeStable.lean:78::writeLoggedOne_outbox_mono` and
`:118::writeLoggedRules_edge_delta` keep their statements once `writeLoggedOne` gains the
prologue — the first because a bridge leg must never DROP a frontier row, the second
because a bridge EDGE must come with one.

⚠ **Why `d.node = ab.2` survives on the bridge arm.** `ensureInBridgesLogged` (`:214`)
pushes its row at `wAnyNode (c.type, c.pred)` while the edge `ensureInBridges` adds is
exactly `(c, wAnyNode (c.type, c.pred))` (`UsStarWrite.lean:282`) — so the row sits at the
new edge's TARGET, which is the same denormalisation the routed arm uses
(`writeLoggedOne` emits at `objNode t.object t.relation`, the object end of the edge it
adds). That is what lets the consumer keep the `ab.2` form rather than weakening to a
disjunction over the two endpoints. -/

/-- The logged in-bridge only ever PUSHES outbox rows: the unlogged core leaves the outbox
    alone (`ensureInBridges_outbox`) and the logged wrapper conses at most one row. -/
theorem ensureInBridgesLogged_outbox_mono (σ : GraphState) (c : NodeKey) :
    ∀ d ∈ σ.outbox, d ∈ (σ.ensureInBridgesLogged c).outbox := by
  intro d hd
  unfold GraphState.ensureInBridgesLogged
  split
  · rw [ensureInBridges_outbox]; exact hd
  · rw [pushDelta_outbox]
    exact List.mem_cons_of_mem _ (by rw [ensureInBridges_outbox]; exact hd)

/-- …and so does the whole logged prologue (both legs, over the two `addNode`s that touch
    neither the outbox nor the watermark). -/
theorem bridgePreLogged_outbox_mono (σ : GraphState) (t : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.bridgePreLogged t).outbox := by
  intro d hd
  unfold GraphState.bridgePreLogged
  refine ensureInBridgesLogged_outbox_mono _ _ d
    (ensureInBridgesLogged_outbox_mono _ _ d ?_)
  simpa [GraphState.addNode] using hd

/-- ★ **A bridge edge carries its frontier row.** Every edge of the logged in-bridge is an
    old edge, or else the leg emitted a row with an id strictly above the (unchanged)
    watermark, denormalized at that edge's own head. The per-leg core of
    `CascadeStable.lean:118::writeLoggedRules_edge_delta`'s bridge arm; the id bound is
    `ensureInBridges_watermark` (`UsStarWrite.lean:670`) exactly where the routed arm uses
    `writeDirect_watermark`.

    ⚠ **Read the second disjunct as written.** It supplies the ROW, not the edge's identity:
    it does NOT assert `ab = (c, wAnyNode (c.type, c.pred))`. That identity is true and is
    available separately from `UsStarWrite.lean::ensureInBridges_edges_mem` (this proof
    consumes it), but no consumer needs it — `:118`'s shape carries only the row — so
    claiming it here would make the docstring stronger than the theorem. -/
theorem ensureInBridgesLogged_edge_delta (σ : GraphState) (c : NodeKey) :
    ∀ ab ∈ (σ.ensureInBridgesLogged c).edges,
      ab ∈ σ.edges ∨ ∃ d ∈ (σ.ensureInBridgesLogged c).outbox,
        σ.watermark < d.id ∧ d.node = ab.2 := by
  intro ab hab
  rw [ensureInBridgesLogged_edges] at hab
  by_cases hEq : (σ.ensureInBridges c).edges = σ.edges
  · rw [hEq] at hab; exact Or.inl hab
  · rcases ensureInBridges_edges_mem hab with hold | ⟨heq, _⟩
    · exact Or.inl hold
    · have hob : (σ.ensureInBridgesLogged c).outbox
          = ⟨(σ.ensureInBridges c).nextDeltaId, wAnyNode (c.type, c.pred), c.pred, true⟩
            :: (σ.ensureInBridges c).outbox := by
        unfold GraphState.ensureInBridgesLogged
        rw [if_neg hEq, pushDelta_outbox]
      refine Or.inr ⟨⟨(σ.ensureInBridges c).nextDeltaId, wAnyNode (c.type, c.pred),
        c.pred, true⟩, ?_, ?_, ?_⟩
      · rw [hob]; exact List.mem_cons_self
      · show σ.watermark < (σ.ensureInBridges c).nextDeltaId
        have h1 : (σ.ensureInBridges c).nextDeltaId
            = max (σ.ensureInBridges c).maxOutboxId (σ.ensureInBridges c).watermark + 1 := rfl
        have h2 : (σ.ensureInBridges c).watermark = σ.watermark := ensureInBridges_watermark σ c
        omega
      · show (⟨(σ.ensureInBridges c).nextDeltaId, wAnyNode (c.type, c.pred),
          c.pred, true⟩ : Delta).node = ab.2
        rw [heq]

/-- …and the same fact for the whole prologue: an edge of `bridgePreLogged` is old, or one
    of the two legs' bridge edges, which carries its row. (Not on the plan's step-7 list,
    which names only the per-leg form; landed because the re-pointed `writeLoggedOne`
    presents the prologue, not a single leg, and the composition is three lines.) -/
theorem bridgePreLogged_edge_delta (σ : GraphState) (t : Tuple) :
    ∀ ab ∈ (σ.bridgePreLogged t).edges,
      ab ∈ σ.edges ∨ ∃ d ∈ (σ.bridgePreLogged t).outbox,
        σ.watermark < d.id ∧ d.node = ab.2 := by
  intro ab hab
  unfold GraphState.bridgePreLogged at hab ⊢
  rcases ensureInBridgesLogged_edge_delta _ (objNode t.object t.relation) ab hab with
    h1 | ⟨d, hd, hgt, hnode⟩
  · rcases ensureInBridgesLogged_edge_delta _ (subjNode t.subject) ab h1 with
      h2 | ⟨d, hd, hgt, hnode⟩
    · exact Or.inl (by simpa [GraphState.addNode] using h2)
    · exact Or.inr ⟨d, ensureInBridgesLogged_outbox_mono _ _ d hd,
        by simpa [GraphState.addNode] using hgt, hnode⟩
  · exact Or.inr ⟨d, hd, by simpa [GraphState.addNode] using hgt, hnode⟩

/-- The logged write leaves the watermark untouched.

    ★ **STATEMENT UNCHANGED across `P6` step 3b re-point #1 (2026-09-14); only the tactic
    block moved.** The then-branch was `writeDirect` and is now `bridgePreLogged` + `addEdge`,
    so `rw [writeDirect_watermark]` no longer fires. ⚠ It cannot be replaced by the obvious
    `rw [addEdge_watermark]` either — **there is no such lemma anywhere in the tree**
    (`State.lean` carries `addEdge_nodes` / `_residue` / `_schema` / `_edges` and no
    watermark twin), which is why the last step is an `exact` through defeq rather than a
    `rw` chain of named lemmas: `GraphState.addEdge` is the structure update
    `{ σ with edges := … }` and leaves the watermark reducibly alone. The bridge prologue
    is what needs an actual lemma, and it has one (`bridgePreLogged_watermark`) — a bridge
    leg must not move the drain cursor. -/
theorem writeLoggedRules_watermark (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeLoggedRules S t).watermark = σ.watermark := by
  unfold GraphState.writeLoggedRules
  generalize rewriteClosureL S (rawWriteTuples S t) = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]
    unfold GraphState.writeLoggedOne
    split
    · rw [pushDelta_watermark]
      exact bridgePreLogged_watermark σ u
    · rfl

/-! ## Logged retractions (W3d remove-leg R2 substrate — the retract mirror of the
    logged writes above)

`connectedstore/apply.py::_apply_row` routes BOTH an ADD and a REMOVE log row
through the IDENTICAL `ruleset.apply(triple)` rewrite fan-out, then applies
`_add_tuple_trusted` (ADD) or `_remove_tuple_trusted` (REMOVE) per rewrite-closure member.
So the retraction of a raw tuple is the fold of a per-member edge decrement over the SAME
`rewriteClosureL S (rawWriteTuples S t)` the write path folds `writeLoggedOne` over —
modelled below as `removeLoggedRules`, the exact retract mirror of `writeLoggedRules`. The per-member step
uses `removeEdgeOne` (erase ONE copy — the ref-counted `-1`, NOT the filter-all
`removeEdgePair`; see the `ReconcileDiff.lean` R1 KILL note) and emits its retraction
delta the way `writeLoggedOne` emits its write delta. These are STANDALONE additive defs:
the `remove` constructor on `ReachedByW3d2E` (which consumes them) is a LATER leg (R5),
armed with the R4 confluence — added last so every increment stays green. -/

/-- ★ **The retract mirror of `bridgePreLogged` — the EPILOGUE of a logged retraction.**
    Python's `index_v4/wildcard.py::WildcardIndex._remove_tuple_trusted` runs
    `remove_edge_by_id`, then `_maybe_remove_bridges(subject)` and
    `_maybe_remove_bridges(obj)` — so the release is an epilogue on BOTH endpoints, in that
    order, and `P6` step 3b re-point #3 wraps exactly this around `removeLoggedOne`'s
    then-branch.

    (Landed by step 3a as an ADDITIVE definition with no caller; **MOVED up above
    `removeLoggedOne` on 2026-09-14** by re-point #3, which made it a caller. Pure
    relocation — statement and body are unchanged, and `Cascade.lean` has no forward
    references, so the definition must precede its use.) -/
def GraphState.releasePostLogged (σ : GraphState) (t : Tuple) : GraphState :=
  (σ.releaseInBridgesLogged (subjNode t.subject)).releaseInBridgesLogged
    (objNode t.object t.relation)

/-- One logged routed-edge retraction: erase ONE copy of the guarded direct edge and,
    iff a copy was actually present to remove, emit its retraction delta row. The exact
    retract mirror of `writeLoggedOne`: where the write emits iff the edge was ADMITTED
    (the direct-edge multiset GREW), the retraction emits iff the edge was PRESENT (the
    multiset SHRANK) — same "emit on an actual flip of the direct-edge multiset" rule, one
    delta at the object node with the tuple's relation. Mirror of Python
    `index_v4/wildcard.py::WildcardIndex._remove_tuple_trusted` →
    `index_v4/core.py::ReachabilityIndex.remove_edge_by_id` →
    `::ReachabilityIndex._remove_edge_locked`: the ref-counted `-1` update
    (`_add_direct_edge_unsafe(subject_id, object_id, -1)`) is the sole
    driver of `_emit(subject_id, object_id, "REMOVED")` on the reachability flip
    (`::ReachabilityIndex._emit`, denormalised over the closure; the model reconstructs
    that cone at cascade time via `affectedObjects`, decision 1). The presence guard
    mirrors the `direct_edge_count == 0 ⇒ ValueError` reject in
    `::ReachabilityIndex._remove_edge_locked` / the non-existent-endpoint `ValueError`
    in `index_v4/wildcard.py::WildcardIndex._remove_tuple_trusted`; store consistency
    makes the else-branch dead at every admitted removal (an R3 fact), so it is present
    only for totality.

    ★ **`P6` step 3b RE-POINT #3 LANDED 2026-09-14 — the bridge RELEASE epilogue.** The
    then-branch is now wrapped in `releasePostLogged`, mirroring Python's order in
    `index_v4/wildcard.py::WildcardIndex._remove_tuple_trusted`: `remove_edge_by_id`
    (which emits) FIRST, then `_maybe_remove_bridges` on both endpoints. So the wrap goes
    **outside** `pushDelta`, not between the erase and the emit.

    ⚠ **The else-branch stays a bare `σ`, and that is a fidelity decision, not an
    oversight.** Python raises `AdmissionRejected` out of `remove_edge_by_id`
    (`index_v4/core.py::ReachabilityIndex._remove_edge_locked`) and so never reaches the
    release pair: a removal that found no edge must not run the epilogue. Wrapping the
    whole `if` instead would release bridges on a no-op retraction.

    ⚠ **Why this re-point is free for the W3d theory**: `ReachedByW3d` (below) has NO
    remove constructor — write and cascade only — so nothing in the W3d closure development
    sees it. That is why step 3b does it FIRST of the three, as four lines of tactic
    repair. -/
def GraphState.removeLoggedOne (σ : GraphState) (t : Tuple) : GraphState :=
  if (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges
  then ((σ.removeEdgeOne (subjNode t.subject) (objNode t.object t.relation)).pushDelta
    (objNode t.object t.relation) t.relation true).releasePostLogged t
  else σ

/-- **The logged rule-routed retraction**: the retract mirror of `writeLoggedRules` — fold
    `removeLoggedOne` over the SAME `rewriteClosureL S (rawWriteTuples S t)` the write path
    folds `writeLoggedOne` over (`zanzibar_utils_v1.py::RuleSet.apply` as a list, stage 1 =
    the re-addressing onto storage leaves, stage 2 = the closure under
    `schemaRewritesL`). Mirrors `connectedstore/apply.py::_apply_row`'s REMOVE branch: the
    `ruleset.apply(triple)` fan-out with `WildcardIndex._remove_tuple_trusted` per member.

    **RE-POINTED by step R5 (the remove leg of THE FLIP)**: `apply.py::_apply_row`
    (`:62-66`) computes `ruleset.apply(triple)` ONCE, OUTSIDE the ADD/REMOVE choice —
    `fn = widx._add_tuple_trusted if row.op == 'ADD' else widx._remove_tuple_trusted`,
    then `for d in ruleset.apply(triple): fn(...)`. So the retraction fan-out is
    byte-for-byte the write fan-out, and folding the PLAIN `rewriteClosure S t` here while
    the write leg folds the leaf-routed closure was a MODEL BUG: it left the minted leaf
    edge behind on a write-then-remove of one tuple (the "edge leak"). With both legs on
    the same list the retraction retracts exactly what the write leg materialised. -/
def GraphState.removeLoggedRules (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl (fun acc u => acc.removeLoggedOne u) σ

/-- **The chain-level retraction admission guard** — the retract mirror of the write leg's
    `FoldAdmits`. A raw tuple may be retracted only if it is IN the store: `t ∈ T`. Mirror
    of `connectedstore/source.py::TupleSource.remove`, whose `engine.remove_tuple`
    raises `ValueError` and logs nothing on an absent tuple. **Scope caveat
    (`ZT-P4-2c`):** presence is only ONE conjunct of the chain's remove gate —
    `GraphIndex/Exec.lean::removeGateB` additionally demands a DRAINED prior state,
    which `TupleSource.remove` does not impose and the batched apply schedule
    routinely violates. `σ` is carried for constructor
    symmetry with the write leg's `hadm : FoldAdmits σ …` (the guard itself is store-only). -/
def RemoveAdmits (_σ : GraphState) (T : Store) (t : Tuple) : Prop := t ∈ T

/-- The bridge release leaves the watermark untouched (`P6` step 3). -/
@[simp] theorem releaseInBridges_watermark (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridges c).watermark = σ.watermark := by
  unfold GraphState.releaseInBridges
  split <;> simp

/-- …and so does its logged twin. -/
@[simp] theorem releaseInBridgesLogged_watermark (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridgesLogged c).watermark = σ.watermark := by
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

/-- The release epilogue is residue-inert. ★ ADDITIVE, `P6` step 3b (2026-09-14): re-point
    #3 put it inside `removeLoggedOne`, and two downstream `removeLoggedOne_residue` twins
    (`CascadeStrataInv.lean`, `CascadeStrataSettle.lean`) are one `rw` over it. -/
@[simp] theorem releaseInBridgesLogged_residue (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridgesLogged c).residue = σ.residue := by
  unfold GraphState.releaseInBridgesLogged
  split <;> simp

@[simp] theorem releasePostLogged_residue (σ : GraphState) (t : Tuple) :
    (σ.releasePostLogged t).residue = σ.residue := by
  unfold GraphState.releasePostLogged; simp

/-- The release epilogue leaves the schema, the nodes and the watermark fixed — the three
    projections `removeLoggedOne`'s own trio needs now that step 3b's re-point #3 wraps it.
    (Landed by `P6` step 3a; **MOVED up above that trio on 2026-09-14**, when the re-point
    turned "the dischargers step 3b will need" into "the dischargers the next three proofs
    call". Statements and proofs unchanged.) -/
@[simp] theorem releasePostLogged_schema (σ : GraphState) (t : Tuple) :
    (σ.releasePostLogged t).schema = σ.schema := by
  unfold GraphState.releasePostLogged; simp

@[simp] theorem releasePostLogged_nodes (σ : GraphState) (t : Tuple) :
    (σ.releasePostLogged t).nodes = σ.nodes := by
  unfold GraphState.releasePostLogged; simp

@[simp] theorem releasePostLogged_watermark (σ : GraphState) (t : Tuple) :
    (σ.releasePostLogged t).watermark = σ.watermark := by
  unfold GraphState.releasePostLogged; simp

/-! ★ **The trio below keeps its STATEMENTS across `P6` step 3b re-point #3 (2026-09-14)**;
each proof gains one leading `rw` through the release epilogue. `removeLoggedOne_nodes` is
the one worth pausing on: it stays TRUE because `releaseInBridges` removes an EDGE via
`removeEdgeOne` and this model has no node GC — a deliberate, recorded model/Python gap.
If node GC is ever modelled, this is the theorem that goes false first. -/

/-- One logged retraction leaves the schema fixed. -/
@[simp] theorem removeLoggedOne_schema (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).schema = σ.schema := by
  unfold GraphState.removeLoggedOne
  split
  · rw [releasePostLogged_schema, pushDelta_schema, removeEdgeOne_schema]
  · rfl

/-- One logged retraction leaves the nodes fixed (node GC is modeled away, cf.
    `removeEdgeOne`). -/
@[simp] theorem removeLoggedOne_nodes (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).nodes = σ.nodes := by
  unfold GraphState.removeLoggedOne
  split
  · rw [releasePostLogged_nodes, pushDelta_nodes, removeEdgeOne_nodes]
  · rfl

/-- One logged retraction leaves the watermark untouched (it only decrements an edge and
    appends a frontier row — the drain watermark advances in the cascade, not here). -/
@[simp] theorem removeLoggedOne_watermark (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).watermark = σ.watermark := by
  unfold GraphState.removeLoggedOne
  split
  · rw [releasePostLogged_watermark, pushDelta_watermark, removeEdgeOne_watermark]
  · rfl

/-! ### ★ The release epilogue's EDGE and OUTBOX facts (`P6` step 3b, 2026-09-13g)

The retract mirror of the write-side block above, and ADDITIVE in the same way. Step 7 of
the `P6` plan needs them so `CascadeStable.lean:2305::removeLoggedOne_edges_subset`,
`:2333::removeLoggedOne_outbox_mono` and `:2359::removeLoggedRules_edge_delta` keep their
statements once `removeLoggedOne` gains the epilogue. The `d.node = ab.2` form survives
here for the same reason it survives on the write side: `releaseInBridges` erases exactly
`(c, wAnyNode (c.type, c.pred))` (`:247`) while `releaseInBridgesLogged` (`:253`) pushes
its row at `wAnyNode (c.type, c.pred)` — the erased edge's TARGET. -/

/-- The bridge release never touches the outbox (it only erases one edge) — the fourth
    member of the `releaseInBridges_schema/nodes/residue` projection family above, needed
    by the logged twin's monotonicity below. -/
@[simp] theorem releaseInBridges_outbox (σ : GraphState) (c : NodeKey) :
    (σ.releaseInBridges c).outbox = σ.outbox := by
  unfold GraphState.releaseInBridges
  split <;> simp

/-- The logged release only ever PUSHES outbox rows (retract mirror of
    `ensureInBridgesLogged_outbox_mono`). -/
theorem releaseInBridgesLogged_outbox_mono (σ : GraphState) (c : NodeKey) :
    ∀ d ∈ σ.outbox, d ∈ (σ.releaseInBridgesLogged c).outbox := by
  intro d hd
  unfold GraphState.releaseInBridgesLogged
  split
  · rw [releaseInBridges_outbox]; exact hd
  · rw [pushDelta_outbox]
    exact List.mem_cons_of_mem _ (by rw [releaseInBridges_outbox]; exact hd)

/-- …and so does the whole release epilogue (both endpoints). -/
theorem releasePostLogged_outbox_mono (σ : GraphState) (t : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.releasePostLogged t).outbox := by
  intro d hd
  unfold GraphState.releasePostLogged
  exact releaseInBridgesLogged_outbox_mono _ _ d
    (releaseInBridgesLogged_outbox_mono σ _ d hd)

/-- The logged release only shrinks the edge multiset — `releaseInBridges_edges_subset`
    (`:464`) carried through the outbox wrapper. -/
theorem releaseInBridgesLogged_edges_subset (σ : GraphState) (c : NodeKey) :
    ∀ e ∈ (σ.releaseInBridgesLogged c).edges, e ∈ σ.edges := by
  intro e he
  rw [releaseInBridgesLogged_edges] at he
  exact releaseInBridges_edges_subset σ c e he

/-- …and so does the whole release epilogue — what
    `CascadeStable.lean:2305::removeLoggedOne_edges_subset` needs on top of its own
    `removeEdgeOne` + `List.mem_of_mem_erase` step once the epilogue wraps it. -/
theorem releasePostLogged_edges_subset (σ : GraphState) (t : Tuple) :
    ∀ e ∈ (σ.releasePostLogged t).edges, e ∈ σ.edges := by
  intro e he
  unfold GraphState.releasePostLogged at he
  exact releaseInBridgesLogged_edges_subset σ _ e
    (releaseInBridgesLogged_edges_subset _ _ e he)

/-- ★ **The release leg erases ONLY `wAny`-targeted edges**, so anything else survives it
    verbatim. `GraphState.releaseInBridges` erases exactly
    `(c, wAnyNode (c.type, c.pred))`, whose target is a `wAny` node by construction
    (`State.lean::wAnyNode`).

    (`P6` step 3b, 2026-09-14.) This is the ONE fact that lets the retraction leg's
    edge-preservation family keep working: those theorems say "an edge survives one
    retraction step when no closure member targets it", and after re-point #3 that is FALSE
    as stated — the release can erase a bridge edge no closure member ever targeted. Adding
    `b.variant ≠ Variant.wAny` is strictly sufficient and free at every consumer, because
    the consumer chain instantiates `b := objNode ⟨dt, on⟩ R` and
    `State.lean::objNode_ne_wAny` discharges it. ⚠ Do NOT instead widen the `hne` premise
    into a disjunction over the two endpoints' bridge shapes: that pushes two obligations
    where one variant fact suffices. -/
theorem mem_releaseInBridgesLogged_edges_of_ne_wAny (σ : GraphState) (c : NodeKey)
    {a b : NodeKey} (hb : b.variant ≠ Variant.wAny) (h : (a, b) ∈ σ.edges) :
    (a, b) ∈ (σ.releaseInBridgesLogged c).edges := by
  rw [releaseInBridgesLogged_edges]
  unfold GraphState.releaseInBridges
  split
  · refine (mem_removeEdgeOne_edges_of_ne ?_).mpr h
    intro heq
    exact hb (congrArg NodeKey.variant (congrArg Prod.snd heq))
  · exact h

/-- …and so does the whole epilogue, both legs. -/
theorem mem_releasePostLogged_edges_of_ne_wAny (σ : GraphState) (t : Tuple)
    {a b : NodeKey} (hb : b.variant ≠ Variant.wAny) (h : (a, b) ∈ σ.edges) :
    (a, b) ∈ (σ.releasePostLogged t).edges := by
  unfold GraphState.releasePostLogged
  exact mem_releaseInBridgesLogged_edges_of_ne_wAny _ _ hb
    (mem_releaseInBridgesLogged_edges_of_ne_wAny σ _ hb h)

/-- ★ **The release leg is MULTIPLICITY-inert off the `wAny` targets.** The membership form
    above is not enough for the R3 occurrence-count stack, which reasons about `List.count`
    rather than `∈`: an epilogue that erased one copy of a non-bridge edge would preserve
    membership at multiplicity ≥ 2 and still break the count law. (`P6` step 3b, 2026-09-14.) -/
theorem count_releaseInBridgesLogged_of_ne_wAny (σ : GraphState) (c : NodeKey)
    {p : NodeKey × NodeKey} (hp : p.2.variant ≠ Variant.wAny) :
    (σ.releaseInBridgesLogged c).edges.count p = σ.edges.count p := by
  rw [releaseInBridgesLogged_edges]
  unfold GraphState.releaseInBridges
  split
  · refine count_removeEdgeOne_of_ne ?_
    intro heq
    exact hp (congrArg NodeKey.variant (congrArg Prod.snd heq))
  · rfl

/-- …and so is the whole epilogue. -/
theorem count_releasePostLogged_of_ne_wAny (σ : GraphState) (t : Tuple)
    {p : NodeKey × NodeKey} (hp : p.2.variant ≠ Variant.wAny) :
    (σ.releasePostLogged t).edges.count p = σ.edges.count p := by
  unfold GraphState.releasePostLogged
  rw [count_releaseInBridgesLogged_of_ne_wAny _ _ hp,
    count_releaseInBridgesLogged_of_ne_wAny _ _ hp]

/-- ★ **A released bridge edge carries its frontier row** (per-leg retract mirror of
    `ensureInBridgesLogged_edge_delta`): an edge present before the logged release and
    absent after was the bridge edge, and the release emitted a row with an id strictly
    above the unchanged watermark at that edge's own head. The id bound is
    `releaseInBridges_watermark` (`:889`) exactly where the routed arm uses
    `removeEdgeOne_watermark`. -/
theorem releaseInBridgesLogged_edge_delta (σ : GraphState) (c : NodeKey) :
    ∀ ab, ab ∈ σ.edges → ab ∉ (σ.releaseInBridgesLogged c).edges →
      ∃ d ∈ (σ.releaseInBridgesLogged c).outbox, σ.watermark < d.id ∧ d.node = ab.2 := by
  intro ab hin hout
  rw [releaseInBridgesLogged_edges] at hout
  by_cases hOnly : σ.inBridgeOnly c = true
  · have hrel : (σ.releaseInBridges c).edges
        = σ.edges.erase (c, wAnyNode (c.type, c.pred)) := by
      unfold GraphState.releaseInBridges
      rw [if_pos hOnly, removeEdgeOne_edges]
    have habeq : ab = (c, wAnyNode (c.type, c.pred)) := by
      by_contra hne
      exact hout (by rw [hrel]; exact (List.mem_erase_of_ne hne).mpr hin)
    have hEq : ¬ ((σ.releaseInBridges c).edges = σ.edges) := by
      intro h
      exact hout (by rw [h]; exact hin)
    have hob : (σ.releaseInBridgesLogged c).outbox
        = ⟨(σ.releaseInBridges c).nextDeltaId, wAnyNode (c.type, c.pred), c.pred, true⟩
          :: (σ.releaseInBridges c).outbox := by
      unfold GraphState.releaseInBridgesLogged
      rw [if_neg hEq, pushDelta_outbox]
    refine ⟨⟨(σ.releaseInBridges c).nextDeltaId, wAnyNode (c.type, c.pred),
      c.pred, true⟩, ?_, ?_, ?_⟩
    · rw [hob]; exact List.mem_cons_self
    · show σ.watermark < (σ.releaseInBridges c).nextDeltaId
      have h1 : (σ.releaseInBridges c).nextDeltaId
          = max (σ.releaseInBridges c).maxOutboxId (σ.releaseInBridges c).watermark + 1 := rfl
      have h2 : (σ.releaseInBridges c).watermark = σ.watermark := releaseInBridges_watermark σ c
      omega
    · show (⟨(σ.releaseInBridges c).nextDeltaId, wAnyNode (c.type, c.pred),
        c.pred, true⟩ : Delta).node = ab.2
      rw [habeq]
  · exact absurd (by
      show ab ∈ (σ.releaseInBridges c).edges
      unfold GraphState.releaseInBridges
      rw [if_neg (by simpa using hOnly)]
      exact hin) hout

/-- …and the epilogue-level form, which is what
    `CascadeStable.lean:2359::removeLoggedRules_edge_delta` consumes: the lost edge was
    released by one of the two legs, and either leg's row survives to the end (the second
    leg only pushes, `releaseInBridgesLogged_outbox_mono`) with the watermark unmoved. -/
theorem releasePostLogged_edge_delta (σ : GraphState) (t : Tuple) :
    ∀ ab, ab ∈ σ.edges → ab ∉ (σ.releasePostLogged t).edges →
      ∃ d ∈ (σ.releasePostLogged t).outbox, σ.watermark < d.id ∧ d.node = ab.2 := by
  intro ab hin hout
  unfold GraphState.releasePostLogged at hout ⊢
  by_cases h1 : ab ∈ (σ.releaseInBridgesLogged (subjNode t.subject)).edges
  · obtain ⟨d, hd, hgt, hnode⟩ :=
      releaseInBridgesLogged_edge_delta (σ.releaseInBridgesLogged (subjNode t.subject))
        (objNode t.object t.relation) ab h1 hout
    exact ⟨d, hd, by rwa [releaseInBridgesLogged_watermark] at hgt, hnode⟩
  · obtain ⟨d, hd, hgt, hnode⟩ :=
      releaseInBridgesLogged_edge_delta σ (subjNode t.subject) ab hin h1
    exact ⟨d, releaseInBridgesLogged_outbox_mono _ (objNode t.object t.relation) d hd,
      hgt, hnode⟩

/-! ### ★ Red-to-green witnesses for the LOGGED step-3a legs (2026-09-13d)

`bridgePreLogged`, `releasePostLogged` and `writeBridgedOne_logged_evalEq` are additive and
INERT — nothing calls them until step 3b — so, exactly as for step 2's four definitions,
`decide` pins are the only evidence they are right. The store and the concrete are
`UsStarWrite.lean::BridgedWriteWitness`'s, so the unlogged pins there and the logged pins
here read as ONE scenario.

⚠ The load-bearing one is `prologue_second_member_silent`. It couples the composition to
the step-2 presence guard: without the guard, a leaf-routed fold that touches the same
subject twice emits a SECOND delta row — one dirty key per redundant routed member, which
is worse than the duplicate edge, and which `UsStarWrite.lean::BridgedWriteWitness.
fold_keeps_one_bridge_copy` cannot see because it reads the edges, not the outbox. -/
namespace BridgedLegWitness

/-- The step-3a write scenario, logged: the through-shape member over `Sthru`. -/
def base : GraphState := BridgedWriteWitness.base

/-- The prologue run once, on the member the whole item exists for. -/
def pre1 : GraphState := base.bridgePreLogged BridgedWriteWitness.tThru

/-- The prologue run again on the SAME subject — the second routed member of a fold. -/
def pre2 : GraphState := pre1.bridgePreLogged BridgedWriteWitness.tThru2

/-- **NON-VACUITY**: the prologue FIRES — one row, at the bridge target, carrying the
    concrete's predicate and the leaf flag `writeLoggedOne` uses. The whole row is pinned,
    not its length: a row at the wrong key would keep a length pin green. -/
theorem prologue_emits : pre1.outbox = [⟨1, BridgedWriteWitness.w0, "viewer", true⟩] := by
  decide

/-- ★ **The presence guard, through the COMPOSED prologue**: a second member sharing the
    subject is not a flip, so it emits nothing more. -/
theorem prologue_second_member_silent : pre2.outbox = pre1.outbox := by decide

/-- **ATTRIBUTION**: at a member with no bridged-in endpoint the prologue is silent from
    the start, so `prologue_emits` is the bridge firing and not "this leg always emits". -/
theorem prologue_unbridged_silent :
    (base.bridgePreLogged BridgedWriteWitness.tCtrl).outbox = [] := by decide

/-- ★ **THE HINGE, executably**: the logged prologue and the unlogged one agree on
    everything a READ consults. `bridgePreLogged_evalEq` is the theorem; this is its
    red-to-green arm, and it is what will let step 3b bridge the logged leg AND its
    unlogged `writeRulesRaw` twin without restating `writeLoggedRules_evalEq`. -/
theorem prologue_evalEq_edges :
    pre1.edges = (base.bridgePre BridgedWriteWitness.tThru).edges := by decide

theorem prologue_evalEq_nodes :
    pre1.nodes = (base.bridgePre BridgedWriteWitness.tThru).nodes := by decide

/-- **ATTRIBUTION for the hinge**: the two states are NOT equal — the outbox is exactly
    where they differ — so the pair above is a real agreement, not two names for one
    state. -/
theorem prologue_outboxes_differ :
    pre1.outbox ≠ (base.bridgePre BridgedWriteWitness.tThru).outbox := by decide

/-- The bridged-only state the release epilogue is meant to collect. -/
def bridgedOnly : GraphState := base.bridgePre BridgedWriteWitness.tThru

/-- **NON-VACUITY**: the epilogue FIRES on a dead bridge — the edge multiset returns to
    its pre-write value, which is the `releaseFixes := true` the step-1 probe measured. -/
theorem epilogue_fires :
    (bridgedOnly.releasePostLogged BridgedWriteWitness.tThru).edges = base.edges := by
  decide

/-- ★ **THE CONTROL that makes the epilogue safe**: with the grant still in place the
    release DECLINES and the bridge stays. An epilogue that fired here would silently
    revoke a live grant's bridge — `_maybe_remove_bridges`'s `reference_count == degree`
    guard is what forbids it. -/
theorem epilogue_declines_on_a_live_node :
    ((base.writeBridgedOne BridgedWriteWitness.tThru).releasePostLogged
      BridgedWriteWitness.tThru).edges
      = (base.writeBridgedOne BridgedWriteWitness.tThru).edges := by decide

/-! ### ★★ `P6` step 3b, RE-POINTS #1 and #3 — the ROUND TRIP (2026-09-14)

**The plan's ASSURANCE BLOCKER, discharged here.** Every pin ABOVE this note is stated on
`bridgePreLogged` / `bridgePre` / `writeBridgedOne` / `releasePostLogged` **directly** — I
checked each one — and therefore **no re-point can flip any of them**. The composition would
otherwise land with zero red-to-green evidence: `writeLoggedOne` and `removeLoggedOne` are
the definitions that actually moved, and until now nothing decided anything about them.

The six pins below sit on the re-pointed definitions themselves. `round_trip_returns_to_base`
is the one to read first: it is what the *pair* of re-points buys, and it is FALSE under
either one alone.

⚠ **`writeLoggedOne`/`removeLoggedOne` here are the LOGGED leg, so these pins also carry the
outbox discipline** — a bridge that fires without its frontier row, or a release that moves
the drain cursor, would break the cascade rather than the edge set, and no edge-level pin
would see it.

##### CONTROLLED — MUTATION SWEEP (2026-09-14)

Five mutations, one `lake build ZanzibarProofs.GraphIndex.Cascade` each, file restored
byte-clean between runs (`md5 53738b9610ed673e93b95d4209c0921c` is the swept file). The
GREEN column was written down BEFORE each run. **Two of the five changed the deliverable**,
and that is the point of recording them rather than the reds alone.

```
M0  INSTRUMENT CONTROL -- flip `unbridged_probe_would_have_admitted_it`, `= true` -> `= false`.
    RED: exactly 1, attributed by line and proposition. -> the harness works.

M6  UNDO RE-POINT #3 -- drop `.releasePostLogged t` from `removeLoggedOne`'s then-branch.
    RED: the `removeLoggedOne_{schema,nodes,watermark}` trio (stale `rw`) and ONE kernel
    refutation:
      error: Cascade.lean:1267:58: Tactic `decide` proved that the proposition
        ((base.writeLoggedOne …tThru).removeLoggedOne …tThru).edges = base.edges
      is false
    GREEN: every `writeLoggedOne_*` pin, `absent_retraction_is_the_identity`,
    `round_trip_leaves_the_watermark`.
    -> the bridge LEAKS on a write-then-remove without #3, refuted rather than argued.

M7  WRONG PLACEMENT -- wrap the WHOLE `if` instead of the then-branch.
    RED: the trio's `rfl` steps, and exactly ONE kernel refutation:
      error: Cascade.lean:1295:2: Tactic `decide` proved that the proposition
        (bridgedOnly.removeLoggedOne …tThru).edges = bridgedOnly.edges
      is false
    GREEN: `round_trip_returns_to_base` -- at the round-trip fixture the two placements
    AGREE, which is exactly why that pin cannot stand in for this one.
    -> `absent_retraction_is_the_identity` is the ONLY thing in the tree separating the two
       placements. It was added for this mutation.

M8  UNDO RE-POINT #1 -- `writeLoggedOne` back to `if σ.admitEdge … then (σ.writeDirect t)…`.
    RED: `writeLoggedOne_evalEq` and `writeLoggedRules_watermark` (proof failures), plus
    THREE kernel refutations: `writeLoggedOne_creates_the_bridge`,
    `writeLoggedOne_emits_the_bridge_row`, `round_trip_starts_two_edges_up`.
    ⚠ **THIS RUN CHANGED THE DELIVERABLE.** On its first pass the third refutation did not
    exist: the pin read `(base.writeLoggedOne tThru).edges ≠ base.edges` and stayed GREEN,
    because the routed GRANT alone already makes that true. The docstring on
    `round_trip_returns_to_base` claimed it as the non-vacuity that forbids the
    "no bridge, so nothing to collect" reading, and **it did not forbid it**. Both were
    fixed: the pin now counts (`= base.edges.length + 2`) and the docstring now points at
    the pins that actually discriminate. A `≠` non-vacuity is the weakest useful form;
    prefer one that names the thing, or counts it.
    GREEN: `round_trip_returns_to_base` -- correctly, and that is the reading the fix
    documents rather than hides.

M9  WRONG ORDER -- probe `σ.admitEdge` (UNBRIDGED) while still writing the bridged state,
    i.e. bridge-after-probe. The `M5` shape from step 3a, at the logged leg.
    RED: `writeLoggedOne_evalEq` (proof failure) and TWO kernel refutations:
      error: Cascade.lean:1302:78: … (base.writeLoggedOne …tCycle).edges = base.edges
      is false
      error: Cascade.lean:1308:80: … (base.writeLoggedOne …tCycle).outbox = base.outbox
      is false
    ⚠ **THIS RUN ALSO CHANGED THE DELIVERABLE.** On its first pass BOTH refutations were
    absent — the namespace had no cycle fixture, every other pin stayed green, and the only
    red was a broken PROOF. Per `docs/sabotage-procedure.md` §"A RED ON A HELPER LEMMA DOES
    NOT PROPAGATE", a proof-only red is not evidence: Lean admits a failed declaration at
    its stated type, so a later rewrite of `writeLoggedOne_evalEq` would have retired the
    only signal that the ORDER is load-bearing on this leg. `logged_leg_refuses_the_cycle`
    and `_silently` were added in response, and `unbridged_probe_would_have_admitted_it`
    is their attribution.
    -> the step-3a order pins (`UsStarWrite.lean::BridgedWriteWitness`) are stated on
       `bridgePre`/`writeBridgedOne` DIRECTLY and are blind to this mutation. A pin must
       name the definition that moved.
```

⚠ **Honest limit.** A module sweep: a mutation here stops the build at `Cascade`, so every
downstream consumer is un-elaborated and each RED list means *"at least these"*. The line
numbers in the fenced block are the swept file's and were pushed down by this very note —
resolve by SYMBOL. -/

/-- ★★ **RE-POINT #1, observed at `writeLoggedOne`.** The live logged write leg materialises
    the in-bridge. FALSE on 2026-09-13, when `writeLoggedOne` was
    `if σ.admitEdge … then (σ.writeDirect t).pushDelta … else σ`. -/
theorem writeLoggedOne_creates_the_bridge :
    (subjNode BridgedWriteWitness.tThru.subject, BridgedWriteWitness.w0)
      ∈ (base.writeLoggedOne BridgedWriteWitness.tThru).edges := by decide

/-- ★ **…and it comes with its frontier row**, at the bridge TARGET, which is the
    denormalisation `writeLoggedRules_edge_delta`'s `d.node = ab.2` shape depends on. The
    whole row is pinned, not its length: a row at the wrong key would keep a length pin
    green. -/
theorem writeLoggedOne_emits_the_bridge_row :
    ⟨1, BridgedWriteWitness.w0, "viewer", true⟩
      ∈ (base.writeLoggedOne BridgedWriteWitness.tThru).outbox := by decide

/-- ★ **ATTRIBUTION CONTROL for re-point #1**: at a member with no bridged-in endpoint the
    re-pointed `writeLoggedOne` agrees with the PRE-RE-POINT body, spelled out. So the pin
    above is the bridge's doing and not "the definition changed everywhere". -/
theorem writeLoggedOne_control_agrees_with_the_old_body :
    (base.writeLoggedOne BridgedWriteWitness.tCtrl).edges
      = (if base.admitEdge (subjNode BridgedWriteWitness.tCtrl.subject)
            (objNode BridgedWriteWitness.tCtrl.object BridgedWriteWitness.tCtrl.relation)
          then ((base.writeDirect BridgedWriteWitness.tCtrl).pushDelta
            (objNode BridgedWriteWitness.tCtrl.object BridgedWriteWitness.tCtrl.relation)
            BridgedWriteWitness.tCtrl.relation true)
          else base).edges := by decide

/-- ★★ **RE-POINTS #1 AND #3 TOGETHER — the round trip.** Write a through-shape member on
    the live logged leg, then retract it on the live logged leg: the edge multiset returns
    to exactly where it started.

    ⚠ **This equation is NOT by itself evidence for re-point #1, and an earlier draft of
    this docstring said it was.** Undoing #1 leaves it GREEN — no bridge is created, so the
    retraction has nothing to collect and the round trip closes for the wrong reason
    (mutation `M8`, measured). What forbids that reading is
    `writeLoggedOne_creates_the_bridge` above, which names the bridge edge, plus
    `round_trip_starts_two_edges_up` below, which pins that the intermediate state is two
    edges — grant AND bridge — above `base`. Read the three together.
    What this pin DOES carry alone is re-point #3: without it the bridge is created and
    never released, so a write-then-remove **leaks** it — the `_leak_accumulates` shape,
    kernel-refuted as mutation `M6`. -/
theorem round_trip_returns_to_base :
    ((base.writeLoggedOne BridgedWriteWitness.tThru).removeLoggedOne
      BridgedWriteWitness.tThru).edges = base.edges := by decide

/-- **NON-VACUITY for the round trip, in the form that actually discriminates.** The
    intermediate state sits exactly TWO edges above `base` — the routed grant and the
    subject's in-bridge. A `≠ base.edges` pin would have been satisfied by the grant alone
    and so would have stayed green with re-point #1 undone; this one does not. -/
theorem round_trip_starts_two_edges_up :
    (base.writeLoggedOne BridgedWriteWitness.tThru).edges.length
      = base.edges.length + 2 := by decide

/-- ★ **RE-POINT #3 does not move the drain cursor.** The release epilogue runs inside a
    retraction that also emits; the watermark is the cascade's to advance, not the write
    leg's. An epilogue that touched it would desynchronise the drain from the frontier
    without changing a single edge. -/
theorem round_trip_leaves_the_watermark :
    ((base.writeLoggedOne BridgedWriteWitness.tThru).removeLoggedOne
      BridgedWriteWitness.tThru).watermark = base.watermark := by decide

/-- ★★ **RE-POINT #1 PROBES THE BRIDGED STATE, and this pin is what makes the ORDER
    observable on the LOGGED leg.** ⚠ It exists because a mutation asked for it: moving the
    guard back to `σ.admitEdge` while keeping the bridged write — *probe first, bridge
    second* — left every other pin in this namespace green (`M9`). `UsStarWrite.lean::
    BridgedWriteWitness.{bridged_probe_refuses_the_cycle, cycle_write_materialises_nothing}`
    pin the order on the UNLOGGED step and cannot see it here, because they never mention
    `writeLoggedOne`.

    `tCycle` is the wildcard-userset grant `folder:*#viewer viewer folder:f1`, whose object
    endpoint's own in-bridge closes a cycle with it. Bridge-before-grant REFUSES it — the
    shipped index's behaviour, where "cycle errors attach to the grant, the offending
    write" — so the logged leg materialises nothing at all. -/
theorem logged_leg_refuses_the_cycle :
    (base.writeLoggedOne BridgedWriteWitness.tCycle).edges = base.edges := by decide

/-- ★ **…and emits nothing either.** The edge pin alone would be satisfied by a leg that
    rolled the edge back but left the frontier row, which is the worse failure: a delta
    with no edge behind it drives a cascade over a grant that was rejected. -/
theorem logged_leg_refuses_the_cycle_silently :
    (base.writeLoggedOne BridgedWriteWitness.tCycle).outbox = base.outbox := by decide

/-- ★ **ATTRIBUTION for the order.** The UNBRIDGED probe ADMITS the same grant. So the two
    refusals above are the bridge prologue's doing, and a `writeLoggedOne` that probed
    before bridging would accept a write the shipped index rejects. -/
theorem unbridged_probe_would_have_admitted_it :
    base.admitEdge (subjNode BridgedWriteWitness.tCycle.subject)
      (objNode BridgedWriteWitness.tCycle.object BridgedWriteWitness.tCycle.relation)
      = true := by decide

/-- ★★ **THE ELSE-BRANCH IS OBSERVABLE, and this is the only pin that sees it.** A
    retraction that finds no edge must be the IDENTITY: Python raises `AdmissionRejected`
    out of `remove_edge_by_id` (`index_v4/core.py::ReachabilityIndex._remove_edge_locked`)
    and never reaches `_maybe_remove_bridges`. Re-point #3 therefore wraps
    `removeLoggedOne`'s **then-branch**, not its whole `if`.

    `bridgedOnly` is the state where that distinction bites: it carries the bridge and NOT
    the grant, so the `∈ σ.edges` guard fails, while `epilogue_fires` (above, same fixture)
    proves the release would have collected that bridge had it run. Wrapping the whole `if`
    — the plausible and wrong edit — would revoke a live bridge on a retraction of a tuple
    that was never there. Nothing else in the tree distinguishes the two placements. -/
theorem absent_retraction_is_the_identity :
    (bridgedOnly.removeLoggedOne BridgedWriteWitness.tThru).edges = bridgedOnly.edges := by
  decide

/-- **NON-VACUITY for the placement pin**: `bridgedOnly` really does carry something the
    epilogue would take, so the identity above is a decision not to act, not an absence of
    anything to act on. -/
theorem bridgedOnly_has_something_to_release :
    bridgedOnly.edges ≠ base.edges := by decide

end BridgedLegWitness

/-- The logged retraction keeps the schema fixed (a fold of `removeLoggedOne_schema`). -/
theorem removeLoggedRules_schema (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).schema = σ.schema := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosureL S (rawWriteTuples S t) = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_schema σ u

/-- The logged retraction keeps the nodes fixed (a fold of `removeLoggedOne_nodes`). -/
theorem removeLoggedRules_nodes (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).nodes = σ.nodes := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosureL S (rawWriteTuples S t) = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_nodes σ u

/-- The logged retraction leaves the watermark untouched (mirror of
    `writeLoggedRules_watermark`; a fold of `removeLoggedOne_watermark`). -/
theorem removeLoggedRules_watermark (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).watermark = σ.watermark := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosureL S (rawWriteTuples S t) = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_watermark σ u

/-! ## The reconcile pass is `EvalEq`-congruent -/

/-- Persisted coverage is residue-determined. -/
theorem coveredAt_congr {σ' σ : GraphState} (h : σ'.residue = σ.residue) (k : NodeKey)
    (R : String) (sh : Shape) : σ'.coveredAt k R sh = σ.coveredAt k R sh := by
  unfold GraphState.coveredAt
  rw [h]

/-- The wholesale residue recompute is `EvalEq`-congruent (its three filters read
    `checkFn`/`coveredFn`, which consult only edges/nodes). -/
theorem reconcileResidueKey_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    EvalEq (σ'.reconcileResidueKey T dt on R e shapes negCands uposCands)
      (σ.reconcileResidueKey T dt on R e shapes negCands uposCands) := by
  have hcov : ∀ sh : Shape, σ'.coveredFn T dt on R e sh = σ.coveredFn T dt on R e sh := by
    intro sh
    unfold GraphState.coveredFn
    exact checkFn_congr h.edges h.nodes T _ dt on R e
  have hchk : ∀ c : SubjectRef, σ'.checkFn T c dt on R e = σ.checkFn T c dt on R e :=
    fun c => checkFn_congr h.edges h.nodes T c dt on R e
  refine ⟨?_, ?_, ?_, ?_⟩
  · rw [reconcileResidueKey_schema, reconcileResidueKey_schema]; exact h.schema
  · rw [reconcileResidueKey_edges, reconcileResidueKey_edges]; exact h.edges
  · rw [reconcileResidueKey_nodes, reconcileResidueKey_nodes]; exact h.nodes
  · funext k' r'
    by_cases hk : k' = objNode ⟨dt, on⟩ R ∧ r' = R
    · obtain ⟨hk1, hk2⟩ := hk
      subst hk1; subst hk2
      rw [reconcileResidueKey_residue_self, reconcileResidueKey_residue_self]
      simp only [hcov, hchk]
    · rw [reconcileResidueKey_residue_other hk, reconcileResidueKey_residue_other hk]
      rw [h.residue]

/-- Edge removal is `EvalEq`-congruent. -/
theorem removeEdgePair_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (a b : NodeKey) :
    EvalEq (σ'.removeEdgePair a b) (σ.removeEdgePair a b) :=
  ⟨h.schema, by rw [removeEdgePair_edges, removeEdgePair_edges, h.edges],
   by rw [removeEdgePair_nodes, removeEdgePair_nodes, h.nodes],
   by rw [removeEdgePair_residue, removeEdgePair_residue, h.residue]⟩

/-- The diffing edge audit is `EvalEq`-congruent. -/
theorem reconcileKeyD_evalEq (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ' σ : GraphState}, EvalEq σ' σ →
      EvalEq (σ'.reconcileKeyD T dt on R e cands) (σ.reconcileKeyD T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ' σ h; exact h
  | cons c rest ih =>
    intro σ' σ h
    rw [reconcileKeyD_cons, reconcileKeyD_cons, checkFn_congr h.edges h.nodes T c dt on R e,
      coveredAt_congr h.residue]
    split
    · exact ih (writeDirect_evalEq h ⟨c, R, ⟨dt, on⟩⟩)
    · exact ih (removeEdgePair_evalEq h _ _)

/-- **The combined diffing pass is `EvalEq`-congruent.** -/
theorem reconcileStarsKeyD_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    EvalEq (σ'.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands)
      (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands) := by
  unfold GraphState.reconcileStarsKeyD
  exact reconcileKeyD_evalEq T dt on R e cands
    (reconcileResidueKey_evalEq h T dt on R e shapes negCands uposCands)

/-! ## The delta → key mapping (decision 4) -/

/-- Candidate object nodes of one delta: the row's own object node plus its
    cascade-time reach cone — the model-level reconstruction of the per-flip rows'
    denormalized object ends (`{y : b ⇝ y}`, decision 1). -/
def GraphState.affectedObjects (σ : GraphState) (d : Delta) : List NodeKey :=
  d.node :: σ.nodes.filter (fun v => σ.reach d.node v)

/-- **The delta → derived-key mapping**
    (`index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`).

    Two branches, matching Python's LeafFamily/DerivedFamily split on the delta row.
    **Scope note (`ZT-P4-1`/§7.1, 2026-07-26):** Python's mapper has grown further
    channels this model does NOT carry (the subject-GC residue rescan over
    `::DeltaProcessor._keys_referencing`, the leaf `tupleset-ttu` dependents, and the
    `tupleset_feeders` / `target_feeders` arms); see `CORRESPONDENCE.md` §7.

    * **LeafFamily own-key branch** (the `isinstance(fam, LeafFamily)` arm of
      `::DeltaProcessor._map_deltas_to_keys`, `processor.py:1411-1422`): a RAW leaf-routed
      write/remove (`d.leaf = true`) dirties the PUBLIC key the delta's leaf name belongs
      to, `(d.node.type, publicOfLeaf S d.node.type d.node.pred, d.node.name)`.

      **RE-POINTED by step (alpha).** This branch used to test
      `isDerived S (d.node.type, d.node.pred)` on the DELTA'S OWN PREDICATE and emit that
      predicate as the key's relation. Post-flip that is simply the wrong lookup: the
      leaf-routed write re-addresses onto the MINTED LEAF NAME `<R>.<i>`, so the delta
      carries `d.node.pred = "approver.0"`, `isDerived` is FALSE there (a minted name is
      not a declared key), the branch never fired, and the cascade never reconciled the
      public key. Python does the lookup Python does: `fam = namespace.get((o_type,
      o_pred))` on the delta's OBJECT PREDICATE, and if that resolves to a `LeafFamily`
      it dirties `key = (o_type, fam.owner_relation, o_name)` — the PUBLIC owner
      relation recovered from the leaf. `Leaf.lean::publicOfLeaf` is exactly
      `fam.owner_relation`, index-agnostically (`::publicOfLeaf_leafPred`), and
      `::publicOfLeaf_rawWriteRels` is the round trip.

      REPLACE, not append. Python's arms are exclusive: a PUBLIC derived name resolves to
      a `DerivedFamily` and takes `_fan_out` (`processor.py:1445-1452`, an `elif`), never
      the own-key arm. The dropped `isDerived S (d.node.type, d.node.pred)` disjunct is
      also provably DEAD post-flip on a WF schema — for a derived seed every closure
      member is leaf-named (`Leaf.lean::mem_rawWriteRels_derived`) and no rule of
      `schemaRewritesL` outputs a derived relation (`noRuleOutputsL_of_derived`) — so
      keeping it as a third append component would perturb every
      `List.mem_append_left/right` shape in the tree for zero content.

      `d.node.name ≠ STAR` is KEPT: Python's `if o_name == '*': raise InvariantViolation`
      in that same arm (a wildcard-object delta on a derived key is a leaked decision-15
      shape; a `raise` rather than an `assert` since `ZT-P1-2`, so it survives
      `python -O`). `d.leaf = true` is KEPT and is load-bearing: reconcile emissions push
      with the default `leaf := false`, so this branch is empty for them — the fence that
      lets the cascade quiesce, since `_fan_out` never re-dirties its own key. Untainted
      families keep having no derived own-key: `publicOfLeaf` returns `none` on them
      (`Leaf.lean::publicOfLeaf_untainted`), which is the guard this branch now reads.
    * **DerivedFamily fan-out** (`::DeltaProcessor._fan_out`'s `edge.via == 'computed'`
      arm, fragment-restricted): a candidate object node `v` (concrete — derived keys
      are never star-named, which is what the wildcard-object `raise InvariantViolation`
      above and the compile-time `zanzibar_utils_v1.py::_reject_object_wildcard_scope`
      jointly enforce) dirties every declared derived key `(v.type, R)` whose def
      reads `v.pred` as a computed operand, at object `v.name`.

    Keys are `(dt, R, on)` triples. -/
def affectedKeys (S : Schema) (σ : GraphState) (d : Delta) :
    List (String × String × String) :=
  (if d.leaf = true ∧ d.node.name ≠ STAR then
     match publicOfLeaf S d.node.type d.node.pred with
     | some R => [(d.node.type, R, d.node.name)]
     | none   => []
   else [])
  ++ (σ.affectedObjects d).flatMap (fun v =>
    if v.name = STAR then []
    else S.keys.filterMap (fun k =>
      if k.1 = v.type ∧ isDerived S k = true ∧
          ((S.lookup k).map (fun e => (computedRefs e).contains v.pred)).getD false = true
      then some (k.1, k.2, v.name) else none))

/-- The rows above the drain watermark — this transaction's frontier
    (`outbox_rows(session, store, after_id=watermark)`). -/
def GraphState.frontierRows (σ : GraphState) : List Delta :=
  σ.outbox.filter (fun d => σ.watermark < d.id)

/-- The invalidation key set of the round: every frontier row's affected keys.
    This W3d-1 form is consumed only as a SET (`= []`, `∈`, `∉`), so it stays a bare
    `flatMap`. ⚠ It used to say "coalescing/dedup is irrelevant — reconciles are
    idempotent". That is true of the ANSWER and false of the STATE: `reconcileKeyDR`
    stacks one edge per candidate occurrence (`CORRESPONDENCE.md` §7.2 item 6), so a
    key reconciled twice in a round doubles its multiplicity, and the executed W3d-2
    form `cascadeKeysAbove` (`CascadeStrata.lean`) is deduplicated since 2026-09-05b
    after that compounding timed out ten conformance tests. -/
def cascadeKeys (S : Schema) (σ : GraphState) : List (String × String × String) :=
  σ.frontierRows.flatMap (affectedKeys S σ)

/-! ## The logged reconcile pass (decision 3) -/

/-- The `(dt, R, on)` key a job settles. -/
def W3cJob.key (j : W3cJob) : String × String × String := (j.dt, j.R, j.on)

/-- Apply one W3d job — the DIFFING pass (decision 7; shapes fixed to the schema's
    declared `wildcardShapes`). -/
def W3cJob.applyD (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : GraphState :=
  σ.reconcileStarsKeyD T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
    j.uposCands

/-- Run a batch of unlogged diffing jobs left-to-right. -/
def reconcileJobsD (S : Schema) (T : Store) (σ0 : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyD S T) σ0

/-- One diffing reconcile pass plus its coalesced processor emission: a single row at
    the derived key (all the pass's per-flip rows — adds AND removes — share that
    object end; the R-node is terminal on the fragment). -/
def W3cJob.applyLogged (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    GraphState :=
  (j.applyD S T σ).pushDelta (objNode ⟨j.dt, j.on⟩ j.R) j.R

/-- Run a batch of logged reconcile jobs left-to-right
    (`index_v4/processor.py::DeltaProcessor._run_cascade`'s per-round
    key loop; one-stratum, so ordering is irrelevant — operand reads are
    pass-inert). -/
def reconcileJobsL (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyLogged S T) σ

/-- A logged job batch's core is the unlogged `reconcileJobsD` batch — all per-pass
    facts about the diffing batch transfer. -/
theorem reconcileJobsL_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (S : Schema)
    (T : Store) (jobs : List W3cJob) :
    EvalEq (reconcileJobsL S T σ' jobs) (reconcileJobsD S T σ jobs) := by
  unfold reconcileJobsL reconcileJobsD
  induction jobs generalizing σ' σ with
  | nil => exact h
  | cons j rest ih =>
    simp only [List.foldl_cons]
    refine ih ?_
    have happ : EvalEq (j.applyD S T σ') (j.applyD S T σ) :=
      reconcileStarsKeyD_evalEq h T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands
    exact ⟨happ.schema, happ.edges, happ.nodes, happ.residue⟩

/-! ### Outbox/watermark bookkeeping of the logged batch -/

/-- One unlogged diffing pass never touches the outbox. -/
theorem W3cJob.applyD_outbox (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).outbox = σ.outbox := by
  unfold W3cJob.applyD GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_outbox, reconcileResidueKey_outbox]

/-- One unlogged diffing pass never touches the watermark. -/
theorem W3cJob.applyD_watermark (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).watermark = σ.watermark := by
  unfold W3cJob.applyD GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_watermark, reconcileResidueKey_watermark]

/-- One unlogged diffing pass keeps the fresh-id source fixed. -/
theorem W3cJob.applyD_nextDeltaId (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).nextDeltaId = σ.nextDeltaId := by
  unfold GraphState.nextDeltaId GraphState.maxOutboxId
  rw [W3cJob.applyD_outbox, W3cJob.applyD_watermark]

/-- The logged batch leaves the watermark untouched (the drain advance is
    `runCascade`'s final act, not the passes'). -/
theorem reconcileJobsL_watermark (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (reconcileJobsL S T σ jobs).watermark = σ.watermark := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    have hfold : reconcileJobsL S T σ (j :: rest)
        = reconcileJobsL S T (j.applyLogged S T σ) rest := by
      unfold reconcileJobsL
      rw [List.foldl_cons]
    rw [hfold, ih]
    unfold W3cJob.applyLogged
    rw [pushDelta_watermark, W3cJob.applyD_watermark]

/-- **Outbox soundness of the logged batch**: every row is an original row or a
    pass-emitted row — at some job's derived key, with an id strictly above the
    pre-batch frontier `max maxOutboxId watermark`. -/
theorem reconcileJobsL_outbox_sound (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ d ∈ (reconcileJobsL S T σ jobs).outbox,
      d ∈ σ.outbox ∨
      ((∃ j ∈ jobs, d.node = objNode ⟨j.dt, j.on⟩ j.R ∧ d.relation = j.R ∧ d.leaf = false) ∧
        max σ.maxOutboxId σ.watermark < d.id) := by
  intro jobs
  induction jobs with
  | nil => intro σ d hd; exact Or.inl hd
  | cons j rest ih =>
    intro σ d hd
    have hfold : reconcileJobsL S T σ (j :: rest)
        = reconcileJobsL S T (j.applyLogged S T σ) rest := by
      unfold reconcileJobsL
      rw [List.foldl_cons]
    rw [hfold] at hd
    have hout1 : (j.applyLogged S T σ).outbox
        = ⟨σ.nextDeltaId, objNode ⟨j.dt, j.on⟩ j.R, j.R, false⟩ :: σ.outbox := by
      unfold W3cJob.applyLogged
      rw [pushDelta_outbox, W3cJob.applyD_outbox]
      have := W3cJob.applyD_nextDeltaId S T σ j
      rw [this]
    have hwm1 : (j.applyLogged S T σ).watermark = σ.watermark := by
      unfold W3cJob.applyLogged
      rw [pushDelta_watermark, W3cJob.applyD_watermark]
    have hmax1 : (j.applyLogged S T σ).maxOutboxId = σ.nextDeltaId := by
      unfold W3cJob.applyLogged
      rw [pushDelta_maxOutboxId, W3cJob.applyD_nextDeltaId]
    rcases ih (j.applyLogged S T σ) d hd with hin | ⟨⟨j', hj', hn, hr, hl⟩, hgt⟩
    · rw [hout1] at hin
      rcases List.mem_cons.mp hin with rfl | hmem
      · refine Or.inr ⟨⟨j, List.mem_cons_self, rfl, rfl, rfl⟩, ?_⟩
        show max σ.maxOutboxId σ.watermark < σ.nextDeltaId
        have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
        omega
      · exact Or.inl hmem
    · refine Or.inr ⟨⟨j', List.mem_cons_of_mem _ hj', hn, hr, hl⟩, ?_⟩
      rw [hmax1, hwm1] at hgt
      have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
      omega

/-! ## The drain loop (decision 5) -/

/-- **`runCascade`** (`index_v4/processor.py::DeltaProcessor._run_cascade`, at
    one stratum): reconcile
    the batch, then Python's final quiescence check — the rows above the round
    frontier must map to NO keys, else `InvariantViolation` aborts the transaction.
    The abort is modeled as the reject branch (state unchanged); on accept the
    watermark advances past everything, which the next transaction's frontier read
    (`connectedstore/apply.py::advance_index` re-reads
    `index_v4/outbox.py::outbox_watermark`) makes faithful. -/
def runCascade (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  if ((reconcileJobsL S T σ jobs).outbox.filter
        (fun d => max σ.maxOutboxId σ.watermark < d.id)).all
      (fun d => (affectedKeys S (reconcileJobsL S T σ jobs) d).isEmpty)
  then { reconcileJobsL S T σ jobs with watermark := (reconcileJobsL S T σ jobs).maxOutboxId }
  else σ

/-- A cascade run either accepts (the drained logged batch) or rejects (identity).

    (Lives here since `P6` step 3b, 2026-09-13g; it was `CascadeStable.lean`'s. Pure
    relocation — name, statement and proof unchanged. `Cascade.lean` needs it and imports
    that file's consumers, not the other way round: `reachedByW3d_schema` below is the
    theorem `Cascade` needs and its cascade case case-splits on this.) -/
theorem runCascade_cases (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    runCascade S T σ jobs
        = { reconcileJobsL S T σ jobs with
            watermark := (reconcileJobsL S T σ jobs).maxOutboxId }
      ∨ runCascade S T σ jobs = σ := by
  unfold runCascade
  split
  · exact Or.inl rfl
  · exact Or.inr rfl

/-! ## Schema preservation along a chain

Relocated here by `P6` step 3b (2026-09-13g) from `CascadeSettle.lean`, unchanged in
statement and proof. `Cascade.lean` needs `σ.schema = S` itself — the `P6` R-node
restatement has to turn a claim about `σ.schema`, which is what
`UsStarWrite.lean::GraphState.bridgedInConcrete` reads, into one about `S` — and
`Cascade.lean` imports `CascadeSettle`'s consumers, not the other way round. -/

/-- The `writeDirect` fold keeps the baked-in schema. -/
theorem foldl_writeDirect_schema (us : List Tuple) :
    ∀ (σ : GraphState), (us.foldl (fun acc u => acc.writeDirect u) σ).schema = σ.schema := by
  induction us with
  | nil => intro σ; rfl
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih, writeDirect_schema]

/-- The diffing batch keeps the baked-in schema. -/
theorem reconcileJobsD_schema {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState), (reconcileJobsD S T σ jobs).schema = σ.schema := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold, ih]
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    rw [reconcileKeyD_schema, reconcileResidueKey_schema]

/-! ## The W3d closure — interleaved logged writes and cascades -/

/-! ## ★ `FoldAdmitsBridged` — the honest fold-admission predicate (`P6` step 14, additive half)

**The obligation.** Once step 3 re-points `LeafRules.lean::GraphState.writeRulesRaw` (and with
it `GraphState.writeLoggedRules`) to fold `GraphState.writeBridgedOne`, the `write`
constructors of `ReachedByW3d` (`:1536`) and `ReachedByW3d2` keep a hypothesis
`FoldAdmits σ (rewriteClosureL S (rawWriteTuples S t))` (`RulesComplete.lean::FoldAdmits`)
that probes `GraphState.writeDirect`'s UNBRIDGED state — while the fold actually taken probes
`(σ.bridgePre u).admitEdge`. `GraphState.admitEdge` is ANTI-monotone in edges and
`GraphState.bridgePre` only ADDS edges, so the stale hypothesis is strictly WEAKER than the
truth: every `hadm` binder keeps type-checking while describing a fold nobody runs. That is
this repo's named house failure mode — an assurance step that fails by PASSING
(`docs/sabotage-procedure.md`).

**What lands here, and what does not.** The predicate, its decidable twin, its `Bool` mirror
and the EVIDENCE that the two predicates differ. The MOVE — re-pointing the 19 `hadm`
signature binders enumerated in `docs/p6-step3b-plan-2026-09-13.md` § Step 14 — is RED work
and is deliberately not started; nothing below is referenced by any existing declaration, so
this section is purely additive and lands green ahead of the re-point (the additive-first
test of that plan's `C9`).

⚠ **`FoldAdmits` lives in `RulesComplete.lean`, which is upstream of this file and is NOT
imported by `UsStarWrite.lean`.** So the honest twin cannot live beside
`GraphState.writeBridgedOne`; `Cascade.lean` is the first module that sees both. Do not
"tidy" it up next to its subject — the import direction `Cascade → UsStarWrite` must never be
reversed. -/

/-- **`FoldAdmitsBridged σ us`** — folding `GraphState.writeBridgedOne` over `us` from `σ`
    admits every write. The honest twin of `RulesComplete.lean::FoldAdmits`, differing from
    it in exactly one place: the probe reads the BRIDGED pre-state `σ.bridgePre u`, which is
    the state `GraphState.writeBridgedOne` itself probes, and the tail continues at
    `σ.writeBridgedOne u` rather than `σ.writeDirect u`.

    Shape-for-shape a mirror of `FoldAdmits`, so a consumer that `rcases`es one can `rcases`
    the other, and `foldAdmitsBridgedB` below stands to it exactly as
    `Exec.lean::foldAdmitsB` stands to `FoldAdmits`. -/
def FoldAdmitsBridged : GraphState → List Tuple → Prop
  | _, [] => True
  | σ, u :: rest =>
      (σ.bridgePre u).admitEdge (subjNode u.subject) (objNode u.object u.relation) = true ∧
      FoldAdmitsBridged (σ.writeBridgedOne u) rest

/-- `FoldAdmitsBridged` is a finite conjunction of `admitEdge` Bool tests, hence decidable at
    a concrete state and list — the mirror of `RulesComplete.lean::decFoldAdmits`, supplied
    for the same reason (a plain recursive `def` is not unfolded by instance synthesis). It
    is what the `by decide` pins below run on. -/
def decFoldAdmitsBridged :
    (σ : GraphState) → (us : List Tuple) → Decidable (FoldAdmitsBridged σ us)
  | _, [] => isTrue trivial
  | σ, u :: rest =>
      if h : (σ.bridgePre u).admitEdge (subjNode u.subject)
          (objNode u.object u.relation) = true then
        match decFoldAdmitsBridged (σ.writeBridgedOne u) rest with
        | isTrue ht => isTrue ⟨h, ht⟩
        | isFalse hf => isFalse (fun hc => hf hc.2)
      else isFalse (fun hc => h hc.1)

instance instDecidableFoldAdmitsBridged (σ : GraphState) (us : List Tuple) :
    Decidable (FoldAdmitsBridged σ us) := decFoldAdmitsBridged σ us

/-- Executable mirror of `FoldAdmitsBridged`, verbatim the shape of
    `Exec.lean::foldAdmitsB`. It is deliberately NOT placed in `Exec.lean` beside that one:
    `Exec` is DOWNSTREAM of this file (`docs/p6-step3b-plan-2026-09-13.md` § Corrections'
    19-module downstream set), and the runtime driver cannot gate on the bridged fold until
    the leg it drives is re-pointed. When step 3 lands, `Exec.lean::graphRunAux` (`:82`) and
    `::graphRunOpsAux` (`:454`) are the two runtime gates that must move to this. -/
def foldAdmitsBridgedB : GraphState → List Tuple → Bool
  | _, [] => true
  | σ, u :: rest =>
      (σ.bridgePre u).admitEdge (subjNode u.subject) (objNode u.object u.relation)
      && foldAdmitsBridgedB (σ.writeBridgedOne u) rest

/-- The mirror is exact: `foldAdmitsBridgedB` decides `FoldAdmitsBridged`. Same proof as
    `Exec.lean::foldAdmitsB_iff`. -/
theorem foldAdmitsBridgedB_iff (us : List Tuple) :
    ∀ σ : GraphState, foldAdmitsBridgedB σ us = true ↔ FoldAdmitsBridged σ us := by
  induction us with
  | nil => intro σ; simp [foldAdmitsBridgedB, FoldAdmitsBridged]
  | cons u rest ih =>
    intro σ
    simp [foldAdmitsBridgedB, FoldAdmitsBridged, Bool.and_eq_true, ih]

/-- ★★ **THE BRIDGED FOLD'S EDGE-COMPLETENESS — and it can only be stated over
    `FoldAdmitsBridged`.** Every member of an admitted bridged fold contributes its grant
    edge to the final state.

    ⚠ **This is the theorem that turns step 14 from an honesty obligation into a
    CORRECTNESS one.** The obvious move — restate `RulesComplete.lean::
    foldl_writeDirect_edge_complete` with `writeDirect` swapped for `writeBridgedOne` and
    the `FoldAdmits` binder left alone — is **FALSE**, kernel-refuted in this file at
    `FoldAdmitsHonestyWitness.foldl_edge_complete_is_false_for_the_bridged_fold`. The reason
    is not incidental: `GraphState.admitEdge` is anti-monotone in edges and
    `GraphState.bridgePre` only ADDS edges, so a stale `FoldAdmits` hypothesis is strictly
    WEAKER than the fold's real precondition — it keeps type-checking while describing a
    fold nobody runs, and at a cycle through a fresh bridge it is satisfied where the actual
    write is refused. So there is no version of this lemma that lets a caller hold the old
    binder.

    Landed here rather than in `UsStarWrite.lean` for the recorded import reason:
    `FoldAdmitsBridged` needs `RulesComplete`, which imports `UsStarWrite`, so `Cascade` is
    the first module that sees both. The proof is character-for-character
    `foldl_writeDirect_edge_complete`'s with the bridged twins substituted — the difficulty
    was never the proof, it was the binder. -/
theorem foldl_writeBridgedOne_edge_complete (us : List Tuple) :
    ∀ {σ : GraphState}, FoldAdmitsBridged σ us →
      ∀ u ∈ us, (subjNode u.subject, objNode u.object u.relation) ∈
        (us.foldl (fun acc u => acc.writeBridgedOne u) σ).edges := by
  induction us with
  | nil => intro σ _ u hu; simp at hu
  | cons t rest ih =>
    intro σ hfa u hu
    obtain ⟨hadm, hrest⟩ := hfa
    rcases List.mem_cons.mp hu with rfl | hmem
    · have hstep : (subjNode u.subject, objNode u.object u.relation)
          ∈ (σ.writeBridgedOne u).edges := by
        unfold GraphState.writeBridgedOne
        rw [if_pos hadm, addEdge_edges]
        exact List.mem_cons_self
      exact foldl_writeBridgedOne_edges_mono rest _ hstep
    · exact ih hrest u hmem

/-- **`ReachedByW3d σ S T`** — the interleaved scheduler closure: admitted logged
    rule-routed writes and cascade runs, in ANY order (Python: each write
    transaction runs its own in-transaction cascade; `build_index` batches many
    writes before one backfill). The jobs of a cascade leg must cover exactly the
    frontier's affected keys (`_map_deltas_to_keys` + the per-key reconcile loop):
    every cascade key has a job, every job settles a cascade key. -/
inductive ReachedByW3d : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3d (emptyState S) S []
  /-- ★★ **`hadm` MOVED to `FoldAdmitsBridged` by `P6` step 3b step 14 (2026-09-14).** It was
      `FoldAdmits σ (rewriteClosureL S (rawWriteTuples S t))` — a predicate about the
      `writeDirect` fold, i.e. about a fold this constructor's own conclusion no longer runs.
      That was not merely dishonest: `FoldAdmitsBridged` is STRICTLY STRONGER (`admitEdge` is
      anti-monotone in edges, `bridgePre` only adds edges), so keeping the old binder
      entitled every downstream write-leg argument to a FALSE conclusion — kernel-refuted at
      `FoldAdmitsHonestyWitness.foldl_edge_complete_is_false_for_the_bridged_fold`. -/
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
      (hprev : ReachedByW3d σ S T) :
      ReachedByW3d (σ.writeLoggedRules S t) S (t :: T)
  | cascade {σ : GraphState} {S : Schema} {T : Store} (jobs : List W3cJob)
      (hjv : ∀ j ∈ jobs, W3cJobValid S j)
      (hcover : ∀ k ∈ cascadeKeys S σ, ∃ j ∈ jobs, j.key = k)
      (hscope : ∀ j ∈ jobs, j.key ∈ cascadeKeys S σ)
      (hprev : ReachedByW3d σ S T) :
      ReachedByW3d (runCascade S T σ jobs) S T

/-- **Every W3d state carries its own schema** — the read's `isDerived` routing reads
    the right `S`.

    (Lives here since `P6` step 3b, 2026-09-13g; it was `CascadeSettle.lean`'s — pure
    relocation, name/statement/proof unchanged, and the name is audited
    (`formal/audited_theorems.txt`) so it had to stay exactly that. `Cascade.lean` needs it
    and imports that file's consumers, not the other way round: the `P6` R-node
    restatement must convert `σ.schema.isSubjectWildcardUserset …` into a claim about `S`,
    because bridging is keyed on the STATE's schema.) -/
theorem reachedByW3d_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) : σ.schema = S := by
  induction h with
  | empty S => rfl
  | @write σp S T t hadm hprev ih =>
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).schema]
    -- `P6` step 3b (2026-09-14): the unlogged twin now folds `writeBridgedOne`, so the
    -- discharger is `UsStarWrite.lean::schema_foldl_writeBridgedOne`, not
    -- `foldl_writeDirect_schema`. Statement unchanged; this is the whole repair.
    show ((rewriteClosureL S (rawWriteTuples S t)).foldl
      (fun acc u => acc.writeBridgedOne u) σp).schema = S
    rw [schema_foldl_writeBridgedOne]
    exact ih
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc]
      show (reconcileJobsL S T σp jobs).schema = S
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).schema, reconcileJobsD_schema]
      exact ih
    · rw [hrc]
      exact ih

/-! ## Edge soundness and R-node terminality over the interleaved closure -/

/-- Every edge of an unlogged diffing batch is an old edge or a candidate's derived
    edge onto the job's own R-node (removal only shrinks; NB old edges need NOT
    survive — the stale-edge retraction). -/
theorem reconcileJobsD_edge_sound {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (reconcileJobsD S T σ jobs).edges →
      (a, b) ∈ σ.edges ∨
        ∃ j ∈ jobs, ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
  intro jobs
  induction jobs with
  | nil => intro σ a b h; exact Or.inl h
  | cons j rest ih =>
    intro σ a b h
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold] at h
    rcases ih _ a b h with hin | ⟨j', hj', c, hc, h1, h2⟩
    · unfold W3cJob.applyD at hin
      rcases reconcileStarsKeyD_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ a b hin with hold | ⟨c, hc, h1, h2⟩
      · exact Or.inl hold
      · exact Or.inr ⟨j, List.mem_cons_self, c, hc, h1, h2⟩
    · exact Or.inr ⟨j', List.mem_cons_of_mem _ hj', c, hc, h1, h2⟩

/-- **No W3d edge sourced at a node of the derived SHAPE `(dt, R)`** (the interleaved analog
    of `reachedByW3a_edge_source_ne_R`): a logged write's routed edge sources are rewrite-
    closure subjects (predicate ≠ `R` by `NoTtuTarget` + `NoStoreSubjectR`), a
    cascade's edge sources are bare candidates (`BARE ≠ R`), and a write's BRIDGE edge
    sources are of a bridged-in shape, which `NoBridgedDerived` forbids at a derived key.
    The store hypothesis is taken at the chain's own store and weakens along the prefix.

    ★★ **RESTATED by `P6` step 3b (2026-09-14), and the restatement is FORCED.** Until the
    re-point the conclusion was the shape-free `∀ a b, (a, b) ∈ σ.edges → a.pred ≠ R`. That
    is **FALSE** once the write leg bridges, and false for a reason that no premise about
    `R` alone can repair: a bridge edge is sourced at its CONCRETE endpoint, and
    `Schema.isSubjectWildcardUserset` is keyed on `(type, relation)`, so a literal
    `[x:*#R]` restriction at an UNTAINTED key `(x, R)` is legal Python and bridges a node
    whose `pred` IS `R`. Two changes answer it, and they are different in kind:
      * the CONCLUSION gains `a.type = dt`, making the claim shape-level rather than
        predicate-level — this is `TK68`'s type-index trap, and dropping the type is what
        makes the old reading false;
      * the HYPOTHESES gain `(hNBD : NoBridgedDerived S)`, which is exactly "no derived key
        is bridged in" and is precisely what kills the new third disjunct.

    ⚠ **`NoBridgedDerived S` mentions no `Store`, and that is why it was chosen.** It rides
    through a `write` leg (`t :: T`) or a `remove` leg (`T.erase t`) VERBATIM, with no
    weakening lambda anywhere — unlike the store-indexed `W4Fragment.term`, which is spelled
    out at 134 declarations and needs a two-line store-weakening lambda at 22 of them. Do
    NOT answer a later obligation by widening `term` instead; put the carry immediately
    after `hRne` at every threading site so the argument position stays uniform. -/
theorem reachedByW3d_edge_source_ne_R {σ : GraphState} {S : Schema} {T : Store}
    {dt R : String} (hRne : R ≠ BARE) (hNBD : NoBridgedDerived S)
    (h : ReachedByW3d σ S T) :
    isDerived S (dt, R) = true → NoTtuTarget S R → NoStoreSubjectR T R →
      ∀ a b, (a, b) ∈ σ.edges → a.type = dt → a.pred ≠ R := by
  induction h with
  | empty S =>
    intro _ _ _ a b hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hder hnt hns a b hab hty
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    unfold GraphState.writeRulesRaw at hab
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hab
      with hin | ⟨u, hu, h1, _⟩ | ⟨hsw, _⟩
    · exact ih hNBD hder hnt (fun t' ht' => hns t' (List.mem_cons_of_mem _ ht')) a b hin hty
    · rw [h1, subjNode_pred]
      exact rewriteClosureL_subject_pred_ne_of_noTtuTarget hnt hder
        (hns t List.mem_cons_self) hu
    · -- THE NEW DISJUNCT: `a` is a bridged-in concrete, so its SHAPE is a declared
      -- subject-wildcard userset shape. Under `a.type = dt` and `a.pred = R` that shape is
      -- `(dt, R)`, which `hNBD` un-bridges at every derived key. The conversion from the
      -- state's schema to `S` is `reachedByW3d_schema` — the reason step 4 had to relocate
      -- it up into this file.
      intro hpr
      have hshape := (bridgedInConcrete_elim hsw).2.2.2
      rw [reachedByW3d_schema hprev, hty, hpr] at hshape
      rw [hNBD dt R hder] at hshape
      exact Bool.noConfusion hshape
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hder hnt hns a b hab hty
    unfold runCascade at hab
    split at hab
    · have hab' : (a, b) ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hab'
      rcases reconcileJobsD_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, hc, h1, _⟩
      · exact ih hNBD hder hnt hns a b hold hty
      · rw [h1, subjNode_pred]
        obtain ⟨_, hcb, _⟩ := hjv j hj
        rw [hcb c hc]
        exact Ne.symm hRne
    · exact ih hNBD hder hnt hns a b hab hty

/-- **The derived R-node is never an edge source on a W3d state.**

    ★ **STATEMENT UNCHANGED by `P6` step 3b — it gains a HYPOTHESIS only** (2026-09-14),
    and that is the material correction to the `P6` row's forecast: this theorem does NOT
    go false, so 10 of the restatement's 12 application sites consume an unchanged
    conclusion. **Why it survives**: its node is `objNode ⟨dt, on⟩ R`, whose `.type` is
    `dt` (`State.lean::objNode_type`) and whose `.pred` is `R` (`::objNode_pred`) — i.e.
    exactly the key `hder` says is derived, which is exactly the key `NoBridgedDerived`
    un-bridges. The type-index escape hatch that forced the restatement above cannot reach
    a node whose type is pinned to `dt`, so the new `a.type = dt` premise is discharged
    here by `objNode_type` and nothing else moves. -/
theorem reachedByW3d_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hNBD : NoBridgedDerived S) (hder : isDerived S (dt, R) = true)
    (h : ReachedByW3d σ S T) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges := by
  obtain ⟨hnt, hns⟩ := hterm dt R hder
  intro y hy
  exact reachedByW3d_edge_source_ne_R hRne hNBD h hder hnt hns _ y hy
    (objNode_type ⟨dt, on⟩ R) (objNode_pred ⟨dt, on⟩ R)

/-- R-node terminality survives the batch itself (the mid-cascade state the leftover
    check reads): a batch edge's source is a bare candidate, never an R-node.

    ★ `P6` step 3b (2026-09-14): statement unchanged, gains and FORWARDS the
    `NoBridgedDerived` carry. Its own cascade-edge arm is untouched — a reconcile batch adds
    no bridges. (Not on the `P6` row's fallout list; it is a consumer of the restatement
    above, which is how it joined.) -/
theorem reconcileJobsL_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {jobs : List W3cJob} {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hNBD : NoBridgedDerived S) (hder : isDerived S (dt, R) = true)
    (h : ReachedByW3d σ S T) (hjv : ∀ j ∈ jobs, W3cJobValid S j) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (reconcileJobsL S T σ jobs).edges := by
  intro y hy
  rw [(reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs).edges] at hy
  rcases reconcileJobsD_edge_sound jobs σ _ y hy with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact reachedByW3d_Rnode_not_source hterm hRne hNBD hder h y hold
  · obtain ⟨_, hcb, _⟩ := hjv j hj
    have hpred : (objNode ⟨dt, on⟩ R).pred = BARE := by
      rw [h1, subjNode_pred, hcb c hc]
    rw [objNode_pred] at hpred
    exact hRne hpred

/-! ## T5 — the reject branch never fires; the drain is justified -/

/-- **`runCascade_no_abort` (T5 half a).** On the fragment the leftover check always
    passes: every row above the round frontier is a pass-emitted row at a derived
    R-node, whose reach cone is empty (terminality) and whose own predicate is
    derived — hence not a computed operand of any derived def (`hLU`) — so it maps
    to no keys. Python's leftover `raise InvariantViolation` (the tail of
    `index_v4/processor.py::DeltaProcessor._run_cascade`) is dead code
    at one stratum. -/
theorem runCascade_no_abort {σ : GraphState} {S : Schema} {T : Store}
    {jobs : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hNBD : NoBridgedDerived S)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) (h : ReachedByW3d σ S T) :
    runCascade S T σ jobs
      = { reconcileJobsL S T σ jobs with
          watermark := (reconcileJobsL S T σ jobs).maxOutboxId } := by
  unfold runCascade
  refine if_pos ?_
  rw [List.all_eq_true]
  intro d hd
  obtain ⟨hdmem, hdgt⟩ := List.mem_filter.mp hd
  have hdgt' : max σ.maxOutboxId σ.watermark < d.id := of_decide_eq_true hdgt
  rcases reconcileJobsL_outbox_sound S T jobs σ d hdmem
    with hold | ⟨⟨j, hj, hnode, hrel, hleaf⟩, _⟩
  · -- an original row sits at or below the frontier — it cannot be in the filter
    exfalso
    have := mem_outbox_le_maxOutboxId σ d hold
    omega
  · -- a pass-emitted row: maps to no keys
    obtain ⟨hRne, _hcb, _hcS, _hnS, _huP, _huS, hder, _hlke, hon⟩ := hjv j hj
    -- the reach cone of the R-node is empty
    have hRns := reconcileJobsL_Rnode_not_source (on := j.on) hterm hRne hNBD hder h hjv
    have hreach : ∀ v, (reconcileJobsL S T σ jobs).reach d.node v = false := by
      intro v
      by_contra hne
      have htrue : (reconcileJobsL S T σ jobs).reach d.node v = true := by
        revert hne
        cases (reconcileJobsL S T σ jobs).reach d.node v <;> simp
      obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound htrue)
      rw [hnode] at hy
      exact hRns y hy
    have hobj : (reconcileJobsL S T σ jobs).affectedObjects d = [d.node] := by
      unfold GraphState.affectedObjects
      rw [List.filter_eq_nil_iff.mpr (fun v _ => by rw [hreach v]; exact Bool.false_ne_true)]
    -- the single candidate object is the derived R-node: no derived def reads a
    -- derived predicate as a computed operand (`hLU`), so no key is emitted
    have htype : d.node.type = j.dt := by rw [hnode, objNode_type]
    have hpred : d.node.pred = j.R := by rw [hnode, objNode_pred]
    have hkeys : affectedKeys S (reconcileJobsL S T σ jobs) d = [] := by
      unfold affectedKeys
      rw [hobj]
      -- **(alpha)**: the own-key guard lost its `isDerived` conjunct; `d.leaf = false`
      -- still kills it, which is the quiescence fence.
      have hleaf_ne : ¬(d.leaf = true ∧ d.node.name ≠ STAR) := by rw [hleaf]; simp
      rw [if_neg hleaf_ne, List.nil_append]
      simp only [List.flatMap_cons, List.flatMap_nil, List.append_nil]
      by_cases hst : d.node.name = STAR
      · rw [if_pos hst]
      · rw [if_neg hst]
        rw [List.filterMap_eq_nil_iff]
        intro k hk
        have hcond : ¬(k.1 = d.node.type ∧ isDerived S k = true ∧
            ((S.lookup k).map
              (fun e => (computedRefs e).contains d.node.pred)).getD false = true) := by
          rintro ⟨hk1, hkder, hkref⟩
          cases hlk : S.lookup k with
          | none => rw [hlk] at hkref; simp at hkref
          | some e =>
            rw [hlk] at hkref
            simp only [Option.map_some, Option.getD_some] at hkref
            have hmem : d.node.pred ∈ computedRefs e := by
              rw [List.contains_eq_mem] at hkref
              exact of_decide_eq_true hkref
            have hfalse := hLU k.1 k.2 e hlk hkder _ hmem
            rw [hk1, htype, hpred] at hfalse
            cases hder.symm.trans hfalse
        rw [if_neg hcond]
    rw [hkeys]
    rfl

/-- **`cascade_drains` (T5 half b).** After a cascade run on the fragment the state
    is `Quiescent` — every outbox row sits at or below the advanced watermark.
    Contentful: a non-empty pre-cascade frontier (un-drained user-write rows) IS
    drained, and the watermark advance is JUSTIFIED by `runCascade_no_abort` (the
    skipped rows provably map to no keys), never asserted — the fix for the old
    vacuous `cascade_converges` shape. -/
theorem cascade_drains {σ : GraphState} {S : Schema} {T : Store} {jobs : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hNBD : NoBridgedDerived S)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) (h : ReachedByW3d σ S T) :
    Quiescent (runCascade S T σ jobs) := by
  rw [runCascade_no_abort hterm hNBD hLU hjv h]
  intro d hd
  exact mem_outbox_le_maxOutboxId _ d hd

/-! ### ★ The two predicates PROVABLY disagree — the evidence step 14 exists for

Without this namespace the section above is a definition nobody calls, and "the stale `hadm`
is weaker" stays a claim in a docstring. The positive control it lifts already existed at the
PROBE level — `UsStarWrite.lean::BridgedWriteWitness.bridged_probe_refuses_the_cycle`
(`= false`) against `::unbridged_probe_admits_the_cycle` (`= true`), both by `decide`. What
is new here is the same fact at the PREDICATE level, and then at the **argument shape `hadm`
actually binds**, `rewriteClosureL S (rawWriteTuples S t)`.

The fixture is `UsStarWrite.lean::BridgedWriteWitness`'s, unchanged, so step 2's, step 3a's
and this session's pins all read as ONE scenario: `ThroughShapeWitness.Sthru`, and the
wildcard-userset grant `tCycle = folder:*#viewer viewer folder:f1`, whose own subject-side
bridge `folder:f1#viewer → w_any(folder, viewer)` closes a cycle with the grant.

⚠ **Honest limit, measured not assumed.** `cycle_closure_is_the_member` reports that the
closure list here is the SINGLETON seed — `Sthru`'s only rewrite rule is `doc#viewer ←
viewer from parent`, which matches relation `parent`, and `tCycle`'s relation is `viewer`, so
nothing fires. So these pins exhibit the disagreement at the right argument SHAPE, not inside
a multi-member fold. A multi-member divergence is not needed for the honesty obligation (one
member already makes the hypothesis describe the wrong fold) and is not claimed. -/
namespace FoldAdmitsHonestyWitness

/-- The step-3a / step-2 scenario, unchanged. -/
def base : GraphState := BridgedWriteWitness.base

/-- **The closure list, measured.** `rawWriteTuples` is the identity on this untainted key
    and no rewrite of `Sthru` matches relation `viewer`, so the list `hadm` quantifies over is
    the seed alone. Stated rather than assumed, because every pin below that is phrased at the
    closure is derived THROUGH this equation. -/
theorem cycle_closure_is_the_member :
    rewriteClosureL ThroughShapeWitness.Sthru
        (rawWriteTuples ThroughShapeWitness.Sthru BridgedWriteWitness.tCycle)
      = [BridgedWriteWitness.tCycle] := by decide

/-- The same measurement at the ADMITTED fixture, which the post-step-14 constructor pin
    (`w3d_write_applies_with_the_bridged_hypothesis`) is phrased through. Same reason: the
    pin is derived at the closure the constructor quantifies over, never at a hand-written
    list that happens to look like it. -/
theorem thru_closure_is_the_member :
    rewriteClosureL ThroughShapeWitness.Sthru
        (rawWriteTuples ThroughShapeWitness.Sthru BridgedWriteWitness.tThru)
      = [BridgedWriteWitness.tThru] := by decide

/-- **The stale predicate ADMITS the fold** — `RulesComplete.lean::FoldAdmits` probes the
    unbridged state, which does not yet hold the bridge the cycle runs through. -/
theorem unbridged_fold_admits :
    FoldAdmits base [BridgedWriteWitness.tCycle] := by decide

/-- …and the executable mirror of the honest predicate REFUSES it. -/
theorem bridgedB_refuses : foldAdmitsBridgedB base [BridgedWriteWitness.tCycle] = false := by
  decide

/-- ★ **The honest predicate refuses the same fold.** Derived THROUGH
    `foldAdmitsBridgedB_iff` rather than `decide`d directly, so it certifies that the `Bool`
    mirror and the `Prop` agree on a fixture where the answer is `false` — the direction a
    mirror that had drifted would be caught in. -/
theorem bridged_fold_refuses : ¬ FoldAdmitsBridged base [BridgedWriteWitness.tCycle] := by
  intro h
  have hb := (foldAdmitsBridgedB_iff _ _).mpr h
  rw [bridgedB_refuses] at hb
  exact Bool.noConfusion hb

/-- ★ **THE PIN: the two predicates disagree at the argument shape `hadm` binds.**
    `ReachedByW3d.write`'s hypothesis is `FoldAdmits σ (rewriteClosureL S (rawWriteTuples S
    t))`; this is that exact expression, true of `FoldAdmits` and FALSE of
    `FoldAdmitsBridged`. So re-pointing the binders is a REAL change of hypothesis and not a
    definitional unfolding — which is the thing a reader deferring step 14 has to know. -/
theorem disagree_at_a_closure_list :
    FoldAdmits base (rewriteClosureL ThroughShapeWitness.Sthru
        (rawWriteTuples ThroughShapeWitness.Sthru BridgedWriteWitness.tCycle)) ∧
      ¬ FoldAdmitsBridged base (rewriteClosureL ThroughShapeWitness.Sthru
        (rawWriteTuples ThroughShapeWitness.Sthru BridgedWriteWitness.tCycle)) := by
  rw [cycle_closure_is_the_member]
  exact ⟨unbridged_fold_admits, bridged_fold_refuses⟩

/-- ★ **ATTRIBUTION CONTROL 1**: at a member with NO bridged-in endpoint the two predicates
    agree. Without it, `disagree_at_a_closure_list` would be satisfied by a
    `FoldAdmitsBridged` that differs from `FoldAdmits` everywhere, which would say nothing
    about the bridge. Mirrors `UsStarWrite.lean::BridgedWriteWitness.
    control_agrees_with_writeDirect`. -/
theorem control_unbridged_member_agrees :
    FoldAdmits base [BridgedWriteWitness.tCtrl] ∧
      FoldAdmitsBridged base [BridgedWriteWitness.tCtrl] := by decide

/-- ★ **ATTRIBUTION CONTROL 2, the sharper one**: at `tThru` the subject IS bridged in
    (`::subject_is_bridged_in`) and the two predicates STILL agree. So the divergence is not
    "the bridge fires", it is specifically the cycle the bridge closes — which is why the
    honest predicate is needed rather than a side condition saying "no endpoint is
    bridged". -/
theorem control_bridged_grant_agrees :
    FoldAdmits base [BridgedWriteWitness.tThru] ∧
      FoldAdmitsBridged base [BridgedWriteWitness.tThru] := by decide

/-- The unbridged fold materialises `tCycle`'s grant… -/
theorem unbridged_fold_lands_the_grant :
    (subjNode BridgedWriteWitness.tCycle.subject,
      objNode BridgedWriteWitness.tCycle.object BridgedWriteWitness.tCycle.relation) ∈
      ([BridgedWriteWitness.tCycle].foldl (fun acc u => acc.writeDirect u) base).edges := by
  decide

/-- …and the bridged fold — the one step 3 makes live — does NOT. This pair is the
    CONSEQUENCE of the hypothesis mismatch: it is not a matter of which state a probe reads,
    it is the difference between an edge existing and not existing. -/
theorem bridged_fold_drops_the_grant :
    (subjNode BridgedWriteWitness.tCycle.subject,
      objNode BridgedWriteWitness.tCycle.object BridgedWriteWitness.tCycle.relation) ∉
      ([BridgedWriteWitness.tCycle].foldl (fun acc u => acc.writeBridgedOne u) base).edges := by
  decide

/-- ★★ **THE REFUTATION — why step 14 is an honesty obligation and not a tidy-up.**
    `RulesComplete.lean::foldl_writeDirect_edge_complete` is the workhorse every
    edge-completeness argument on the write leg runs through: *`FoldAdmits` ⇒ every member's
    edge is in the folded state.* Stated over the BRIDGED fold with `FoldAdmits` still as its
    hypothesis — i.e. exactly what a session that re-points the fold and leaves the binders
    alone would be entitled to assume — it is FALSE, and this refutes it on one member.

    The weakening refuted is the narrowest plausible one: it is character-for-character the
    existing lemma with `writeDirect` swapped for `writeBridgedOne` in the fold, which is what
    the re-point does to the code while leaving the hypothesis untouched. Mirrors
    `UsStarWrite.lean::BridgedWriteWitness.two_disjunct_soundness_is_false`. -/
theorem foldl_edge_complete_is_false_for_the_bridged_fold :
    ¬ (∀ (us : List Tuple) (σ : GraphState), FoldAdmits σ us → ∀ u ∈ us,
        (subjNode u.subject, objNode u.object u.relation) ∈
          (us.foldl (fun acc u => acc.writeBridgedOne u) σ).edges) := by
  intro h
  have hc := h [BridgedWriteWitness.tCycle] base unbridged_fold_admits
    BridgedWriteWitness.tCycle (by decide)
  revert hc
  decide

/-- ★★ **THE TRIPWIRE FIRED, 2026-09-14, AND THIS IS THE RECORDED FLIP.**

    Until step 14 landed, this declaration read

    ```
    theorem w3d_write_applies_with_the_stale_hypothesis :
        ReachedByW3d (base.writeLoggedRules …Sthru …tCycle) …Sthru [BridgedWriteWitness.tCycle] :=
      .write BridgedWriteWitness.tCycle
        (by rw [cycle_closure_is_the_member]; exact unbridged_fold_admits)
        (.empty ThroughShapeWitness.Sthru)
    ```

    — the live `ReachedByW3d.write` constructor inhabited AT THE CYCLE FIXTURE, which is the
    whole of step 14 in one line: the chain admitted a step whose own fold refuses the grant.
    It was placed deliberately so the honesty fix could not land silently. When `hadm` moved
    to `FoldAdmitsBridged` the build produced EXACTLY ONE error, and it was this one:

    ```
    error: Cascade.lean:2428:42: Type mismatch
      unbridged_fold_admits
    has type
      FoldAdmits base [BridgedWriteWitness.tCycle]
    but is expected to have type
      FoldAdmitsBridged base [BridgedWriteWitness.tCycle]
    ```

    That single-declaration attribution is itself the evidence the tripwire was aimed right:
    a trap that reddened the module would not have distinguished "the constructor moved" from
    "the file broke". `bridged_fold_refuses` proves no term can inhabit it there, so the
    prescribed response — move the pin to an ADMITTED fixture, do not weaken the constructor —
    is what is applied below.

    ⚠ **The pin now runs at `BridgedWriteWitness.tThru`**, where `control_bridged_grant_agrees`
    machine-checks that BOTH predicates hold. That control is what keeps this from being a
    retreat to a fixture where the question cannot be asked: the subject at `tThru` IS bridged
    in (`::subject_is_bridged_in`), so the constructor is still exercised on a bridging write —
    only not on the cycle that the honest predicate is there to refuse. The cycle case is not
    lost either; it lives on in `bridged_fold_refuses` and `bridged_fold_drops_the_grant`,
    which say the thing this declaration used to say, from the other side. -/
theorem w3d_write_applies_with_the_bridged_hypothesis :
    ReachedByW3d (base.writeLoggedRules ThroughShapeWitness.Sthru BridgedWriteWitness.tThru)
      ThroughShapeWitness.Sthru [BridgedWriteWitness.tThru] :=
  .write BridgedWriteWitness.tThru
    (by rw [thru_closure_is_the_member]; exact control_bridged_grant_agrees.2)
    (.empty ThroughShapeWitness.Sthru)

end FoldAdmitsHonestyWitness

end Zanzibar
