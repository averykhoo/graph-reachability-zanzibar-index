import ZanzibarProofs.GraphIndex.Cascade
import ZanzibarProofs.GraphIndex.Leaf
import ZanzibarProofs.GraphIndex.LeafRules

/-!
# Fan-out completeness — write-leg operand stability off the mapped keys (ROADMAP W3d-1b)

`index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` +
`index_v4/core.py::ReachabilityIndex._emit`: a write
transaction's outbox rows must dirty EVERY derived key whose reconciled representation
its edges can have changed — the cross-key re-reconcile hazard as a theorem, in
contrapositive form: **if a derived key `(dt, R, on)` is NOT in `cascadeKeys` after a
logged write leg, then every operand `graphRec` read at that key — hence the pass guard
`checkFn`/`coveredFn` itself — is unchanged by the leg** (`writeLeg_checkFn_stable`).

The route: a changed untainted probe needs a new path into the operand node
`objNode ⟨dt,on⟩ r'`; the path's first NEW edge is a routed edge of the write
(`nreaches_factor`), which emitted an outbox row above the (unchanged) watermark,
denormalized at the edge's own head (`writeLoggedRules_edge_delta`); the operand node
then lies in that row's cascade-time reach cone, so the key is in `affectedKeys`
(`mem_affectedKeys`) — contradiction.

**Attack-first (2026-07-11g, machine-checked `#eval` vs the real `graphRec`/
`cascadeKeys`/`sem`; scratch deleted).** In-fragment hunts all CONFIRMED the statement:
multi-hop userset threading (`dave → group:eng → doc:1#member`, 2-hop `group:sub`
cones), sibling computed routing (`editor@doc:3` dirties the `viewer` key through the
routed `member` edge — decision 1's per-routed-edge rows), bare star grants
(`user:* @doc:3` dirties via the routed edge's concrete head, probe-2 source
irrelevant), ghost writes onto fresh nodes (fuel growth is read-inert at closed
states), and cross-key `excl`-operand writes. **OUT-of-fragment REFUTATION confirmed
live**: an object-star write `member@doc:*` flips probe 3 (`reach (subjNode s)
(wAllNode doc member)`) at EVERY object of the type while mapping NO keys — the routed
edge's head is the `wAll` node, whose name is `STAR`, which
`index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` maps to no derived own-key
(an UNTAINTED head matches no compiled family at all; a DERIVED head with `o_name ==
'*'` is not skipped but `raise InvariantViolation` — the leaked decision-15 shape,
hardened from a bare `assert` by `ZT-P1-2`, 2026-07-26). The Python system is immune because its closure
materializes out-bridges whose per-flip rows land at CONCRETE object ends; the model's
decision-1 row reconstruction has no out-bridges, so the fragment must keep edge
targets plain — exactly `BareStarStore`'s object-star-freeness, threaded here as
`reachedByW3d_edges_target_plain`.
-/

namespace Zanzibar

/-! ## Path factoring through marked edges -/

/-- **New-edge factoring.** A path over `E'` whose edges each are old (`∈ E`) or
    marked (`P`) either lives entirely in `E`, or passes through a marked edge — and
    from that edge's HEAD the rest of the path (possibly empty) runs in `E'`. -/
theorem nreaches_factor {P : NodeKey × NodeKey → Prop}
    {E E' : List (NodeKey × NodeKey)} {u v : NodeKey}
    (hsub : ∀ ab ∈ E', ab ∈ E ∨ P ab) (h : NReaches E' u v) :
    NReaches E u v ∨ ∃ ab, P ab ∧ NReachesR E' ab.2 v := by
  induction h with
  | @edge u v huv =>
    rcases hsub _ huv with hE | hP
    · exact Or.inl (NReaches.edge hE)
    · exact Or.inr ⟨(u, v), hP, Or.inl rfl⟩
  | @head u w v huw hrest ih =>
    rcases ih with hE | hP
    · rcases hsub _ huw with hEw | hPw
      · exact Or.inl (NReaches.head hEw hE)
      · exact Or.inr ⟨(u, w), hPw, Or.inr hrest⟩
    · exact Or.inr hP

/-! ## Write-leg bookkeeping — the logged fold's outbox and edges -/

/-! ★ **`P6` step 3b, 2026-09-14 — the write-leg bookkeeping below keeps every STATEMENT
across re-point #1; the proofs swap one discharger each.** The pattern is uniform: where a
proof reached for a `writeDirect_*` projection it now reaches for the bridge prologue's
(`Cascade.lean::bridgePreLogged_*`), because the then-branch of `writeLoggedOne` is
`(σ.bridgePreLogged t).addEdge …` rather than `σ.writeDirect t`. `GraphState.addEdge` is the
structure update `{ σ with edges := … }`, so its watermark/outbox/nodes projections reduce
definitionally and need no lemma — which is just as well, because **`addEdge_watermark` and
`addEdge_outbox` do not exist** (`State.lean` has `addEdge_nodes` / `_residue` / `_schema` /
`_edges` only). -/

/-- One logged write step keeps the watermark. The bridge prologue must not move the drain
    cursor — that is `bridgePreLogged_watermark`'s whole job. -/
theorem writeLoggedOne_watermark (σ : GraphState) (t : Tuple) :
    (σ.writeLoggedOne t).watermark = σ.watermark := by
  unfold GraphState.writeLoggedOne
  split
  · rw [pushDelta_watermark]
    exact bridgePreLogged_watermark σ t
  · rfl

/-- One logged write step only pushes outbox rows.

    ⚠ Post-re-point this is a STRONGER fact than it looks: the prologue itself emits (one
    row per bridge that fires), so "only pushes" now has to survive two emitting stages, not
    one. `bridgePreLogged_outbox_mono` is the first. -/
theorem writeLoggedOne_outbox_mono (σ : GraphState) (t : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.writeLoggedOne t).outbox := by
  intro d hd
  unfold GraphState.writeLoggedOne
  split
  · rw [pushDelta_outbox]
    refine List.mem_cons_of_mem _ ?_
    show d ∈ (σ.bridgePreLogged t).outbox
    exact bridgePreLogged_outbox_mono σ t d hd
  · exact hd

/-- The logged fold only pushes outbox rows. -/
theorem foldl_writeLoggedOne_outbox_mono (us : List Tuple) :
    ∀ (σ : GraphState), ∀ d ∈ σ.outbox,
      d ∈ (us.foldl (fun acc u => acc.writeLoggedOne u) σ).outbox := by
  induction us with
  | nil => intro σ d hd; exact hd
  | cons u rest ih =>
    intro σ d hd
    simp only [List.foldl_cons]
    exact ih _ d (writeLoggedOne_outbox_mono σ u d hd)

/-- The whole logged write only pushes outbox rows. -/
theorem writeLoggedRules_outbox_mono (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.writeLoggedRules S t).outbox := by
  unfold GraphState.writeLoggedRules
  exact foldl_writeLoggedOne_outbox_mono (rewriteClosureL S (rawWriteTuples S t)) σ

/-- A logged write leg only adds edges (its core is the unlogged `writeRulesRaw`).

    ★ `P6` step 3b (2026-09-14): statement unchanged, discharger swapped for the bridged
    twin. Monotonicity is **strictly easier** after the re-point, not harder — bridging only
    ever ADDS a node and an edge (`UsStarWrite.lean::ensureInBridges_mono`), and a refused
    grant rolls the whole prologue back to `σ` rather than to some partially-bridged state. -/
theorem writeLoggedRules_edges_mono (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ ab ∈ σ.edges, ab ∈ (σ.writeLoggedRules S t).edges := by
  intro ab hab
  rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges]
  exact foldl_writeBridgedOne_edges_mono _ ab hab

/-- **New edges carry frontier rows.** Every edge of a logged write leg is an old
    edge, or has an emitted outbox row with an id strictly above the (unchanged)
    watermark, denormalized at the edge's own head — the model-level content of
    `index_v4/core.py::ReachabilityIndex._emit`: a flip stages its row (perf N16) and
    `::ReachabilityIndex._flush_outbox` inserts it inside the same transaction. -/
theorem writeLoggedRules_edge_delta (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab ∈ σ.edges ∨ ∃ d ∈ (σ.writeLoggedRules S t).outbox,
        σ.watermark < d.id ∧ d.node = ab.2 := by
  unfold GraphState.writeLoggedRules
  suffices H : ∀ (us : List Tuple) (σc : GraphState), σc.watermark = σ.watermark →
      (∀ ab ∈ σc.edges, ab ∈ σ.edges ∨ ∃ d ∈ σc.outbox, σ.watermark < d.id ∧ d.node = ab.2) →
      ∀ ab ∈ (us.foldl (fun acc u => acc.writeLoggedOne u) σc).edges,
        ab ∈ σ.edges ∨ ∃ d ∈ (us.foldl (fun acc u => acc.writeLoggedOne u) σc).outbox,
          σ.watermark < d.id ∧ d.node = ab.2 from
    H (rewriteClosureL S (rawWriteTuples S t)) σ rfl (fun ab hab => Or.inl hab)
  intro us
  induction us with
  | nil => intro σc _ h ab hab; exact h ab hab
  | cons u rest ih =>
    intro σc hwm h ab hab
    simp only [List.foldl_cons] at hab ⊢
    refine ih (σc.writeLoggedOne u) (by rw [writeLoggedOne_watermark, hwm]) ?_ ab hab
    intro ab' hab'
    unfold GraphState.writeLoggedOne at hab' ⊢
    by_cases hadm : (σc.bridgePreLogged u).admitEdge (subjNode u.subject)
        (objNode u.object u.relation) = true
    · rw [if_pos hadm] at hab' ⊢
      rw [pushDelta_edges, addEdge_edges] at hab'
      rw [pushDelta_outbox]
      rcases List.mem_cons.mp hab' with heq | hmem
      · -- the fresh GRANT edge: its row is the pushed head
        refine Or.inr ⟨⟨((σc.bridgePreLogged u).addEdge (subjNode u.subject)
            (objNode u.object u.relation)).nextDeltaId, objNode u.object u.relation,
          u.relation, true⟩, List.mem_cons_self, ?_, ?_⟩
        · show σ.watermark < ((σc.bridgePreLogged u).addEdge (subjNode u.subject)
            (objNode u.object u.relation)).nextDeltaId
          have h1 : ((σc.bridgePreLogged u).addEdge (subjNode u.subject)
                (objNode u.object u.relation)).nextDeltaId
              = max ((σc.bridgePreLogged u).addEdge (subjNode u.subject)
                  (objNode u.object u.relation)).maxOutboxId
                ((σc.bridgePreLogged u).addEdge (subjNode u.subject)
                  (objNode u.object u.relation)).watermark + 1 := rfl
          have h2 : ((σc.bridgePreLogged u).addEdge (subjNode u.subject)
              (objNode u.object u.relation)).watermark = σc.watermark :=
            bridgePreLogged_watermark σc u
          omega
        · show (⟨((σc.bridgePreLogged u).addEdge (subjNode u.subject)
            (objNode u.object u.relation)).nextDeltaId, objNode u.object u.relation,
            u.relation, true⟩ : Delta).node = ab'.2
          rw [heq]
      · -- ★ `P6` step 3b (2026-09-14): the one genuinely NEW case. Post-re-point this is
        -- an edge of the PROLOGUE, not of `σc` — so it is old, or it is a BRIDGE edge,
        -- which carries its own frontier row at the bridge target. That the row sits at
        -- `ab.2` on the bridge arm too is what lets this theorem keep its statement
        -- instead of weakening to a disjunction over the two endpoints; see
        -- `Cascade.lean::ensureInBridgesLogged_edge_delta`.
        rcases bridgePreLogged_edge_delta σc u ab' hmem with hold | ⟨d, hd, hgt, hnode⟩
        · rcases h ab' hold with hσ | ⟨d, hd, hgt', hnode⟩
          · exact Or.inl hσ
          · exact Or.inr ⟨d, List.mem_cons_of_mem _
              (bridgePreLogged_outbox_mono σc u d hd), hgt', hnode⟩
        · refine Or.inr ⟨d, List.mem_cons_of_mem _ hd, ?_, hnode⟩
          rw [← hwm]; exact hgt
    · rw [if_neg hadm] at hab' ⊢
      exact h ab' hab'

/-! ## Endpoint closure over the interleaved closure

★ **MOVED OUT, `P6` step 3b (2026-09-13g): `runCascade_cases` now lives in `Cascade.lean`**,
immediately after the `runCascade` definition it case-splits. Name, statement and proof are
unchanged, so all six call sites in this file and downstream still resolve. It travelled
with the schema-preservation trio out of `CascadeSettle.lean` because
`reachedByW3d_schema`'s cascade case needs it: `Cascade.lean` needs that theorem and imports
this file's consumers, not the other way round. -/

/-- The `writeDirect` fold only adds nodes. -/
theorem foldl_writeDirect_nodes_mono (us : List Tuple) :
    ∀ (σ : GraphState), ∀ k ∈ σ.nodes,
      k ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).nodes := by
  induction us with
  | nil => intro σ k hk; exact hk
  | cons u rest ih =>
    intro σ k hk
    simp only [List.foldl_cons]
    exact ih _ k (writeDirect_monoNodes σ u k hk)

/-- **The `writeDirect` fold's node SOUNDNESS** — the converse of
    `foldl_writeDirect_nodes_mono`: every node of the folded state is an old node or an
    endpoint minted by one of the folded tuples. Added by step 4c-ii for
    `untaintedShadow_writeLegL`'s `nodesSub` field, where the two folds run over DIFFERENT
    lists and monotonicity alone no longer bridges them. -/
theorem foldl_writeDirect_nodes_sound (us : List Tuple) :
    ∀ (σ : GraphState), ∀ k ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).nodes,
      k ∈ σ.nodes ∨
        ∃ u ∈ us, k = subjNode u.subject ∨ k = objNode u.object u.relation := by
  induction us with
  | nil => intro σ k hk; exact Or.inl hk
  | cons u rest ih =>
    intro σ k hk
    simp only [List.foldl_cons] at hk
    rcases ih (σ.writeDirect u) k hk with hstep | ⟨w, hw, hwk⟩
    · rw [writeDirect_nodes] at hstep
      split at hstep
      · rcases List.mem_cons.mp hstep with heq | hstep2
        · exact Or.inr ⟨u, List.mem_cons_self, Or.inr heq⟩
        · rcases List.mem_cons.mp hstep2 with heq | hold
          · exact Or.inr ⟨u, List.mem_cons_self, Or.inl heq⟩
          · exact Or.inl hold
      · exact Or.inl hstep
    · exact Or.inr ⟨w, List.mem_cons_of_mem _ hw, hwk⟩

/-- The `writeDirect` fold preserves edge endpoint-closure. -/
theorem edgesClosed_foldl_writeDirect (us : List Tuple) :
    ∀ (σ : GraphState), (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      ∀ ab ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).edges,
        ab.1 ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).nodes
          ∧ ab.2 ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).nodes := by
  induction us with
  | nil => intro σ hcl; exact hcl
  | cons u rest ih =>
    intro σ hcl
    simp only [List.foldl_cons]
    exact ih _ (edgesClosed_writeDirect hcl u)

/-- The unlogged diffing batch preserves edge endpoint-closure (the residue half is
    edge/node-inert). -/
theorem edgesClosed_reconcileJobsD {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      ∀ ab ∈ (reconcileJobsD S T σ jobs).edges,
        ab.1 ∈ (reconcileJobsD S T σ jobs).nodes
          ∧ ab.2 ∈ (reconcileJobsD S T σ jobs).nodes := by
  intro jobs
  induction jobs with
  | nil => intro σ hcl; exact hcl
  | cons j rest ih =>
    intro σ hcl
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    refine ih _ ?_
    intro ab hab
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD at hab ⊢
    refine edgesClosed_reconcileKeyD T j.dt j.on j.R j.e j.cands _ ?_ ab hab
    intro ab' hab'
    rw [reconcileResidueKey_edges] at hab'
    rw [reconcileResidueKey_nodes]
    exact hcl ab' hab'

/-- **Every W3d state is edge endpoint-closed** — the `reach ↔ NReaches` bridge is
    available on the whole interleaved chain.

    ★ `P6` step 3b (2026-09-14): statement unchanged, one discharger swapped. The bridged
    fold preserves endpoint closure for a structural reason worth stating once, because
    several proofs below lean on it: `ensureInBridges` interns the `wAnyNode` via `addNode`
    on EVERY bridged branch *before* it can add the bridge edge, and `bridgePre` adds both
    grant endpoints first — so no stage can produce an edge whose endpoint is not already a
    node. -/
theorem reachedByW3d_edgesClosed {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes := by
  induction h with
  | empty S =>
    intro ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    have hev := writeLoggedRules_evalEq (EvalEq.refl σp) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σp ih ab hab
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro ab hab
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc] at hab ⊢
      have hev := reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs
      have hab' : ab ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [hev.edges] at hab'
      have hres := edgesClosed_reconcileJobsD jobs σp ih ab hab'
      show ab.1 ∈ (reconcileJobsL S T σp jobs).nodes
        ∧ ab.2 ∈ (reconcileJobsL S T σp jobs).nodes
      rw [hev.nodes]
      exact hres
    · rw [hrc] at hab ⊢
      exact ih ab hab

/-! ## Plain edge targets over the interleaved closure (the attack's fragment fence) -/

/-- **No W3d edge target is a `wAll` node** on `BareStarStore` stores: a routed edge's
    object is the raw write's object (star-free by `BareStarStore`), a cascade edge's
    object is the job's concrete `on`, and a write's bridge target is a `wAny`. This is the
    fence the attack found load-bearing: a `wAll`-targeted edge would flip probe 3 at every
    object of the type while `affectedKeys` skips the star-named head (Python's
    `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` never dirties a derived
    own-key from one, and rejects the derived-head case outright). The store
    hypothesis is taken at the chain's own store and weakens along the prefix.

    ★★ **RESTATED by `P6` step 3b (2026-09-14). The old form went HARD-FALSE.** It read
    `∀ ab ∈ σ.edges, ab.2.variant = Variant.plain`; once the write leg materialises
    in-bridges there is a counterexample in every bridged write, because a bridge target is
    `wAnyNode (ty,p) = ⟨ty, STAR, p, Variant.wAny⟩`. ⚠ **The NAME is audited**
    (`formal/audited_theorems.txt`, plus a `#print axioms` row in `Audit.lean`) and the
    name therefore stays, misleading suffix and all — renaming it would red `verify.sh`
    step 4a. The statement is not pinned, so it was free to move.

    **Why `≠ wAll` and not the disjunctive `plain ∨ wAny`.** Its sole consumer chain is
    `writeLeg_reach_wAll_false` → `writeLeg_graphRec_stable` → `writeLeg_checkFn_stable`,
    and every use feeds `DirectCorrect.lean::nreaches_target_variant_ne` a `wAllNode` to
    derive `False`. `≠ wAll` is exactly sufficient and needs NO case split at any consumer;
    the disjunction would push a two-way `rcases` into three proofs to say the same thing.
    The same restatement is owed at the twin `CascadeStrataSettle.lean::
    reachedByW3d2_edges_target_plain` (NOT audited), which has six consumers. -/
theorem reachedByW3d_edges_target_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    BareStarStore T → ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll := by
  induction h with
  | empty S =>
    intro _ ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hBS ab hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hab
      with hold | ⟨w, hw, _, h2⟩ | ⟨_, h2⟩
    · exact ih (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')) (a, b) hold
    · show b.variant ≠ Variant.wAll
      have hwo : w.object.name ≠ STAR := by
        rw [rewriteClosureL_object hw]
        exact (hBS t List.mem_cons_self).2
      rw [h2, objNode_plain hwo]
      exact Variant.noConfusion
    · -- ★ THE NEW DISJUNCT, and the reason this statement had to move: a bridge target is
      -- `wAnyNode`, so it is NOT plain. It is not `wAll` either, and that is all the fence
      -- was ever used for.
      show b.variant ≠ Variant.wAll
      rw [h2]
      exact Variant.noConfusion
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hBS ab hab
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc] at hab
      have hab' : ab ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hab'
      obtain ⟨a, b⟩ := ab
      rcases reconcileJobsD_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, _, _, h2⟩
      · exact ih hBS (a, b) hold
      · show b.variant ≠ Variant.wAll
        obtain ⟨_, _, _, _, _, _, _, _, hon⟩ := hjv j hj
        rw [h2, objNode_plain hon]
        exact Variant.noConfusion
    · rw [hrc] at hab
      exact ih hBS ab hab

/-! ## The delta → key mapping, introduction form -/

/-- **`affectedKeys` membership, introduction.** A concrete operand node
    `objNode ⟨dt,on⟩ r'` in a row's candidate-object set dirties the derived key
    `(dt, R, on)` whenever `(dt, R)`'s def reads `r'` as a computed operand — the
    positive of `_map_deltas_to_keys`' LeafFamily/`via='computed'` branch. -/
theorem mem_affectedKeys {S : Schema} {σ' : GraphState} {d : Delta}
    {dt on R r' : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hobj : objNode ⟨dt, on⟩ r' ∈ σ'.affectedObjects d) :
    (dt, R, on) ∈ affectedKeys S σ' d := by
  have hname : (objNode ⟨dt, on⟩ r').name = on := by
    rw [objNode_plain hon]
  unfold affectedKeys
  refine List.mem_append_right _ (List.mem_flatMap.mpr ⟨objNode ⟨dt, on⟩ r', hobj, ?_⟩)
  rw [if_neg (by rw [hname]; exact hon)]
  refine List.mem_filterMap.mpr ⟨(dt, R), ?_, ?_⟩
  · exact List.mem_map.mpr ⟨((dt, R), e), mem_defs_of_lookup hlk, rfl⟩
  · have hcond : (dt, R).1 = (objNode ⟨dt, on⟩ r').type ∧ isDerived S (dt, R) = true ∧
        ((S.lookup (dt, R)).map
          (fun e => (computedRefs e).contains (objNode ⟨dt, on⟩ r').pred)).getD false
          = true := by
      refine ⟨by rw [objNode_type], hder, ?_⟩
      rw [objNode_pred, hlk]
      simp only [Option.map_some, Option.getD_some]
      rw [List.contains_eq_mem]
      exact decide_eq_true hr'
    rw [if_pos hcond, hname]

/-! ## The write-leg stability theorems -/

/-- **Reach into a concrete operand node is stable across an unmapped write leg.**
    Forward, edges are monotone; backward, a new path factors through a routed edge
    whose frontier row's reach cone contains the operand node — putting the key in
    `cascadeKeys`, contradicting unmappedness. -/
theorem writeLeg_reach_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (x : NodeKey) :
    (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σ hclσ ab hab
  cases h' : (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
    <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
  · rfl
  · -- pre-path survives (edges monotone)
    exfalso
    have hmono := NReaches.mono_subset (writeLoggedRules_edges_mono σ S t) (reach_sound h0)
    have := reach_complete hclσ' hmono
    rw [h'] at this
    cases this
  · -- new path: factor through a routed edge, map the key
    exfalso
    have hN := reach_sound h'
    rcases nreaches_factor
      (P := fun ab => ∃ d ∈ (σ.writeLoggedRules S t).outbox, σ.watermark < d.id ∧ d.node = ab.2)
      (writeLoggedRules_edge_delta σ S t) hN with hold | ⟨ab, ⟨d, hd, hgt, hnode⟩, hR⟩
    · have := reach_complete hclσ hold
      rw [h0] at this
      cases this
    · apply hunmapped
      have hfront : d ∈ (σ.writeLoggedRules S t).frontierRows := by
        unfold GraphState.frontierRows
        refine List.mem_filter.mpr ⟨hd, ?_⟩
        rw [writeLoggedRules_watermark]
        exact decide_eq_true hgt
      refine List.mem_flatMap.mpr ⟨d, hfront, ?_⟩
      refine mem_affectedKeys hlk hder hr' hon ?_
      unfold GraphState.affectedObjects
      rcases hR with heq | hreach
      · rw [hnode, ← heq]
        exact List.mem_cons_self
      · refine List.mem_cons_of_mem _ (List.mem_filter.mpr ⟨?_, ?_⟩)
        · obtain ⟨y, _, hyv⟩ := nreaches_last hreach
          exact (hclσ' _ hyv).2
        · rw [hnode]
          exact reach_complete hclσ' hreach
  · rfl

/-- Reach into the operand's `wAll` node is `false` on both sides of a write leg
    whose edge targets are plain (the attack's fragment fence). -/
theorem writeLeg_reach_wAll_false {σ : GraphState} {S : Schema} {t : Tuple}
    {dt r' : String}
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll) :
    (∀ u, (σ.writeLoggedRules S t).reach u (wAllNode dt r') = false) ∧
    (∀ u, σ.reach u (wAllNode dt r') = false) := by
  have htp0 : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll :=
    fun ab hab => htp' ab (writeLoggedRules_edges_mono σ S t ab hab)
  constructor
  · intro u
    cases hc : (σ.writeLoggedRules S t).reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_variant_ne htp' (reach_sound hc)
      simp [wAllNode] at this
  · intro u
    cases hc : σ.reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_variant_ne htp0 (reach_sound hc)
      simp [wAllNode] at this

/-- **Write-leg `graphRec` stability off the mapped keys** (fan-out completeness,
    contrapositive): an unmapped derived key's operand read is unchanged by the
    logged write, for EVERY subject. Probes 1–2 by reach stability into the concrete
    operand node; probes 3–4 dead on both sides (plain targets). -/
theorem writeLeg_graphRec_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (s : SubjectRef) :
    GraphModel.graphRec (σ.writeLoggedRules S t) s dt on r'
      = GraphModel.graphRec σ s dt on r' := by
  obtain ⟨hwall', hwall0⟩ := writeLeg_reach_wAll_false (σ := σ) (S := S) (t := t)
    (dt := dt) (r' := r') htp'
  unfold GraphModel.graphRec GraphModel.probeNonDerived
  dsimp only
  rw [writeLeg_reach_stable hclσ hlk hder hr' hon hunmapped (subjNode s),
    writeLeg_reach_stable hclσ hlk hder hr' hon hunmapped (wAnyNode s.shape),
    hwall' (subjNode s), hwall0 (subjNode s),
    hwall' (wAnyNode s.shape), hwall0 (wAnyNode s.shape)]

/-- **Write-leg `checkFn` stability off the mapped keys.** The compiled pass guard —
    hence `coveredFn` at any shape (a `checkFn` at the star subject) — is unchanged by
    a logged write that does not map the key: fan-out completeness at the guard level,
    the exact form the settledness invariant's write legs consume. -/
theorem writeLeg_checkFn_stable {σ : GraphState} {S : Schema} {t : Tuple} (T' : Store)
    {dt on R : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (s : SubjectRef) :
    (σ.writeLoggedRules S t).checkFn T' s dt on R e = σ.checkFn T' s dt on R e := by
  unfold GraphState.checkFn
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  exact writeLeg_graphRec_stable hclσ htp' hlk hder hr' hon hunmapped s

/-! ## `cascadeKeys` is monotone along a write leg — dirty keys stay dirty -/

/-- A row's candidate-object set only grows across a write leg (the row's node is
    kept; reach cones grow with edges/nodes at closed states). -/
theorem affectedObjects_writeLeg_mono {σ : GraphState} {S : Schema} {t : Tuple}
    (hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes)
    (d : Delta) :
    ∀ v ∈ σ.affectedObjects d, v ∈ (σ.writeLoggedRules S t).affectedObjects d := by
  intro v hv
  unfold GraphState.affectedObjects at hv ⊢
  rcases List.mem_cons.mp hv with heq | hmem
  · rw [heq]
    exact List.mem_cons_self
  · obtain ⟨hvn, hvr⟩ := List.mem_filter.mp hmem
    refine List.mem_cons_of_mem _ (List.mem_filter.mpr ⟨?_, ?_⟩)
    · have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
      rw [hev.nodes]
      exact foldl_writeBridgedOne_nodes_mono (rewriteClosureL S (rawWriteTuples S t)) σ v hvn
    · exact reach_complete hclσ'
        (NReaches.mono_subset (writeLoggedRules_edges_mono σ S t) (reach_sound hvr))

/-- **`cascadeKeys` write-leg monotonicity**: a key dirtied before a logged write is
    still dirty after it — frontier rows persist (outbox grows, watermark fixed) and
    per-row key sets grow with the reach cones. Dirty keys stay dirty until a cascade. -/
theorem cascadeKeys_writeLeg_mono {σ : GraphState} {S : Schema} {t : Tuple}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) :
    ∀ k ∈ cascadeKeys S σ, k ∈ cascadeKeys S (σ.writeLoggedRules S t) := by
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σ hclσ ab hab
  intro k hk
  unfold cascadeKeys at hk ⊢
  obtain ⟨d, hd, hkd⟩ := List.mem_flatMap.mp hk
  refine List.mem_flatMap.mpr ⟨d, ?_, ?_⟩
  · obtain ⟨hdmem, hdgt⟩ := List.mem_filter.mp hd
    refine List.mem_filter.mpr ⟨writeLoggedRules_outbox_mono σ S t d hdmem, ?_⟩
    rw [writeLoggedRules_watermark]
    exact hdgt
  · unfold affectedKeys at hkd ⊢
    rcases List.mem_append.mp hkd with hown | hfan
    · exact List.mem_append_left _ hown
    · obtain ⟨v, hv, hkv⟩ := List.mem_flatMap.mp hfan
      exact List.mem_append_right _
        (List.mem_flatMap.mpr ⟨v, affectedObjects_writeLeg_mono hclσ' d v hv, hkv⟩)

/-! ## The untainted-core shadow — the W3d read bridge

The W3a shadow does not extend over diffing passes (a removal is not a W3a reconcile
leg), so the W3c `checkFn = sem` bridge does not transfer pointwise to W3d states. The
replacement: every W3d state differs from a `ReachedByRulesAdmitted` state ON THE
CURRENT STORE only in edges into terminal derived R-nodes (`DerNode`s) — which no
untainted probe ever traverses (through-hops die on terminality, landings on the
target mismatch). So the untainted operand reads — hence the pass guard `checkFn` —
agree with the rules base, where `checkFn_eq_sem_bs` applies: **`checkFn = sem` at
EVERY W3d state** (`checkFn_eq_sem_w3d`), cascaded or not. (The DERIVED read is stale
mid-transaction — that is settledness's business, scoped to cascaded states.)

The new content vs W3c's `CoreEq` shadow is the write-leg ADMISSION transfer
(`shadow_admitEdge_agree`): the logged fold and the shadow's `writeRules` fold accept
the same edges, because the admission probe's back-reach target is a rewrite-closure
subject node — never a `DerNode` (`hterm` keeps store/closure subjects off derived
predicates) — so the reach agreement applies. -/

/-- A derived R-node key: the target of processor-materialised derived edges
    (concrete object, non-bare derived relation). -/
def DerNode (S : Schema) (k : NodeKey) : Prop :=
  ∃ dt on R, isDerived S (dt, R) = true ∧ R ≠ BARE ∧ on ≠ STAR ∧ k = objNode ⟨dt, on⟩ R

/-- **A bridge node** — the `w_any (ty, p)` node that an in-bridge points AT, for a shape the
    schema declares a subject-wildcard userset (`UsStarWrite.lean::
    Schema.isSubjectWildcardUserset`, = `zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes`).

    **This is the THIRD extras disjunct of the shadow** (`P6` step 3b step 8): once the write
    leg folds `GraphState.writeBridgedOne`, a W3d state carries edges the
    `ReachedByRulesAdmitted` base does not, and the new ones land at exactly these nodes —
    `UsStarWrite.lean::foldl_writeBridgedOne_edges_sound`'s third disjunct says so, and
    `bridgeNode_wAnyNode` below is the one-line conversion from that disjunct into this
    predicate.

    ⚠ **Minting it is additive; USING it is not.** `UntaintedShadow` below is NOT widened
    here — that is the red half of step 3b, and widening it would move
    `ShadowOver`'s obligations at 18 declarations in this file alone. Defined so the support
    lemmas the widening needs can be proved and committed green ahead of it, per the
    additive-first test of `docs/p6-step3b-plan-2026-09-13.md` `C9`.

    Keyed on `(type, pred)` and never on the predicate STRING alone — the same `TK68`
    type-index trap `UsStarWrite.lean::NoBridgedDerived` documents: a literal `[x:*#R]`
    restriction at an untainted `(x, R)` is legal Python, so a bridge node's `pred` can be
    any relation name, derived-looking or not. -/
def BridgeNode (S : Schema) (k : NodeKey) : Prop :=
  ∃ ty p, S.isSubjectWildcardUserset ty p = true ∧ k = wAnyNode (ty, p)

/-- **Intro** — a declared subject-wildcard userset shape's `w_any` node IS a bridge node.
    The form `ShadowOver.classify` will consume: `UsStarWrite.lean::
    foldl_writeBridgedOne_edges_sound`'s third disjunct delivers
    `σ.schema.isSubjectWildcardUserset a.type a.pred = true ∧ b = wAnyNode (a.type, a.pred)`,
    which is this applied at `(a.type, a.pred)` after `reachedByW3d_schema` converts
    `σ.schema` to `S`. -/
theorem bridgeNode_wAnyNode {S : Schema} {ty p : String}
    (h : S.isSubjectWildcardUserset ty p = true) : BridgeNode S (wAnyNode (ty, p)) :=
  ⟨ty, p, h, rfl⟩

/-- **Elim** — a bridge node is a `wAny`-variant STAR node of a declared subject-wildcard
    userset shape, read off its own key. Mirrors `UsStarWrite.lean::bridgedInConcrete_elim`,
    including the `pred ≠ BARE` conjunct recovered from `isSubjectWildcardUserset`'s OUTER
    `p != BARE` guard — which is the second consumer of that guard's placement, and a second
    reason not to push it inside the disjunction. -/
theorem bridgeNode_elim {S : Schema} {k : NodeKey} (h : BridgeNode S k) :
    k.variant = Variant.wAny ∧ k.name = STAR ∧ k.pred ≠ BARE ∧
      S.isSubjectWildcardUserset k.type k.pred = true := by
  obtain ⟨ty, p, hsw, rfl⟩ := h
  refine ⟨rfl, rfl, ?_, hsw⟩
  unfold Schema.isSubjectWildcardUserset at hsw
  simp only [Bool.and_eq_true, bne_iff_ne, ne_eq] at hsw
  exact hsw.1

/-- **A bridge node is never itself bridged IN** — so the bridge is one hop deep and
    `GraphState.ensureInBridges` cannot chain at its own target. Holds at ANY state and needs
    no schema agreement: `GraphState.bridgedInConcrete`'s first conjunct demands
    `variant = plain` and a bridge node's is `wAny`. (The `c.name ≠ STAR` conjunct would do it
    too; the variant is the more robust of the two, since `subjNode` of a STAR subject is also
    `wAny`-variant.) -/
theorem not_bridgedInConcrete_of_bridgeNode {S : Schema} {σ : GraphState} {k : NodeKey}
    (h : BridgeNode S k) : σ.bridgedInConcrete k = false := by
  obtain ⟨ty, p, _, rfl⟩ := h
  simp [GraphState.bridgedInConcrete, wAnyNode]

/-- **The two extras predicates are DISJOINT** — no bridge node is a `DerNode`. A `DerNode` is
    `objNode ⟨dt, on⟩ R` at a concrete `on ≠ STAR`, hence `plain`-variant; a bridge node is
    `wAny`. Worth landing with the definition because the widened extras predicate is a
    DISJUNCTION, and every `ShadowOver` obligation discharged by cases on it will want to know
    the cases do not overlap (a shared node would have to satisfy both `term` arguments at
    once). -/
theorem not_derNode_of_bridgeNode {S : Schema} {k : NodeKey} (hb : BridgeNode S k) :
    ¬ DerNode S k := by
  rintro ⟨dt, on, R, _, _, hon, rfl⟩
  have hv := (bridgeNode_elim hb).1
  unfold objNode at hv
  simp only [if_neg hon] at hv
  exact Variant.noConfusion hv

/-- **The shadow relation, generic in its EXTRAS predicate `P`.** `σ`'s edges are
    `σ0`'s plus edges into terminal `P`-nodes; both endpoint-closed; `σ0`'s core embeds.

    `P` is a parameter rather than a fixed `DerNode` because 4c-ii's Route B widens the
    extras from `DerNode` to `DerNode ∨ LeafNode` (scope doc §11.9, `Leaf.lean::LeafNode`):
    the re-pointed write leg mints leaf-named targets that the unweakened `classify` has
    no branch for (`Scratch4cii.lean::strong_shadow_false_at_d_own_sigma0`). Every lemma
    below that only needs "extras are terminal and off the probe target" is proved ONCE,
    here, at generic `P`; widening then instantiates rather than re-proves.

    ⚠ Nothing in this structure may mention `DerNode`. A lemma that needs a
    `DerNode`-specific fact belongs below the `UntaintedShadow` abbreviation, not here —
    that separation is the whole reason the widening is a one-line change instead of a
    re-proof of the cascade chain. -/
structure ShadowOver (P : NodeKey → Prop) (σ σ0 : GraphState) : Prop where
  classify : ∀ ab ∈ σ.edges, ab ∈ σ0.edges ∨ P ab.2
  sub : ∀ ab ∈ σ0.edges, ab ∈ σ.edges
  nodesSub : ∀ k ∈ σ0.nodes, k ∈ σ.nodes
  closed : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes
  closed0 : ∀ ab ∈ σ0.edges, ab.1 ∈ σ0.nodes ∧ ab.2 ∈ σ0.nodes
  term : ∀ k, P k → ∀ y, (k, y) ∉ σ.edges

/-- **The untainted-core shadow relation** — `ShadowOver` at the extras predicate the
    live tree uses. **RE-POINTED at `DerNode ∨ LeafNode` by 4c-ii (2026-09-02d)**; this
    docstring previously described the genericization as "a NO-OP rather than a
    re-point", which was true only until this line moved.

    `abbrev` (hence reducible) is load-bearing and must stay: every field access,
    anonymous constructor and `rcases` against this name survived the re-point
    unchanged, which is why the flip cost 2 `have` deletions and 4 argument re-points
    across 2 files rather than a re-proof of the cascade chain. Turning it into a `def`
    while re-pointing would break all of them.

    ⚠ The flip is INVISIBLE TO EVERY PIN — `headline_statements.txt` /
    `headline_definitions.txt` contain no occurrence of `UntaintedShadow`, `ShadowOver`,
    `LeafNode` or `DerNode`, and the definition closure stops before this line. Its only
    mechanical control is the flip probe (SAB-1, 2026-09-02d): reverting this one line
    reds `:1625`/`:1626` (`hsubjW` too wide) and the bare `hv1` use, while the three
    self-adapting `first | … | …` sites stay GREEN — which is exactly why those three
    are not evidence and this probe is. -/
abbrev UntaintedShadow (S : Schema) (σ σ0 : GraphState) : Prop :=
  ShadowOver (fun k => DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) σ σ0

/-! ### Leaf-free `computed` operands (4c-ii step 7)

⚠ **PLAN CORRECTION, 2026-09-01c — the step as enumerated names a predicate whose
premise is FALSE, and this session measured it.** `PROOF_STATUS.md:933-943` calls step 7
`ComputedRefsDeclared`, and `PROOF_STATUS.md:2074-2082` proposes it as a `WF` clause
`∀ p ∈ S.defs, ∀ r ∈ computedRefs p.2, relNameOK r`. Python enforces neither.
`zanzibar_utils_v1.py::_validate_ast_references` (`:910-940`) enforces a **DOT-LOCK** on
*referenced* names — `check_name` (`:915-919`) raises iff `'.' in name and name != '...'`,
applied to `Direct` restriction predicates (`:926-927`), `Computed.relation` (`:929`) and
both TTU names (`:930-932`). Declared-ness is enforced nowhere. Literal observed output:

```text
A  undeclared-operand    : ACCEPTED    -- define alias: ghost
A2 undeclared-in-boolean : ACCEPTED    -- define alias: viewer but not ghost
B  dotted-operand        : REFUSED -> ValueError doc#alias: 'viewer.0' is inside the
                                      reserved leaf namespace ('.' in referenced
                                      relation names)
```

A `ComputedRefsDeclared` would therefore be STRICTLY STRONGER than Python: it would
exclude schemas Python accepts and compiles — unfaithful in the dangerous direction —
and it would contradict `Core/Schema.lean:66-69`, whose `WF` docstring already records
that "reference-declared-ness is handled by the `undefined ⇒ empty` convention, so they
are not extra `WF` clauses".

`relNameOK` is wrong for a second, independent reason: `Core/Ident.lean::BARE = "..."`
CONTAINS a dot, so `relNameOK BARE` is FALSE, while `check_name` escapes `'...'`
explicitly. `Leaf.lean:604::NotLeafName p := p = BARE ∨ isLeafPred p = false` is
`check_name` byte for byte, escape included. That is the predicate below.

✅ **This block is NO LONGER INERT (4c-ii, 2026-09-02d).** It shipped inert on
2026-09-01c and this paragraph used to say a green build vetted nothing here; that is
now false. Its awaited consumer arrived: `shadow_graphRec_agree`'s `hv1` takes an `hnl`
premise, and `ComputedRefsNotLeaf` discharges it at the ELEVEN membership sites through
`::notLeafNode_of_computedRef` / `::checkFn_agree_of_graphRec_notLeafNode`, with
`GraphAdmission.computedRefsNotLeaf` terminating the thread at the headline.

The pins below are still the evidence that the PREDICATE has content, and they are
still the only such evidence — `ComputedRefsNotLeaf := True` would compile and audit
identically, and no build failure would report it. Do not "simplify" them away.
SAB-2 (2026-09-02d) additionally pins that the CONSUMER carries the content: narrowing
`hnl` to the already-derivable `¬ DerNode` reds at `:1653`, `exact hnl hleaf`. -/

/-- **No `computed` operand of any def names a minted leaf family.**
    Quantified over `S.defs` rather than behind an `S.lookup k = some e →` binder so that
    it is a nest of BOUNDED quantifiers over decidable atoms, hence `by decide`-able at a
    concrete schema — the `LeafRules.lean:572-586` design rule. The binder form is not
    decidable and every pin below would have become a hand proof. -/
def ComputedRefsNotLeaf (S : Schema) : Prop :=
  ∀ p ∈ S.defs, ∀ r ∈ computedRefs p.2, NotLeafName r

/-- …and it is DECIDABLE. (A plain `def` is not unfolded by instance synthesis, so the
    instance has to be stated — `LeafRules.lean:605`, same shape.) -/
instance (S : Schema) : Decidable (ComputedRefsNotLeaf S) :=
  inferInstanceAs (Decidable (∀ p ∈ S.defs, ∀ r ∈ computedRefs p.2, NotLeafName r))

/-- The eliminator, read back through a lookup rather than `S.defs` membership. -/
theorem notLeafName_of_computedRef {S : Schema} {k : String × String} {e : Expr}
    {r : String} (h : ComputedRefsNotLeaf S) (hlk : S.lookup k = some e)
    (hr : r ∈ computedRefs e) : NotLeafName r :=
  h (k, e) (mem_defs_of_lookup hlk) r hr

/-- **The consumer form** — the exact shape `shadow_graphRec_agree`'s `hv1` needs when it
    is pre-widened at step 9, at an arbitrary object type and name. -/
theorem notLeafNode_of_computedRef {S : Schema} {k : String × String} {e : Expr}
    {r dt on : String} (h : ComputedRefsNotLeaf S) (hlk : S.lookup k = some e)
    (hr : r ∈ computedRefs e) : ¬ LeafNode S (objNode ⟨dt, on⟩ r) :=
  not_leafNode_of_notLeafName
    (by simpa [objNode_pred] using notLeafName_of_computedRef h hlk hr)

/-- **`checkFn` agreement from a callback that can refute `LeafNode` at every operand it
    sees** — the consumer that makes the `hag` widening load-bearing.

    `hmem` exists only because `ReconcileStars.lean::checkFn_agree_of_graphRec` now forwards
    `r' ∈ computedRefs e` to `hag`. Against the pre-widening `hag`, which handed the callback
    an arbitrary `r'` under `isDerived S (dt, r') = false` alone, this statement is NOT
    provable: `hunt` does not refute a minted leaf name (pinned below at
    `slVBadRef_hunt_holds`). That was scope-doc 11.13 trap (g).

    Stated with `¬ LeafNode` — not `ComputedRefsNotLeaf` — in the callback so that it is
    already the shape `shadow_graphRec_agree`'s `hv1` needs once step 9 pre-widens it.

    **SABOTAGE** (`docs/sabotage-procedure.md`), run 2026-09-01d. The narrowest plausible
    weakening is not "revert the widening" but "the binder was added and carries nothing":
    `hag`'s new premise was changed to `r' = r'` and the forward at
    `ReconcileStars.lean::checkFn_agree_of_graphRec` to `hag s r' rfl (hleafUnt r' hr')`.
    Observed `rc=1`, and this was the ONLY error in the tree:

        error: ZanzibarProofs/GraphIndex/CascadeStable.lean:641:74: Application type
          mismatch: The argument
          hmem
        has type
          r' = r'
        but is expected to have type
          r' ∈ computedRefs e
        in the application
          notLeafNode_of_computedRef hcr hlk hmem

    All NINE `checkFn_agree_of_graphRec{,_cd}` call sites stayed green under that weakening,
    because each discards the membership with `_`. So the call sites are not the instrument
    for the widening — this theorem is the only thing in the tree that can tell a binder
    that carries the membership from one that does not. ⚠ "Only error" is a LOWER bound:
    Lean does not build dependents of a failed module, and `CascadeStable` is upstream of
    twenty of them. -/
theorem checkFn_agree_of_graphRec_notLeafNode {σ σ0 : GraphState} {S : Schema}
    {k : String × String} (T : Store) (s : SubjectRef) (dt on R : String) (e : Expr)
    (hco : ComputedOnly e) (hcr : ComputedRefsNotLeaf S) (hlk : S.lookup k = some e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hag : ∀ (s' : SubjectRef) (r' : String), ¬ LeafNode S (objNode ⟨dt, on⟩ r') →
      isDerived S (dt, r') = false →
      GraphModel.graphRec σ s' dt on r' = GraphModel.graphRec σ0 s' dt on r') :
    σ.checkFn T s dt on R e = σ0.checkFn T s dt on R e :=
  checkFn_agree_of_graphRec T s dt on R e hco hleafUnt
    (fun s' r' hmem hunt => hag s' r' (notLeafNode_of_computedRef hcr hlk hmem) hunt)

/-! #### The pins — the SOLE evidence, since the predicate is inert (step 7)

Everything above is additive, so a green build vets nothing: `ComputedRefsNotLeaf`
returning `True` on every schema would compile and audit exactly as cleanly. Each pin
below exists for no other reason. The template is step 4's witness/control set
(`LeafRules.lean:949-1048`): one witness, one non-vacuity companion, and controls that
differ from the witness in exactly ONE cell so the red points at one thing.

## ★ CONTROLLED — two sabotages, run 2026-09-01c (`docs/sabotage-procedure.md`)

**(S1) The predicate is swapped for the one the PLAN proposed** — `NotLeafName r` →
`relNameOK r`, applied consistently to the `def` AND its `Decidable` instance (the first
attempt changed only the `def` and died of a type mismatch in the instance: an INSTRUMENT
artifact, not a result — `:281-313`). **S1 did NOT discriminate what it was meant to.** It
failed before reaching any pin:
```text
error: CascadeStable.lean:605:2: failed to synthesize
  Decidable (∀ p ∈ S.defs, ∀ r ∈ computedRefs p.2, relNameOK r)
```
`relNameOK` carries no `DecidablePred` instance in this tree, so it cannot serve as this
step's predicate without new instance work — an independent reason to refuse it, but not
the BARE-escape reason the docstring claims. That green was a verdict on the PINS, and it
is why `SlVBareRef` / `computedRefsNotLeaf_bare_true` were added afterwards.

**(S2) The quantifier is narrowed to the first def** — `∀ p ∈ S.defs` →
`∀ p ∈ S.defs.take 1`, again on both sites. This is the innocent-looking refactor that
makes the feature stop being tested. Literal output:
```text
error: CascadeStable.lean:651:74: Tactic `decide` proved that the proposition
  ¬ComputedRefsNotLeaf SlVBadRef
is false
```
**Attributable**: exactly one pin reddened (`computedRefsNotLeaf_false`) plus the
eliminator `notLeafName_of_computedRef` on the code side (`(k, e) ∈ List.take 1 S.defs`).
Controls GREEN throughout: `computedRefsNotLeaf_slV`, `computedRefsNotLeaf_ghost_true`,
`computedRefsNotLeaf_bare_true`, `slVBadRef_hunt_holds`, `slVBadRef_shape_reachable`.
Restored, rebuilt, `rc=0`, 1056 jobs. -/

namespace CrnlWitness

/-- **Positive pin** at the canonical boolean shape `viewer := editor but not banned`
    (`LeafRules.lean:743`). Says little alone — the refutations below give it content. -/
theorem computedRefsNotLeaf_slV : ComputedRefsNotLeaf LeafRuleWitness.SlV := by decide

/-- **Non-vacuity, and it is mandatory**: the predicate is trivially true at any schema
    whose defs carry no `computed` leaf — the same trap `lrV_untainted_layer_silent`
    (`LeafRules.lean:762`) exists to close. This exhibits a NONEMPTY, two-atom operand
    list, so the witness above is quantifying over something. -/
theorem computedRefsNotLeaf_slV_nonvacuous :
    (LeafRuleWitness.SlV.lookup ("doc", "viewer")).map computedRefs
      = some ["editor", "banned"] := by decide

/-- The control: `SlV` with the exclusion's SUBTRACT operand re-pointed at a minted leaf
    name. Differs from `SlV` in exactly ONE cell. -/
def SlVBadRef : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned.0"))], []⟩

/-- **REFUTATION** — reddens iff the predicate stops seeing dotted `computed` operands. -/
theorem computedRefsNotLeaf_false : ¬ ComputedRefsNotLeaf SlVBadRef := by decide

/-- **★ THE CENSUS HOLE, EXHIBITED RATHER THAN ARGUED.** This is the whole reason step 7
    exists. At the control, `shadow_graphRec_agree`'s hypothesis `hunt` **HOLDS** at the
    dotted operand while the enclosing relation is genuinely derived — i.e. `hunt` alone
    does NOT exclude a minted leaf name, so the pre-widened `hv1` cannot be discharged
    from it (`CascadeStable.lean::shadow_graphRec_agree`'s ⚠ comment; scope-doc §11.13
    trap (g)). Structural reason: `Spec/Stratify.lean::taintedKeys` filters `S.keys`, so a
    name that is not a declared key can never be tainted. -/
theorem slVBadRef_hunt_holds : isDerived SlVBadRef ("doc", "banned.0") = false := by decide

/-- …and the shape is REACHABLE, not a curiosity: the enclosing relation really is
    derived, so this is a state the cascade can be in. Without this, the pin above is
    consistent with the whole schema being untainted. -/
theorem slVBadRef_shape_reachable : isDerived SlVBadRef ("doc", "viewer") = true := by decide

/-- **★ THE DISCRIMINATING CONTROL — this is what makes the plan correction machine-
    checked rather than argued.** `SlV` with the subtract operand re-pointed at a
    dot-free but UNDECLARED name. Python ACCEPTS this schema and compiles it (measured
    this session — the `A`/`A2` rows in the block above), and the dot-lock reading
    accepts it too. A `ComputedRefsDeclared` would REFUSE it, excluding a schema the
    implementation runs. One cell from `SlV`, as with the other control. -/
def SlVGhostRef : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "ghost"))], []⟩

/-- The dot-lock reading ACCEPTS the undeclared operand, faithfully to Python. Flip this
    to `¬ ComputedRefsNotLeaf` and you have written `ComputedRefsDeclared` by accident. -/
theorem computedRefsNotLeaf_ghost_true : ComputedRefsNotLeaf SlVGhostRef := by decide

/-- …and the ghost really is undeclared — otherwise the pin above is vacuous, since a
    DECLARED operand would satisfy both readings and discriminate nothing. -/
theorem slVGhostRef_undeclared : SlVGhostRef.lookup ("doc", "ghost") = none := by decide

/-! ##### The BARE escape — added because the S1 sabotage did NOT discriminate it

The docstring above rejects `relNameOK` partly on the ground that `BARE = "..."` contains
a dot, so `relNameOK BARE` is FALSE while Python's `check_name` escapes `'...'`
explicitly. Sabotage S1 (swap `NotLeafName` → `relNameOK`, consistently across the def
and its instance) was run to test that claim and **failed to test it**: it died at
`failed to synthesize Decidable (relNameOK …)` before reaching any pin, because
`relNameOK` carries no `DecidablePred` instance in this tree (`NotLeafName`'s is
`LeafRules.lean:593`). Measured separately: `NotLeafName BARE = true`,
`isLeafPred BARE = true`.

Per `docs/sabotage-procedure.md:137-141` — "use the sabotage to reject a NARROWER pin you
were about to write" — the fixtures below exist because that green was a verdict on the
PINS, not on the code. -/

/-- `SlV` with the subtract operand at the BARE sentinel. Python's `check_name` escapes
    `'...'`, so this is accepted there; `relNameOK` would refuse it. -/
def SlVBareRef : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed BARE))], []⟩

/-- **The escape is load-bearing.** Green under `NotLeafName`; a `relNameOK` reading
    refuses this schema, which is the difference the S1 sabotage could not reach. -/
theorem computedRefsNotLeaf_bare_true : ComputedRefsNotLeaf SlVBareRef := by decide

/-- …and the escape is doing real work rather than being unreachable: `BARE` is exactly
    the string the leaf test would otherwise classify AS a leaf name. -/
theorem bare_is_leafPred : isLeafPred BARE = true := by decide

end CrnlWitness

/-! ### The `NoLeafSubjects` → `TtuTargetsSat` bridge (4c-ii step 6)

`LeafRules.lean::NoLeafSubjects` quantifies over `LeafRules.lean::schemaRewritesL`, which
is *literally* `schemaRewrites S ++ leafRewrites S` — a **superset** of the untainted list
`ReconcileCorrect.lean::TtuTargetsSat` quantifies over, not a different one. So the leaf
discipline implies the untainted one, and the implication is one `List.mem_append_left`.

This is the only reason `CascadeStable` imports `LeafRules` (verified acyclic 2026-08-31:
`LeafRules`' transitive import cone is `Leaf`/`Write`/`RulesWrite`/`State`/`Closure` +
`Core.*`/`Spec.*` + Mathlib and contains **no** `Cascade*` or `Reconcile*` module; the
reverse cone of `CascadeStable` is 20 modules, so the recompile is 21 files).
-/

/-- **`NoLeafSubjects` discharges `TtuTargetsSat _ NotLeafName`.** The whole content is the
    containment `schemaRewrites S ⊆ schemaRewritesL S` (the LEFT summand of the append) plus
    `LeafRules.lean::ttuTargets_of_kind` turning the kind equation `r.kind = .ttu tr` into
    the list membership `tr ∈ ttuTargets r` that `NoLeafSubjects`' bounded quantifier wants.

    ⚠ **SABOTAGED 2026-08-31** — the only thing this lemma asserts is the *direction* of that
    containment, so the sabotage is `List.mem_append_left → List.mem_append_right`, the
    narrowest plausible weakening (it type-checks as a name and is exactly the confusion a
    reader who thinks the two lists are siblings would make). Literal observed output (the
    quoted line number is as-observed, i.e. against this docstring's shorter draft; the
    anchor is `ttuTargetsSat_notLeafName_of_noLeafSubjects`'s `exact` line):

    ```text
    error: ZanzibarProofs/GraphIndex/CascadeStable.lean:600:37: Application type mismatch: The
    argument
      hr
    has type
      r ∈ schemaRewrites S
    but is expected to have type
      r ∈ leafRewrites S
    in the application
      List.mem_append_right (schemaRewrites S) hr
    error: Lean exited with code 1
    Some required targets logged failures:
    - ZanzibarProofs.GraphIndex.CascadeStable
    error: build failed
    ```

    The red is ATTRIBUTABLE: it is the ONLY error in the tree, and the three applicability
    theorems below (which consume this lemma) are downstream of it in the same file, so the
    message names the containment and nothing else. Restored: `Build completed successfully
    (1089 jobs)` — the same job count as the pre-change tree, because `LeafRules` was already
    built through the root aggregator; the new import moves no jobs, only edges. -/
theorem ttuTargetsSat_notLeafName_of_noLeafSubjects {S : Schema}
    (h : NoLeafSubjects S) : TtuTargetsSat S NotLeafName := by
  unfold TtuTargetsSat
  unfold NoLeafSubjects schemaRewritesL at h
  intro r hr tr hk
  exact h r (List.mem_append_left _ hr) tr
    (by rw [ttuTargets_of_kind hk]; exact List.Mem.head _)

/-- **The `LeafNode` half of the widened write-leg subject obligation, on the
    `rewriteClosure` chain** (4c-ii step 5 / the D3 pre-widen).

    The three `hsubj : ∀ u ∈ rewriteClosure S t, ¬ DerNode S (subjNode u.subject)`
    obligations (here at `reachedByW3d_shadow`, and twice in
    `CascadeStrataSettle.lean::reachedByW3d2_shadow` / `::reachedByW3d2_shadow_d`) are
    quantified over the rewrite CLOSURE, whose subject predicate is **not BARE in general**:
    `ReconcileCorrect.lean::rewriteStep`'s `.ttu tr` branch overwrites it with the rule's
    target. So `Leaf.lean::bare_subjNode_not_leafNode` — which discharges the RAW-write
    sites (`CascadeStrataSettle.lean::reachedByW3d2_shadow_d`'s derived branch, via
    `StoreValidRulesD`'s bare-subject conjunct) — does not reach them, and the
    `LeafNode` half needs `Leaf.lean::NotLeafName` transported along the closure by
    `ReconcileCorrect.lean::rewriteClosure_subject_pred_gen`.

    ⚠ **`hQ` HAS an owner; `hbase` does not — and the three call sites still supply
    neither.** Corrected 2026-08-31; this paragraph previously read *"`LeafRules.lean::
    NoLeafSubjects` is the same discipline on the OTHER rule list (`schemaRewritesL`, the
    leaf-routed chain) and does not discharge these"*, which is **false**.
    `LeafRules.lean::schemaRewritesL` is not another list: it is
    `schemaRewrites S ++ leafRewrites S`, a SUPERSET of the very list `TtuTargetsSat`
    ranges over. So `NoLeafSubjects S` **does** discharge `hQ`, by
    `ttuTargetsSat_notLeafName_of_noLeafSubjects` above. (Prose fix recorded at
    `formal/history/PROOF_STATUS.md` `## Session 2026-08-31` §4; this is the source-side
    half of it.)

    What is genuinely unowned at the three sites is the **seed side**, `hbase`: nothing in
    scope there constrains a *stored* subject predicate's name shape. `NoTtuTarget S R`
    (all `hterm` supplies) constrains TTU targets by `≠ R`, not by shape; `WF` constrains
    DECLARED relation keys while a TTU target is a referenced string inside an `Expr`; and
    `NodupKeys` / `StoreValidRules` / `StoreValidRulesD` / `BareStarStore` say nothing about
    it either. **Neither premise is available at any of those three sites today** — the
    bridge above supplies a *route* to `hQ` from a hypothesis nothing currently carries,
    which is a smaller gap than the one this docstring used to claim, but still a gap. -/
theorem rewriteClosure_subject_not_leafNode {S : Schema} {t u : Tuple}
    (hQ : TtuTargetsSat S NotLeafName) (hbase : NotLeafName t.subject.predicate)
    (hu : u ∈ rewriteClosure S t) : ¬ LeafNode S (subjNode u.subject) :=
  not_leafNode_of_notLeafName
    (by rw [subjNode_pred]; exact rewriteClosure_subject_pred_gen hQ hbase hu)

/-! #### Applicability — the bridge is instantiated at a witness that HAS a TTU rule

Anti-vacuity, per `docs/sabotage-procedure.md` §"a check that PARSES before it compares":
a bridge INTO a `∀ r ∈ …, ∀ tr, r.kind = .ttu tr → …` is trivially true at any schema whose
untainted rule list carries no `.ttu` rule at all, so proving it and stopping would certify
nothing about the `.ttu` branch — the only branch either premise constrains.

The floor is `LeafRules.lean::snlBoth_untainted_layer_ttu`, which pins
`schemaRewrites SnlBoth = [⟨"doc", "parent", "editor", .ttu "viewer"⟩]` **by `decide`** — a
measured, derived minimum (the list has exactly one rule, and its kind is `.ttu`), not a
guessed one. The witness is reused rather than minted: `LeafRuleWitness.SnlBoth` already
carries a TTU rule in *both* layers and is controlled there by two per-layer refutations
(`::noLeafSubjects_false_leafLayer` / `::noLeafSubjects_false_untLayer`). -/

/-- The bridge, applied. `SnlBoth`'s untainted layer is a one-element list holding a `.ttu`
    rule (`LeafRules.lean::snlBoth_untainted_layer_ttu`), so this is not the
    empty-quantifier instance. -/
theorem ttuTargetsSat_notLeafName_snlBoth :
    TtuTargetsSat LeafRuleWitness.SnlBoth NotLeafName :=
  ttuTargetsSat_notLeafName_of_noLeafSubjects LeafRuleWitness.noLeafSubjects_snlBoth

/-- The extra the UNTAINTED TTU rule mints on `LeafRuleWitness.tnlParent` really is in the
    `rewriteClosure` that `rewriteClosure_subject_not_leafNode` quantifies over — the
    non-vacuity denominator for the applied conclusion below. Its subject predicate is
    `viewer`, REWRITTEN from the seed's `BARE` (`LeafRules.lean::tnlParent_subject_bare`),
    so the `.ttu` branch of `ReconcileCorrect.lean::rewriteStep_subject_pred_gen` — the one
    branch `TtuTargetsSat` constrains — is the branch that fires. -/
theorem snlBoth_rewriteClosure_ttu_extra :
    (⟨⟨"folder", "f1", "viewer"⟩, "editor", ⟨"doc", "d1"⟩⟩ : Tuple)
      ∈ rewriteClosure LeafRuleWitness.SnlBoth LeafRuleWitness.tnlParent := by decide

/-- **The applied conclusion, derived THROUGH the bridge and through
    `rewriteClosure_subject_not_leafNode`** — never `decide`d directly, because deciding the
    conclusion alone would say nothing about whether either lemma applies. -/
theorem rewriteClosure_subject_not_leafNode_snlBoth :
    ¬ LeafNode LeafRuleWitness.SnlBoth (subjNode ⟨"folder", "f1", "viewer"⟩) :=
  rewriteClosure_subject_not_leafNode ttuTargetsSat_notLeafName_snlBoth
    (t := LeafRuleWitness.tnlParent)
    (show NotLeafName LeafRuleWitness.tnlParent.subject.predicate from
      Or.inl LeafRuleWitness.tnlParent_subject_bare)
    snlBoth_rewriteClosure_ttu_extra

/-! ### The SEED side — an owner for `hbase` (4c-ii step 9)

`rewriteClosure_subject_not_leafNode` takes two premises. `hQ` is owned above
(`ttuTargetsSat_notLeafName_of_noLeafSubjects`); this section owns `hbase`, which the
docstring there records as unowned at all three `rewriteClosure` sites.

**The design call is the user's, 2026-09-02** (`formal/history/PROOF_STATUS.md
## Session 2026-09-02`): thread the premise AND discharge it from admission, rather than
leave it free-floating on downstream statements. The discharge is the content here, and it
is worth naming what it rests on. A stored tuple's subject predicate is **not free** — it
is PINNED by the restriction that admitted the tuple: `Spec/Semantics.lean::
restrictionMatches`' second conjunct is literally `tup.subject.predicate == r.2.1`. So
*"no stored subject is a leaf name"* reduces to *"no declared restriction NAMES a leaf
name"*, a schema fact, and that is exactly what Python enforces —
`zanzibar_utils_v1.py::_validate_ast_references` (`:916-919`) refuses `'.'` in any
referenced relation name, and a restriction's predicate component is either `BARE` or such
a name. It is step 7's dot-lock (`ComputedRefsNotLeaf`) read at the OTHER syntactic
position, which is why this is faithful modelling and not a new scope restriction.

⚠ **Nuance against the docstring above**, which says `StoreValidRulesD` "says nothing
about" the seed predicate. That is INCOMPLETE rather than wrong, and the difference is this
section: `StoreValidRulesD` *does* pin the predicate to some restriction's, but until now
nothing constrained that restriction's NAME SHAPE, so the pin bottomed out in an
unconstrained string. `DirectRestrictionsNotLeaf` is the missing half; neither premise
discharges `hbase` alone.
-/

/-- **`NoLeafStoreSubjects T`** — no stored tuple's subject predicate is a minted leaf
    name. Stated as a plain `∀ t ∈ T, …` exactly like `BareStarCorrect.lean::BareStarStore`
    and `ReconcileCorrect.lean::NoStoreSubjectR`, so it weakens along a cons the same way
    the `write` case of every `reachedBy*_shadow` induction needs. -/
def NoLeafStoreSubjects (T : Store) : Prop :=
  ∀ t ∈ T, NotLeafName t.subject.predicate

theorem NoLeafStoreSubjects.tail {t : Tuple} {T : Store}
    (h : NoLeafStoreSubjects (t :: T)) : NoLeafStoreSubjects T :=
  fun t' ht' => h t' (List.mem_cons_of_mem _ ht')

theorem NoLeafStoreSubjects.head {t : Tuple} {T : Store}
    (h : NoLeafStoreSubjects (t :: T)) : NotLeafName t.subject.predicate :=
  h t List.mem_cons_self

/-- **`DirectRestrictionsNotLeaf S`** — no `Direct` restriction anywhere in the schema
    names a leaf-named subject predicate.

    Quantified over `exprDirectsAll`, NOT `exprDirects`, and the difference is load-bearing:
    `exprDirects` returns `[]` under `inter`/`excl`, so the narrower form would leave the
    DERIVED disjunct of `StoreValidRulesD` — the one that admits a stored tuple on
    `can_view: [user] but not blocked` — completely unguarded. Pinned by
    `directRestrictionsNotLeaf_false_sdrBadDerived` below.

    Bounded quantifiers throughout, on the same purpose as `LeafRules.lean::NoLeafSubjects`:
    it makes the predicate `by decide`-able at a concrete schema, so the witnesses below are
    machine-checked pins rather than hand proofs. -/
def DirectRestrictionsNotLeaf (S : Schema) : Prop :=
  ∀ d ∈ S.defs, ∀ rs ∈ exprDirectsAll d.2, ∀ r ∈ rs, NotLeafName r.2.1

instance (S : Schema) : Decidable (DirectRestrictionsNotLeaf S) :=
  inferInstanceAs (Decidable (∀ d ∈ S.defs, ∀ rs ∈ exprDirectsAll d.2, ∀ r ∈ rs,
    NotLeafName r.2.1))

/-- `exprDirects` is a sublist-wise subset of `exprDirectsAll` (the latter also recurses
    into `inter`/`excl`), so a `DirectRestrictionsNotLeaf` covers the narrow enumeration
    that `StoreValidRules` and the untainted disjunct of `StoreValidRulesD` use. -/
theorem mem_exprDirectsAll_of_mem_exprDirects :
    ∀ {e : Expr} {rs : List Restriction}, rs ∈ exprDirects e → rs ∈ exprDirectsAll e := by
  intro e
  induction e with
  | direct _ => intro rs h; exact h
  | computed _ => intro rs h; simp [exprDirects] at h
  | ttu _ _ => intro rs h; simp [exprDirects] at h
  | inter _ _ _ _ => intro rs h; simp [exprDirects] at h
  | excl _ _ _ _ => intro rs h; simp [exprDirects] at h
  | union a b iha ihb =>
      intro rs h
      simp only [exprDirects, List.mem_append] at h
      simp only [exprDirectsAll, List.mem_append]
      exact h.imp iha ihb

/-- **The pin step.** A matched restriction fixes the subject predicate to its own
    predicate component, so a name-shape fact about restrictions transfers to the tuple. -/
theorem notLeafName_of_restrictionMatches {rs : List Restriction} {t : Tuple}
    (hr : ∀ r ∈ rs, NotLeafName r.2.1) (h : restrictionMatches rs t = true) :
    NotLeafName t.subject.predicate := by
  unfold restrictionMatches at h
  rw [List.any_eq_true] at h
  obtain ⟨r, hmem, hcond⟩ := h
  simp only [Bool.and_eq_true, beq_iff_eq] at hcond
  rw [hcond.1.2]
  exact hr r hmem

/-- **The discharge, narrow admission** — `NoLeafStoreSubjects` is a CONSEQUENCE of write
    admission plus the schema's dot-lock, never an extra scope restriction. -/
theorem noLeafStoreSubjects_of_storeValidRules {S : Schema} {T : Store}
    (hd : DirectRestrictionsNotLeaf S) (hSV : StoreValidRules S T) :
    NoLeafStoreSubjects T := by
  intro t ht
  obtain ⟨e, rs, hlk, hrs, hm⟩ := hSV t ht
  exact notLeafName_of_restrictionMatches
    (fun r hr => hd _ (mem_defs_of_lookup hlk) rs
      (mem_exprDirectsAll_of_mem_exprDirects hrs) r hr) hm

/-- **The discharge, widened admission** (`StoreValidRulesD`, the form `GraphAdmission.
    storeValid` actually carries). The derived disjunct needs no schema premise at all: it
    already requires a BARE subject, which is `NotLeafName`'s left disjunct outright. -/
theorem noLeafStoreSubjects_of_storeValidRulesD {S : Schema} {T : Store}
    (hd : DirectRestrictionsNotLeaf S) (hSV : StoreValidRulesD S T) :
    NoLeafStoreSubjects T := by
  intro t ht
  rcases hSV t ht with ⟨_, e, rs, hlk, hrs, hm⟩ | ⟨_, hbare, _⟩
  · exact notLeafName_of_restrictionMatches
      (fun r hr => hd _ (mem_defs_of_lookup hlk) rs
        (mem_exprDirectsAll_of_mem_exprDirects hrs) r hr) hm
  · exact Or.inl hbare

/-! #### Non-vacuity — the pins, which for an INERT addition are the sole evidence

Nothing consumes the four declarations above yet (step 9's threading is the next
increment), so a green build vets none of them: `DirectRestrictionsNotLeaf` returning
`True` on every schema, or looking at the wrong component of a restriction, would compile
and audit exactly as cleanly (`docs/sabotage-procedure.md`, "a check that PARSES before it
compares"). Each pin below is chosen to redden under one specific plausible weakening.

`LeafRuleWitness.SnlBoth` is deliberately NOT reused as the positive witness: every one of
its `Direct` restrictions is `BARE`, so it would satisfy `DirectRestrictionsNotLeaf` via
`NotLeafName`'s left disjunct without ever testing a referenced relation name — the
all-`BARE` triviality.

## ★ CONTROLLED — two sabotages, run 2026-09-02 (`docs/sabotage-procedure.md`)

Both were run against the green tree (`Build completed successfully (1089 jobs). rc=0`,
first attempt) and both fired attributably.

**S1 — the quantifier is narrowed from `exprDirectsAll` to `exprDirects`** (in the `def`
and its `Decidable` instance, nothing else). This is the narrowest *plausible* weakening:
it is what someone would write who had only read `StoreValidRules`, and it is silent at
every other pin here. Literal output, `rc=1`:

```text
error: ZanzibarProofs/GraphIndex/CascadeStable.lean:1095:52: Tactic `decide` proved that the proposition
  ¬DirectRestrictionsNotLeaf SdrBadDerived
is false
```

Exactly the discriminating pin, and only it among the `decide` pins —
`directRestrictionsNotLeaf_false_sdrBadLeaf` stayed green, which is what makes the pair
*discriminating* rather than merely red. (Two further errors at `:1028`/`:1040` are the two
discharge lemmas' `mem_exprDirectsAll_of_mem_exprDirects` conversions becoming
ill-typed — attributable, and evidence that the bridges really do depend on the widened
enumeration.)

**S2 — the predicate reads the wrong component of a restriction** (`NotLeafName r.2.1` →
`NotLeafName r.1`, i.e. the subject TYPE instead of the subject PREDICATE). Literal
output, `rc=1`:

```text
error: ZanzibarProofs/GraphIndex/CascadeStable.lean:1082:49: Tactic `decide` proved that the proposition
  ¬DirectRestrictionsNotLeaf SdrBadLeaf
is false
error: ZanzibarProofs/GraphIndex/CascadeStable.lean:1095:52: Tactic `decide` proved that the proposition
  ¬DirectRestrictionsNotLeaf SdrBadDerived
is false
```

⚠ **What neither sabotage vets** — that `NotLeafName` is the right predicate *shape*. It is
not `relNameOK` ("dot-free"), and the difference is not cosmetic: `BARE = "..."`
(`Core/Ident.lean:20`) is itself dot-carrying and `isLeafPred` is a bare dot test
(`Leaf.lean:196`, `::isLeafPred_bare`), so a `relNameOK`-shaped clause would be **FALSE at
every `GraphAdmission` witness schema** — whose `Direct` restrictions are all
`("user", BARE, _)` — and would therefore re-vacuate the headline theorems rather than
narrow them. `NotLeafName`'s BARE escape is load-bearing, and it mirrors Python's own
`name != '...'` escape in `_validate_ast_references`. -/

namespace DirRestrWitness

/-- Carries a USERSET restriction (`[group#member]`), so the positive pin tests
    `NotLeafName` at a real referenced relation name rather than at `BARE`. -/
def SdrUserset : Schema :=
  ⟨[(("doc", "viewer"), .direct [("user", BARE, false), ("group", "member", false)]),
    (("group", "member"), .direct [("user", BARE, false)])], []⟩

theorem directRestrictionsNotLeaf_sdrUserset :
    DirectRestrictionsNotLeaf SdrUserset := by decide

/-- …and the witness is non-trivial in the direction that matters: it really does carry a
    non-`BARE` restriction predicate, so the pin above is not the all-`BARE` case. -/
theorem sdrUserset_has_userset_restriction :
    (("group", "member", false) : Restriction) ∈
      (exprDirectsAll (.direct [("user", BARE, false), ("group", "member", false)] : Expr)).flatten
    := by decide

/-- **REFUTATION 1 — the predicate component.** One restriction predicate replaced by a
    minted leaf name on an UNTAINTED def. Reddens iff `DirectRestrictionsNotLeaf` stops
    reading `r.2.1`, or `NotLeafName` stops rejecting a dotted name. -/
def SdrBadLeaf : Schema :=
  ⟨[(("doc", "viewer"), .direct [("user", BARE, false), ("group", "viewer.0", false)]),
    (("group", "member"), .direct [("user", BARE, false)])], []⟩

theorem directRestrictionsNotLeaf_false_sdrBadLeaf :
    ¬ DirectRestrictionsNotLeaf SdrBadLeaf := by decide

/-- **REFUTATION 2 — the `exprDirectsAll` choice.** The leaf-named restriction sits inside
    an `excl` arm, where `exprDirects` returns `[]` and only `exprDirectsAll` reaches.
    Reddens iff the quantifier is narrowed to `exprDirects` — the narrowing that would
    leave `StoreValidRulesD`'s derived disjunct unguarded while every other pin here
    stayed green. -/
def SdrBadDerived : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "access"), .excl (.direct [("group", "viewer.0", false)])
      (.computed "banned"))], []⟩

theorem directRestrictionsNotLeaf_false_sdrBadDerived :
    ¬ DirectRestrictionsNotLeaf SdrBadDerived := by decide

/-- The companion that makes REFUTATION 2 discriminating rather than merely red: the same
    schema IS clean under the narrow enumeration, so the two pins differ exactly on the
    `exprDirects` / `exprDirectsAll` choice and on nothing else. -/
theorem sdrBadDerived_clean_under_exprDirects :
    ∀ d ∈ SdrBadDerived.defs, ∀ rs ∈ exprDirects d.2, ∀ r ∈ rs, NotLeafName r.2.1 := by
  decide

/-- A tuple admitted by `SdrUserset`'s userset arm, with a NON-bare subject predicate. -/
def tdrUserset : Tuple := ⟨⟨"group", "g1", "member"⟩, "viewer", ⟨"doc", "d1"⟩⟩

theorem tdrUserset_subject_not_bare : tdrUserset.subject.predicate ≠ BARE := by decide

theorem storeValidRules_sdrUserset : StoreValidRules SdrUserset [tdrUserset] := by
  intro t ht
  rw [List.mem_singleton] at ht
  subst ht
  refine ⟨.direct [("user", BARE, false), ("group", "member", false)],
          [("user", BARE, false), ("group", "member", false)], rfl, ?_, by decide⟩
  simp [exprDirects]

/-- **The discharge, APPLIED** — derived THROUGH `noLeafStoreSubjects_of_storeValidRules`
    and never `decide`d directly, so it certifies that the bridge APPLIES rather than that
    its conclusion happens to hold at this store. Together with
    `tdrUserset_subject_not_bare` it also certifies that the `restrictionMatches` route was
    the one taken, not `NotLeafName`'s BARE shortcut. -/
theorem noLeafStoreSubjects_sdrUserset : NoLeafStoreSubjects [tdrUserset] :=
  noLeafStoreSubjects_of_storeValidRules directRestrictionsNotLeaf_sdrUserset
    storeValidRules_sdrUserset

end DirRestrWitness

/-! ### T2 — a LEAF predicate is never a bridge SOURCE (`P6` step 3b, additive half)

**What this discharges.** `P6` step 3b widens the shadow's extras predicate with a
`BridgeNode` disjunct, and `ShadowOver.term` then owes three "no extra node is an edge
SOURCE" obligations. The SECOND of them (T2) is: no `Leaf.lean::LeafNode` is bridged in,
i.e. at a leaf predicate `p` the bridge test `UsStarWrite.lean::
Schema.isSubjectWildcardUserset ty p` is `false`. **The widening itself is NOT landed here**
— this section is deliberately additive: every definition it mentions already exists, so the
lemma is provable and committable GREEN, ahead of the red re-point run.

**The route, and why it needs FOUR supports rather than the one the plan body priced.**
`isSubjectWildcardUserset` is an outer `p != BARE` guard over a DISJUNCTION, and the guard
is useless here (a leaf name is not `BARE`), so both disjuncts must die separately, from two
DIFFERENT hypotheses `reachedByW3d_shadow` already binds:
  (a) the literal `[ty:*#p]` restriction is killed by `DirectRestrictionsNotLeaf S` — but
      that premise quantifies over `exprDirectsAll` while the disjunct is a membership in
      `exprRestrictions`, and only the CONVERSE flattening existed
      (`ReconcileStarsComplete.lean::mem_exprRestrictions_of_directsAll`). The forward
      direction is `::mem_exprDirectsAll_of_mem_exprRestrictions`, landed with it.
  (b) `isStarTuplesetThrough` is killed by `TtuTargetsSat S NotLeafName` — but that premise
      ranges over `schemaRewrites`, which DROPS every derived def, while the disjunct scans
      `exprTtus` over ALL of `S.defs`. The gap splits in two and needs three more lemmas:
      at a DERIVED def the ComputedOnly-at-derived premise empties the scan
      (`ReconcileCorrect.lean::exprTtus_computedOnly`); at an UNTAINTED def the def is
      boolean-free (`RestrictBase.lean::containsBool_of_mem_defs_untainted`) so its TTU
      nodes really are rewrite arms (`RulesWrite.lean::mem_exprArms_of_mem_exprTtus` — FALSE
      without boolean-freeness, see its own note) which really are schema rewrites
      (`RulesWrite.lean::mem_schemaRewrites_of_mem_exprArms`).
⚠ The precedent the plan body cited for (b), `ReconcileCorrect.lean::
rewriteStep_subject_pred_gen`, is the wrong shape and does not transfer: it CONSUMES
`TtuTargetsSat` across a `rewriteStep` membership and maps nothing out of `exprTtus`.

**No new `LeafScope` / `GraphAdmission` field is needed** — `hNK`, `hCO`, `hQ` and `hDR`
below are hypotheses 1, 2, 5 and 6 of `reachedByW3d_shadow` verbatim. -/

/-- ★ **The TTU-FREE form, and the one the `_d` chain needs** (`P6` step 3b step 8,
    2026-09-14). The argument below never used `ComputedOnly` for anything except "a derived
    def has no TTU node"; stating that directly lets BOTH shadow chains use one lemma —
    `reachedByW3d2_shadow_d` carries `ComputedOrDirect`, which is equally TTU-free
    (`ReconcileCorrect.lean::exprTtus_computedOrDirect`). The `ComputedOnly` form below is
    kept as a wrapper so its existing consumers do not move. -/
theorem isSubjectWildcardUserset_false_of_ttuFree {S : Schema} {ty p : String}
    (hNK : NodupKeys S)
    (hTF : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → exprTtus e = [])
    (hQ : TtuTargetsSat S NotLeafName)
    (hDR : DirectRestrictionsNotLeaf S)
    (hleaf : ¬ NotLeafName p) :
    S.isSubjectWildcardUserset ty p = false := by
  have hA : S.defs.any (fun d => (exprRestrictions d.2).contains (ty, p, true)) = false := by
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    simp only [List.any_eq_true] at hcon
    obtain ⟨d, hd, hmem⟩ := hcon
    rw [List.contains_eq_mem] at hmem
    obtain ⟨rs, hrs, hr⟩ :=
      mem_exprDirectsAll_of_mem_exprRestrictions (of_decide_eq_true hmem)
    exact hleaf (hDR d hd rs hrs (ty, p, true) hr)
  have hB : S.isStarTuplesetThrough ty p = false := by
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    unfold Schema.isStarTuplesetThrough at hcon
    simp only [List.any_eq_true] at hcon
    obtain ⟨d, hd, tt, htt, hcond⟩ := hcon
    rw [Bool.and_eq_true, beq_iff_eq] at hcond
    have htr : tt.1 = p := hcond.1
    cases hder : isDerived S d.1 with
    | true =>
      rw [hTF d.1.1 d.1.2 d.2 (lookup_of_mem hNK hd) hder] at htt
      simp at htt
    | false =>
      have htt' : (tt.1, tt.2) ∈ exprTtus d.2 := htt
      have hrule : (⟨d.1.1, tt.2, d.1.2, RuleKind.ttu tt.1⟩ : RRule) ∈ schemaRewrites S :=
        mem_schemaRewrites_of_mem_exprArms hd hder
          (mem_exprArms_of_mem_exprTtus
            (containsBool_of_mem_defs_untainted hNK hd hder) htt')
      exact hleaf (htr ▸ hQ _ hrule tt.1 rfl)
  simp only [Schema.isSubjectWildcardUserset, hA, hB, Bool.or_self, Bool.and_false]


/-- **T2, the payoff.** At a LEAF predicate — `¬ NotLeafName p`, i.e. `p ≠ BARE` and `p`
    carries a `'.'` — no subject-wildcard userset shape is declared, so nothing of that
    shape is ever bridged in.

    The hypothesis list is what the proof actually consumes, and all four are already bound
    (in this order, as premises 1 / 2 / 5 / 6) by `reachedByW3d_shadow` and by both
    `CascadeStrataSettle.lean` W3d-2 twins, so threading this costs those theorems NO new
    binder. `NodupKeys` is needed twice — it is what makes `S.lookup d.1` return THIS def's
    body, for `hCO` and for the boolean-freeness step.

    Non-vacuity is pinned below (`LeafBridgeWitness`), and it matters: `LeafRules.lean::
    lrV_untainted_layer_silent` proves `schemaRewrites SlV = []`, so `hQ` discharges
    VACUOUSLY at that fixture and `SlV` cannot serve as the witness. -/
theorem isSubjectWildcardUserset_false_of_notLeafName {S : Schema} {ty p : String}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hQ : TtuTargetsSat S NotLeafName)
    (hDR : DirectRestrictionsNotLeaf S)
    (hleaf : ¬ NotLeafName p) :
    S.isSubjectWildcardUserset ty p = false := by
  -- disjunct (a): a literal `[ty:*#p]` restriction, refuted by `DirectRestrictionsNotLeaf`
  have hA : S.defs.any (fun d => (exprRestrictions d.2).contains (ty, p, true)) = false := by
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    simp only [List.any_eq_true] at hcon
    obtain ⟨d, hd, hmem⟩ := hcon
    rw [List.contains_eq_mem] at hmem
    obtain ⟨rs, hrs, hr⟩ :=
      mem_exprDirectsAll_of_mem_exprRestrictions (of_decide_eq_true hmem)
    exact hleaf (hDR d hd rs hrs (ty, p, true) hr)
  -- disjunct (b): a star-tupleset TTU through-shape, refuted by `TtuTargetsSat`
  have hB : S.isStarTuplesetThrough ty p = false := by
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    unfold Schema.isStarTuplesetThrough at hcon
    simp only [List.any_eq_true] at hcon
    obtain ⟨d, hd, tt, htt, hcond⟩ := hcon
    rw [Bool.and_eq_true, beq_iff_eq] at hcond
    have htr : tt.1 = p := hcond.1
    cases hder : isDerived S d.1 with
    | true =>
      -- a derived def is `ComputedOnly`, and a `ComputedOnly` tree has no TTU node at all
      rw [exprTtus_computedOnly (hCO d.1.1 d.1.2 d.2 (lookup_of_mem hNK hd) hder)] at htt
      simp at htt
    | false =>
      -- an untainted def is boolean-free, so its TTU node IS a schema rewrite rule
      have htt' : (tt.1, tt.2) ∈ exprTtus d.2 := htt
      have hrule : (⟨d.1.1, tt.2, d.1.2, RuleKind.ttu tt.1⟩ : RRule) ∈ schemaRewrites S :=
        mem_schemaRewrites_of_mem_exprArms hd hder
          (mem_exprArms_of_mem_exprTtus
            (containsBool_of_mem_defs_untainted hNK hd hder) htt')
      exact hleaf (htr ▸ hQ _ hrule tt.1 rfl)
  simp only [Schema.isSubjectWildcardUserset, hA, hB, Bool.or_self, Bool.and_false]

/-- **T2 as `ShadowOver.term` will consume it**: a `LeafNode` of `S` is not a bridged-in
    concrete node of any state carrying `S`, so it sources no bridge edge. Routed through
    `Leaf.lean::not_leafNode_of_notLeafName` (contrapositive), never re-derived. -/
theorem not_bridgedInConcrete_of_leafNode {S : Schema} {σ : GraphState} {k : NodeKey}
    (hsc : σ.schema = S)
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hQ : TtuTargetsSat S NotLeafName)
    (hDR : DirectRestrictionsNotLeaf S)
    (hk : LeafNode S k) :
    σ.bridgedInConcrete k = false := by
  have hnl : ¬ NotLeafName k.pred := fun h => not_leafNode_of_notLeafName h hk
  unfold GraphState.bridgedInConcrete
  rw [hsc, isSubjectWildcardUserset_false_of_notLeafName hNK hCO hQ hDR hnl]
  exact Bool.and_false _

/-! #### Non-vacuity — the pin the recon sweep demanded, and the fixture it ruled out

★ **A vacuous T2 is worse than no T2.** Two verifiers disagreed about whether the lemma
above does any work at the tree's existing leaf fixture `SlV`, and the reconciliation was
that BOTH are right about different questions: T2 is *sound* there, and its `hQ` premise is
*vacuous* there, because `LeafRules.lean::lrV_untainted_layer_silent` proves
`schemaRewrites SlV = []` by `decide` — so ANY `∀ r ∈ schemaRewrites S` premise discharges
for free and `SlV` cannot be the witness. Hence this fixture, following
`LeafRules.lean::wf_does_not_give_keysNonempty`.

`Snv` is built so that **every premise is non-vacuous and every disjunct of the conclusion is
live**:
  * `hQ` — `schemaRewrites Snv` is a ONE-rule list carrying a real `RuleKind.ttu`
    (`snv_schemaRewrites`), so the premise is a constraint, not an empty quantifier.
  * `hDR` — the schema carries a non-`BARE` restriction predicate (`snv_hDR_is_not_vacuous`),
    so the premise is tested at a referenced relation name and not only via `NotLeafName`'s
    `BARE` escape — the all-`BARE` triviality `DirRestrWitness` already documents.
  * `hCO` — there IS a derived key (`snv_hCO_is_not_vacuous`), so the ComputedOnly-at-derived
    premise has a non-empty domain.
  * the CONCLUSION is not constantly `false` on this schema: `isSubjectWildcardUserset`
    returns `true` here at a non-leaf predicate through disjunct (a)
    (`snv_bridges_a_non_leaf_pred`) AND disjunct (b) is live too
    (`snv_through_shape_is_live`). So `snv_leaf_pred_is_not_a_bridge_source` is a fact ABOUT
    the leaf predicate, not about a schema that bridges nothing.

**The two controls are what make it discriminating.** Each perturbs exactly one premise and
flips the conclusion at the SAME leaf predicate `"editor.0"`, so neither disjunct can be
claimed to be dead weight:
  * `SnvLeafDirect` adds a literal `[user:*#editor.0]` — `hDR` goes FALSE, `hQ` still holds,
    and the conclusion goes TRUE through disjunct (a).
  * `SnvLeafTtu` renames the TTU target to `"editor.0"` — `hQ` goes FALSE, `hDR` still
    holds, and the conclusion goes TRUE through disjunct (b). -/

namespace LeafBridgeWitness

/-- `folder#viewer: [user, group:*#member]` · `doc#parent: [folder, folder:*]` ·
    `doc#viewer: [user] or viewer from parent` · `doc#editor: viewer but not banned`.

    The `excl` def makes `("doc","editor")` the one DERIVED key (so `hCO` has a domain and
    `"editor.0"` is a plausible minted leaf name of a real derived family); the `[folder:*]`
    restriction under a TTU tupleset makes the through-shape disjunct live; the
    `[group:*#member]` restriction makes the literal disjunct live at a NON-leaf predicate. -/
def Snv : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false), ("group", "member", true)]),
    (("group", "member"),  .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent")),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "editor"),    .excl (.computed "viewer") (.computed "banned"))], []⟩

-- (`NodupKeys` is a plain `def`, so instance search will not unfold it for `decide`.)
theorem snv_nodupKeys : NodupKeys Snv := by unfold NodupKeys; decide

theorem snv_directRestrictionsNotLeaf : DirectRestrictionsNotLeaf Snv := by decide

/-- `hQ`'s quantifier is NON-EMPTY here — this is the exact fact `SlV` fails. -/
theorem snv_schemaRewrites :
    schemaRewrites Snv = [⟨"doc", "parent", "viewer", RuleKind.ttu "viewer"⟩] := by decide

theorem snv_ttuTargetsSat : TtuTargetsSat Snv NotLeafName := by
  intro r hr tr hkind
  rw [snv_schemaRewrites, List.mem_singleton] at hr
  subst hr
  have heq : RuleKind.ttu "viewer" = RuleKind.ttu tr := hkind
  injection heq with h
  subst h
  exact Or.inr (by decide)

theorem snv_taintedKeys : taintedKeys Snv = [("doc", "editor")] := by decide

theorem snv_computedOnly :
    ∀ dt R e, Snv.lookup (dt, R) = some e → isDerived Snv (dt, R) = true → ComputedOnly e := by
  intro dt R e hlk hder
  have hk : (dt, R) ∈ taintedKeys Snv := by
    unfold isDerived at hder
    rw [List.contains_eq_mem] at hder
    exact of_decide_eq_true hder
  rw [snv_taintedKeys, List.mem_singleton] at hk
  rw [hk] at hlk
  have hval : Snv.lookup ("doc", "editor")
      = some (Expr.excl (.computed "viewer") (.computed "banned")) := by decide
  rw [hval] at hlk
  injection hlk with he
  subst he
  exact ⟨trivial, trivial⟩

/-- **THE PIN.** Derived THROUGH the lemma and never `decide`d directly, so it certifies
    that T2 APPLIES at a schema where all four premises are live — not merely that its
    conclusion happens to hold. -/
theorem snv_leaf_pred_is_not_a_bridge_source :
    Snv.isSubjectWildcardUserset "doc" "editor.0" = false :=
  isSubjectWildcardUserset_false_of_notLeafName snv_nodupKeys snv_computedOnly
    snv_ttuTargetsSat snv_directRestrictionsNotLeaf (by decide)

theorem snv_hCO_is_not_vacuous : isDerived Snv ("doc", "editor") = true := by decide

/-- ★ **The JOINT witness, and it is the one the battery above was missing** (added
    2026-09-13g, after an audit found the gap). `not_bridgedInConcrete_of_leafNode` is the
    form `ShadowOver.term` will actually consume, and it needs a `LeafNode` AND the four
    premises **at the same schema**. Everything else here pins the premises at `Snv` while
    the tree's only `LeafNode` pins live at `Sw` — so the composed lemma had no witness of
    its own and could have been vacuously true at every schema in the development. It is
    not: `Snv` carries one. Routed through the PROVED decider (`Leaf.lean::leafNodeB_correct`)
    rather than asserting the `Prop` directly, per this namespace's own convention. -/
theorem snv_has_a_leafNode :
    LeafNode Snv (objNode ⟨"doc", "d1"⟩ (leafPred "editor" 0)) :=
  (leafNodeB_correct Snv _).mp (by decide)

theorem snv_hDR_is_not_vacuous :
    ∃ d ∈ Snv.defs, ∃ rs ∈ exprDirectsAll d.2,
      (("group", "member", true) : Restriction) ∈ rs := by decide

/-- The conclusion is doing work: the SAME function returns `true` on this schema at a
    non-leaf predicate, through disjunct (a). -/
theorem snv_bridges_a_non_leaf_pred :
    Snv.isSubjectWildcardUserset "group" "member" = true := by decide

/-- …and disjunct (b) is live here too, so neither arm of the proof is scanning a dead set. -/
theorem snv_through_shape_is_live :
    Snv.isStarTuplesetThrough "folder" "viewer" = true := by decide

/-- **CONTROL A — `hDR` is load-bearing.** `Snv` plus a literal `[user:*#editor.0]`. -/
def SnvLeafDirect : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false), ("group", "member", true),
        ("user", "editor.0", true)]),
    (("group", "member"),  .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent")),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "editor"),    .excl (.computed "viewer") (.computed "banned"))], []⟩

theorem snvLeafDirect_breaks_hDR : ¬ DirectRestrictionsNotLeaf SnvLeafDirect := by decide

theorem snvLeafDirect_schemaRewrites :
    schemaRewrites SnvLeafDirect = [⟨"doc", "parent", "viewer", RuleKind.ttu "viewer"⟩] := by
  decide

/-- …and ONLY `hDR` breaks: `hQ` is untouched, which is what makes the control attributable
    to disjunct (a) rather than to "the schema got worse". -/
theorem snvLeafDirect_keeps_hQ : TtuTargetsSat SnvLeafDirect NotLeafName := by
  intro r hr tr hkind
  rw [snvLeafDirect_schemaRewrites, List.mem_singleton] at hr
  subst hr
  have heq : RuleKind.ttu "viewer" = RuleKind.ttu tr := hkind
  injection heq with h
  subst h
  exact Or.inr (by decide)

theorem snvLeafDirect_bridges_the_leaf_pred :
    SnvLeafDirect.isSubjectWildcardUserset "user" "editor.0" = true := by decide

/-- **CONTROL B — `hQ` is load-bearing.** `Snv` with the TTU target renamed to the leaf
    name, so the through-shape disjunct fires at `"editor.0"`. -/
def SnvLeafTtu : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false), ("group", "member", true)]),
    (("group", "member"),  .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)])
                                  (.ttu "editor.0" "parent")),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "editor"),    .excl (.computed "viewer") (.computed "banned"))], []⟩

theorem snvLeafTtu_breaks_hQ : ¬ TtuTargetsSat SnvLeafTtu NotLeafName := by
  intro h
  exact absurd
    (h ⟨"doc", "parent", "viewer", RuleKind.ttu "editor.0"⟩ (by decide) "editor.0" rfl)
    (by decide)

/-- …and ONLY `hQ` breaks: `hDR` still holds, so the control is attributable to disjunct (b).
    Together with CONTROL A this is what proves BOTH disjuncts have to be killed — a proof
    that handled only one of them would be green at one of these two schemas. -/
theorem snvLeafTtu_keeps_hDR : DirectRestrictionsNotLeaf SnvLeafTtu := by decide

theorem snvLeafTtu_bridges_the_leaf_pred :
    SnvLeafTtu.isSubjectWildcardUserset "folder" "editor.0" = true := by decide

/-! ##### CONTROLLED — MUTATION SWEEP (2026-09-14), and the two refutations it forced

★ Per `docs/sabotage-procedure.md`. `docs/p6-step3b-plan-2026-09-13.md` §`C10` recorded
"no source-level sabotage rebuild of the T2 payoff was run" as OWED. It has now been run:
four mutations, one whole-tree `lake build` each, source restored byte-identical after
every one (`md5` re-checked against the pre-sweep snapshot; final restore rebuilt to
`Build completed successfully (1089 jobs).` with the warning count unchanged at 88).
Literal observed outcomes, reds attributed by `lake`'s own `file:line:col`:

| # | the mutation | what reddened |
|---|---|---|
| `M0` | INSTRUMENT CONTROL. `SnvLeafTtu`'s TTU target `"editor.0"` reverted to `"viewer"`, i.e. control B undone. Expected reds NAMED IN ADVANCE: `snvLeafTtu_breaks_hQ`, `snvLeafTtu_bridges_the_leaf_pred` | EXACTLY those two, and nothing else. `:1558` — ``Tactic `decide` proved that the proposition { objectType := "doc", matchRel := "parent", outRel := "viewer", kind := RuleKind.ttu "editor.0" } ∈ schemaRewrites SnvLeafTtu is false``; `:1567` — ``Tactic `decide` proved that the proposition SnvLeafTtu.isSubjectWildcardUserset "folder" "editor.0" = true is false``. `snvLeafTtu_keeps_hDR` stayed GREEN, so the red is attributable to the mutated premise and not to "the schema got worse" |
| `M1` | THE NAMED WEAKENING. The disjunct-(b) `have hB` block deleted from `isSubjectWildcardUserset_false_of_notLeafName` and the conclusion asserted from `hDR` (i.e. `hA`) alone | ONE error, on the lemma itself: `:1342:47: unsolved goals`, residual goal `⊢ (p != BARE && S.isStarTuplesetThrough ty p) = false` — literally the disjunct-(b) obligation, with `hQ` sitting unused in the context |
| `M2` | THE DUAL. The disjunct-(a) `have hA` block deleted, conclusion asserted from `hQ` (i.e. `hB`) alone | ONE error, same site: `:1342:47: unsolved goals`, residual goal `⊢ (p != BARE && S.defs.any fun d => (exprRestrictions d.2).contains (ty, p, true)) = false` |
| `M4` | THE PREMISE DROP. `(hQ : TtuTargetsSat S NotLeafName)` deleted from the STATEMENT | FOUR errors across THREE declarations: `:1373 Unknown identifier `hQ`` (the lemma), `:1386 unsolved goals` + `:1389 Application type mismatch … hQ has type TtuTargetsSat S NotLeafName but is expected to have type DirectRestrictionsNotLeaf S` (`not_bridgedInConcrete_of_leafNode`), and `:1484` the same mismatch on `snv_ttuTargetsSat` (`snv_leaf_pred_is_not_a_bridge_source`) |

⚠ **What `M1`/`M2` do NOT show, and it is the point of running them.** Each reddened
exactly ONE declaration — its own. `not_bridgedInConcrete_of_leafNode`,
`snv_leaf_pred_is_not_a_bridge_source` and every `SnvLeaf*` control stayed GREEN under a
lemma whose proof no longer closes, because Lean ERROR-RECOVERS a failed declaration at
its stated type. That is the `TK68` failure mode (`docs/sabotage-procedure.md`
§"A RED ON A HELPER LEMMA DOES NOT PROPAGATE") reproduced here: a proof-level weakening is
invisible downstream, a statement-level one (`M4`) is not. So the mutation establishes only
that THIS proof needs both branches — never that the weakened THEOREM is false.

**Hence the two theorems below, which are the durable form of `M1` and `M2`.** They state
that the `hQ`-free and `hDR`-free readings of `isSubjectWildcardUserset_false_of_notLeafName`
are FALSE, not merely unproven, by instantiating each at the control schema that keeps the
other premise. Nothing regenerates them and no error recovery can hide them; they are what
a future contributor's "surely one of these four is redundant" runs into. -/

theorem snvLeafDirect_nodupKeys : NodupKeys SnvLeafDirect := by unfold NodupKeys; decide

theorem snvLeafDirect_taintedKeys : taintedKeys SnvLeafDirect = [("doc", "editor")] := by decide

theorem snvLeafDirect_computedOnly :
    ∀ dt R e, SnvLeafDirect.lookup (dt, R) = some e →
      isDerived SnvLeafDirect (dt, R) = true → ComputedOnly e := by
  intro dt R e hlk hder
  have hk : (dt, R) ∈ taintedKeys SnvLeafDirect := by
    unfold isDerived at hder
    rw [List.contains_eq_mem] at hder
    exact of_decide_eq_true hder
  rw [snvLeafDirect_taintedKeys, List.mem_singleton] at hk
  rw [hk] at hlk
  have hval : SnvLeafDirect.lookup ("doc", "editor")
      = some (Expr.excl (.computed "viewer") (.computed "banned")) := by decide
  rw [hval] at hlk
  injection hlk with he
  subst he
  exact ⟨trivial, trivial⟩

theorem snvLeafTtu_nodupKeys : NodupKeys SnvLeafTtu := by unfold NodupKeys; decide

theorem snvLeafTtu_taintedKeys : taintedKeys SnvLeafTtu = [("doc", "editor")] := by decide

theorem snvLeafTtu_computedOnly :
    ∀ dt R e, SnvLeafTtu.lookup (dt, R) = some e →
      isDerived SnvLeafTtu (dt, R) = true → ComputedOnly e := by
  intro dt R e hlk hder
  have hk : (dt, R) ∈ taintedKeys SnvLeafTtu := by
    unfold isDerived at hder
    rw [List.contains_eq_mem] at hder
    exact of_decide_eq_true hder
  rw [snvLeafTtu_taintedKeys, List.mem_singleton] at hk
  rw [hk] at hlk
  have hval : SnvLeafTtu.lookup ("doc", "editor")
      = some (Expr.excl (.computed "viewer") (.computed "banned")) := by decide
  rw [hval] at hlk
  injection hlk with he
  subst he
  exact ⟨trivial, trivial⟩

/-- ★ **`M1` as a kernel fact.** Drop `hQ` from `isSubjectWildcardUserset_false_of_notLeafName`
    and the resulting statement is FALSE — `SnvLeafTtu` satisfies every remaining premise
    (`hNK`, `hCO`, `hDR` via `snvLeafTtu_keeps_hDR`) at the leaf predicate `"editor.0"`, and
    the conclusion fails there through disjunct (b) (`snvLeafTtu_bridges_the_leaf_pred`).
    Stated over an explicitly quantified `S` so it is a claim about the STATEMENT rather than
    about one application. -/
theorem hQ_free_statement_is_false :
    ¬ ∀ (S : Schema) (ty p : String),
        NodupKeys S →
        (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
        DirectRestrictionsNotLeaf S →
        ¬ NotLeafName p →
        S.isSubjectWildcardUserset ty p = false := by
  intro h
  have hfalse := h SnvLeafTtu "folder" "editor.0" snvLeafTtu_nodupKeys snvLeafTtu_computedOnly
    snvLeafTtu_keeps_hDR (by decide)
  rw [snvLeafTtu_bridges_the_leaf_pred] at hfalse
  exact Bool.noConfusion hfalse

/-- ★ **`M2` as a kernel fact**, the dual: drop `hDR` and the statement is FALSE at
    `SnvLeafDirect`, which keeps `hQ` (`snvLeafDirect_keeps_hQ`) and bridges the same leaf
    predicate through disjunct (a). Together with `hQ_free_statement_is_false` this is the
    machine-checked form of "both disjuncts must be killed, from two different premises". -/
theorem hDR_free_statement_is_false :
    ¬ ∀ (S : Schema) (ty p : String),
        NodupKeys S →
        (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
        TtuTargetsSat S NotLeafName →
        ¬ NotLeafName p →
        S.isSubjectWildcardUserset ty p = false := by
  intro h
  have hfalse := h SnvLeafDirect "user" "editor.0" snvLeafDirect_nodupKeys
    snvLeafDirect_computedOnly snvLeafDirect_keeps_hQ (by decide)
  rw [snvLeafDirect_bridges_the_leaf_pred] at hfalse
  exact Bool.noConfusion hfalse

end LeafBridgeWitness

/-! ### T3 — the L-closure STAR-BARE family (`P6` step 3b, additive half)

**What this discharges, and why `BareStarStore` alone does NOT.** `P6` step 3b widens the
shadow's extras predicate with a bridge-node disjunct, and `ShadowOver.term` then owes a
third obligation (T3): a bridge node `wAnyNode (ty, p)` sources no edge. The plan body
justified T3 from `FullScope.lean::W4Fragment.bareStar : BareStarStore T` — "every stored
STAR subject is BARE, and `isSubjectWildcardUserset _ BARE = false` by the outer
`p != BARE` guard". **That justification is REFUTED.** `BareStarStore`
(`BareStarCorrect.lean::BareStarStore`) quantifies over STORED tuples, while the
obligation is about members of `rewriteClosureL S (rawWriteTuples S t)` — the list the
re-pointed write leg folds — and the closure MANUFACTURES a non-BARE star subject:
`RulesWrite.lean::applyRRule`'s `ttu` arm preserves the subject NAME (so `STAR` survives)
and OVERWRITES the predicate with the TTU target, a declared relation name and hence not
`BARE`. The outer guard never fires and that member IS an edge source. The hazard is the
designed case, not a corner.

**The tree already pays this price for the PLAIN closure, and the engine is `private`.**
`RulesBareStar.lean::rewriteClosure_star_bare` exists for exactly this hazard and takes
`TtuTuplesetsDirect S`, `TtuStarFree S T` and `BareStarStore T`; its engine `StarSeed` /
`starSeed_step` is `private`, so an L version cannot reuse it. This section is the L twin,
re-minted. **Nothing is re-pointed, no existing statement moves and nothing is
de-privatised** — every definition mentioned here already exists, so the family lands
GREEN ahead of the red re-point run.

**Two premises the plain twin does not need, and one of them is the unbudgeted gap.**
  * `hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false` — free from
    `LeafRules.lean::LeafScope.matchNotLeaf`, premise 7 of `reachedByW3d_shadow`. It closes
    the two arms the L step adds over the plain one: on a DERIVED write `rawWriteTuples`
    re-addresses the seed onto `leafPred` names, and `leafRewrites` outputs carry them too,
    and neither can be matched by an untainted rule, whose `matchRel` is a declared,
    dot-free name. It is genuinely load-bearing rather than tidy: a rule's `matchRel` is
    whatever relation NAME its `computed`/`ttu` arm references, and nothing in `WF` stops an
    untainted def from referencing a dot-carrying name.
  * ⚠ `hlc : ∀ r ∈ leafRewrites S, r.kind = RuleKind.computed` — **THE GAP, and it is what
    makes this section cost more than a transcription.** `TtuStarFree` quantifies over
    `schemaRewrites S`, the untainted-ONLY rule set, but `rewriteStepL` steps over
    `schemaRewritesL S = schemaRewrites S ++ leafRewrites S`, and `leafRewrites` mints
    `.ttu` arms off DERIVED defs' closure leaves — arms OUTSIDE `TtuStarFree`'s quantifier
    entirely. So `TtuTuplesetsDirect + TtuStarFree + BareStarStore` is **not sufficient**
    for the L closure. `hlc` kills those arms and is itself derived from the
    ComputedOnly-at-derived premise the `reachedByW3d*_shadow` family already binds
    (`kind_computed_of_mem_leafRewrites_computedOnly` below), so T3 costs NO new admission
    or scope field beyond the `TtuTuplesetsDirect` / `TtuStarFree` pair. The refutation of
    the `hlc`-free statement is machine-checked at `StarBareWitness`:
    `slStP_leaf_ttu_breaks_star_bare`.

⚠ **The cheap route is REFUSED, as a recorded decision on the `P6` row.**
`LeafRules.lean::rewriteClosureL_subject_pred_gen` at a suitable `TtuTargetsSatL` gives T3
in about three lines, but its provider is a SCHEMA-LEVEL ban on TTU targets that rejects
through-shape schemas the STORE-level `TtuStarFree` admits — it would narrow the Lean
fragment below what the Python compiler accepts. Nothing below uses it. -/

/-! #### (2) The killer — a `ComputedOnly` derived layer mints no `.ttu` leaf rule

Structurally a `ComputedOnly` twin of `LeafRules.lean`'s purity chain
(`isPure_of_mem_splitPure_snd` … `isPure_of_closure_mem_persistedLeaves`), which is the
only place in the tree that walks `persistedLeaves`' closure leaves. It cannot live beside
it: `ComputedOnly` is `ReconcileCorrect.lean`'s and `LeafRules.lean` does not import that
module. This file imports both. -/

/-- Splitting a `ComputedOnly` subtree (`Leaf.lean::splitPure`) leaves every non-`Direct`
    member `ComputedOnly`. EASIER than its purity twin on two arms: `splitPure` returns an
    `inter`/`excl` node whole, and `ComputedOnly` is happy there (where `isPure` is `false`
    and the arm is vacuous). -/
theorem computedOnly_of_mem_splitPure_snd :
    ∀ {e : Expr}, ComputedOnly e → ∀ x ∈ (splitPure e).2, ComputedOnly x := by
  intro e
  induction e with
  | direct rs => intro h; exact h.elim
  | computed R => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | ttu tgt ts => intro h; exact h.elim
  | union a b iha ihb =>
      intro h x hx
      rw [splitPure] at hx
      simp only [List.mem_append] at hx
      rcases hx with hx | hx
      · exact iha h.1 x hx
      · exact ihb h.2 x hx
  | inter a b _ _ => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | excl a b _ _ => intro h x hx; simp [splitPure] at hx; subst hx; exact h

/-- Re-folding `ComputedOnly` members into `unionAll`'s LEFT-nested union keeps them
    `ComputedOnly`. -/
theorem computedOnly_foldl_union :
    ∀ (es : List Expr) (e : Expr), ComputedOnly e →
      (∀ x ∈ es, ComputedOnly x) → ComputedOnly (es.foldl Expr.union e) := by
  intro es
  induction es with
  | nil => intro e he _; simpa using he
  | cons a es ih =>
      intro e he hall
      simp only [List.foldl_cons]
      refine ih _ ?_ (fun x hx => hall x (List.mem_cons_of_mem _ hx))
      exact ⟨he, hall a (List.mem_cons_self ..)⟩

/-- `unionAll` of `ComputedOnly` members is `ComputedOnly`. -/
theorem computedOnly_of_unionAll {es : List Expr} {sub : Expr}
    (hall : ∀ x ∈ es, ComputedOnly x) (h : unionAll es = some sub) : ComputedOnly sub := by
  cases es with
  | nil => simp [unionAll] at h
  | cons e es =>
      rw [unionAll] at h
      simp only [Option.some.injEq] at h
      subst h
      exact computedOnly_foldl_union es e (hall e (List.mem_cons_self ..))
        (fun x hx => hall x (List.mem_cons_of_mem _ hx))

/-! ★ The `ComputedOrDirect` twins of the three helpers above (`P6` step 3b step 8,
2026-09-14). Each is its original with the `.direct` arm's `h.elim` replaced by the
now-inhabited case — `splitPure` returns a `.direct` node whole, and `ComputedOrDirect` is
happy there. -/

theorem computedOrDirect_of_mem_splitPure_snd :
    ∀ {e : Expr}, ComputedOrDirect e → ∀ x ∈ (splitPure e).2, ComputedOrDirect x := by
  intro e
  induction e with
  | direct rs => intro h x hx; simp [splitPure] at hx
  | computed R => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | ttu tgt ts => intro h; exact h.elim
  | union a b iha ihb =>
      intro h x hx
      rw [splitPure] at hx
      simp only [List.mem_append] at hx
      rcases hx with hx | hx
      · exact iha h.1 x hx
      · exact ihb h.2 x hx
  | inter a b _ _ => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | excl a b _ _ => intro h x hx; simp [splitPure] at hx; subst hx; exact h

theorem computedOrDirect_foldl_union :
    ∀ (es : List Expr) (e : Expr), ComputedOrDirect e →
      (∀ x ∈ es, ComputedOrDirect x) → ComputedOrDirect (es.foldl Expr.union e) := by
  intro es
  induction es with
  | nil => intro e he _; simpa using he
  | cons a es ih =>
      intro e he hall
      simp only [List.foldl_cons]
      refine ih _ ?_ (fun x hx => hall x (List.mem_cons_of_mem _ hx))
      exact ⟨he, hall a (List.mem_cons_self ..)⟩

theorem computedOrDirect_of_unionAll {es : List Expr} {sub : Expr}
    (hall : ∀ x ∈ es, ComputedOrDirect x) (h : unionAll es = some sub) :
    ComputedOrDirect sub := by
  cases es with
  | nil => simp [unionAll] at h
  | cons e es =>
      rw [unionAll] at h
      simp only [Option.some.injEq] at h
      subst h
      exact computedOrDirect_foldl_union es e (hall e (List.mem_cons_self ..))
        (fun x hx => hall x (List.mem_cons_of_mem _ hx))

/-- **The MERGED closure leaf of a `ComputedOnly` subtree is `ComputedOnly`** — the arm
    that covers `persistedLeaves`' pure-union merge, and the one a lemma written only for
    atoms would miss. -/
theorem computedOnly_of_closure_mem_pureLeaves {e sub : Expr}
    (hco : ComputedOnly e) (h : PLeaf.closure sub ∈ pureLeaves e) : ComputedOnly sub := by
  simp only [pureLeaves, List.mem_append] at h
  rcases h with h | h
  · split at h <;> simp at h
  · split at h
    · simp at h
    · rename_i sub' heq
      simp only [List.mem_singleton, PLeaf.closure.injEq] at h
      subst h
      exact computedOnly_of_unionAll (computedOnly_of_mem_splitPure_snd hco) heq

/-- Every `.closure` leaf `atomLeaves` emits from a `ComputedOnly` expression is
    `ComputedOnly`. Only the `.computed` arm can fire at all: `ComputedOnly` is `False` at
    `.direct` and `.ttu`, and `atomLeaves` is `[]` at the three boolean shapes. -/
theorem computedOnly_of_closure_mem_atomLeaves {S : Schema} {ty : String} {e sub : Expr}
    (hco : ComputedOnly e) (h : PLeaf.closure sub ∈ atomLeaves S ty e) : ComputedOnly sub := by
  cases e with
  | direct rs => exact hco.elim
  | computed R =>
      rw [atomLeaves] at h
      split at h
      · simp at h
      · simp only [List.mem_singleton, PLeaf.closure.injEq] at h
        subst h
        exact hco
  | ttu tgt ts => exact hco.elim
  | union a b => simp [atomLeaves] at h
  | inter a b => simp [atomLeaves] at h
  | excl a b => simp [atomLeaves] at h

/-- The `ComputedOrDirect` twin of `computedOnly_of_closure_mem_pureLeaves`. ★ ADDITIVE,
    `P6` step 3b step 8 (2026-09-14) — see the section note below `computedOnly_of_closure_
    mem_persistedLeaves` for why the whole chain needed a `ComputedOrDirect` copy. -/
theorem computedOrDirect_of_closure_mem_pureLeaves {e sub : Expr}
    (hco : ComputedOrDirect e) (h : PLeaf.closure sub ∈ pureLeaves e) :
    ComputedOrDirect sub := by
  simp only [pureLeaves, List.mem_append] at h
  rcases h with h | h
  · split at h <;> simp at h
  · split at h
    · simp at h
    · rename_i sub' heq
      simp only [List.mem_singleton, PLeaf.closure.injEq] at h
      subst h
      exact computedOrDirect_of_unionAll (computedOrDirect_of_mem_splitPure_snd hco) heq

/-- The `ComputedOrDirect` twin of `computedOnly_of_closure_mem_atomLeaves`. The `.direct`
    arm is no longer refuted by the premise — instead `atomLeaves` sends it to a STORAGE
    leaf, so there is no `.closure` leaf to be about. -/
theorem computedOrDirect_of_closure_mem_atomLeaves {S : Schema} {ty : String} {e sub : Expr}
    (hco : ComputedOrDirect e) (h : PLeaf.closure sub ∈ atomLeaves S ty e) :
    ComputedOrDirect sub := by
  cases e with
  | direct rs =>
      rw [atomLeaves] at h
      split at h
      · exact computedOrDirect_of_closure_mem_pureLeaves hco h
      · simp only [List.mem_append, List.mem_map] at h
        rcases h with h | h
        · split at h <;> simp at h
        · obtain ⟨_, _, hx⟩ := h; exact PLeaf.noConfusion hx
  | computed R =>
      rw [atomLeaves] at h
      split at h
      · simp at h
      · simp only [List.mem_singleton, PLeaf.closure.injEq] at h
        subst h
        exact hco
  | ttu tgt ts => exact hco.elim
  | union a b => simp [atomLeaves] at h
  | inter a b => simp [atomLeaves] at h
  | excl a b => simp [atomLeaves] at h

/-- **The `ComputedOnly` twin of `LeafRules.lean::isPure_closure_persistedLeaves_and_spine`,
    both halves at once.** One plain structural induction discharges the mutually-defined
    pair for the reason that lemma records — every recursive call in the block is on an
    IMMEDIATE subterm. The `.union` case is where the two allocators differ and where the
    content sits: `persistedLeaves` may MERGE (through `pureLeaves`), `unionSpineLeaves`
    never does. -/
theorem computedOnly_closure_persistedLeaves_and_spine {S : Schema} {ty : String} :
    ∀ (e : Expr), ComputedOnly e →
      (∀ sub, PLeaf.closure sub ∈ persistedLeaves S ty e → ComputedOnly sub) ∧
      (∀ sub, PLeaf.closure sub ∈ unionSpineLeaves S ty e → ComputedOnly sub) := by
  intro e
  induction e with
  | direct rs => intro hco; exact hco.elim
  | computed R =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        exact computedOnly_of_closure_mem_atomLeaves hco h
      · simp only [unionSpineLeaves] at h
        exact computedOnly_of_closure_mem_atomLeaves hco h
  | ttu tgt ts => intro hco; exact hco.elim
  | union a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        split at h
        · exact computedOnly_of_closure_mem_pureLeaves hco h
        · simp only [List.mem_append] at h
          exact h.elim ((iha hco.1).2 sub) ((ihb hco.2).2 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).2 sub) ((ihb hco.2).2 sub)
  | inter a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
  | excl a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)

/-! ### ★ The `ComputedOrDirect` twins of the leaf-kind chain (`P6` step 3b step 8, 2026-09-14)

**Why these exist.** `T3` — "no closure member's subject is a bridge node" — runs through
`kind_computed_of_mem_leafRewrites_computedOnly`, which is stated under the
`ComputedOnly`-at-derived premise the `reachedByW3d_shadow` family binds. The W3d-2 `_d`
shadow chain (`CascadeStrataSettle.lean::reachedByW3d2_shadow_d`) binds **`ComputedOrDirect`**
instead — that is the whole point of the `_d` chain, which exists to admit derived defs with
`direct` arms — so `T3` could not be discharged there.

**The two predicates differ only at `.direct`, and this chain never needed `.direct` to be
absent.** `RulesWrite.lean::exprArms` returns `[]` at a `.direct` node, so a direct arm mints
no rewrite rule at all and cannot mint a `.ttu` one; and `Leaf.lean::persistedLeaves` sends a
`.direct` to a STORAGE leaf, never a `.closure` leaf. So the whole chain generalises verbatim,
with the two `hco.elim` steps replaced by "this case is empty". Three twins, no new content.

⚠ The `ComputedOnly` originals are LEFT IN PLACE and unchanged — they still have consumers,
and making them wrappers would have moved an audited-adjacent proof for no gain. -/

theorem computedOrDirect_closure_persistedLeaves_and_spine {S : Schema} {ty : String} :
    ∀ (e : Expr), ComputedOrDirect e →
      (∀ sub, PLeaf.closure sub ∈ persistedLeaves S ty e → ComputedOrDirect sub) ∧
      (∀ sub, PLeaf.closure sub ∈ unionSpineLeaves S ty e → ComputedOrDirect sub) := by
  intro e
  induction e with
  | direct rs =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        exact computedOrDirect_of_closure_mem_atomLeaves hco h
      · simp only [unionSpineLeaves] at h
        exact computedOrDirect_of_closure_mem_atomLeaves hco h
  | computed R =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        exact computedOrDirect_of_closure_mem_atomLeaves hco h
      · simp only [unionSpineLeaves] at h
        exact computedOrDirect_of_closure_mem_atomLeaves hco h
  | ttu tgt ts => intro hco; exact hco.elim
  | union a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        split at h
        · exact computedOrDirect_of_closure_mem_pureLeaves hco h
        · simp only [List.mem_append] at h
          exact h.elim ((iha hco.1).2 sub) ((ihb hco.2).2 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).2 sub) ((ihb hco.2).2 sub)
  | inter a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
  | excl a b iha ihb =>
      intro hco
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim ((iha hco.1).1 sub) ((ihb hco.2).1 sub)

/-- Every rewrite arm of a `ComputedOrDirect` expression is a `.computed` arm: `exprArms`
    mints a `.ttu` rule at a `.ttu` node and nowhere else, and mints NOTHING at a `.direct`
    node (`RulesWrite.lean::exprArms`). -/
theorem kind_computed_of_mem_exprArms_computedOrDirect :
    ∀ {e : Expr}, ComputedOrDirect e → ∀ {ot outRel : String} {r : RRule},
      r ∈ exprArms ot outRel e → r.kind = RuleKind.computed := by
  intro e
  induction e with
  | direct rs => intro _ _ _ _ hr; simp [exprArms] at hr
  | computed R =>
      intro _ _ _ _ hr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      rfl
  | ttu tgt ts => intro hco; exact hco.elim
  | union a b iha ihb =>
      intro hco _ _ _ hr
      rw [exprArms, List.mem_append] at hr
      exact hr.elim (iha hco.1) (ihb hco.2)
  | inter a b _ _ => intro _ _ _ _ hr; simp [exprArms] at hr
  | excl a b _ _ => intro _ _ _ _ hr; simp [exprArms] at hr

/-- **The killer, at the `_d` chain's premise.** Twin of
    `kind_computed_of_mem_leafRewrites_computedOnly`, same proof. -/
theorem kind_computed_of_mem_leafRewrites_computedOrDirect {S : Schema}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOrDirect e)
    {r : RRule} (h : r ∈ leafRewrites S) : r.kind = RuleKind.computed := by
  unfold leafRewrites at h
  obtain ⟨d, hd, hdr⟩ := List.mem_flatMap.mp h
  have hdefs : d ∈ S.defs := (List.mem_filter.mp hd).1
  have hder : isDerived S d.1 = true := (List.mem_filter.mp hd).2
  have hco : ComputedOrDirect d.2 := hCO d.1.1 d.1.2 d.2 (lookup_of_mem hNK hdefs) hder
  unfold keyLeafRewrites at hdr
  obtain ⟨pi, hpi, hr⟩ := List.mem_flatMap.mp hdr
  split at hr
  · rename_i sub heq
    have hmem : PLeaf.closure sub ∈ persistedLeaves S d.1.1 d.2 := by
      rw [← heq]
      have := List.mem_map_of_mem (f := Prod.fst) hpi
      rwa [List.zipIdx_map_fst] at this
    exact kind_computed_of_mem_exprArms_computedOrDirect
      ((computedOrDirect_closure_persistedLeaves_and_spine d.2 hco).1 sub hmem) hr
  · simp at hr

/-- **Every `.closure` leaf of a `ComputedOnly` allocation is `ComputedOnly`.** -/
theorem computedOnly_of_closure_mem_persistedLeaves {S : Schema} {ty : String} {e sub : Expr}
    (hco : ComputedOnly e) (h : PLeaf.closure sub ∈ persistedLeaves S ty e) :
    ComputedOnly sub :=
  (computedOnly_closure_persistedLeaves_and_spine e hco).1 sub h

/-- Every rewrite arm of a `ComputedOnly` expression is a `.computed` arm — `exprArms` mints
    a `.ttu` rule at a `.ttu` node and nowhere else, and `ComputedOnly` has none. -/
theorem kind_computed_of_mem_exprArms_computedOnly :
    ∀ {e : Expr}, ComputedOnly e → ∀ {ot outRel : String} {r : RRule},
      r ∈ exprArms ot outRel e → r.kind = RuleKind.computed := by
  intro e
  induction e with
  | direct rs => intro hco; exact hco.elim
  | computed R =>
      intro _ _ _ _ hr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      rfl
  | ttu tgt ts => intro hco; exact hco.elim
  | union a b iha ihb =>
      intro hco _ _ _ hr
      rw [exprArms, List.mem_append] at hr
      exact hr.elim (iha hco.1) (ihb hco.2)
  | inter a b _ _ => intro _ _ _ _ hr; simp [exprArms] at hr
  | excl a b _ _ => intro _ _ _ _ hr; simp [exprArms] at hr

/-- **★ THE KILLER** — `C1`'s item 4, the piece neither the plan body nor the first recon
    sweep had. Under the ComputedOnly-at-derived premise the `reachedByW3d*_shadow` family
    already binds, the LEAF layer of the compiled rule set mints only `.computed` rules, so
    `rewriteStepL` can fire a `ttu` arm only from `schemaRewrites` — which is exactly where
    `RulesBareStar.lean::TtuStarFree`'s quantifier lives.

    `NodupKeys` is what makes `S.lookup d.1` return THIS def's body, exactly as in
    `isSubjectWildcardUserset_false_of_notLeafName` above. Neither premise is new.

    ⚠ **`hCO` is load-bearing and the fixture that shows it already existed.**
    `LeafRules.lean::lrStP_rules` pins `leafRewrites LeafRuleWitness.SlStP` as carrying
    `⟨"doc", "parent", access.0, RuleKind.ttu "viewer"⟩` — a `.ttu` LEAF rule — and
    `StarBareWitness.slStP_breaks_hCO` below is the `hCO` failure that admits it. -/
theorem kind_computed_of_mem_leafRewrites_computedOnly {S : Schema}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    {r : RRule} (h : r ∈ leafRewrites S) : r.kind = RuleKind.computed := by
  unfold leafRewrites at h
  obtain ⟨d, hd, hdr⟩ := List.mem_flatMap.mp h
  have hdefs : d ∈ S.defs := (List.mem_filter.mp hd).1
  have hder : isDerived S d.1 = true := (List.mem_filter.mp hd).2
  have hco : ComputedOnly d.2 := hCO d.1.1 d.1.2 d.2 (lookup_of_mem hNK hdefs) hder
  unfold keyLeafRewrites at hdr
  obtain ⟨pi, hpi, hr⟩ := List.mem_flatMap.mp hdr
  split at hr
  · rename_i sub heq
    have hmem : PLeaf.closure sub ∈ persistedLeaves S d.1.1 d.2 := by
      rw [← heq]
      have := List.mem_map_of_mem (f := Prod.fst) hpi
      rwa [List.zipIdx_map_fst] at this
    exact kind_computed_of_mem_exprArms_computedOnly
      (computedOnly_of_closure_mem_persistedLeaves hco hmem) hr
  · simp at hr

/-! #### (a) The SEEDS are free — `rawWriteTuples` re-addresses the RELATION only -/

/-- **Every seed of the raw write's fan-out carries the raw write's own subject.** Stated
    over the FAN-OUT rather than the singleton, which is the form the L closure needs:
    `Leaf.lean::rawWriteTuples` is `(rawWriteRels S t).map (fun r => { t with relation := r })`
    and touches nothing but the relation. -/
theorem rawWriteTuples_subject {S : Schema} {t w : Tuple} (h : w ∈ rawWriteTuples S t) :
    w.subject = t.subject := by
  unfold rawWriteTuples at h
  obtain ⟨r, _, rfl⟩ := List.mem_map.mp h
  rfl

/-- …and every seed is either the raw write itself or carries a MINTED LEAF relation
    (`Leaf.lean::mem_rawWriteRels_derived`). This is the dichotomy the untainted `ttu` arm is
    killed on: an untainted rule's `matchRel` is dot-free (`hmd`), so it cannot match the
    leaf-routed half of the fan-out, and what remains is the stored tuple `TtuStarFree`
    already speaks about. -/
theorem mem_rawWriteTuples_eq_or_isLeafPred {S : Schema} {t w : Tuple}
    (h : w ∈ rawWriteTuples S t) : w = t ∨ isLeafPred w.relation = true := by
  by_cases hd : isDerived S (t.object.type, t.relation) = true
  · refine Or.inr ?_
    unfold rawWriteTuples at h
    obtain ⟨r, hr, rfl⟩ := List.mem_map.mp h
    obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
    simp
  · rw [rawWriteTuples_untainted (by simpa using hd)] at h
    exact Or.inl (List.mem_singleton.mp h)

/-! #### (b) + (c) The `StarSeed` machinery, ported to `schemaRewritesL` -/

/-- The L carrier — `RulesBareStar.lean::StarSeed` with the seed SET widened to the raw
    write's fan-out and the output provenance widened to the FULL rule set. The plain
    original is `private`, so this is a re-mint; `RulesBareStar.lean` is not touched. -/
def StarSeedL (S : Schema) (t w : Tuple) : Prop :=
  (w.subject.name = STAR → w.subject = t.subject) ∧
  (w ∈ rawWriteTuples S t ∨
    ∃ r ∈ schemaRewritesL S, r.objectType = w.object.type ∧ r.outRel = w.relation)

/-- **The step.** Only a `ttu` arm can change a subject predicate, and under the four
    premises no `ttu` arm ever fires on a star-subject L-closure member. FOUR cases, two of
    which the plain twin does not have:
      * a LEAF `ttu` arm — impossible outright, by `hlc` (the gap `C1` names);
      * an untainted `ttu` arm on the stored seed — `TtuStarFree` verbatim;
      * an untainted `ttu` arm on a leaf-ROUTED seed, or on a leaf-routed rewrite OUTPUT —
        both carry a minted leaf relation, which `hmd` forbids an untainted `matchRel` from
        being;
      * an untainted `ttu` arm on an untainted rewrite output — `TtuTuplesetsDirect`, via
        `RulesCorrect.lean::no_rewrite_outputs_tupleset`, exactly as in the plain twin. -/
theorem starSeedL_step {S : Schema} {T : Store}
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hlc : ∀ r ∈ leafRewrites S, r.kind = RuleKind.computed)
    {t : Tuple} (ht : t ∈ T) {x u : Tuple}
    (hx : StarSeedL S t x) (hu : u ∈ rewriteStepL S x) : StarSeedL S t u := by
  obtain ⟨hxs, hRx⟩ := hx
  refine ⟨?_, Or.inr (rewriteStepL_outRel hu)⟩
  unfold rewriteStepL at hu
  obtain ⟨r, hr, happly⟩ := List.mem_filterMap.mp hu
  rw [schemaRewritesL, List.mem_append] at hr
  unfold applyRRule at happly
  split at happly
  · rename_i hcond
    cases hk : r.kind with
    | computed =>
      rw [hk] at happly
      simp only [Option.some.injEq] at happly
      intro hustar
      rw [← happly] at hustar ⊢
      exact hxs hustar
    | ttu tr =>
      rw [hk] at happly
      simp only [Option.some.injEq] at happly
      intro hustar
      have hxstar : x.subject.name = STAR := by rw [← happly] at hustar; exact hustar
      exfalso
      rcases hr with hrS | hrL
      · rcases hRx with hseed | ⟨r', hr', hr'ot, hr'out⟩
        · -- a SEED: either the stored tuple itself, or a leaf-routed re-addressing
          rcases mem_rawWriteTuples_eq_or_isLeafPred hseed with rfl | hlp
          · exact hTS _ ht hxstar r hrS tr hk hcond
          · rw [hcond.1, hmd r hrS] at hlp
            exact Bool.noConfusion hlp
        · -- an OUTPUT: of an untainted rule, or of a leaf rule
          obtain ⟨d, hd, hd1, harm⟩ := schemaRewrites_provenance hrS
          have htt : (tr, r.matchRel) ∈ exprTtus d.2 := exprArms_ttu_mem d.2 harm tr hk
          rw [schemaRewritesL, List.mem_append] at hr'
          rcases hr' with hr'S | hr'L
          · refine no_rewrite_outputs_tupleset hTT hd htt hr'S ?_ ?_
            · rw [hr'ot, hcond.2]
              exact (congrArg Prod.fst hd1).symm
            · rw [hr'out, hcond.1]
          · have hlp := isLeafPred_outRel_of_mem_leafRewrites hr'L
            rw [hr'out, hcond.1, hmd r hrS] at hlp
            exact Bool.noConfusion hlp
      · -- a LEAF `ttu` arm: outside `TtuStarFree`'s quantifier entirely, killed by `hlc`
        rw [hlc r hrL] at hk
        exact RuleKind.noConfusion hk
  · simp at happly

/-- **A star-subject L-closure member carries the raw write's FULL subject.** The L twin of
    `RulesBareStar.lean::rewriteClosure_star_subject`; same kernel induction, at the
    fan-out seed list. -/
theorem rewriteClosureL_star_subject {S : Schema} {T : Store}
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hlc : ∀ r ∈ leafRewrites S, r.kind = RuleKind.computed)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hstar : u.subject.name = STAR) : u.subject = t.subject := by
  have haux : ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, StarSeedL S t w) →
      ∀ v ∈ rewriteClosureAuxL S n cur, StarSeedL S t v := by
    intro n
    induction n with
    | zero => intro cur hcur v hv; exact hcur v hv
    | succ m ih =>
      intro cur hcur v hv
      rw [rewriteClosureAuxL, List.mem_append] at hv
      rcases hv with hin | hrec
      · exact hcur v hin
      · refine ih (cur.flatMap (rewriteStepL S)) ?_ v hrec
        intro w hw
        obtain ⟨y, hy, hwy⟩ := List.mem_flatMap.mp hw
        exact starSeedL_step hTT hTS hmd hlc ht (hcur y hy) hwy
  rw [mem_rewriteClosureL_iff] at hu
  unfold rewriteClosureRawL at hu
  refine (haux (S.keys.length + 1) (rawWriteTuples S t) ?_ u hu).1 hstar
  intro w hw
  exact ⟨fun _ => rawWriteTuples_subject hw, Or.inl hw⟩

/-- **(1) `rewriteClosureL_star_bare`** — the L analogue of
    `RulesBareStar.lean::rewriteClosure_star_bare`, and its premise list is SIX rather than
    that theorem's three. The three extras are all already bound by `reachedByW3d_shadow`
    and by both `CascadeStrataSettle.lean` W3d-2 twins — `NodupKeys` (premise 1), the
    ComputedOnly-at-derived clause (premise 2), and `hmd`, supplied by
    `LeafScope.matchNotLeaf` off premise 7 — so threading this costs those theorems no new
    binder beyond the `TtuTuplesetsDirect` / `TtuStarFree` pair the plain twin already
    needs, whose providers exist (`FullScope.lean::GraphAdmission.ttuDirect` and
    `::W4Fragment.ttuStarFree`). `W4Fragment.ttuStarFree` is CONSUMED here, never narrowed. -/
theorem rewriteClosureL_star_bare {S : Schema} {T : Store}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hstar : u.subject.name = STAR) : u.subject.predicate = BARE := by
  have hsub := rewriteClosureL_star_subject hTT hTS hmd
    (fun r hr => kind_computed_of_mem_leafRewrites_computedOnly hNK hCO hr) ht hu hstar
  rw [hsub]
  exact (hBS t ht).1 (by rw [← hsub]; exact hstar)

/-! #### (3) The bridge-node endpoint, and T3 in the shape `term` consumes -/

/-- **A node that IS a bridge node belongs to a STAR subject.** The EXTRACTION direction of
    `RulesBareStar.lean::wAnyNode_eq_subjNode`, which only CONSTRUCTS
    (`wAnyNode (ty, p) = subjNode ⟨ty, STAR, p⟩`); a tree-wide grep finds no lemma going the
    other way, and `ShadowOver.term`'s bridge case arrives holding exactly this equation.
    One `variant` mismatch: a non-star subject's node is `plain`. -/
theorem star_of_subjNode_eq_wAnyNode {s : SubjectRef} {sh : Shape}
    (h : subjNode s = wAnyNode sh) : s.name = STAR := by
  by_contra hne
  rw [subjNode, if_neg hne] at h
  simp [wAnyNode] at h

/-- **T3 at the write leg's SUBJECT endpoint, assembled.** No member of the list the
    re-pointed write leg folds has a bridge node as its subject node: a bridge node forces a
    STAR subject (`star_of_subjNode_eq_wAnyNode`), a star subject of the L closure is BARE
    (`rewriteClosureL_star_bare`), and `UsStarWrite.lean::Schema.isSubjectWildcardUserset`
    is `false` at `BARE` by the OUTER `p != BARE` guard the file insists stays outermost.

    Stated over `isSubjectWildcardUserset` rather than over `BridgeNode` because this
    statement predates it (2026-09-13g) and restating a landed theorem is not additive work.
    `BridgeNode` now EXISTS (`:571`, landed additively 2026-09-14) and
    `not_bridgeNode_of_star_bare` just below is this fact in the shape `ShadowOver.term` will
    consume; the two are the same content, so do not "unify" them by editing this one. -/
theorem isSubjectWildcardUserset_false_of_star_bare {S : Schema} {T : Store}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) {ty p : String}
    (hnode : subjNode u.subject = wAnyNode (ty, p)) :
    S.isSubjectWildcardUserset ty p = false := by
  have hstar : u.subject.name = STAR := star_of_subjNode_eq_wAnyNode hnode
  have hbare : u.subject.predicate = BARE :=
    rewriteClosureL_star_bare hNK hCO hmd hTT hTS hBS ht hu hstar
  have hp : p = BARE := by
    have h2 := congrArg NodeKey.pred hnode
    simp only [subjNode_pred, wAnyNode] at h2
    exact h2.symm.trans hbare
  rw [hp]
  simp [Schema.isSubjectWildcardUserset]

/-- ★ **T3 in the shape `ShadowOver.term` consumes it.** No member of the list the re-pointed
    write leg folds has a `BridgeNode` as its SUBJECT node, so no bridge node is ever an edge
    SOURCE on the write leg — which is precisely the obligation the third extras disjunct owes
    (`BridgeNode`, `:571`). A wrapper over `isSubjectWildcardUserset_false_of_star_bare` above,
    which carries the whole argument; it exists so step 8 can apply the fact without unfolding
    the predicate it is widening the shadow with.

    Premise-for-premise identical to the theorem it wraps, and every one of the six is FREE at
    `reachedByW3d_shadow` (premises 1 and 7 give `hNK` / `hmd` via `LeafScope.matchNotLeaf`;
    `hTT` / `hTS` are the two new binders `C1` prices, provided by
    `FullScope.lean::GraphAdmission.ttuDirect` and `::W4Fragment.ttuStarFree` — CONSUMED, never
    narrowed). -/
theorem not_bridgeNode_of_star_bare {S : Schema} {T : Store}
    (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) :
    ¬ BridgeNode S (subjNode u.subject) := by
  rintro ⟨ty, p, hsw, hnode⟩
  rw [isSubjectWildcardUserset_false_of_star_bare hNK hCO hmd hTT hTS hBS ht hu hnode] at hsw
  exact Bool.noConfusion hsw

/-- ★ **The `leafRewrites`-kind form, and the one BOTH shadow chains can reach.** `P6` step
    3b step 8 (2026-09-14): the `ComputedOnly` premise below was only ever a route to *"the
    leaf layer mints no `.ttu` rule"*, and the `_d` chain reaches that fact from
    `ComputedOrDirect` instead (`kind_computed_of_mem_leafRewrites_computedOrDirect`).
    Taking the CONCLUSION as the hypothesis lets one lemma serve both. -/
theorem rewriteClosureL_star_bare_of_leafKinds {S : Schema} {T : Store}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hLK : ∀ r ∈ leafRewrites S, r.kind = RuleKind.computed)
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hstar : u.subject.name = STAR) : u.subject.predicate = BARE := by
  have hsub := rewriteClosureL_star_subject hTT hTS hmd hLK ht hu hstar
  rw [hsub]
  exact (hBS t ht).1 (by rw [← hsub]; exact hstar)

/-- ★ **T3 at the `leafRewrites`-kind premise** — the form the `_d` shadow chain consumes. -/
theorem not_bridgeNode_of_star_bare_of_leafKinds {S : Schema} {T : Store}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hLK : ∀ r ∈ leafRewrites S, r.kind = RuleKind.computed)
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) :
    ¬ BridgeNode S (subjNode u.subject) := by
  rintro ⟨ty, p, hsw, hnode⟩
  have hstar : u.subject.name = STAR := star_of_subjNode_eq_wAnyNode hnode
  have hbare : u.subject.predicate = BARE :=
    rewriteClosureL_star_bare_of_leafKinds hmd hLK hTT hTS hBS ht hu hstar
  have hp : p = BARE := by
    have h2 := congrArg NodeKey.pred hnode
    simp only [subjNode_pred, wAnyNode] at h2
    exact h2.symm.trans hbare
  rw [hp] at hsw
  simp [Schema.isSubjectWildcardUserset] at hsw


/-- **NON-VACUITY for `BridgeNode` itself**: the predicate is inhabited, at the one scenario
    the whole `P6` bridge item runs on (`UsStarWrite.lean::ThroughShapeWitness.Sthru`, whose
    through-shape is `(folder, viewer)`). Without it, `not_bridgeNode_of_star_bare` and
    `not_derNode_of_bridgeNode` would both be satisfiable by a predicate that is false
    everywhere, and the widened shadow would gain a disjunct that never fires. Derived THROUGH
    `bridgeNode_wAnyNode` so it also certifies that the intro rule applies. -/
theorem bridgeNode_nonvacuous :
    BridgeNode ThroughShapeWitness.Sthru BridgedWriteWitness.w0 :=
  bridgeNode_wAnyNode ThroughShapeWitness.through_shape_is_bridged_in

/-! #### Non-vacuity, and the control that makes `hCO` load-bearing

★ Per `docs/sabotage-procedure.md`. The vacuity risk here is specific and worth naming: a
star-subject member of `rewriteClosureL S (rawWriteTuples S t)` might simply never exist,
in which case the whole family would be a theorem about an empty set. `snv_star_closure_member`
refutes that by exhibiting one at a NON-seed member (`unvStar_ne_seed`), on the `Snv` fixture
the T2 section already built, and `snv_star_closure_member_is_bare` derives the conclusion
THROUGH `rewriteClosureL_star_bare` rather than by `decide`, so it certifies applicability.
(The conclusion's VALUE is `rfl` at any fixture — a seed star subject is bare by
`BareStarStore` and the closure is what could break it — so the content of that pin is the
applicability, not the equation. Stated rather than implied.)

**The control is the load-bearing half.** `LeafRuleWitness.SlStP` is `access := viewer from
parent but not banned`: its derived def carries a `.ttu`, `hCO` is FALSE there
(`slStP_breaks_hCO`), and `LeafRules.lean::lrStP_rules` already pins that its leaf layer
mints `⟨"doc", "parent", access.0, RuleKind.ttu "viewer"⟩`. EVERY other premise of
`rewriteClosureL_star_bare` holds at that fixture and the conclusion FAILS — a bare
`folder:*` parent walks out of the L closure carrying predicate `"viewer"`. That is `C1`'s
third gap as a kernel refutation rather than a paper one, and it is why the
`TtuTuplesetsDirect + TtuStarFree + BareStarStore` premise list of the plain twin cannot
simply be transcribed.

★ **`hmd` IS controlled, as of 2026-09-14** — `SmdLeaf` below, in the same one-statement
shape as the `hCO` control and equally strong: every OTHER premise of
`rewriteClosureL_star_bare` holds there and the conclusion is FALSE. (Until then this note
recorded the control as OWED, and the load-bearingness of `hmd` rested on inspection alone;
`docs/p6-step3b-plan-2026-09-13.md` §`C10`'s last paragraph is the entry it discharges.) The
inspection argument it replaces was right and is now machine-checked in two halves:
`smdLeaf_wf` proves the witness is `WF`, so nothing in `WF` forbids an untainted def from
REFERENCING a dot-carrying name — `WF.relNames` constrains only DECLARED key names — and
`smdLeaf_breaks_rewriteMatchDeclared` names what does forbid it. -/

namespace StarBareWitness

/-! ⚠ **Deliberately NOT `open LeafBridgeWitness`.** `statement_pin.py` pins an
`ambient:<path>` row per hosting file — the file's `variable` / `open` lines, in order —
and `CascadeStable.lean` hosts pinned declarations, so ONE `open` here turns
`check_definitions` red (measured this session: `FAIL: … ambient:…/CascadeStable.lean`).
Every `LeafBridgeWitness` reference below is spelled out instead. -/

/-- The raw write whose L closure carries a STAR subject ACROSS a rewrite step: a bare
    `user:*` grant of `LeafBridgeWitness.Snv`'s UNTAINTED `doc#viewer`. -/
def tnvStar : Tuple := ⟨⟨"user", STAR, BARE⟩, "viewer", ⟨"doc", "d1"⟩⟩

/-- …and the member it produces — `Snv`'s derived `doc#editor` routes `viewer` onto the
    minted leaf `editor.0`, so this is a genuine closure OUTPUT, not a re-addressed seed. -/
def unvStar : Tuple := ⟨⟨"user", STAR, BARE⟩, leafPred "editor" 0, ⟨"doc", "d1"⟩⟩

theorem unvStar_ne_seed : unvStar ≠ tnvStar := by decide

theorem snv_leafRewrites_nonempty : leafRewrites LeafBridgeWitness.Snv ≠ [] := by decide

theorem snv_star_closure_member :
    unvStar ∈ rewriteClosureL LeafBridgeWitness.Snv
      (rawWriteTuples LeafBridgeWitness.Snv tnvStar) := by decide

theorem snv_star_closure_member_is_star : unvStar.subject.name = STAR := by decide

theorem snv_ttuTuplesetsDirect : TtuTuplesetsDirect LeafBridgeWitness.Snv := by
  unfold TtuTuplesetsDirect; decide

theorem snv_matchNotLeaf :
    ∀ r ∈ schemaRewrites LeafBridgeWitness.Snv, isLeafPred r.matchRel = false := by
  intro r hr
  rw [LeafBridgeWitness.snv_schemaRewrites, List.mem_singleton] at hr
  subst hr
  decide

theorem snv_bareStar : BareStarStore [tnvStar] := by
  intro t' ht'
  rw [List.mem_singleton] at ht'
  subst ht'
  exact ⟨fun _ => rfl, by decide⟩

/-- Non-vacuous for the right reason: `schemaRewrites Snv` is a ONE-rule list carrying a real
    `RuleKind.ttu` (`snv_schemaRewrites`), so this premise is a constraint rather than an
    empty quantifier — it is discharged because `tnvStar`'s relation is not that rule's
    tupleset, not because there is no rule. -/
theorem snv_ttuStarFree : TtuStarFree LeafBridgeWitness.Snv [tnvStar] := by
  intro t' ht' _ a ha tr _ hmatch
  rw [List.mem_singleton] at ht'
  subst ht'
  rw [LeafBridgeWitness.snv_schemaRewrites, List.mem_singleton] at ha
  subst ha
  exact absurd hmatch.1 (by decide)

/-- The leaf layer of `Snv` is non-empty (`snv_leafRewrites_nonempty`) and entirely
    `.computed`, derived THROUGH the killer rather than `decide`d. -/
theorem snv_leaf_rules_all_computed :
    ∀ r ∈ leafRewrites LeafBridgeWitness.Snv, r.kind = RuleKind.computed :=
  fun _ hr => kind_computed_of_mem_leafRewrites_computedOnly
    LeafBridgeWitness.snv_nodupKeys LeafBridgeWitness.snv_computedOnly hr

/-- **THE PIN.** Derived THROUGH `rewriteClosureL_star_bare`, at a configuration where the
    star-subject hypothesis is REACHED at a non-seed closure member and every premise is
    live. See the section note on what this pin does and does not certify. -/
theorem snv_star_closure_member_is_bare : unvStar.subject.predicate = BARE :=
  rewriteClosureL_star_bare LeafBridgeWitness.snv_nodupKeys
    LeafBridgeWitness.snv_computedOnly snv_matchNotLeaf
    snv_ttuTuplesetsDirect snv_ttuStarFree snv_bareStar (List.mem_singleton_self tnvStar)
    snv_star_closure_member snv_star_closure_member_is_star

/-- The control's raw write: a BARE `folder:*` parent — legal under `BareStarStore`. -/
def tstpStar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

/-- …and the non-BARE star subject `SlStP`'s LEAF `ttu` rule manufactures out of it. -/
def ustpStar : Tuple := ⟨⟨"folder", STAR, "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩

theorem slStP_nodupKeys : NodupKeys LeafRuleWitness.SlStP := by unfold NodupKeys; decide

/-- The untainted layer is EMPTY at `SlStP` — which is what makes `hmd` and `TtuStarFree`
    hold there vacuously, and therefore what makes the control attributable to `hCO`. -/
theorem slStP_untainted_layer_silent : schemaRewrites LeafRuleWitness.SlStP = [] := by decide

theorem slStP_matchNotLeaf :
    ∀ r ∈ schemaRewrites LeafRuleWitness.SlStP, isLeafPred r.matchRel = false := by
  intro r hr
  rw [slStP_untainted_layer_silent] at hr
  simp at hr

theorem slStP_ttuStarFree : TtuStarFree LeafRuleWitness.SlStP [tstpStar] := by
  intro t' _ _ a ha
  rw [slStP_untainted_layer_silent] at ha
  simp at ha

theorem slStP_ttuTuplesetsDirect : TtuTuplesetsDirect LeafRuleWitness.SlStP := by
  unfold TtuTuplesetsDirect; decide

theorem slStP_bareStar : BareStarStore [tstpStar] := by
  intro t' ht'
  rw [List.mem_singleton] at ht'
  subst ht'
  exact ⟨fun _ => rfl, by decide⟩

theorem slStP_star_member :
    ustpStar ∈ rewriteClosureL LeafRuleWitness.SlStP
      (rawWriteTuples LeafRuleWitness.SlStP tstpStar) := by decide

theorem slStP_star_member_is_star : ustpStar.subject.name = STAR := by decide

theorem slStP_star_member_is_not_bare : ustpStar.subject.predicate ≠ BARE := by decide

/-- `hCO` is FALSE at `SlStP`: `access := viewer from parent but not banned` is an `excl`
    whose LEFT arm is a `.ttu`, and `ComputedOnly` is `False` at a `.ttu` leaf. -/
theorem slStP_breaks_hCO :
    ¬ (∀ dt R e, LeafRuleWitness.SlStP.lookup (dt, R) = some e →
        isDerived LeafRuleWitness.SlStP (dt, R) = true → ComputedOnly e) := by
  intro h
  have hlk : LeafRuleWitness.SlStP.lookup ("doc", "access")
      = some (Expr.excl (.ttu "viewer" "parent") (.computed "banned")) := by decide
  have hder : isDerived LeafRuleWitness.SlStP ("doc", "access") = true := by decide
  exact (h "doc" "access" _ hlk hder).1

/-- **★ THE CONTROL, in one statement.** Every premise of `rewriteClosureL_star_bare`
    EXCEPT the ComputedOnly one holds at `LeafRuleWitness.SlStP`, and the conclusion is
    FALSE there. So the `hCO` premise — equivalently `hlc`, the leaf-layer killer — is not
    decoration: without it the theorem is false, not merely unproven. This is `C1`'s
    "`TtuStarFree` quantifies over `schemaRewrites` but `rewriteStepL` steps over
    `schemaRewritesL`" gap as a kernel fact. -/
theorem slStP_leaf_ttu_breaks_star_bare :
    NodupKeys LeafRuleWitness.SlStP ∧
    (∀ r ∈ schemaRewrites LeafRuleWitness.SlStP, isLeafPred r.matchRel = false) ∧
    TtuTuplesetsDirect LeafRuleWitness.SlStP ∧
    TtuStarFree LeafRuleWitness.SlStP [tstpStar] ∧
    BareStarStore [tstpStar] ∧
    tstpStar ∈ [tstpStar] ∧
    ustpStar ∈ rewriteClosureL LeafRuleWitness.SlStP
      (rawWriteTuples LeafRuleWitness.SlStP tstpStar) ∧
    ustpStar.subject.name = STAR ∧
    ustpStar.subject.predicate ≠ BARE :=
  ⟨slStP_nodupKeys, slStP_matchNotLeaf, slStP_ttuTuplesetsDirect, slStP_ttuStarFree,
    slStP_bareStar, List.mem_singleton_self tstpStar, slStP_star_member,
    slStP_star_member_is_star, slStP_star_member_is_not_bare⟩

/-! ##### CONTROLLED — the `hmd` NEGATIVE CONTROL (2026-09-14)

★ Per `docs/sabotage-procedure.md`, and the second of the two items
`docs/p6-step3b-plan-2026-09-13.md` §`C10` recorded as OWED rather than asserted.

**What `hmd` claims and how to break it.** `hmd : ∀ r ∈ schemaRewrites S, isLeafPred
r.matchRel = false` says no UNTAINTED rewrite rule fires on a minted leaf relation. A
rule's `matchRel` is whatever relation name its `computed`/`ttu` arm REFERENCES
(`RulesWrite.lean::exprArms`), so the narrowest schema that breaks it is one untainted def
referencing a dot-carrying name. `SmdLeaf` is `LeafBridgeWitness.Snv` plus exactly one such
declaration — `doc#shared := owner from editor.0` — where `"editor.0"` is the leaf name `Snv`'s
derived `doc#editor` family mints at index 0, which is what makes the break CONSEQUENTIAL
rather than cosmetic: the untainted `ttu` arm now fires on the leaf-routed closure member
`StarBareWitness.unvStar` and manufactures a STAR subject with predicate `"owner"`.

**The finding, in two parts, because they answer different questions.**
  * `hmd` CAN fail, and `WF` is not what stops it. `smdLeaf_wf` is machine-checked:
    `Core/Schema.lean::WF.relNames` quantifies over `p.1.2`, the DECLARED relation name of
    each def, and says nothing about the names its BODY references. So the premise is not
    droppable from `rewriteClosureL_star_bare` and not derivable from `WF`.
  * `hmd` cannot fail on an ADMITTED schema, and that is a statement about a different
    predicate. `LeafRules.lean::matchNotLeaf_of_declared` derives `hmd` from `WF` plus the
    first component of `RestrictBase.lean::RewriteMatchDeclared`, which
    `FullScope.lean::GraphAdmission.matchDecl` carries — so at every live consumer `hmd` is
    free, exactly as this file's header says. `smdLeaf_breaks_rewriteMatchDeclared` pins
    which of the two the witness violates: `("doc", "editor.0")` is not a declared key.
    Read together, the pair says the premise earns its place in the GENERAL lemma while
    costing the `reachedByW3d*_shadow` family no new binder.

**Why this is not the `SlStP` control over again.** `SlStP` breaks `hCO` and lets a LEAF
`ttu` rule survive; `SmdLeaf` keeps `hCO` (its derived layer is `ComputedOnly`, so every
leaf rule is `.computed`) and breaks the UNTAINTED layer instead. The two controls
therefore kill the two different quantifiers `starSeedL_step` splits on, and neither
substitutes for the other. -/

/-- **THE `hmd` CONTROL SCHEMA** — `LeafBridgeWitness.Snv` with one untainted def added:
    `doc#shared := owner from editor.0`, whose tupleset is a MINTED LEAF name rather than a
    declared relation. Everything else is byte-for-byte `Snv`, so the store, the raw write
    and the leaf layer are the ones the pins above already characterise. -/
def SmdLeaf : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false), ("group", "member", true)]),
    (("group", "member"),  .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "viewer"),    .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent")),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "editor"),    .excl (.computed "viewer") (.computed "banned")),
    (("doc", "shared"),    .ttu "owner" "editor.0")], []⟩

/-- The non-BARE star subject the leaf-matching untainted `ttu` arm manufactures. -/
def umdStar : Tuple := ⟨⟨"user", STAR, "owner"⟩, "shared", ⟨"doc", "d1"⟩⟩

/-- The added def's rule, as `exprArms` mints it: `matchRel` is the leaf name. -/
theorem smdLeaf_leaf_matchRel_rule :
    (⟨"doc", "editor.0", "shared", RuleKind.ttu "owner"⟩ : RRule) ∈ schemaRewrites SmdLeaf := by
  decide

/-- **`hmd` is FALSE here** — the fixture the section note above used to record as missing. -/
theorem smdLeaf_breaks_hmd :
    ¬ ∀ r ∈ schemaRewrites SmdLeaf, isLeafPred r.matchRel = false := by
  intro h
  exact absurd (h _ smdLeaf_leaf_matchRel_rule) (by decide)

/-- …and the schema is `WF`, so `WF` is not what supplies `hmd`. -/
theorem smdLeaf_wf : WF SmdLeaf := by
  refine ⟨fun p hp => ?_⟩
  simp only [SmdLeaf, List.mem_cons, List.not_mem_nil, or_false] at hp
  rcases hp with rfl | rfl | rfl | rfl | rfl | rfl | rfl <;> simp [relNameOK]

/-- …while `RewriteMatchDeclared` — the admission field that DOES supply it, through
    `LeafRules.lean::matchNotLeaf_of_declared` — is exactly what the witness violates. -/
theorem smdLeaf_breaks_rewriteMatchDeclared : ¬ RewriteMatchDeclared SmdLeaf := by
  intro h
  exact absurd (h _ smdLeaf_leaf_matchRel_rule).1 (by decide)

theorem smdLeaf_nodupKeys : NodupKeys SmdLeaf := by unfold NodupKeys; decide

/-- Only `doc#editor` is derived: the added def is a bare `.ttu` whose one reference,
    `("doc", "editor.0")`, is not a declared key and so can carry no taint. -/
theorem smdLeaf_taintedKeys : taintedKeys SmdLeaf = [("doc", "editor")] := by decide

theorem smdLeaf_computedOnly :
    ∀ dt R e, SmdLeaf.lookup (dt, R) = some e → isDerived SmdLeaf (dt, R) = true →
      ComputedOnly e := by
  intro dt R e hlk hder
  have hk : (dt, R) ∈ taintedKeys SmdLeaf := by
    unfold isDerived at hder
    rw [List.contains_eq_mem] at hder
    exact of_decide_eq_true hder
  rw [smdLeaf_taintedKeys, List.mem_singleton] at hk
  rw [hk] at hlk
  have hval : SmdLeaf.lookup ("doc", "editor")
      = some (Expr.excl (.computed "viewer") (.computed "banned")) := by decide
  rw [hval] at hlk
  injection hlk with he
  subst he
  exact ⟨trivial, trivial⟩

theorem smdLeaf_ttuTuplesetsDirect : TtuTuplesetsDirect SmdLeaf := by
  unfold TtuTuplesetsDirect; decide

theorem smdLeaf_schemaRewrites :
    schemaRewrites SmdLeaf =
      [⟨"doc", "parent", "viewer", RuleKind.ttu "viewer"⟩,
       ⟨"doc", "editor.0", "shared", RuleKind.ttu "owner"⟩] := by decide

/-- Non-vacuous for the same reason `snv_ttuStarFree` is: BOTH untainted `ttu` rules are
    real and both are discharged because `tnvStar`'s relation is neither one's tupleset. -/
theorem smdLeaf_ttuStarFree : TtuStarFree SmdLeaf [tnvStar] := by
  intro t' ht' _ a ha tr _ hmatch
  rw [List.mem_singleton] at ht'
  subst ht'
  rw [smdLeaf_schemaRewrites] at ha
  simp only [List.mem_cons, List.not_mem_nil, or_false] at ha
  rcases ha with rfl | rfl
  · exact absurd hmatch.1 (by decide)
  · exact absurd hmatch.1 (by decide)

/-- The store is `StarBareWitness`'s own, unchanged — the control perturbs the SCHEMA and
    nothing else, which is what makes the red attributable to `hmd`. -/
theorem smdLeaf_bareStar : BareStarStore [tnvStar] := snv_bareStar

theorem smdLeaf_star_member :
    umdStar ∈ rewriteClosureL SmdLeaf (rawWriteTuples SmdLeaf tnvStar) := by decide

theorem smdLeaf_star_member_is_star : umdStar.subject.name = STAR := by decide

theorem smdLeaf_star_member_is_not_bare : umdStar.subject.predicate ≠ BARE := by decide

/-! ###### The mutation's own non-vacuity — the edit moved what it was meant to move

Per `docs/sabotage-procedure.md` §"A MUTATION NEEDS ITS OWN NON-VACUITY ARGUMENT": an
`INERT` row and a load-bearing one look identical unless you check that the edit changed
the property it was aimed at. `SmdLeaf` differs from `LeafBridgeWitness.Snv` in ONE def,
over the SAME store and the SAME raw write (`smdLeaf_bareStar` is literally
`snv_bareStar`), and the two pins below bracket what that def did: the offending member
does not exist at `Snv`, and the leaf-routed member it is manufactured FROM does. So the
counterexample is attributable to the untainted rule matching a minted leaf relation —
which is `hmd` — and not to the schema having been made worse in some other way. -/

/-- The counterexample member is ABSENT from `Snv`'s closure: it is produced by the added
    def, not merely surfaced by it. -/
theorem umdStar_not_in_snv_closure :
    umdStar ∉ rewriteClosureL LeafBridgeWitness.Snv
      (rawWriteTuples LeafBridgeWitness.Snv tnvStar) := by decide

/-- …and the leaf-routed member it is manufactured from — `Snv`'s own `snv_star_closure_member`
    — survives into `SmdLeaf`'s closure, so the route really is
    `tnvStar` → (leaf `.computed` rule) → `unvStar` → (untainted `ttu` rule on `"editor.0"`)
    → `umdStar`. -/
theorem unvStar_in_smdLeaf_closure :
    unvStar ∈ rewriteClosureL SmdLeaf (rawWriteTuples SmdLeaf tnvStar) := by decide

/-- **★ THE CONTROL, in one statement.** Every premise of `rewriteClosureL_star_bare` EXCEPT
    `hmd` holds at `SmdLeaf`, and the conclusion is FALSE there. So `hmd` is not decoration:
    without it the theorem is false, not merely unproven. Deliberately the same shape as
    `slStP_leaf_ttu_breaks_star_bare` so the two premises can be compared side by side. -/
theorem smdLeaf_hmd_breaks_star_bare :
    NodupKeys SmdLeaf ∧
    (∀ dt R e, SmdLeaf.lookup (dt, R) = some e → isDerived SmdLeaf (dt, R) = true →
      ComputedOnly e) ∧
    TtuTuplesetsDirect SmdLeaf ∧
    TtuStarFree SmdLeaf [tnvStar] ∧
    BareStarStore [tnvStar] ∧
    tnvStar ∈ [tnvStar] ∧
    umdStar ∈ rewriteClosureL SmdLeaf (rawWriteTuples SmdLeaf tnvStar) ∧
    umdStar.subject.name = STAR ∧
    umdStar.subject.predicate ≠ BARE :=
  ⟨smdLeaf_nodupKeys, smdLeaf_computedOnly, smdLeaf_ttuTuplesetsDirect, smdLeaf_ttuStarFree,
    smdLeaf_bareStar, List.mem_singleton_self tnvStar, smdLeaf_star_member,
    smdLeaf_star_member_is_star, smdLeaf_star_member_is_not_bare⟩

end StarBareWitness

/-- **Reach agreement off the extras**: a probe into a non-`Extra` target reads the same
    on `σ` and its shadow — extra edges are trailing hops onto terminal nodes the path can
    neither traverse nor end at. Generic in `Extra`; at today's instantiation
    (`UntaintedShadow`) that reads "off the `DerNode`s".

    `Extra` is genuinely load-bearing here, not decoration: instantiating the
    `UntaintedShadow` abbreviation at `fun _ => True` fails the build with 10 errors
    (2026-08-30c sabotage), four of them in this lemma's consumers. -/
theorem shadow_reach_agree {Extra : NodeKey → Prop} {σ σ0 : GraphState}
    (hsh : ShadowOver Extra σ σ0) {v : NodeKey} (hv : ¬ Extra v) (x : NodeKey) :
    σ.reach x v = σ0.reach x v := by
  cases h1 : σ.reach x v <;> cases h0 : σ0.reach x v
  · rfl
  · exfalso
    have := reach_complete hsh.closed (NReaches.mono_subset hsh.sub (reach_sound h0))
    rw [h1] at this
    cases this
  · exfalso
    rcases nreaches_factor (P := fun ab => Extra ab.2) hsh.classify (reach_sound h1)
      with hE | ⟨ab, hD, hR⟩
    · have := reach_complete hsh.closed0 hE
      rw [h0] at this
      cases this
    · rcases hR with heq | hr
      · exact hv (heq ▸ hD)
      · obtain ⟨y, hy⟩ := nreaches_first_edge hr
        exact hsh.term ab.2 hD y hy
  · rfl

/-- Admission agreement across the shadow: the cycle probe's target is the write's
    subject node, which callers must show is never an `Extra`. At today's instantiation
    that obligation is "never a `DerNode` on the fragment"; post-widening it also has a
    `LeafNode` half, free at a BARE subject via the E3 `leafPublic p ≠ ""` guard. -/
theorem shadow_admitEdge_agree {Extra : NodeKey → Prop} {σ σ0 : GraphState}
    (hsh : ShadowOver Extra σ σ0) {a : NodeKey} (ha : ¬ Extra a) (b : NodeKey) :
    σ.admitEdge a b = σ0.admitEdge a b := by
  unfold GraphState.admitEdge
  rw [shadow_reach_agree hsh ha b]

/-! ### ★★ The BRIDGE layer of the shadow (`P6` step 3b, step 8 — 2026-09-14)

The re-pointed logged write leg runs `GraphState.bridgePreLogged` before its grant, so it
materialises edges the shadow's `σ0` does not have and never will — the recorded design
leaves `RulesWrite.lean::GraphState.writeRules` unbridged (a 40-module reverse cone against
`writeBridgedOne`'s 24, and bridging it re-opens `checkFn_eq_sem_bs`). `ShadowOver.classify`
therefore needs a home for those edges, and `ShadowOver.term` needs them to be terminal.

**The two obligations are stated on the SCHEMA, not on the state**, and that is what makes
them survive a fold. `GraphState.bridgedInConcrete` reads `σ.schema`; the schema is
invariant along every leg here (`Cascade.lean::writeLoggedOne_schema`,
`::bridgePreLogged_schema`), so a hypothesis phrased on `Sc` transfers from accumulator to
accumulator by rewriting, where a hypothesis phrased on `σ` would have to be re-established
at each step.

  `hT` — a bridge TARGET is an `Extra`. Discharged at `BridgeNode` by `bridgeNode_wAnyNode`.
  `hS` — a bridge SOURCE is NOT an `Extra`. This is where `T1`/`T2`/disjointness are
         consumed, and stating it over an arbitrary `c` rather than per-endpoint is
         deliberate: all three disjuncts are killed by facts about `c` alone
         (`NoBridgedDerived` for `DerNode`, `not_bridgedInConcrete_of_leafNode` for
         `LeafNode`, `not_bridgedInConcrete_of_bridgeNode` for `BridgeNode`), so the
         subject/object split the plan sketched buys nothing and costs two obligations. -/

/-- Adding a node preserves the shadow: edges are untouched and `nodesSub` only gets easier. -/
theorem shadowOver_addNode {Extra : NodeKey → Prop} {σ σ0 : GraphState}
    (hsh : ShadowOver Extra σ σ0) (k : NodeKey) : ShadowOver Extra (σ.addNode k) σ0 := by
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · rw [addNode_edges]; exact hsh.classify
  · rw [addNode_edges]; exact hsh.sub
  · intro k' hk'
    rw [addNode_nodes]
    exact List.mem_cons_of_mem _ (hsh.nodesSub k' hk')
  · intro ab hab
    rw [addNode_edges] at hab
    rw [addNode_nodes]
    obtain ⟨h1, h2⟩ := hsh.closed ab hab
    exact ⟨List.mem_cons_of_mem _ h1, List.mem_cons_of_mem _ h2⟩
  · rw [addNode_edges]; exact hsh.term

/-- One logged in-bridge leg preserves the shadow: its only new edge is `c → w_any(c)`,
    whose TARGET is an extra (`hT`) and whose SOURCE is not (`hS`, so `term` is unbroken). -/
theorem untaintedShadow_ensureInBridgesLogged {Extra : NodeKey → Prop} {Sc : Schema}
    {σ σ0 : GraphState} (hsh : ShadowOver Extra σ σ0) (hsc : σ.schema = Sc)
    {c : NodeKey} (hc : c ∈ σ.nodes)
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k) :
    ShadowOver Extra (σ.ensureInBridgesLogged c) σ0 := by
  have hsw : σ.bridgedInConcrete c = true → Sc.isSubjectWildcardUserset c.type c.pred = true :=
    fun h => hsc ▸ (bridgedInConcrete_elim h).2.2.2
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · intro ab hab
    rw [ensureInBridgesLogged_edges] at hab
    rcases ensureInBridges_edges_mem hab with hold | ⟨heq, hbr⟩
    · exact hsh.classify ab hold
    · exact Or.inr (by rw [heq]; exact hT c.type c.pred (hsw hbr))
  · intro ab hab
    rw [ensureInBridgesLogged_edges]
    exact ensureInBridges_edges_mono (hsh.sub ab hab)
  · intro k hk
    rw [ensureInBridgesLogged_nodes]
    exact ensureInBridges_mono (hsh.nodesSub k hk)
  · rw [ensureInBridgesLogged_edges, ensureInBridgesLogged_nodes]
    exact edgesClosed_ensureInBridges hsh.closed hc
  · intro k hk y hy
    rw [ensureInBridgesLogged_edges] at hy
    rcases ensureInBridges_edges_mem hy with hold | ⟨heq, hbr⟩
    · exact hsh.term k hk y hold
    · have hkc : k = c := by
        have := congrArg Prod.fst heq
        simpa using this
      exact hS c (bridgedInConcrete_elim hbr).1 (hsw hbr) (hkc ▸ hk)

/-- The whole logged bridge prologue preserves the shadow — both endpoints' legs, on top of
    the two node interns that precede them. -/
theorem untaintedShadow_bridgePreLogged {Extra : NodeKey → Prop} {Sc : Schema}
    {σ σ0 : GraphState} (hsh : ShadowOver Extra σ σ0) (hsc : σ.schema = Sc) (u : Tuple)
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k) :
    ShadowOver Extra (σ.bridgePreLogged u) σ0 := by
  unfold GraphState.bridgePreLogged
  have h2 : ShadowOver Extra ((σ.addNode (subjNode u.subject)).addNode
      (objNode u.object u.relation)) σ0 :=
    shadowOver_addNode (shadowOver_addNode hsh _) _
  have hsc2 : ((σ.addNode (subjNode u.subject)).addNode
      (objNode u.object u.relation)).schema = Sc := by
    rw [addNode_schema, addNode_schema]; exact hsc
  have hmem : subjNode u.subject ∈ ((σ.addNode (subjNode u.subject)).addNode
      (objNode u.object u.relation)).nodes := by
    rw [addNode_nodes]
    exact List.mem_cons_of_mem _ (by rw [addNode_nodes]; exact List.mem_cons_self)
  have h3 := untaintedShadow_ensureInBridgesLogged h2 hsc2 hmem hT hS
  refine untaintedShadow_ensureInBridgesLogged h3 (by rw [ensureInBridgesLogged_schema]; exact hsc2)
    ?_ hT hS
  rw [ensureInBridgesLogged_nodes]
  refine ensureInBridges_mono ?_
  rw [addNode_nodes]
  exact List.mem_cons_self

/-- One parallel step: the logged write on `σ`, the plain write on the shadow —
    admission agrees, so the shadow relation is maintained.

    ★★ **`P6` step 3b step 8 (2026-09-14): the STATEMENT is unchanged; the proof now runs
    through the BRIDGED pre-state, and two hypotheses arrive.** The admission probe moved —
    `writeLoggedOne` reads `(σ.bridgePreLogged u).admitEdge`, not `σ.admitEdge` — so
    `shadow_admitEdge_agree` has to be applied at the prologue's state rather than at `σ`,
    which is only legal once the prologue is itself known to shadow `σ0`. That is
    `untaintedShadow_bridgePreLogged` above, and it is the whole content of the step; from
    there the grant case is character-for-character the old proof with `bridgePreLogged`
    substituted for `σ`. -/
theorem untaintedShadow_writeLoggedOne {Extra : NodeKey → Prop} {Sc : Schema}
    {σ σ0 : GraphState} (hsh : ShadowOver Extra σ σ0) (hsc : σ.schema = Sc) {u : Tuple}
    (ha : ¬ Extra (subjNode u.subject))
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k) :
    ShadowOver Extra (σ.writeLoggedOne u) (σ0.writeDirect u) := by
  have hpre : ShadowOver Extra (σ.bridgePreLogged u) σ0 :=
    untaintedShadow_bridgePreLogged hsh hsc u hT hS
  have hadm := shadow_admitEdge_agree hpre ha (objNode u.object u.relation)
  unfold GraphState.writeLoggedOne
  by_cases hb : (σ.bridgePreLogged u).admitEdge (subjNode u.subject)
      (objNode u.object u.relation) = true
  · rw [if_pos hb]
    have hb0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true := by
      rw [← hadm]; exact hb
    have hcl0 : ∀ ab ∈ (σ0.writeDirect u).edges,
        ab.1 ∈ (σ0.writeDirect u).nodes ∧ ab.2 ∈ (σ0.writeDirect u).nodes :=
      edgesClosed_writeDirect hsh.closed0 u
    have hsubjMem : subjNode u.subject ∈ (σ.bridgePreLogged u).nodes := by
      unfold GraphState.bridgePreLogged
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [addNode_nodes]
      exact List.mem_cons_of_mem _ (by rw [addNode_nodes]; exact List.mem_cons_self)
    have hobjMem : objNode u.object u.relation ∈ (σ.bridgePreLogged u).nodes := by
      unfold GraphState.bridgePreLogged
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [addNode_nodes]
      exact List.mem_cons_self
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
    · -- classify
      intro ab hab
      rw [pushDelta_edges, addEdge_edges] at hab
      rw [writeDirect_edges, if_pos hb0]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact Or.inl (heq ▸ List.mem_cons_self)
      · rcases hpre.classify ab hmem with h0 | hD
        · exact Or.inl (List.mem_cons_of_mem _ h0)
        · exact Or.inr hD
    · -- sub
      intro ab hab
      rw [writeDirect_edges, if_pos hb0] at hab
      rw [pushDelta_edges, addEdge_edges]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact heq ▸ List.mem_cons_self
      · exact List.mem_cons_of_mem _ (hpre.sub ab hmem)
    · -- nodesSub
      intro k hk
      rw [writeDirect_nodes, if_pos hb0] at hk
      rw [pushDelta_nodes, addEdge_nodes]
      rcases List.mem_cons.mp hk with heq | hk2
      · exact heq ▸ hobjMem
      · rcases List.mem_cons.mp hk2 with heq | hk3
        · exact heq ▸ hsubjMem
        · exact hpre.nodesSub k hk3
    · -- closed
      intro ab hab
      rw [pushDelta_edges, addEdge_edges] at hab
      rw [pushDelta_nodes, addEdge_nodes]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact heq ▸ ⟨hsubjMem, hobjMem⟩
      · exact hpre.closed ab hmem
    · -- closed0
      exact hcl0
    · -- term
      intro k hk y hy
      rw [pushDelta_edges, addEdge_edges] at hy
      rcases List.mem_cons.mp hy with heq | hmem
      · have h1 : k = subjNode u.subject := (Prod.ext_iff.mp heq).1
        rw [h1] at hk
        exact ha hk
      · exact hpre.term k hk y hmem
  · rw [if_neg hb]
    have hb0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = false := by
      rw [← hadm]
      exact Bool.eq_false_iff.mpr hb
    rw [writeDirect_reject hb0]
    exact hsh

/-- The parallel write-leg fold maintains the shadow. -/
theorem untaintedShadow_writeLeg {Extra : NodeKey → Prop} {Sc : Schema}
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k) :
    ∀ (us : List Tuple) (σ σ0 : GraphState), ShadowOver Extra σ σ0 → σ.schema = Sc →
      (∀ u ∈ us, ¬ Extra (subjNode u.subject)) →
      ShadowOver Extra (us.foldl (fun acc u => acc.writeLoggedOne u) σ)
        (us.foldl (fun acc u => acc.writeDirect u) σ0) := by
  intro us
  induction us with
  | nil => intro σ σ0 hsh _ _; exact hsh
  | cons u rest ih =>
    intro σ σ0 hsh hsc hs
    simp only [List.foldl_cons]
    exact ih _ _ (untaintedShadow_writeLoggedOne hsh hsc (hs u List.mem_cons_self) hT hS)
      (by rw [writeLoggedOne_schema]; exact hsc)
      (fun x hx => hs x (List.mem_cons_of_mem _ hx))

/-- `FoldAdmits` is `EvalEq`-congruent (it reads only edges/nodes through
    `admitEdge`/`writeDirect`). -/
theorem foldAdmits_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) :
    ∀ (us : List Tuple), FoldAdmits σ us → FoldAdmits σ' us := by
  intro us
  induction us generalizing σ' σ with
  | nil => intro _; exact trivial
  | cons u rest ih =>
    intro hfa
    obtain ⟨hadm, hrest⟩ := hfa
    refine ⟨by rw [admitEdge_evalEq h]; exact hadm, ?_⟩
    exact ih (writeDirect_evalEq h u) hrest

/-- `FoldAdmitsBridged` is `EvalEq`-congruent too. ★ ADDITIVE, `P6` step 3b step 14
    (2026-09-14). It needs one more congruence than its plain twin — the prologue's
    (`Cascade.lean::bridgePre_evalEq`), because the probe reads `σ.bridgePre u` — and that is
    the only difference. -/
theorem foldAdmitsBridged_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) :
    ∀ (us : List Tuple), FoldAdmitsBridged σ us → FoldAdmitsBridged σ' us := by
  intro us
  induction us generalizing σ' σ with
  | nil => intro _; exact trivial
  | cons u rest ih =>
    intro hfa
    obtain ⟨hadm, hrest⟩ := hfa
    refine ⟨by rw [admitEdge_evalEq (bridgePre_evalEq h u)]; exact hadm, ?_⟩
    exact ih (writeBridgedOne_evalEq h u) hrest

/-- **Admission transfers to the shadow**: the logged (BRIDGED) fold and the shadow's plain
    fold accept the same writes.

    ★★ **`P6` step 3b step 14 (2026-09-14): the INPUT moved to `FoldAdmitsBridged`; the
    output did NOT.** That asymmetry is the theorem's whole content now, and it is the
    honest shape: the left fold bridges and the right one does not, so a single predicate
    cannot describe both. What it says is that the STRONGER hypothesis on the bridged side
    still yields the plain one on the shadow side — which is exactly the direction the
    shadow is used in, and the direction that would have been unsound the other way round. -/
theorem untaintedShadow_foldAdmits {Extra : NodeKey → Prop} {Sc : Schema}
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k) :
    ∀ (us : List Tuple) (σ σ0 : GraphState), ShadowOver Extra σ σ0 → σ.schema = Sc →
      (∀ u ∈ us, ¬ Extra (subjNode u.subject)) →
      FoldAdmitsBridged σ us → FoldAdmits σ0 us := by
  intro us
  induction us with
  | nil => intro σ σ0 _ _ _ _; exact trivial
  | cons u rest ih =>
    intro σ σ0 hsh hsc hs hfa
    obtain ⟨hadm1, hrest⟩ := hfa
    -- ⚠ the probe on the σ side reads the BRIDGED pre-state, so the shadow agreement has to
    -- be taken there — which is legal because the prologue itself shadows σ0.
    have hpre : ShadowOver Extra (σ.bridgePreLogged u) σ0 :=
      untaintedShadow_bridgePreLogged hsh hsc u hT hS
    have hadm0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true := by
      rw [← shadow_admitEdge_agree hpre (hs u List.mem_cons_self) (objNode u.object u.relation)]
      -- `bridgePreLogged` differs from `bridgePre` only in the outbox, which `admitEdge`
      -- does not read.
      rw [admitEdge_evalEq (bridgePreLogged_evalEq (EvalEq.refl σ) u)]
      exact hadm1
    refine ⟨hadm0, ?_⟩
    have hstep : ShadowOver Extra (σ.writeLoggedOne u) (σ0.writeDirect u) :=
      untaintedShadow_writeLoggedOne hsh hsc (hs u List.mem_cons_self) hT hS
    have hfd : FoldAdmitsBridged (σ.writeLoggedOne u) rest := by
      -- the logged step's CORE is `writeBridgedOne`, which is where the bridged fold
      -- continues; the two agree on everything `FoldAdmitsBridged` reads.
      exact foldAdmitsBridged_evalEq (writeLoggedOne_evalEq (EvalEq.refl σ) u) rest hrest
    exact ih _ _ hstep (by rw [writeLoggedOne_schema]; exact hsc)
      (fun x hx => hs x (List.mem_cons_of_mem _ hx)) hfd

/-! ### The TWO-LIST write leg — what THE FLIP (step 4c-ii) needs

`untaintedShadow_writeLeg` above pairs the SAME list on both folds. After the write-path
re-point the logged state folds `rewriteClosureL S (rawWriteTuples S t)` while the shadow
`σ0` keeps folding `rewriteClosure S t` (`ReachedByRulesAdmitted` is unchanged by the
adjudicated design), so the two lists genuinely differ and the one-list lemma no longer
types. The generalization below is stated over an arbitrary pair `us` / `vs` under exactly
the three relations the flip supplies:

* `hextra` — every logged-side member is a shadow-side member OR is `Extra`-TARGETED
  (`LeafRules.lean::rewriteClosureL_extras_leafNode`, at `Extra = DerNode ∨ LeafNode`);
* `hsub` — every shadow-side member is a logged-side member (the L closure is a superset);
* `hus` — no logged-side member has an `Extra` SUBJECT (`writeLegSubjectsWide_L`).

Nothing here is specific to the two closures, which is the point: the arithmetic of the
shadow is separated from the closure combinatorics. -/

/-- `ShadowOver` reads only edges and nodes, so it transports along `EvalEq` on the left. -/
theorem shadowOver_evalEq_left {Extra : NodeKey → Prop} {σ1 σ2 σ0 : GraphState}
    (h : EvalEq σ1 σ2) (hsh : ShadowOver Extra σ2 σ0) : ShadowOver Extra σ1 σ0 := by
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · rw [h.edges]; exact hsh.classify
  · rw [h.edges]; exact hsh.sub
  · rw [h.nodes]; exact hsh.nodesSub
  · rw [h.edges, h.nodes]; exact hsh.closed
  · exact hsh.closed0
  · rw [h.edges]; exact hsh.term

/-- **The two-list parallel write leg maintains the shadow.** The logged fold runs `us`
    from `σ`, the shadow's plain fold runs `vs` from `σ0`; both folds must be fully
    admitted, since the correspondence is now carried by edge COMPLETENESS on each side
    rather than by a shared step. -/
theorem untaintedShadow_writeLegL {Extra : NodeKey → Prop} {Sc : Schema}
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true → Extra (wAnyNode (ty, p)))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true → ¬ Extra k)
    (us vs : List Tuple) (σ σ0 : GraphState) (hsh : ShadowOver Extra σ σ0)
    (hsc : σ.schema = Sc)
    (hus : ∀ u ∈ us, ¬ Extra (subjNode u.subject))
    (hextra : ∀ u ∈ us, u ∈ vs ∨ Extra (objNode u.object u.relation))
    (hsub : ∀ u ∈ vs, u ∈ us)
    (hadmU : FoldAdmitsBridged σ us) (hadmV : FoldAdmits σ0 vs) :
    ShadowOver Extra (us.foldl (fun acc u => acc.writeLoggedOne u) σ)
      (vs.foldl (fun acc u => acc.writeDirect u) σ0) := by
  -- ★ `P6` step 3b (2026-09-14). `shadowOver_evalEq_left` retargets the LEFT fold, and
  -- after re-point #1 it lands on `writeBridgedOne`, not `writeDirect`. Every σ-side
  -- discharger below therefore moves to its bridged twin while every σ0-side one stays —
  -- that split is the whole repair, and the asymmetry is the design (`writeRules` is
  -- deliberately unbridged). ⚠ `hadmU` moved to `FoldAdmitsBridged` because
  -- `foldl_writeBridgedOne_edge_complete` CANNOT be stated over `FoldAdmits`
  -- (`Cascade.lean::FoldAdmitsHonestyWitness.foldl_edge_complete_is_false_for_the_bridged_fold`
  -- is the kernel refutation) — which is why step 14 is a precondition of this step and not
  -- a follow-up to it.
  refine shadowOver_evalEq_left (foldl_writeLoggedOne_evalEq us (EvalEq.refl σ)) ?_
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeBridgedOne_edges_sound us hab with hold | ⟨u, hu, h1, h2⟩ | ⟨hsw, h2⟩
    · rcases hsh.classify (a, b) hold with h0 | hE
      · exact Or.inl (foldl_writeDirect_edges_mono vs _ h0)
      · exact Or.inr hE
    · rcases hextra u hu with hv | hE
      · refine Or.inl ?_
        have hc := foldl_writeDirect_edge_complete vs hadmV u hv
        rw [show (a, b) = (subjNode u.subject, objNode u.object u.relation) from
          Prod.ext h1 h2]
        exact hc
      · exact Or.inr (by rw [show (a, b).2 = objNode u.object u.relation from h2]; exact hE)
    · -- ★ THE BRIDGE DISJUNCT: the edge is a bridge, so its target is an `Extra` and
      -- `classify` sends it right rather than looking for it in σ0. This is the obligation
      -- the third extras disjunct exists to discharge.
      refine Or.inr ?_
      show Extra (a, b).2
      rw [h2]
      exact hT a.type a.pred (hsc ▸ (bridgedInConcrete_elim hsw).2.2.2)
  · -- sub
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeDirect_edges_sound vs hab with hold | ⟨u, hu, h1, h2⟩
    · exact foldl_writeBridgedOne_edges_mono us _ (hsh.sub (a, b) hold)
    · rw [show (a, b) = (subjNode u.subject, objNode u.object u.relation) from
        Prod.ext h1 h2]
      exact foldl_writeBridgedOne_edge_complete us hadmU u (hsub u hu)
  · -- nodesSub
    intro k hk
    rcases foldl_writeDirect_nodes_sound vs σ0 k hk with hold | ⟨u, hu, hwk⟩
    · exact foldl_writeBridgedOne_nodes_mono us σ k (hsh.nodesSub k hold)
    · have hedge := foldl_writeBridgedOne_edge_complete us hadmU u (hsub u hu)
      have hcl := edgesClosed_foldl_writeBridgedOne us σ hsh.closed _ hedge
      rcases hwk with heq | heq
      · rw [heq]; exact hcl.1
      · rw [heq]; exact hcl.2
  · exact edgesClosed_foldl_writeBridgedOne us σ hsh.closed
  · exact edgesClosed_foldl_writeDirect vs σ0 hsh.closed0
  · -- term
    intro k hk y hy
    rcases foldl_writeBridgedOne_edges_sound us hy with hold | ⟨u, hu, h1, _⟩ | ⟨hsw, _⟩
    · exact hsh.term k hk y hold
    · exact hus u hu (h1 ▸ hk)
    · -- ★ THE BRIDGE DISJUNCT for `term`: the edge's SOURCE `k` is a bridged-in concrete, and
      -- `hS` says no such node is an `Extra` — so the premise `hk : Extra k` is impossible.
      -- This is where `T1` (`NoBridgedDerived`), `T2` (`not_bridgedInConcrete_of_leafNode`)
      -- and the `wAny`-variant disjointness are consumed, all through one hypothesis.
      exact hS k (bridgedInConcrete_elim hsw).1
        (hsc ▸ (bridgedInConcrete_elim hsw).2.2.2) hk

/-! ### The cascade leg preserves the shadow (σ0 fixed) -/

/-- Edges whose target is not the pass's R-node survive the diffing fold. -/
theorem reconcileKeyD_edge_pres_target (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState) (ab : NodeKey × NodeKey),
      ab.2 ≠ objNode ⟨dt, on⟩ R → ab ∈ σ.edges →
      ab ∈ (σ.reconcileKeyD T dt on R e cands).edges := by
  intro cands
  induction cands with
  | nil => intro σ ab _ hab; exact hab
  | cons c rest ih =>
    intro σ ab hne hab
    rw [reconcileKeyD_cons]
    split
    · exact ih _ ab hne (writeDirect_edges_mono σ _ ab hab)
    · refine ih _ ab hne ?_
      obtain ⟨a, b⟩ := ab
      exact mem_removeEdgePair_edges.mpr ⟨hab, fun h => hne h.2⟩

/-- Edges whose target is no job's R-node survive the whole diffing batch. -/
theorem reconcileJobsD_edge_pres_target {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (ab : NodeKey × NodeKey),
      (∀ j ∈ jobs, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R) → ab ∈ σ.edges →
      ab ∈ (reconcileJobsD S T σ jobs).edges := by
  intro jobs
  induction jobs with
  | nil => intro σ ab _ hab; exact hab
  | cons j rest ih =>
    intro σ ab hne hab
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    refine ih _ ab (fun j' hj' => hne j' (List.mem_cons_of_mem _ hj')) ?_
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    refine reconcileKeyD_edge_pres_target T j.dt j.on j.R j.e j.cands _ ab
      (hne j List.mem_cons_self) ?_
    rw [reconcileResidueKey_edges]
    exact hab

/-- The diffing batch only adds nodes. -/
theorem reconcileJobsD_nodes_mono {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ k ∈ σ.nodes,
      k ∈ (reconcileJobsD S T σ jobs).nodes := by
  intro jobs
  induction jobs with
  | nil => intro σ k hk; exact hk
  | cons j rest ih =>
    intro σ k hk
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    refine ih _ k ?_
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    refine reconcileKeyD_nodes_mono T j.dt j.on j.R j.e j.cands _ k ?_
    rw [reconcileResidueKey_nodes]
    exact hk

/-- **One diffing pass preserves the shadow** (the shadow state untouched): pass
    edges are `DerNode`-targeted, removals never hit shadow edges (a rules state has
    no in-edge at a derived R-node), sources stay off the `DerNode`s
    (bare candidates vs non-bare derived relations). Per-job form — every MID-BATCH
    state of a cascade keeps the shadow, hence the read bridge.

    **PRE-WIDENED (4c-ii step 8, 2026-09-01e).** This was one of the three declarations
    the 2026-09-01d flip probe reds, at both of its extras-touching proof steps —
    `Invalid ⟨…⟩` where `classify` BUILDS the extras witness, `unsolved goals` where
    `term` DESTRUCTURES it (`PROOF_STATUS.md` `## Session 2026-09-01d` §6). Both are
    repaired here in place, by step 5's `first | <post-flip form> | <today's form>`
    idiom (`CascadeStrataSettle.lean::untaintedShadow_writeLoggedOne_derived`, whose two
    extras-dependent steps are written that way) rather than by GENERALISE: no new
    declaration, no signature change, no call-site churn, and — since
    `Audit.lean:786` `#print axioms` this name — no risk to the audit pin.

    ⚠ The post-flip alternative is DEAD CODE on today's tree, so a sabotage cannot
    reach it (scope doc §11.13 trap (k): a weakening that hits a redundant guard fires
    for the wrong reason). Its control is therefore the flip PROBE, not a weakening —
    re-point the abbrev at the disjunction, build, and read whether this declaration is
    still in the error set. Run 2026-09-01e: it is NOT; see the docstring of
    `hoffW` below for what the branch actually needs, and the session entry for the
    literal before/after error sets.

    `hoffW` is the widened subject-side obligation, and it costs **no new premise**:
    `W3cJobValid`'s `hcb` conjunct already says every candidate's predicate is `BARE`,
    which `Leaf.lean::bare_subjNode_not_leafNode` turns into `¬ LeafNode`. That is the
    same "free at a BARE subject" fact step 5 used, and it is why the three `hsubj`
    sites over `rewriteClosure S t` are NOT free the same way — `rewriteStep`'s `.ttu`
    branch overwrites the subject predicate, so those need
    `rewriteClosure_subject_not_leafNode`'s two still-unowned premises. -/
theorem untaintedShadow_applyD {S : Schema} {T : Store} {σ σ0 : GraphState}
    {j : W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hjv : W3cJobValid S j) :
    UntaintedShadow S (j.applyD S T σ) σ0 := by
  obtain ⟨hRne, hcb, _, _, _, _, hder, hlke, hon⟩ := hjv
  have hco : ComputedOnly j.e := hCO j.dt j.R j.e hlke hder
  have hnojob : ∀ ab ∈ σ0.edges, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro ab hab heq
    have hno := reachedByRules_derived_no_inedge (on := j.on) hSV hlke hder hco h0 ab.1
    rw [← heq] at hno
    exact hno hab
  have hsound : ∀ a b, (a, b) ∈ (j.applyD S T σ).edges →
      (a, b) ∈ σ.edges ∨ ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
    intro a b hab
    unfold W3cJob.applyD at hab
    exact reconcileStarsKeyD_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands σ a b hab
  -- **PRE-WIDENED (4c-ii step 8).** The subject-side obligation stated at the POST-FLIP
  -- extras predicate, with zero new premises: `hcb` (a `W3cJobValid` conjunct) says every
  -- candidate's predicate is `BARE`, and `Leaf.lean::bare_subjNode_not_leafNode` refutes
  -- `LeafNode` there outright. The `DerNode` half is the argument this proof already made
  -- inline in `term`, lifted here so both halves live in one place.
  -- ★ `P6` step 3b step 8 (2026-09-14): the `BridgeNode` disjunct joins, and it is free for
  -- the THIRD time from the same `hcb`. `bridgeNode_elim` recovers `pred ≠ BARE` from
  -- `isSubjectWildcardUserset`'s OUTER guard, and a candidate's subject node has predicate
  -- `BARE` — so a cascade candidate can never be a bridge node. (That guard's placement has
  -- now paid three times: `bridgedInConcrete_elim`, `bridgeNode_elim`, and here. Do not push
  -- it inside the disjunction.)
  have hoffW : ∀ c ∈ j.cands,
      ¬ (DerNode S (subjNode c) ∨ LeafNode S (subjNode c) ∨ BridgeNode S (subjNode c)) := by
    rintro c hc (⟨dt, on, R, _, hRne', _, hkey⟩ | hleaf | hbr)
    · have hp : R = c.predicate := by
        have := congrArg NodeKey.pred hkey.symm
        simpa [objNode_pred, subjNode_pred] using this
      rw [hcb c hc] at hp
      exact hRne' hp
    · exact bare_subjNode_not_leafNode (hcb c hc) hleaf
    · refine (bridgeNode_elim hbr).2.2.1 ?_
      rw [subjNode_pred]
      exact hcb c hc
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases hsound a b hab with hold | ⟨c, _, _, h2⟩
    · exact hsh.classify (a, b) hold
    · first
      | exact Or.inr (Or.inl ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩)
      | exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
  · -- sub
    intro ab hab
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    refine reconcileKeyD_edge_pres_target T j.dt j.on j.R j.e j.cands _ ab
      (hnojob ab hab) ?_
    rw [reconcileResidueKey_edges]
    exact hsh.sub ab hab
  · -- nodesSub
    intro k hk
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    refine reconcileKeyD_nodes_mono T j.dt j.on j.R j.e j.cands _ k ?_
    rw [reconcileResidueKey_nodes]
    exact hsh.nodesSub k hk
  · -- closed
    intro ab hab
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD at hab ⊢
    refine edgesClosed_reconcileKeyD T j.dt j.on j.R j.e j.cands _ ?_ ab hab
    intro ab' hab'
    rw [reconcileResidueKey_edges] at hab'
    rw [reconcileResidueKey_nodes]
    exact hsh.closed ab' hab'
  · -- term
    intro k hk y hy
    rcases hsound k y hy with hold | ⟨c, hc, h1, _⟩
    · exact hsh.term k hk y hold
    · subst h1
      first
      | exact hoffW c hc hk
      | exact hoffW c hc (Or.inl hk)

/-- The unlogged diffing batch preserves the shadow — every prefix state of a
    cascade's job loop is shadowed, so the read bridge holds MID-BATCH. -/
theorem untaintedShadow_reconcileJobsD {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      ReachedByRules σ0 S T → StoreValidRules S T → NodupKeys S →
      (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
      (∀ j ∈ jobs, W3cJobValid S j) →
      UntaintedShadow S (reconcileJobsD S T σ jobs) σ0 := by
  intro jobs
  induction jobs with
  | nil => intro σ σ0 hsh _ _ _ _ _; exact hsh
  | cons j rest ih =>
    intro σ σ0 hsh h0 hSV hNK hCO hjv
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    exact ih _ _ (untaintedShadow_applyD hsh h0 hSV hNK hCO (hjv j List.mem_cons_self))
      h0 hSV hNK hCO (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))

/-- **A cascade leg preserves the shadow** (the shadow state is untouched). -/
theorem untaintedShadow_cascade {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs : List W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) :
    UntaintedShadow S (runCascade S T σ jobs) σ0 := by
  rcases runCascade_cases S T σ jobs with hrc | hrc
  · rw [hrc]
    have hev := reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs
    have hD := untaintedShadow_reconcileJobsD jobs σ σ0 hsh h0 hSV hNK hCO hjv
    exact ⟨fun ab hab => hD.classify ab (by rw [← hev.edges]; exact hab),
      fun ab hab => by
        show ab ∈ (reconcileJobsL S T σ jobs).edges
        rw [hev.edges]; exact hD.sub ab hab,
      fun k hk => by
        show k ∈ (reconcileJobsL S T σ jobs).nodes
        rw [hev.nodes]; exact hD.nodesSub k hk,
      fun ab hab => by
        show ab.1 ∈ (reconcileJobsL S T σ jobs).nodes
          ∧ ab.2 ∈ (reconcileJobsL S T σ jobs).nodes
        rw [hev.nodes]
        exact hD.closed ab (by rw [← hev.edges]; exact hab),
      hD.closed0,
      fun k hk y hy => hD.term k hk y (by rw [← hev.edges]; exact hy)⟩
  · rw [hrc]
    exact hsh

/-- **The packaged `hsubjW` the flip needs**, at the EXPLICIT disjunction rather than
    through the `UntaintedShadow` abbreviation (scope doc §11.13 trap (w)), and with the
    site's own `hterm` binder verbatim so the flip is a substitution rather than a re-proof.

    ⚠ **Position, not content, changed in round 2 of THE FLIP.** This declaration used to sit
    with its `NoLeafSubjects` section far below (next to
    `admissionNameShape_does_not_give_noLeafSubjects`, which refutes deriving `hnl` from the
    admission fields, and next to the `writeLegSubjectsWide_L_snlBoth` non-vacuity witness
    that still consumes it). It had to move ABOVE `reachedByW3d_shadow` the moment that
    theorem's `@write` arm started calling it: Lean has no forward declarations. Statement
    and proof are unchanged.

    `hnl` now arrives as `hLS.noLeafSubjects` (`LeafRules.lean::LeafScope`); `hterm` is the
    induction's own hypothesis, and `hbase` is `hDR` + `hSV` at `List.mem_cons_self`. -/
theorem writeLegSubjectsWide_L {S : Schema} {T : Store} {t : Tuple}
    (hnl : NoLeafSubjects S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hbase : NotLeafName t.subject.predicate) :
    ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
      ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)) := by
  rintro u hu (⟨dt, on, R, hder, _hRne, _hon, heq⟩ | hleaf)
  · obtain ⟨hnt, hns⟩ := hterm dt R hder
    have hpne : u.subject.predicate ≠ R :=
      rewriteClosureL_subject_pred_ne_of_noTtuTarget hnt hder
        (hns t List.mem_cons_self) hu
    apply hpne
    have hp := congrArg NodeKey.pred heq
    simpa [subjNode_pred, objNode_pred] using hp
  · exact rewriteClosureL_subject_not_leafNode hnl hbase u hu hleaf

/-- **The OBJECT half of the widened extras split, at the shadow's own disjunction.**
    `LeafRules.lean::rewriteClosureL_extras_leafNode` lands in
    `… ∨ LeafNode S (objNode …)`; `UntaintedShadow`'s `Extra` is
    `DerNode S · ∨ LeafNode S ·`, so the leaf disjunct is re-injected on the right. Packaged
    (rather than inlined at each of the five shadow sites) so all four of the scope facts it
    consumes arrive as ONE `LeafScope` projection set. -/
theorem writeLegExtrasWide_L {S : Schema} {t : Tuple}
    (hLS : LeafScope S) (hon : t.object.name ≠ STAR) :
    ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
      u ∈ rewriteClosure S t ∨
        (DerNode S (objNode u.object u.relation) ∨ LeafNode S (objNode u.object u.relation)
          ∨ BridgeNode S (objNode u.object u.relation)) :=
  -- ★ `P6` step 3b step 8 (2026-09-14): the third disjunct is WIDENING ONLY. A closure
  -- member's object node is never a bridge node, but this obligation does not have to say
  -- so — it is a disjunction, and the `LeafNode` arm already discharges every case. Do not
  -- be tempted to prove the stronger `¬ BridgeNode` here; it is owed at `term`
  -- (`hsubjWL`), not at `classify`.
  fun u hu =>
    (rewriteClosureL_extras_leafNode hLS.wf hLS.matchNotLeaf hLS.derivedNameNonempty hon
      u hu).imp id (fun h => Or.inr (Or.inl h))

/-- **The shadow's own plain-list admission, from the FAITHFUL (L-list) one.**

    Post-flip the write constructor carries `FoldAdmits σ (rewriteClosureL S (rawWriteTuples
    S t))` — the list the real system folds — while `ReachedByRulesAdmitted.step` still wants
    `FoldAdmits σ0 (rewriteClosure S t)` (the adjudicated design leaves the plain σ0 chain
    alone). There is no order-free `FoldAdmits`-restriction lemma, because `admitEdge` is
    ANTI-monotone in edges under a fuel tied to `nodes.length`; the honest bridge is
    `RestrictBase.lean::foldAdmits_of_acyclic`, which needs only that every materialised edge
    lands in ONE acyclic relation. Take that relation to be the edges of σ0's own full L-fold:
    it is acyclic because `writeDirect` cannot create a cycle (`structInv_foldl_writeDirect`
    off `σ0`'s `Inv`), it contains σ0's edges (fold monotonicity), and it contains every
    plain-closure edge because the plain closure is a SUBSET of the L closure
    (`LeafRules.lean::rewriteClosure_subset_rewriteClosureL`) and the L fold is fully
    admitted on σ0. -/
theorem foldAdmits_plain_of_L {S : Schema} {T : Store} {σ0 : GraphState} {t : Tuple}
    (h0 : ReachedByRulesAdmitted σ0 S T)
    (hadmL : FoldAdmits σ0 (rewriteClosureL S (rawWriteTuples S t)))
    (hsub : ∀ u ∈ rewriteClosure S t, u ∈ rewriteClosureL S (rawWriteTuples S t)) :
    FoldAdmits σ0 (rewriteClosure S t) := by
  have hSI0 : StructInv S σ0 :=
    (reachedByRules_inv (reachedByRules_of_admitted h0)).1.toStruct
  exact foldAdmits_of_acyclic
    (structInv_foldl_writeDirect (S := S) (rewriteClosureL S (rawWriteTuples S t)) hSI0).acyclic
    (rewriteClosure S t) hSI0
    (fun e he => foldl_writeDirect_edges_mono _ e he)
    (fun u hu => foldl_writeDirect_edge_complete _ hadmL u (hsub u hu))

/-! ### The shadow exists at every W3d state -/

/-- **`reachedByW3d_shadow`** — every W3d state has an untainted-core shadow: a
    rules-ADMITTED state on the CURRENT store agreeing on everything off the derived
    R-nodes. The store-dependent hypotheses sit right of the colon and weaken along
    the chain's prefix stores.

    ADDED HYPOTHESES (4c-ii step 9): `TtuTargetsSat S NotLeafName` and
    `DirectRestrictionsNotLeaf S`, both SCHEMA-level, appended last in the `_d` precedent's
    style. They are what `hsubjW` below needs, and being schema-level they cost no
    weakening line at the recursive call — see scope doc §11.13 **(p)**.

    ADDED BY THE FLIP (4c-ii step 4c-ii, round 2): `LeafScope S` (SCHEMA-level, so again no
    weakening line) and `BareStarStore T` (STORE-level, so it gets one). The first is the
    four-field carrier the leaf-routed write leg's two extras obligations need
    (`LeafRules.lean::LeafScope`); the second supplies `t.object.name ≠ STAR`, which is
    `LeafNode`'s `on ≠ STAR` conjunct and cannot come from the schema. Every existing caller
    of this theorem already holds a `BareStarStore` for the same store.

    ⚠ **`TtuTargetsSat S NotLeafName` (the 5th premise) is now DEAD in this proof** — its only
    consumer was the plain-list `hsubjW`, which the flip deleted, and it is in any case
    subsumed by `hLS.noLeafSubjects` through `ttuTargetsSat_notLeafName_of_noLeafSubjects`
    (`:859`). It is retained because it is positional at ~16 call sites across five modules
    and every one of those callers still consumes its own `hQ` for the read bridge; dropping
    it is a mechanical follow-up, not a correctness question. The same note applies verbatim
    to the two `CascadeStrataSettle.lean` twins. -/
theorem reachedByW3d_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    StoreValidRules S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    TtuTargetsSat S NotLeafName →
    DirectRestrictionsNotLeaf S →
    LeafScope S →
    BareStarStore T →
    NoBridgedDerived S →
    TtuTuplesetsDirect S →
    TtuStarFree S T →
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm hprev ih =>
    intro hNK hCO hSV hterm hQ hDR hLS hBS hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
      hQ hDR hLS (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht'))
      hNBD hTT (fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht'))
    -- ⚠ The PLAIN-list subject fact (`hsubjW`, the pre-flip `rewriteClosure S t` form built
    -- from `rewriteClosure_subject_pred_ne` + `rewriteClosure_subject_not_leafNode hQ`) was
    -- DELETED here in round 2, not commented out: post-flip its only consumer was
    -- `untaintedShadow_foldAdmits` on the plain list, and that call now runs on the L list
    -- through `hsubjWL` below, which is strictly stronger (the plain closure is a subset —
    -- `hsubL`). Leaving it would have been dead code that still type-checks, i.e. exactly
    -- the shape §11.13 trap (n) warns about. `hQ` survives as a premise because the two
    -- W3d-2 twins and the read bridge still consume it.
    -- ══ THE FLIP (step 4c-ii), the shadow write leg ═════════════════════════════════
    -- `σp` now folds `rewriteClosureL S (rawWriteTuples S t)`; `σ0` still folds
    -- `rewriteClosure S t` (the adjudicated design leaves `ReachedByRulesAdmitted`
    -- alone). `untaintedShadow_writeLegL` is the two-list form; the seed is UNTAINTED
    -- here (`hunt` below), so the two closures share their seed and the L one is a
    -- superset whose extras are all leaf-targeted.
    have hunt : isDerived S (t.object.type, t.relation) = false := by
      obtain ⟨e, rs, hlk, hrs, _⟩ := hSV t List.mem_cons_self
      by_contra hcon
      rw [Bool.not_eq_false] at hcon
      rw [exprDirects_computedOnly (hCO _ _ _ hlk hcon)] at hrs
      simp at hrs
    have hsubL : ∀ u ∈ rewriteClosure S t, u ∈ rewriteClosureL S (rawWriteTuples S t) :=
      fun _ hu => rewriteClosure_subset_rewriteClosureL (mem_rawWriteTuples_self hunt) hu
    -- OBLIGATION (D) — DISCHARGED. `hnl` is `hLS.noLeafSubjects`, from the threaded
    -- `LeafScope` carrier; it is PROVABLY not derivable from the name-shape fields
    -- `GraphAdmission` already carried (`admissionNameShape_does_not_give_noLeafSubjects`
    -- below), which is why the carrier exists.
    have hsubjWL0 : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
        ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)) :=
      writeLegSubjectsWide_L hLS.noLeafSubjects hterm
        (noLeafStoreSubjects_of_storeValidRules hDR hSV t List.mem_cons_self)
    -- ★ **`P6` step 3b step 8's `T3`, DISCHARGED HERE** (2026-09-14). The widened extras
    -- predicate adds `BridgeNode`, so obligation (D) gains a third disjunct: no member of
    -- the list the re-pointed write leg folds has a bridge node as its SUBJECT. That is
    -- `not_bridgeNode_of_star_bare`, and its six premises are every one of them FREE at this
    -- site — `hNK` and `hCO` are premises 1 and 2, `hmd` comes from `hLS.matchNotLeaf`,
    -- `hBS` is premise 8, and `hTT`/`hTS` are the TWO NEW BINDERS this step costs
    -- (`TtuTuplesetsDirect S`, `TtuStarFree S T`), both already bound at all five call sites.
    -- Nothing new is assumed that the fragment did not already carry.
    have hsubjWL : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
        ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
          ∨ BridgeNode S (subjNode u.subject)) := by
      intro u hu hc
      rcases hc with h | h | h
      · exact hsubjWL0 u hu (Or.inl h)
      · exact hsubjWL0 u hu (Or.inr h)
      · exact not_bridgeNode_of_star_bare hNK hCO hLS.matchNotLeaf hTT hTS hBS
          (t := t) List.mem_cons_self hu h
    -- OBLIGATION (E), object half — DISCHARGED through `writeLegExtrasWide_L`; `hon` is the
    -- head tuple's `BareStarStore` conjunct.
    have hextraL := writeLegExtrasWide_L (t := t) hLS (hBS t List.mem_cons_self).2
    -- OBLIGATION (E), admission half — DISCHARGED. The write constructor's `hadm` is the
    -- L-list one (the FAITHFUL admission: the real system folds that list); the shadow's
    -- `ReachedByRulesAdmitted.step` wants the plain-list one. Transfer the L-list admission
    -- to σ0 first (`untaintedShadow_foldAdmits`, which is list-generic and consumes exactly
    -- the (D) fact just proved), then restrict to the plain sublist THERE, where σ0's own
    -- `Inv.acyclic` is available — see `foldAdmits_plain_of_L`. Restricting on the σp side
    -- instead is what looked impossible: `FoldAdmits` has no order-free restriction lemma,
    -- and σp's acyclicity is `CascadeInv.lean::reachedByW3d_structInv`, which is DOWNSTREAM
    -- of this module.
    -- ★ The two shadow-side bridge obligations, discharged once and reused at both call
    -- sites below. `hTshadow` routes the bridge TARGET onto the new `BridgeNode` disjunct;
    -- `hSshadow` is where `T1` and `T2` are consumed — a bridged-in concrete is neither a
    -- `DerNode` (`hNBD`) nor a `LeafNode` (`not_bridgedInConcrete_of_leafNode`) nor a
    -- `BridgeNode` (variant: a bridge source is `plain`, a bridge node is `wAny`).
    have hTshadow : ∀ ty p, S.isSubjectWildcardUserset ty p = true →
        (DerNode S (wAnyNode (ty, p)) ∨ LeafNode S (wAnyNode (ty, p))
          ∨ BridgeNode S (wAnyNode (ty, p))) :=
      fun ty p h => Or.inr (Or.inr (bridgeNode_wAnyNode h))
    have hSshadow : ∀ k : NodeKey, k.variant = Variant.plain →
        S.isSubjectWildcardUserset k.type k.pred = true →
        ¬ (DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) := by
      intro k hkv hksw hc
      rcases hc with ⟨dt, on, R, hder', _, hon', rfl⟩ | hleaf | hbr
      · -- T1: `NoBridgedDerived` un-bridges every derived key, and this node's SHAPE is
        -- exactly that key (`objNode_type` / `objNode_pred`).
        rw [objNode_type, objNode_pred] at hksw
        rw [hNBD dt R hder'] at hksw
        exact Bool.noConfusion hksw
      · -- T2: a leaf-named predicate is never a bridged-in SHAPE. Taken at the shape level
        -- (`isSubjectWildcardUserset_false_of_notLeafName`) rather than through
        -- `not_bridgedInConcrete_of_leafNode`, because the goal here is about the shape and
        -- routing through the state predicate would drag in a `name ≠ STAR` side condition
        -- that says nothing extra.
        have hnl : ¬ NotLeafName k.pred := fun h => not_leafNode_of_notLeafName h hleaf
        rw [isSubjectWildcardUserset_false_of_notLeafName hNK hCO hQ hDR hnl] at hksw
        exact Bool.noConfusion hksw
      · exact Variant.noConfusion (hkv ▸ (bridgeNode_elim hbr).1)
    have hadmVL : FoldAdmits σ0 (rewriteClosureL S (rawWriteTuples S t)) :=
      untaintedShadow_foldAdmits hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t))
        σp σ0 hsh (reachedByW3d_schema hprev) hsubjWL hadm
    have hadmV : FoldAdmits σ0 (rewriteClosure S t) :=
      foldAdmits_plain_of_L h0 hadmVL hsubL
    exact ⟨σ0.writeRules S t,
      ReachedByRulesAdmitted.step t h0 hadmV,
      untaintedShadow_writeLegL hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t))
        (rewriteClosure S t) σp σ0 hsh (reachedByW3d_schema hprev)
        hsubjWL hextraL hsubL hadm hadmV⟩
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hNK hCO hSV hterm hQ hDR hLS hBS hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSV hterm hQ hDR hLS hBS hNBD hTT hTS
    exact ⟨σ0, h0,
      untaintedShadow_cascade hsh (reachedByRules_of_admitted h0) hSV hNK hCO hjv⟩

/-! ### The W3d read bridge -/

/-- Untainted operand reads agree with the shadow — for EVERY subject and object:
    the probe targets (the operand node, the operand `wAll` node) are never
    `DerNode`s, so all four probes read identically. -/
theorem shadow_graphRec_agree {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) (s : SubjectRef) {dt' : String} (on' : String)
    {r' : String} (hnl : ¬ LeafNode S (objNode ⟨dt', on'⟩ r'))
    (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec σ s dt' on' r' = GraphModel.graphRec σ0 s dt' on' r' := by
  have hv1 : ¬ (DerNode S (objNode ⟨dt', on'⟩ r') ∨ LeafNode S (objNode ⟨dt', on'⟩ r')
      ∨ BridgeNode S (objNode ⟨dt', on'⟩ r')) := by
    rintro (⟨dt, on, R, hder, _, _, heq⟩ | hleaf | hbr)
    · have htype : dt' = dt := by
        have := congrArg NodeKey.type heq
        simpa [objNode_type] using this
      have hpred : r' = R := by
        have := congrArg NodeKey.pred heq
        simpa [objNode_pred] using this
      rw [htype, hpred, hder] at hunt
      cases hunt
    · exact hnl hleaf
    · -- ★ `P6` step 3b step 8 (2026-09-14): the THIRD disjunct, and it costs NO new
      -- premise — the same variant argument the other two use. A bridge node is `wAny`
      -- (`bridgeNode_elim`); an `objNode` never is (`State.lean::objNode_ne_wAny`), at any
      -- object name including `STAR`. This is what makes the widening cheap on the READ
      -- side: `shadow_reach_agree` is applied tree-wide at exactly two target shapes,
      -- `objNode ⟨dt',on'⟩ r'` and `wAllNode dt' r'`, and a `wAnyNode` matches neither.
      exact objNode_ne_wAny ⟨dt', on'⟩ r' (bridgeNode_elim hbr).1
  -- PRE-WIDENED (4c-ii step 6, 2026-08-31c). This `have` is deliberately STRONGER than
  -- what `shadow_reach_agree` asked for BEFORE the flip, which is why the two uses below
  -- used to go through `Or.inl`. **The re-point has happened (4c-ii, 2026-09-02d):**
  -- `UntaintedShadow` now abbreviates `ShadowOver (fun k => DerNode S k ∨ LeafNode S k)`,
  -- so `shadow_reach_agree` wants exactly this statement and the wrappers are gone --
  -- the flip cost this declaration four deleted wrappers and no proof. Same pattern as
  -- `CascadeStrataSettle.lean:960`. Do NOT "simplify" it back to the `DerNode`-only form.
  --
  -- It costs no new premise, and that is a fact about `wAll` nodes rather than luck:
  -- `State.lean::wAllNode` is `⟨t, STAR, R, Variant.wAll⟩`, while `Leaf.lean::LeafNode`
  -- carries `on ≠ STAR ∧ k = objNode ⟨ty,on⟩ p`, which `DirectCorrect.lean::objNode_plain`
  -- turns into `Variant.plain`. So the LeafNode disjunct dies by the SAME variant mismatch
  -- the DerNode branch already used. Pinned against vacuity by the discriminating pair
  -- `Leaf.lean::minted_leaf_is_leafNode` (true) / `::wAllNode_not_leafNode` (false) --
  -- same schema, same type, same predicate, differing only in node shape.
  --
  -- ⚠ `hv1` was NOT free the same way, and this block used to say so and record the
  -- binder as DEFERRED. **That is spent: the binder LANDED with 4c-ii (2026-09-02d)**,
  -- and the two obstacles it named were closed by two DIFFERENT routes, which is the
  -- fact worth keeping. `hv1` needs `NotLeafName r'` for the OPERAND relation, which
  -- `hunt` does not give (a minted leaf name like `viewer.0` is itself non-derived while
  -- `leafPublic` of it is derived), so the premise had to arrive from the caller.
  --
  -- Route 1 -- the 11 MEMBERSHIP sites (scope-doc 11.13 trap (g), closed 2026-09-01d):
  -- both `ReconcileStars.lean::checkFn_agree_of_graphRec{,_cd}` carry
  -- `r' ∈ computedRefs e`, and `::checkFn_agree_of_graphRec_notLeafNode` above turns that
  -- into `¬ LeafNode S (objNode ⟨dt,on⟩ r')` for a caller holding `ComputedRefsNotLeaf S`.
  --
  -- Route 2 -- the 3 QUERY sites (`CascadeSettle.lean::graph_correct_w3d`,
  -- `CascadeStrataResettle.lean::graph_correct_w3d2{,_d}`) instantiate `r'` with the
  -- arbitrary QUERY's own relation, where no `computedRefs` membership exists at all.
  -- They discharge `hnl` from headline row 27's query guard instead, via
  -- `Leaf.lean::not_leafNode_of_publicOfLeaf_none`. **The two routes are not
  -- interchangeable and that is machine-checked, not asserted**: SAB-4 (2026-09-02d)
  -- mis-typed `hql` inside `graph_correct_w3d2_d` alone and got EXACTLY ONE error, at
  -- that declaration's query site, while its MEMBERSHIP site stayed green.
  --
  -- 14 sites, 11 + 3, and they are why "thread the predicate" and "add the query
  -- premise" could not be separated: `graph_correct_w3d2` and `_d` each host ONE OF EACH.
  have hv3 : ¬ (DerNode S (wAllNode dt' r') ∨ LeafNode S (wAllNode dt' r')
      ∨ BridgeNode S (wAllNode dt' r')) := by
    rintro (⟨dt, on, R, _, _, hon, heq⟩ | ⟨ty, on, p, _, _, hon, heq⟩ | hbr)
    · rw [objNode_plain hon] at heq
      have := congrArg NodeKey.variant heq
      simp [wAllNode] at this
    · rw [objNode_plain hon] at heq
      have := congrArg NodeKey.variant heq
      simp [wAllNode] at this
    · -- ★ `P6` step 3b step 8 (2026-09-14): `wAll` ≠ `wAny`, the third variant mismatch in
      -- a row. Both extras added since 4c-ii die here for the same structural reason, which
      -- is why the read side kept every statement across both widenings.
      have := (bridgeNode_elim hbr).1
      simp [wAllNode] at this
  unfold GraphModel.graphRec GraphModel.probeNonDerived
  dsimp only
  rw [shadow_reach_agree hsh hv1 (subjNode s), shadow_reach_agree hsh hv1 (wAnyNode s.shape),
    shadow_reach_agree hsh hv3 (subjNode s),
    shadow_reach_agree hsh hv3 (wAnyNode s.shape)]

/-- **The W3d read bridge (`checkFn_eq_sem_w3d`)**: the compiled pass guard equals
    `sem` at EVERY W3d state — through the untainted-core shadow (`checkFn` reads
    only untainted operands; `checkFn_eq_sem_bs` at the rules-admitted shadow).
    Subject-generic up to star-BARE subjects. -/
theorem checkFn_eq_sem_w3d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcr : ComputedRefsNotLeaf S)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hstep : σ.checkFn T s dt on R e = σ0.checkFn T s dt on R e :=
    checkFn_agree_of_graphRec_notLeafNode T s dt on R e hco hcr hlk hleafUnt
      (fun s' r' hnl hr' => shadow_graphRec_agree hsh s' on hnl hr')
  rw [hstep]
  exact checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
    (ReachedByW3aAdmitted.base h0) hlk hco hleafUnt hs hon

/-! ## Write-leg settledness transport — unmapped keys keep representation AND meaning

A logged write leg cannot touch any derived key's materialised representation (rows
are write-inert, and no rule-routed edge lands on a derived R-node — model-level
I5 exclusivity). The semantic complement (`writeLeg_sem_stable`): at an UNMAPPED key
the write does not change `sem` either — because the guard equals `sem` on both sides
of the leg (the W3d read bridge, at both stores) and the guard is unchanged
(fan-out completeness). Together: `SettledKey` transports across write legs at
unmapped keys (`settledKey_writeLeg`). -/

/-- A write leg never touches any residue row.

    ★ `P6` step 3b (2026-09-14): statement unchanged. The bridge prologue is residue-inert
    for the same reason the grant is — it only interns nodes and adds edges — so this is a
    one-line swap onto `UsStarWrite.lean::writeBridgedOne_residue`. -/
theorem writeLoggedRules_residue (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeLoggedRules S t).residue = σ.residue := by
  rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).residue]
  show ((rewriteClosureL S (rawWriteTuples S t)).foldl
    (fun acc u => acc.writeBridgedOne u) σ).residue = σ.residue
  generalize rewriteClosureL S (rawWriteTuples S t) = us
  induction us generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih, writeBridgedOne_residue]

/-- **No rule of the FULL leaf-routed rule set outputs onto a DERIVED key.** The
    `schemaRewritesL` extension of `RulesWrite.lean::noRuleOutputs_of_derived`: the untainted
    half is that lemma verbatim, and the leaf half is refuted by NAME — a `leafRewrites` rule
    targets a minted `leafPred` while a derived key's own relation is dot-free
    (`relNameOK_of_isDerived`). Step 4c-ii; consumed wherever a post-flip closure member's
    target node had to be shown off the R-node. -/
theorem noRuleOutputsL_of_derived {S : Schema} (hWF : WF S) {dt R : String}
    (hder : isDerived S (dt, R) = true) (r : RRule) (hr : r ∈ schemaRewritesL S)
    (h : r.objectType = dt ∧ r.outRel = R) : False := by
  rw [schemaRewritesL, List.mem_append] at hr
  rcases hr with hu | hl
  · exact noRuleOutputs_of_derived hder r hu h
  · have hlp := isLeafPred_outRel_of_mem_leafRewrites hl
    rw [h.2, isLeafPred_eq_false_of_relNameOK
      (relNameOK_of_isDerived hWF (k := (dt, R)) hder)] at hlp
    exact Bool.noConfusion hlp

/-- **Write legs never touch a derived key's in-edges** (model-level I5
    exclusivity): a routed closure member cannot land on the R-node (a stored `(dt,R)`
    tuple would need a `Direct` arm, a rewrite output a rule onto `(dt,R)` — both dead
    on a `ComputedOnly` derived def / the taint filter), and write legs remove nothing. -/
theorem writeLeg_derived_inedges_eq {σ : GraphState} {S : Schema} {t : Tuple} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S (t :: T))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  -- **RE-POINTED by step 4c-ii (THE FLIP).** The write leg now folds the leaf-routed
  -- closure, so BOTH arms of `rewriteClosureL_produced` gained a case, and both new cases
  -- are refuted by the SAME fact: `R` is a derived key's relation name, hence dot-free
  -- (`relNameOK_of_isDerived`), while every leaf-routed seed relation and every
  -- `leafRewrites` output relation is a minted `leafPred`, hence dot-carrying. That is why
  -- `hWF` is a new premise here — the flip's only added hypothesis at this site.
  have hRok : relNameOK R := relNameOK_of_isDerived hWF (k := (dt, R)) hder
  constructor
  · intro h
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges] at h
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) h
      with hold | ⟨w, hw, _h1, h2⟩ | ⟨_, h2⟩
    · exact hold
    · exfalso
      have htype : dt = w.object.type := by
        simpa [objNode_type] using congrArg NodeKey.type h2
      have hrel : R = w.relation := by
        simpa [objNode_pred] using congrArg NodeKey.pred h2
      rcases rewriteClosureL_produced hw with hseed | ⟨r, hr', hro, hrout⟩
      · -- the member is a re-addressed SEED (`rawWriteTuples`), not a rewrite output
        by_cases hd : isDerived S (t.object.type, t.relation) = true
        · -- derived raw write: every seed relation is a leaf name, `R` is not
          obtain ⟨r0, hr0, hw0⟩ := List.mem_map.mp hseed
          obtain ⟨i, hi⟩ := mem_rawWriteRels_derived hd hr0
          have hwr : w.relation = r0 := by rw [← hw0]
          exact leafPred_ne_relName hRok t.relation i (by rw [← hi, ← hwr, ← hrel])
        · -- untainted raw write: the seed list is `[t]`, so this is the pre-flip argument
          rw [rawWriteTuples_untainted (by simpa using hd)] at hseed
          have heq : w = t := List.mem_singleton.mp hseed
          rw [heq] at htype hrel
          obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t List.mem_cons_self
          rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
          rw [← hlk', exprDirects_computedOnly hco] at hrs
          simp at hrs
      · rw [schemaRewritesL, List.mem_append] at hr'
        rcases hr' with hru | hrl
        · exact noRuleOutputs_of_derived hder r hru
            ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
        · -- a leaf rule's output relation is a leaf name, `R` is not
          have hlp := isLeafPred_outRel_of_mem_leafRewrites hrl
          rw [hrout, ← hrel, isLeafPred_eq_false_of_relNameOK hRok] at hlp
          exact Bool.noConfusion hlp
    · -- ★ `P6` step 3b (2026-09-14): the BRIDGE disjunct, and it costs one line. The edge's
      -- target here is `wAnyNode (u.type, u.pred)`, but the goal's target is
      -- `objNode ⟨dt, on⟩ R`, which is never `wAny` (`State.lean::objNode_ne_wAny`). No
      -- premise, no `relNameOK` machinery, any `on` including `STAR`. The whole hRok/leaf
      -- chain above is untouched.
      exact absurd (congrArg NodeKey.variant h2) (objNode_ne_wAny ⟨dt, on⟩ R)
  · exact fun h => writeLoggedRules_edges_mono σ S t _ h

/-- `checkFn` ignores its store argument on `ComputedOnly` defs (the store feeds only
    the dead `direct`/`ttu` leaves). -/
theorem checkFn_store_irrel {σ : GraphState} (T1 T2 : Store) (s : SubjectRef)
    (dt on R : String) {e : Expr} (hco : ComputedOnly e) :
    σ.checkFn T1 s dt on R e = σ.checkFn T2 s dt on R e := by
  unfold GraphState.checkFn
  exact evalE_computedOnly e hco (fun _ _ => rfl)

/-- **`writeLeg_sem_stable` — an unmapped key keeps its MEANING.** If a logged write
    does not map the derived key, `sem` at that key is unchanged by the write: the
    guard equals `sem` on both sides of the leg (the W3d read bridge at both stores)
    and the guard itself is stable (fan-out completeness). The semantic form of the
    cross-key hazard's absence. -/
theorem writeLeg_sem_stable {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hQ : TtuTargetsSat S NotLeafName) (hDR : DirectRestrictionsNotLeaf S)
    (hLS : LeafScope S)
    (hcr : ComputedRefsNotLeaf S)
    (hNBD : NoBridgedDerived S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (h : ReachedByW3d σ S T) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  -- the fragment weakens to the pre-write store
  have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
  have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
  have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
  have htermw : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
  have h' : ReachedByW3d (σ.writeLoggedRules S t) S (t :: T) :=
    ReachedByW3d.write t hadm h
  obtain ⟨σ0', h0', hsh'⟩ :=
    reachedByW3d_shadow h' hNK hCO hSV hterm hQ hDR hLS hBS hNBD hTT hTS
  obtain ⟨σ0, h0, hsh⟩ :=
    reachedByW3d_shadow h hNK hCO hSVw htermw hQ hDR hLS hBSw hNBD hTT hTSw
  have hclσ := reachedByW3d_edgesClosed h
  have htp' := reachedByW3d_edges_target_plain h' hBS
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFn (t :: T) s dt on R e :=
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hcr
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSVw hBSw hTSw hCO hMatch hStrat htermw hcr
          h0 hsh hlk hco hleafUnt hs hon

/-! ## `SettledKey` — the per-key soundness-side settledness predicate

The derived key's materialised representation reads at `sem` level against the
CURRENT store. This is the soundness half (what IS materialised is right); the
completeness clauses (row existence, `neg`/`upos`/edge completeness) live with the
audit-enumeration coverage layer (W3d-1c), mirroring the W3c split. -/

/-- The row's members carry their `sem` verdicts; every derived edge witnesses a
    `sem`-true bare star-free subject. -/
def SettledKey (S : Schema) (T : Store) (σ : GraphState) (dt on R : String) : Prop :=
  (∀ res, σ.residue (objNode ⟨dt, on⟩ R) R = some res →
    (∀ sh, res.stars.contains sh = true ↔
      (sh ∈ wildcardShapes S ∧ sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true)) ∧
    (∀ n ∈ res.neg, n.name ≠ STAR ∧ sem S T ⟨n, R, ⟨dt, on⟩⟩ = false) ∧
    (∀ n ∈ res.upos, n.predicate ≠ BARE ∧ n.name ≠ STAR ∧
      sem S T ⟨n, R, ⟨dt, on⟩⟩ = true)) ∧
  (∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR →
    (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges →
    sem S T ⟨s, R, ⟨dt, on⟩⟩ = true)

/-- **Settledness transports across a write leg at an unmapped key**: the
    representation is untouched (rows write-inert, derived in-edges fixed) and the
    key's `sem` is unchanged (`writeLeg_sem_stable`). `hWSbare` scopes the star
    subjects the row mentions to bare shapes (decision-15). -/
theorem settledKey_writeLeg {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hQ : TtuTargetsSat S NotLeafName) (hDR : DirectRestrictionsNotLeaf S)
    (hLS : LeafScope S)
    (hcr : ComputedRefsNotLeaf S)
    (hNBD : NoBridgedDerived S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d σ S T) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hon : on ≠ STAR)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  have hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    fun s hs => writeLeg_sem_stable hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat
      hQ hDR hLS hcr hNBD hterm h hadm hlk hder hco hleafUnt hunmapped hs hon
  constructor
  · intro res hres
    rw [writeLoggedRules_residue] at hres
    obtain ⟨h1, h2, h3⟩ := hrow res hres
    refine ⟨?_, ?_, ?_⟩
    · intro sh
      rw [h1 sh]
      constructor
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
    · intro n hn
      obtain ⟨hnstar, hsm⟩ := h2 n hn
      refine ⟨hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
    · intro n hn
      obtain ⟨hnp, hnstar, hsm⟩ := h3 n hn
      refine ⟨hnp, hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
  · intro s hb hstar hedge'
    rw [writeLeg_derived_inedges_eq hWF hSV hlk hder hco (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-! ## Cascade legs at untargeted keys — settledness is untouched -/

/-- A diffing pass touches no residue row and no in-edge at ANOTHER concrete key. -/
theorem applyD_other_key_fixed {S : Schema} {T : Store} {σ : GraphState} {j : W3cJob}
    (hjv : W3cJobValid S j) {dt on R : String} (hon : on ≠ STAR)
    (hnot : ¬ j.keyMatch dt on R) :
    (j.applyD S T σ).residue (objNode ⟨dt, on⟩ R) R = σ.residue (objNode ⟨dt, on⟩ R) R ∧
    ∀ u : NodeKey, ((u, objNode ⟨dt, on⟩ R) ∈ (j.applyD S T σ).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  obtain ⟨_, _, _, _, _, _, _, _, honj⟩ := hjv
  have hne_node : objNode ⟨dt, on⟩ R ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro heq
    obtain ⟨h1, h2, h3⟩ := objNode_inj_of_ne_star hon honj heq
    exact hnot ⟨h1.symm, h2.symm, h3.symm⟩
  constructor
  · show (σ.reconcileStarsKeyD T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
      j.uposCands).residue (objNode ⟨dt, on⟩ R) R = _
    exact reconcileStarsKeyD_residue_other (fun h => hne_node h.1)
  · intro u
    constructor
    · intro h
      unfold W3cJob.applyD at h
      rcases reconcileStarsKeyD_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ u _ h with hold | ⟨c, _, _, h2⟩
      · exact hold
      · exact absurd h2 hne_node
    · intro h
      unfold W3cJob.applyD GraphState.reconcileStarsKeyD
      refine reconcileKeyD_edge_pres_target T j.dt j.on j.R j.e j.cands _
        (u, objNode ⟨dt, on⟩ R) hne_node ?_
      rw [reconcileResidueKey_edges]
      exact h

/-- The whole diffing batch leaves an untargeted concrete key's row and in-edges
    untouched. -/
theorem reconcileJobsD_other_key_fixed {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) {dt on R : String}, on ≠ STAR →
      (∀ j ∈ jobs, W3cJobValid S j) → (∀ j ∈ jobs, ¬ j.keyMatch dt on R) →
      (reconcileJobsD S T σ jobs).residue (objNode ⟨dt, on⟩ R) R
          = σ.residue (objNode ⟨dt, on⟩ R) R ∧
      ∀ u : NodeKey, ((u, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsD S T σ jobs).edges
        ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  intro jobs
  induction jobs with
  | nil => intro σ dt on R _ _ _; exact ⟨rfl, fun u => Iff.rfl⟩
  | cons j rest ih =>
    intro σ dt on R hon hjv hnot
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    obtain ⟨hres1, hedge1⟩ := applyD_other_key_fixed (hjv j List.mem_cons_self) hon
      (hnot j List.mem_cons_self)
    obtain ⟨hres2, hedge2⟩ := ih (j.applyD S T σ) hon
      (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))
      (fun j' hj' => hnot j' (List.mem_cons_of_mem _ hj'))
    exact ⟨hres2.trans hres1, fun u => (hedge2 u).trans (hedge1 u)⟩

/-- **Settledness is untouched by a cascade at untargeted keys**: the store is
    unchanged (so the key's `sem` is), and the passes touch only their own keys'
    rows and in-edges. -/
theorem settledKey_cascade_untargeted {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R) (hon : on ≠ STAR)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S T (runCascade S T σ jobs) dt on R := by
  rcases runCascade_cases S T σ jobs with hrc | hrc
  · rw [hrc]
    obtain ⟨hrow, hedge⟩ := hset
    have hev := reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs
    obtain ⟨hres, hedges⟩ := reconcileJobsD_other_key_fixed jobs σ hon hjv hnot
    constructor
    · intro res hresrow
      refine hrow res ?_
      rw [← hres, ← hev.residue]
      exact hresrow
    · intro s hb hstar hedge'
      refine hedge s hb hstar ?_
      rw [← (hedges (subjNode s)), ← hev.edges]
      exact hedge'
  · rw [hrc]
    exact hset

/-! ## Retraction-leg duals (R5b-iii-a) — the settledness-dual stack, reach/edge level

Retraction duals of the write-leg stability lemmas above, for `removeLoggedRules`. The
write leg ADDS edges (monotone); the retraction ERASES edges (anti-monotone), so the
"fragment fence"/plainness hypotheses land on the BIGGER state — here the PRE-state `σ`
(the write leg fences its post-state, likewise the bigger one). Two path helpers carry
the anti-monotone reasoning: `nreaches_factor_last` (a LAST-marked-edge decomposition
with the suffix in the smaller kept edge set — mirror of `nreaches_factor`'s FIRST-marked
decomposition) and `removeLoggedRules_edge_delta` (a retracted edge carries a frontier
row at its target — mirror of `writeLoggedRules_edge_delta`). -/

/-- **Last-marked-edge decomposition** (retraction dual of `nreaches_factor`). A path over
    `E` whose edges are each kept (`∈ E'`) or marked (`P`) either lives entirely in the kept
    set `E'`, or passes through a marked edge whose HEAD reaches `v` using only kept edges —
    the LAST marked edge on the path, so the suffix runs in the smaller set `E'`. -/
theorem nreaches_factor_last {P : NodeKey × NodeKey → Prop}
    {E E' : List (NodeKey × NodeKey)} {u v : NodeKey}
    (hclass : ∀ ab ∈ E, ab ∈ E' ∨ P ab) (h : NReaches E u v) :
    NReaches E' u v ∨ ∃ ab, P ab ∧ NReachesR E' ab.2 v := by
  induction h with
  | @edge u v huv =>
    rcases hclass _ huv with hE | hP
    · exact Or.inl (NReaches.edge hE)
    · exact Or.inr ⟨(u, v), hP, Or.inl rfl⟩
  | @head u w v huw _ ih =>
    rcases ih with hE | hP
    · rcases hclass _ huw with hEw | hPw
      · exact Or.inl (NReaches.head hEw hE)
      · exact Or.inr ⟨(u, w), hPw, Or.inr hE⟩
    · exact Or.inr hP

/-- One logged retraction only shrinks the edge multiset (a local subset fact, upstream of
    the count law `mem_removeLoggedRules_edges`).

    ★ `P6` step 3b (2026-09-14): statement unchanged. The release epilogue can only shrink
    too — it erases a bridge edge or declines — so "only shrinks" composes; the added step
    is `Cascade.lean::releasePostLogged_edges_subset`. -/
theorem removeLoggedOne_edges_subset (σ : GraphState) (u : Tuple) :
    ∀ ab ∈ (σ.removeLoggedOne u).edges, ab ∈ σ.edges := by
  intro ab hab
  unfold GraphState.removeLoggedOne at hab
  split at hab
  · have hab' := releasePostLogged_edges_subset _ u ab hab
    rw [pushDelta_edges, removeEdgeOne_edges] at hab'
    exact List.mem_of_mem_erase hab'
  · exact hab

/-- The retraction fold only shrinks the edge multiset. -/
theorem foldl_removeLoggedOne_edges_subset (us : List Tuple) :
    ∀ (σ : GraphState),
      ∀ ab ∈ (us.foldl (fun acc u => acc.removeLoggedOne u) σ).edges, ab ∈ σ.edges := by
  induction us with
  | nil => intro σ ab hab; exact hab
  | cons u rest ih =>
    intro σ ab hab
    simp only [List.foldl_cons] at hab
    exact removeLoggedOne_edges_subset σ u ab (ih _ ab hab)

/-- The whole logged retraction only shrinks the edge multiset (local mirror of the
    monotone `writeLoggedRules_edges_mono`). -/
theorem removeLoggedRules_edges_subset (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ ab ∈ (σ.removeLoggedRules S t).edges, ab ∈ σ.edges := by
  unfold GraphState.removeLoggedRules
  exact foldl_removeLoggedOne_edges_subset (rewriteClosureL S (rawWriteTuples S t)) σ

/-- One logged retraction only pushes outbox rows.

    ★ `P6` step 3b (2026-09-14): statement unchanged. Post-re-point the retraction has TWO
    emitting stages (the edge's own row, then the release epilogue's per-collected-bridge
    rows), so "only pushes" now composes `releasePostLogged_outbox_mono` over the existing
    argument — a retraction still never DROPS a frontier row. -/
theorem removeLoggedOne_outbox_mono (σ : GraphState) (u : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.removeLoggedOne u).outbox := by
  intro d hd
  unfold GraphState.removeLoggedOne
  split
  · refine releasePostLogged_outbox_mono _ u d ?_
    rw [pushDelta_outbox]
    refine List.mem_cons_of_mem _ ?_
    rw [removeEdgeOne_outbox]
    exact hd
  · exact hd

/-- The retraction fold only pushes outbox rows. -/
theorem foldl_removeLoggedOne_outbox_mono (us : List Tuple) :
    ∀ (σ : GraphState), ∀ d ∈ σ.outbox,
      d ∈ (us.foldl (fun acc u => acc.removeLoggedOne u) σ).outbox := by
  induction us with
  | nil => intro σ d hd; exact hd
  | cons u rest ih =>
    intro σ d hd
    simp only [List.foldl_cons]
    exact ih _ d (removeLoggedOne_outbox_mono σ u d hd)

/-- **Retracted edges carry frontier rows** (retraction dual of `writeLoggedRules_edge_delta`).
    Any edge PRESENT in `σ` but ABSENT after the logged retraction was erased by some
    `removeLoggedOne` step, which emitted an outbox row (id above the unchanged watermark)
    denormalized at the edge's own head. -/
theorem removeLoggedRules_edge_delta (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ ab, ab ∈ σ.edges → ab ∉ (σ.removeLoggedRules S t).edges →
      ∃ d ∈ (σ.removeLoggedRules S t).outbox, σ.watermark < d.id ∧ d.node = ab.2 := by
  unfold GraphState.removeLoggedRules
  suffices H : ∀ (us : List Tuple) (σc : GraphState), σc.watermark = σ.watermark →
      ∀ ab, ab ∈ σc.edges → ab ∉ (us.foldl (fun acc u => acc.removeLoggedOne u) σc).edges →
        ∃ d ∈ (us.foldl (fun acc u => acc.removeLoggedOne u) σc).outbox,
          σ.watermark < d.id ∧ d.node = ab.2 from
    H (rewriteClosureL S (rawWriteTuples S t)) σ rfl
  intro us
  induction us with
  | nil => intro σc _ ab hin hout; exact absurd hin hout
  | cons u rest ih =>
    intro σc hwm ab hin hout
    simp only [List.foldl_cons] at hout ⊢
    by_cases hin1 : ab ∈ (σc.removeLoggedOne u).edges
    · exact ih (σc.removeLoggedOne u) (by rw [removeLoggedOne_watermark, hwm]) ab hin1 hout
    · by_cases hp : (subjNode u.subject, objNode u.object u.relation) ∈ σc.edges
      · have hσ1 : σc.removeLoggedOne u
            = ((σc.removeEdgeOne (subjNode u.subject) (objNode u.object u.relation)).pushDelta
                (objNode u.object u.relation) u.relation true).releasePostLogged u := by
          unfold GraphState.removeLoggedOne; rw [if_pos hp]
        have hw1 : ((σc.removeEdgeOne (subjNode u.subject)
            (objNode u.object u.relation)).pushDelta
              (objNode u.object u.relation) u.relation true).watermark = σc.watermark := by
          rw [pushDelta_watermark]
          exact removeEdgeOne_watermark σc _ _
        by_cases hin2 : ab ∈ ((σc.removeEdgeOne (subjNode u.subject)
            (objNode u.object u.relation)).pushDelta
              (objNode u.object u.relation) u.relation true).edges
        · -- ★ `P6` step 3b (2026-09-14): THE NEW BRANCH. The edge survived the grant erase
          -- and was collected by the RELEASE epilogue instead — so it is a bridge edge, and
          -- the row that accounts for it is the release's, at the bridge target. That
          -- `d.node = ab.2` holds on this arm too is what lets this theorem keep its
          -- statement rather than weakening to a disjunction over endpoints; the fact is
          -- proved once at `Cascade.lean::releaseInBridgesLogged_edge_delta`.
          rw [hσ1] at hin1
          obtain ⟨d, hd, hgt, hnode⟩ := releasePostLogged_edge_delta _ u ab hin2 hin1
          refine ⟨d, foldl_removeLoggedOne_outbox_mono rest _ _ (by rw [hσ1]; exact hd),
            ?_, hnode⟩
          rw [← hwm, ← hw1]; exact hgt
        · rw [pushDelta_edges, removeEdgeOne_edges] at hin2
          have hpeq : ab = (subjNode u.subject, objNode u.object u.relation) := by
            by_contra hne
            exact hin2 ((List.mem_erase_of_ne hne).mpr hin)
          subst hpeq
          refine ⟨⟨(σc.removeEdgeOne (subjNode u.subject)
              (objNode u.object u.relation)).nextDeltaId,
              objNode u.object u.relation, u.relation, true⟩, ?_, ?_, rfl⟩
          · refine foldl_removeLoggedOne_outbox_mono rest _ _ ?_
            rw [hσ1]
            refine releasePostLogged_outbox_mono _ u _ ?_
            rw [pushDelta_outbox]
            exact List.mem_cons_self
          · show σ.watermark
              < (σc.removeEdgeOne (subjNode u.subject) (objNode u.object u.relation)).nextDeltaId
            have hdef : (σc.removeEdgeOne (subjNode u.subject)
                  (objNode u.object u.relation)).nextDeltaId
                = max (σc.removeEdgeOne (subjNode u.subject)
                    (objNode u.object u.relation)).maxOutboxId
                  (σc.removeEdgeOne (subjNode u.subject)
                    (objNode u.object u.relation)).watermark + 1 := rfl
            have hw : (σc.removeEdgeOne (subjNode u.subject)
                (objNode u.object u.relation)).watermark = σc.watermark :=
              removeEdgeOne_watermark σc _ _
            rw [hwm] at hw
            omega
      · exfalso
        apply hin1
        unfold GraphState.removeLoggedOne
        rw [if_neg hp]
        exact hin

/-- **Retraction-leg `reach` stability off the mapped keys** (dual of `writeLeg_reach_stable`).
    A path into an unmapped derived key's operand node cannot be broken by the retraction:
    breaking it would erase an edge whose frontier row dirties `(dt, R, on)`. The `false, true`
    arm (a lost path) factors through the LAST retracted edge, whose delta re-dirties the key
    — the anti-monotone mirror of the write leg's new-edge arm. -/
theorem removeLeg_reach_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (x : NodeKey) :
    (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
  have hclσ' : ∀ ab ∈ (σ.removeLoggedRules S t).edges,
      ab.1 ∈ (σ.removeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.removeLoggedRules S t).nodes := by
    intro ab hab
    rw [removeLoggedRules_nodes]
    exact hclσ ab (removeLoggedRules_edges_subset σ S t ab hab)
  cases h' : (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
    <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
  · rfl
  · -- lost path: factor through the LAST retracted edge, map the key
    exfalso
    have hN := reach_sound h0
    rcases nreaches_factor_last
      (P := fun ab => ∃ d ∈ (σ.removeLoggedRules S t).outbox,
        σ.watermark < d.id ∧ d.node = ab.2)
      (E := σ.edges) (E' := (σ.removeLoggedRules S t).edges)
      (fun ab hab => by
        by_cases hpost : ab ∈ (σ.removeLoggedRules S t).edges
        · exact Or.inl hpost
        · exact Or.inr (removeLoggedRules_edge_delta σ S t ab hab hpost))
      hN with hpost | ⟨ab, ⟨d, hd, hgt, hnode⟩, hR⟩
    · have := reach_complete hclσ' hpost
      rw [h'] at this
      cases this
    · apply hunmapped
      have hfront : d ∈ (σ.removeLoggedRules S t).frontierRows := by
        unfold GraphState.frontierRows
        refine List.mem_filter.mpr ⟨hd, ?_⟩
        rw [removeLoggedRules_watermark]
        exact decide_eq_true hgt
      refine List.mem_flatMap.mpr ⟨d, hfront, ?_⟩
      refine mem_affectedKeys hlk hder hr' hon ?_
      unfold GraphState.affectedObjects
      rcases hR with heq | hreach
      · rw [hnode, ← heq]
        exact List.mem_cons_self
      · refine List.mem_cons_of_mem _ (List.mem_filter.mpr ⟨?_, ?_⟩)
        · obtain ⟨y, _, hyv⟩ := nreaches_last hreach
          exact (hclσ' _ hyv).2
        · rw [hnode]
          exact reach_complete hclσ' hreach
  · -- new path: impossible, edges only shrink
    exfalso
    have hmono := NReaches.mono_subset (removeLoggedRules_edges_subset σ S t) (reach_sound h')
    have := reach_complete hclσ hmono
    rw [h0] at this
    cases this
  · rfl

/-- Reach into the operand's `wAll` node is `false` on both sides of a retraction leg whose
    (PRE-state) edge targets are plain (dual of `writeLeg_reach_wAll_false`; the plainness
    fence sits on `σ`, the bigger multiset, and transfers to the post-state by subset). -/
theorem removeLeg_reach_wAll_false {σ : GraphState} {S : Schema} {t : Tuple}
    {dt r' : String}
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll) :
    (∀ u, (σ.removeLoggedRules S t).reach u (wAllNode dt r') = false) ∧
    (∀ u, σ.reach u (wAllNode dt r') = false) := by
  have htpp : ∀ ab ∈ (σ.removeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll :=
    fun ab hab => htp ab (removeLoggedRules_edges_subset σ S t ab hab)
  constructor
  · intro u
    cases hc : (σ.removeLoggedRules S t).reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_variant_ne htpp (reach_sound hc)
      simp [wAllNode] at this
  · intro u
    cases hc : σ.reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_variant_ne htp (reach_sound hc)
      simp [wAllNode] at this

/-- **Retraction-leg `graphRec` stability off the mapped keys** (dual of
    `writeLeg_graphRec_stable`): an unmapped derived key's operand read is unchanged by the
    logged retraction, for EVERY subject. The plainness fence `htp` sits on the PRE-state `σ`
    (bigger multiset) — the sole hypothesis-shape change from the write leg. -/
theorem removeLeg_graphRec_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (s : SubjectRef) :
    GraphModel.graphRec (σ.removeLoggedRules S t) s dt on r'
      = GraphModel.graphRec σ s dt on r' := by
  obtain ⟨hwall', hwall0⟩ := removeLeg_reach_wAll_false (σ := σ) (S := S) (t := t)
    (dt := dt) (r' := r') htp
  unfold GraphModel.graphRec GraphModel.probeNonDerived
  dsimp only
  rw [removeLeg_reach_stable hclσ hlk hder hr' hon hunmapped (subjNode s),
    removeLeg_reach_stable hclσ hlk hder hr' hon hunmapped (wAnyNode s.shape),
    hwall' (subjNode s), hwall0 (subjNode s),
    hwall' (wAnyNode s.shape), hwall0 (wAnyNode s.shape)]

/-- **Retraction-leg `checkFn` stability off the mapped keys** (dual of
    `writeLeg_checkFn_stable`): the compiled pass guard is unchanged by a logged retraction
    that does not map the key. Plainness fence `htp` on the PRE-state. -/
theorem removeLeg_checkFn_stable {σ : GraphState} {S : Schema} {t : Tuple} (T' : Store)
    {dt on R : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (s : SubjectRef) :
    (σ.removeLoggedRules S t).checkFn T' s dt on R e = σ.checkFn T' s dt on R e := by
  unfold GraphState.checkFn
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  exact removeLeg_graphRec_stable hclσ htp hlk hder hr' hon hunmapped s

/-- No LEAF-ROUTED closure member of a derived-def store tuple targets the derived R-node
    `objNode ⟨dt,on⟩ R` (the `writeLeg_derived_inedges_eq` fragment argument, reused for the
    retraction): a stored `(dt,R)` tuple needs a `Direct` arm (dead on `ComputedOnly`), a
    rewrite output `(dt,R)` is forbidden by `noRuleOutputsL_of_derived`, and a re-addressed
    SEED of a derived write carries a MINTED LEAF relation, which `R` — a derived key's
    declared name, hence dot-free — cannot be.

    **RE-POINTED by step R5.** Its plain-closure predecessor
    (`rewriteClosure_notarget_derived`) is deleted: `removeLoggedRules` no longer folds
    `rewriteClosure S t`, so a fact about that list says nothing about the retraction. This
    is the exact remove-leg mirror of `writeLeg_derived_inedges_eq`'s inner argument, and
    `hWF` is here for the same reason it is there — the derived-seed case is refuted by the
    leaf NAME, and `relNameOK_of_isDerived` needs `WF`. -/
theorem rewriteClosureL_notarget_derived {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (w : Tuple) (hw : w ∈ rewriteClosureL S (rawWriteTuples S t)) :
    objNode w.object w.relation ≠ objNode ⟨dt, on⟩ R := by
  intro h2
  have hRok : relNameOK R := relNameOK_of_isDerived hWF (k := (dt, R)) hder
  have htype : dt = w.object.type := by
    simpa [objNode_type] using (congrArg NodeKey.type h2).symm
  have hrel : R = w.relation := by
    simpa [objNode_pred] using (congrArg NodeKey.pred h2).symm
  rcases rewriteClosureL_produced hw with hseed | ⟨r, hr', hro, hrout⟩
  · by_cases hd : isDerived S (t.object.type, t.relation) = true
    · -- derived raw write: every seed relation is a minted leaf name, `R` is not
      obtain ⟨r0, hr0, hw0⟩ := List.mem_map.mp hseed
      obtain ⟨i, hi⟩ := mem_rawWriteRels_derived hd hr0
      have hwr : w.relation = r0 := by rw [← hw0]
      exact leafPred_ne_relName hRok t.relation i (by rw [← hi, ← hwr, ← hrel])
    · -- untainted raw write: the seed list is `[t]`, so this is the pre-flip argument
      rw [rawWriteTuples_untainted (by simpa using hd)] at hseed
      have heq : w = t := List.mem_singleton.mp hseed
      rw [heq] at htype hrel
      obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t ht
      rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
      rw [← hlk', exprDirects_computedOnly hco] at hrs
      simp at hrs
  · exact noRuleOutputsL_of_derived hWF hder r hr'
      ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩

/-- Membership of `(a,b)` survives one retraction step when no closure member targets `b`
    and `b` is not a bridge target.

    ★★ **RESTATED by `P6` step 3b (2026-09-14) — the old form went FALSE, and subtly.**
    It read exactly as now minus `hb`, and the counterexample is immediate once the
    retraction releases: take `b = wAnyNode ((subjNode u.subject).type,
    (subjNode u.subject).pred)`. Then `hne` HOLDS — an `objNode` is never a `wAny`
    (`State.lean::objNode_ne_wAny`) — while `releasePostLogged` erases
    `(subjNode u.subject, b)` anyway, because the release is keyed on the ENDPOINT it
    collects, not on anything the closure targeted. So `hne` was never the right fence for
    a bridge edge; it fences the GRANT.

    One added hypothesis repairs it and nothing else moves. It is **free at the whole
    consumer chain** (`mem_foldl_removeLoggedOne_edges_iff_of_notarget` →
    `removeLeg_derived_inedges_eq`), which instantiates `b := objNode ⟨dt, on⟩ R` and
    discharges `hb` by `objNode_ne_wAny` with no premise of its own. Neither name is
    audited, so the statement was free to move. -/
theorem mem_removeLoggedOne_edges_iff_of_ne {σ : GraphState} {u : Tuple} {a b : NodeKey}
    (hne : objNode u.object u.relation ≠ b) (hb : b.variant ≠ Variant.wAny) :
    ((a, b) ∈ (σ.removeLoggedOne u).edges ↔ (a, b) ∈ σ.edges) := by
  unfold GraphState.removeLoggedOne
  split
  · constructor
    · intro h
      have h' := releasePostLogged_edges_subset _ u (a, b) h
      rw [pushDelta_edges] at h'
      exact (mem_removeEdgeOne_edges_of_ne
        (by intro hh; exact hne (congrArg Prod.snd hh).symm)).mp h'
    · intro h
      refine mem_releasePostLogged_edges_of_ne_wAny _ u hb ?_
      rw [pushDelta_edges]
      exact (mem_removeEdgeOne_edges_of_ne
        (by intro hh; exact hne (congrArg Prod.snd hh).symm)).mpr h
  · exact Iff.rfl

/-- Membership of `(a,b)` survives the retraction fold when no closure member targets `b`
    and `b` is not a bridge target. ★ `P6` step 3b (2026-09-14): forwards the new `hb`. -/
theorem mem_foldl_removeLoggedOne_edges_iff_of_notarget (us : List Tuple) {a b : NodeKey}
    (hnt : ∀ w ∈ us, objNode w.object w.relation ≠ b) (hb : b.variant ≠ Variant.wAny) :
    ∀ (σ : GraphState),
      ((a, b) ∈ (us.foldl (fun acc u => acc.removeLoggedOne u) σ).edges ↔ (a, b) ∈ σ.edges) := by
  induction us with
  | nil => intro σ; exact Iff.rfl
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih (fun w hw => hnt w (List.mem_cons_of_mem _ hw)) (σ.removeLoggedOne u)]
    exact mem_removeLoggedOne_edges_iff_of_ne (hnt u List.mem_cons_self) hb

/-- **The retraction never touches a derived key's in-edges** (dual of
    `writeLeg_derived_inedges_eq`): via `noRuleOutputs_of_derived` no rewrite-closure member
    targets a `DerNode`, so no in-edge into `objNode ⟨dt,on⟩ R` is erased. Clean — no path
    surgery, just fold-preservation. -/
theorem removeLeg_derived_inedges_eq {σ : GraphState} {S : Schema} {t : Tuple} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  unfold GraphState.removeLoggedRules
  exact mem_foldl_removeLoggedOne_edges_iff_of_notarget
    (rewriteClosureL S (rawWriteTuples S t))
    (fun w hw => rewriteClosureL_notarget_derived hWF hSV ht hlk hder hco w hw)
    (objNode_ne_wAny ⟨dt, on⟩ R) σ

/-! ## Obligation (D) of the write-path cone — SCOUTED 2026-09-05: it is ONE PREMISE SHORT

`reachedByW3d_shadow`'s `@write` arm (`:1633-1646`) builds

```text
hsubjW : ∀ u ∈ rewriteClosure S t,
           ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject))
```

and feeds it to `untaintedShadow_foldAdmits` / `untaintedShadow_writeLeg`, both of which
are already LIST-GENERIC in their first argument. So the re-point owes exactly one thing
here: the SAME disjunction over `rewriteClosureL S (rawWriteTuples S t)`.

**The two halves are not in the same state, and the docstrings elsewhere in this tree do
not distinguish them.**

* The `DerNode` half is **DISCHARGED**. `LeafRules.lean::rewriteClosureL_subject_pred_ne`
  wants `TtuTargetsSatL S (· ≠ R)`, which looks like a new premise — but
  `LeafRules.lean::rewriteClosureL_subject_pred_ne_of_noTtuTarget` manufactures it from
  `NoTtuTarget S R` plus `isDerived S (dt, R) = true`, and the site's `hterm dt R hder`
  supplies **both**. `writeLegSubjectsWide_L` below threads it; nothing new is assumed.
* The `LeafNode` half is **NOT**. `LeafRules.lean:680::rewriteClosureL_subject_not_leafNode`
  wants `LeafRules.lean::NoLeafSubjects S`, i.e. `TtuTargetsSatL S NotLeafName` —
  quantified over `schemaRewritesL S = schemaRewrites S ++ leafRewrites S`. The site holds
  only `hQ : TtuTargetsSat S NotLeafName`, quantified over `schemaRewrites S` **alone**
  (`GraphAdmission.ttuNotLeaf`, `FullScope.lean:157`). The bridge that exists,
  `ttuTargetsSat_notLeafName_of_noLeafSubjects` (`:859`), runs the OTHER way — superset to
  subset — and its converse is FALSE.

⚠ **The gap is not closable the way obligation (A)'s was.** (A)'s leaf-layer arm is killed
by `LeafRules.lean::derivedAnywhere_eq_false_of_mem_leafRewrites`: a leaf rule's TTU target
is `derivedAnywhere`-false while `R` is `derivedAnywhere`-true, so `tr ≠ R` is free. That
instrument says nothing about a target's NAME SHAPE. Nor does anything else in scope:
`WF.relNames` (`Core/Schema.lean:71`) constrains DECLARED def keys, while a TTU target is a
referenced string inside an `Expr`; and `RewriteMatchDeclared` (`RestrictBase.lean:289`)
constrains `matchRel` over `schemaRewrites` only.

**Where the premise would have to come from.** ⚠ **This paragraph was WRONG twice and is
corrected here (2026-09-05, first-hand).** It read: "Either a new `GraphAdmission` field
(OUT OF SCOPE for this session by instruction — and it would be a real Python-side scope
claim, since Python's `check_name` does not forbid a dot inside a TTU target either) …".

1. **The Python claim is FALSE.** `zanzibar_utils_v1.py::_validate_ast_references`'s
   `check_name` (`:915-919`) raises iff `'.' in name and name != '...'`, and the TTU arm of
   its `walk` applies it to BOTH TTU components: `check_name(e.target_rel, where)` and
   `check_name(e.tupleset_rel, where)` (`:931-932`). So a dot in a TTU target IS rejected at
   compile time. This same file already states the rule correctly at `:604`, so the tree was
   contradicting itself.
2. **A `GraphAdmission` field is no longer out of scope, and one exists.**
   `noLeafSubjects : NoLeafSubjects S` is a field as of the 4c-ii re-point
   (`FullScope.lean:172`), alongside `keysNonempty`, and it is EXACTLY the Python-enforced
   dot-lock `check_name` implements.

The live route is therefore the second one below — the same threading `hQ`/`hDR` got at
4c-ii step 9: append `NoLeafSubjects S` right of the colon on
`reachedByW3d_shadow` and its two `CascadeStrataSettle.lean` twins
(`::reachedByW3d2_shadow` `:738`, `::reachedByW3d2_shadow_d` `:1348`). It is schema-level,
so it costs **no** weakening line at the recursive call (scope doc §11.13 (p)), and the
ultimate discharge is **free at every concrete admission instance in the tree**: all four
`GraphAdmission` witnesses already prove `ttuNotLeaf` as
`ttuTargetsSat_notLeafName_of_noLeafSubjects (by decide)` (`FullScope.lean:660`, `:820`,
`:1582`, `:1720`) — i.e. `by decide : NoLeafSubjects S` is ALREADY being elaborated there
and then thrown away. Threading it changes those four lines to hand over the stronger fact
they already have.

## ★ CONTROLLED — one sabotage, run 2026-09-05 (`docs/sabotage-procedure.md`)

The claim under attack is the one this whole section exists to assert: **`hnl` is not
redundant** — i.e. (D) is genuinely NOT discharged by what the site holds. The narrowest
plausible weakening is therefore to write the theorem the way an optimistic reading would:
swap `writeLegSubjectsWide_L`'s `hnl : NoLeafSubjects S` for the site's own
`hQ : TtuTargetsSat S NotLeafName` (its binder is left named `hnl` so the message names the
argument) and let it flow into the `LeafNode` half. `rc=1`,
`lake build ZanzibarProofs.GraphIndex.CascadeStable`, TWO errors — the second is the
NON-VACUITY WITNESS below refusing to accept the weaker premise, which is the half that
would otherwise have gone unnoticed:

```text
error: ZanzibarProofs/GraphIndex/CascadeStable.lean:2506:47: Application type mismatch: The argument
  hnl
has type
  TtuTargetsSat S NotLeafName
but is expected to have type
  NoLeafSubjects ?m.109
in the application
  @rewriteClosureL_subject_not_leafNode ?m.109 hnl
error: ZanzibarProofs/GraphIndex/CascadeStable.lean:2556:4: Application type mismatch: The argument
  LeafRuleWitness.noLeafSubjects_snlBoth
has type
  NoLeafSubjects LeafRuleWitness.SnlBoth
but is expected to have type
  TtuTargetsSat ?m.1 NotLeafName
in the application
  writeLegSubjectsWide_L LeafRuleWitness.noLeafSubjects_snlBoth
```

Restored from a byte-exact `cp` backup (never `git checkout --`, trap (aa)); whole tree
`rc=0`, `Build completed successfully (1089 jobs)`, zero `sorry`.

⚠ The error count is a LOWER bound: `CascadeStable` is upstream of the whole cascade chain,
and Lean does not build the dependents of a failed module (traps (k)/(v)). -/

/-- `SnlBadLeaf`'s UNTAINTED layer is CLEAN — `LeafRules.lean::snlBadLeaf_untainted_layer_clean`
    pins it to the single rule `⟨"doc", "parent", "editor", .ttu "viewer"⟩` — so
    `GraphAdmission.ttuNotLeaf`, which quantifies over `schemaRewrites` alone, HOLDS at this
    schema. Proved through the pinned layer rather than by `decide`, because `TtuTargetsSat`
    carries an unbounded `∀ tr` and so has no `Decidable` instance. -/
theorem ttuTargetsSat_notLeafName_snlBadLeaf :
    TtuTargetsSat LeafRuleWitness.SnlBadLeaf NotLeafName := by
  intro r hr tr hk
  rw [LeafRuleWitness.snlBadLeaf_untainted_layer_clean, List.mem_singleton] at hr
  subst hr
  have htr : tr = "viewer" := by simpa using hk.symm
  subst htr
  decide

/-- **THE GAP, MECHANIZED — the finding of this section, as a kernel fact rather than prose.**

    `SnlBadLeaf` satisfies **every** name-shape field `GraphAdmission` carries
    (`ttuNotLeaf`, `directRestrNotLeaf`, `computedRefsNotLeaf`) and still fails
    `NoLeafSubjects`, because its DERIVED key's TTU arm targets `"viewer.0"` and that arm
    compiles into `leafRewrites` — the half of `schemaRewritesL` no admission field ranges
    over. So no combination of the site's in-scope schema premises can produce the premise
    `rewriteClosureL_subject_not_leafNode` needs; the converse of `:859`'s bridge is refuted,
    not merely unproved.

    The witness is REUSED, not minted: `LeafRuleWitness.SnlBadLeaf` and its refutation
    already exist and are controlled by the S12/S13 layer sabotages recorded at
    `LeafRules.lean:1809`. -/
theorem admissionNameShape_does_not_give_noLeafSubjects :
    TtuTargetsSat LeafRuleWitness.SnlBadLeaf NotLeafName
      ∧ DirectRestrictionsNotLeaf LeafRuleWitness.SnlBadLeaf
      ∧ ComputedRefsNotLeaf LeafRuleWitness.SnlBadLeaf
      ∧ ¬ NoLeafSubjects LeafRuleWitness.SnlBadLeaf :=
  ⟨ttuTargetsSat_notLeafName_snlBadLeaf, by decide, by decide,
    LeafRuleWitness.noLeafSubjects_false_leafLayer⟩

/-! ### `writeLegSubjectsWide_L` itself now lives ABOVE `reachedByW3d_shadow`

⚠ **It was MOVED, not changed** (THE FLIP, round 2). Lean has no forward declarations, so a
theorem consumed inside `reachedByW3d_shadow`'s `@write` arm (`:1686`) cannot be stated
after it; the statement and proof are byte-identical to the ones this section was written
around, and the section's sabotage record below still describes them. The `hnl` premise the
docstring above calls "the one thing that is NOT in scope there" is now supplied as
`hLS.noLeafSubjects` from the threaded `LeafRules.lean::LeafScope` carrier. -/

/-! ### Non-vacuity — every one of the three premises is live at the fixture

`writeLegSubjectsWide_L` has three hypotheses and each has a vacuity mode: `hnl` is
vacuously true at a schema whose rule lists carry no `.ttu` rule (`SlV`, whose untainted
layer is EMPTY — `LeafRules.lean::lrV_untainted_layer_silent`), `hterm` is vacuously true at
a schema with no derived key, and the conclusion is vacuously true if the closure is empty.
`SnlBoth` defeats all three: both layers carry a TTU rule
(`snlBoth_untainted_layer_ttu` / `::snlBoth_leaf_layer_ttu`), `("doc","access")` is derived,
and the closure of the raw write on `parent` genuinely CONTAINS a leaf-layer extra whose
subject predicate was rewritten from `BARE` to `viewer`
(`::snlBoth_closure_reaches_leaf_extra`, `::snlBoth_extra_subject_rewritten`). -/

/-- The fixture's `hterm`. Proved WITHOUT case-splitting on the derived key: a derived `R`
    is `derivedAnywhere`-true (`LeafRules.lean::derivedAnywhere_of_isDerived`), while both
    names that could break a conjunct — the untainted layer's sole TTU target `"viewer"`,
    and the stored subject's `BARE` — are `derivedAnywhere`-FALSE by `decide`. A `Bool` is
    not both. -/
theorem snlBoth_hterm :
    ∀ dt R, isDerived LeafRuleWitness.SnlBoth (dt, R) = true →
      NoTtuTarget LeafRuleWitness.SnlBoth R
        ∧ NoStoreSubjectR (LeafRuleWitness.tnlParent :: ([] : Store)) R := by
  intro dt R hder
  have hda : derivedAnywhere LeafRuleWitness.SnlBoth R = true :=
    derivedAnywhere_of_isDerived hder
  refine ⟨?_, ?_⟩
  · intro r hr tr hk
    rw [LeafRuleWitness.snlBoth_untainted_layer_ttu, List.mem_singleton] at hr
    subst hr
    have htr : tr = "viewer" := by simpa using hk.symm
    subst htr
    intro hRv
    rw [← hRv] at hda
    exact absurd hda (by decide)
  · intro t' ht'
    rw [List.mem_singleton] at ht'
    subst ht'
    rw [LeafRuleWitness.tnlParent_subject_bare]
    intro hRb
    rw [← hRb] at hda
    exact absurd hda (by decide)

/-- **The applied conclusion, derived THROUGH `writeLegSubjectsWide_L`** at the pinned
    leaf-layer extra — never `decide`d directly, because deciding the conclusion alone would
    say nothing about whether the theorem applies. -/
theorem writeLegSubjectsWide_L_snlBoth :
    ¬ (DerNode LeafRuleWitness.SnlBoth (subjNode ⟨"folder", "f1", "viewer"⟩)
        ∨ LeafNode LeafRuleWitness.SnlBoth (subjNode ⟨"folder", "f1", "viewer"⟩)) :=
  writeLegSubjectsWide_L (T := ([] : Store)) (t := LeafRuleWitness.tnlParent)
    LeafRuleWitness.noLeafSubjects_snlBoth snlBoth_hterm
    (show NotLeafName LeafRuleWitness.tnlParent.subject.predicate from
      Or.inl LeafRuleWitness.tnlParent_subject_bare)
    ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩ (by decide)

/-! ### The INSTRUMENT was controlled too, not just the subject (trap (u), house rule 7)

A `0 sorry` reading is worth nothing unless the grep that produced it can produce a `1`.
Probed 2026-09-05 by inserting `theorem zz_sorry_instrument_probe : True := by sorry`
immediately above `ttuTargetsSat_notLeafName_snlBadLeaf` and rebuilding this module:

```text
warning: ZanzibarProofs/GraphIndex/CascadeStable.lean:2446:8: declaration uses `sorry`
```

`grep -c 'declaration uses .sorry.'` → **1**; the straight-quote spelling
`grep -c "declaration uses 'sorry'"` → **0** on the SAME log, because Lean prints
backticks. The probe was removed by `cp` from a byte-exact backup and the module rebuilt
`rc=0`; this note sits BELOW the two line numbers quoted in the sabotage block above so
that recording it does not invalidate them. -/

end Zanzibar
