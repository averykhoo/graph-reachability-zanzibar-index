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

/-- One logged write step keeps the watermark. -/
theorem writeLoggedOne_watermark (σ : GraphState) (t : Tuple) :
    (σ.writeLoggedOne t).watermark = σ.watermark := by
  unfold GraphState.writeLoggedOne
  split
  · rw [pushDelta_watermark, writeDirect_watermark]
  · rfl

/-- One logged write step only pushes outbox rows. -/
theorem writeLoggedOne_outbox_mono (σ : GraphState) (t : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.writeLoggedOne t).outbox := by
  intro d hd
  unfold GraphState.writeLoggedOne
  split
  · rw [pushDelta_outbox]
    refine List.mem_cons_of_mem _ ?_
    rw [writeDirect_outbox]
    exact hd
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
  exact foldl_writeLoggedOne_outbox_mono (rewriteClosure S t) σ

/-- A logged write leg only adds edges (its core is the unlogged `writeRules`). -/
theorem writeLoggedRules_edges_mono (σ : GraphState) (S : Schema) (t : Tuple) :
    ∀ ab ∈ σ.edges, ab ∈ (σ.writeLoggedRules S t).edges := by
  intro ab hab
  rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges]
  exact foldl_writeDirect_edges_mono _ ab hab

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
    H (rewriteClosure S t) σ rfl (fun ab hab => Or.inl hab)
  intro us
  induction us with
  | nil => intro σc _ h ab hab; exact h ab hab
  | cons u rest ih =>
    intro σc hwm h ab hab
    simp only [List.foldl_cons] at hab ⊢
    refine ih (σc.writeLoggedOne u) (by rw [writeLoggedOne_watermark, hwm]) ?_ ab hab
    intro ab' hab'
    unfold GraphState.writeLoggedOne at hab' ⊢
    by_cases hadm : σc.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true
    · rw [if_pos hadm] at hab' ⊢
      rw [pushDelta_edges, writeDirect_edges, if_pos hadm] at hab'
      rw [pushDelta_outbox]
      rcases List.mem_cons.mp hab' with heq | hmem
      · -- the fresh edge: its row is the pushed head
        refine Or.inr ⟨⟨(σc.writeDirect u).nextDeltaId, objNode u.object u.relation,
          u.relation, true⟩, List.mem_cons_self, ?_, ?_⟩
        · show σ.watermark < (σc.writeDirect u).nextDeltaId
          have h1 : (σc.writeDirect u).nextDeltaId
              = max (σc.writeDirect u).maxOutboxId (σc.writeDirect u).watermark + 1 := rfl
          have h2 : (σc.writeDirect u).watermark = σc.watermark :=
            writeDirect_watermark σc u
          omega
        · show (⟨(σc.writeDirect u).nextDeltaId, objNode u.object u.relation,
            u.relation, true⟩ : Delta).node = ab'.2
          rw [heq]
      · rcases h ab' hmem with hold | ⟨d, hd, hgt, hnode⟩
        · exact Or.inl hold
        · refine Or.inr ⟨d, List.mem_cons_of_mem _ ?_, hgt, hnode⟩
          rw [writeDirect_outbox]
          exact hd
    · rw [if_neg hadm] at hab' ⊢
      exact h ab' hab'

/-! ## Endpoint closure over the interleaved closure -/

/-- A cascade run either accepts (the drained logged batch) or rejects (identity). -/
theorem runCascade_cases (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    runCascade S T σ jobs
        = { reconcileJobsL S T σ jobs with
            watermark := (reconcileJobsL S T σ jobs).maxOutboxId }
      ∨ runCascade S T σ jobs = σ := by
  unfold runCascade
  split
  · exact Or.inl rfl
  · exact Or.inr rfl

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
    available on the whole interleaved chain. -/
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
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σp ih ab hab
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

/-- **Every W3d edge target is plain** on `BareStarStore` stores: a routed edge's
    object is the raw write's object (star-free by `BareStarStore`), a cascade edge's
    object is the job's concrete `on`. This is the fence the attack found load-bearing:
    a `wAll`-targeted edge would flip probe 3 at every object of the type while
    `affectedKeys` skips the star-named head (Python's
    `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` never dirties a derived
    own-key from one, and rejects the derived-head case outright). The store
    hypothesis is taken at the chain's own store and weakens along the prefix. -/
theorem reachedByW3d_edges_target_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    BareStarStore T → ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain := by
  induction h with
  | empty S =>
    intro _ ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hBS ab hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hold | ⟨w, hw, _, h2⟩
    · exact ih (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')) (a, b) hold
    · show b.variant = Variant.plain
      have hwo : w.object.name ≠ STAR := by
        rw [rewriteClosure_object hw]
        exact (hBS t List.mem_cons_self).2
      rw [h2, objNode_plain hwo]
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hBS ab hab
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc] at hab
      have hab' : ab ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hab'
      obtain ⟨a, b⟩ := ab
      rcases reconcileJobsD_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, _, _, h2⟩
      · exact ih hBS (a, b) hold
      · show b.variant = Variant.plain
        obtain ⟨_, _, _, _, _, _, _, _, hon⟩ := hjv j hj
        rw [h2, objNode_plain hon]
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
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σ hclσ ab hab
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
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain) :
    (∀ u, (σ.writeLoggedRules S t).reach u (wAllNode dt r') = false) ∧
    (∀ u, σ.reach u (wAllNode dt r') = false) := by
  have htp0 : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain :=
    fun ab hab => htp' ab (writeLoggedRules_edges_mono σ S t ab hab)
  constructor
  · intro u
    cases hc : (σ.writeLoggedRules S t).reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain htp' (reach_sound hc)
      simp [wAllNode] at this
  · intro u
    cases hc : σ.reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain htp0 (reach_sound hc)
      simp [wAllNode] at this

/-- **Write-leg `graphRec` stability off the mapped keys** (fan-out completeness,
    contrapositive): an unmapped derived key's operand read is unchanged by the
    logged write, for EVERY subject. Probes 1–2 by reach stability into the concrete
    operand node; probes 3–4 dead on both sides (plain targets). -/
theorem writeLeg_graphRec_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
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
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
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
      exact foldl_writeDirect_nodes_mono (rewriteClosure S t) σ v hvn
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
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σ hclσ ab hab
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

/-- **The untainted-core shadow relation** — `ShadowOver` at today's extras predicate.
    `abbrev` (hence reducible) on purpose: every existing field access, anonymous
    constructor and `rcases` against this name keeps working unchanged, which is what
    makes the genericization above a NO-OP on the current tree rather than a re-point. -/
abbrev UntaintedShadow (S : Schema) (σ σ0 : GraphState) : Prop :=
  ShadowOver (DerNode S) σ σ0

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

⚠ **This block is INERT on today's tree** — nothing consumes it yet; its consumer is
`shadow_graphRec_agree`'s `hv1`, which needs `NotLeafName r'` for the OPERAND relation
(scope-doc §11.13 trap (g)). Per `docs/sabotage-procedure.md:100-141` that flips the
sabotage's job: a green build vets NOTHING here, so the witness/control pins below are
the SOLE evidence that the predicate has content, and they exist for no other reason.
Do not "simplify" them away. -/

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

/-- One parallel step: the logged write on `σ`, the plain write on the shadow —
    admission agrees, so the shadow relation is maintained. -/
theorem untaintedShadow_writeLoggedOne {Extra : NodeKey → Prop} {σ σ0 : GraphState}
    (hsh : ShadowOver Extra σ σ0) {u : Tuple}
    (ha : ¬ Extra (subjNode u.subject)) :
    ShadowOver Extra (σ.writeLoggedOne u) (σ0.writeDirect u) := by
  have hadm := shadow_admitEdge_agree hsh ha (objNode u.object u.relation)
  unfold GraphState.writeLoggedOne
  by_cases hb : σ.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true
  · rw [if_pos hb]
    have hb0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true := by
      rw [← hadm]; exact hb
    have hcl : ∀ ab ∈ (σ.writeDirect u).edges,
        ab.1 ∈ (σ.writeDirect u).nodes ∧ ab.2 ∈ (σ.writeDirect u).nodes :=
      edgesClosed_writeDirect hsh.closed u
    have hcl0 : ∀ ab ∈ (σ0.writeDirect u).edges,
        ab.1 ∈ (σ0.writeDirect u).nodes ∧ ab.2 ∈ (σ0.writeDirect u).nodes :=
      edgesClosed_writeDirect hsh.closed0 u
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
    · -- classify
      intro ab hab
      rw [pushDelta_edges, writeDirect_edges, if_pos hb] at hab
      rw [writeDirect_edges, if_pos hb0]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact Or.inl (heq ▸ List.mem_cons_self)
      · rcases hsh.classify ab hmem with h0 | hD
        · exact Or.inl (List.mem_cons_of_mem _ h0)
        · exact Or.inr hD
    · -- sub
      intro ab hab
      rw [writeDirect_edges, if_pos hb0] at hab
      rw [pushDelta_edges, writeDirect_edges, if_pos hb]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact heq ▸ List.mem_cons_self
      · exact List.mem_cons_of_mem _ (hsh.sub ab hmem)
    · -- nodesSub
      intro k hk
      rw [writeDirect_nodes, if_pos hb0] at hk
      rw [pushDelta_nodes, writeDirect_nodes, if_pos hb]
      rcases List.mem_cons.mp hk with heq | hk2
      · exact heq ▸ List.mem_cons_self
      · rcases List.mem_cons.mp hk2 with heq | hk3
        · exact List.mem_cons_of_mem _ (heq ▸ List.mem_cons_self)
        · exact List.mem_cons_of_mem _ (List.mem_cons_of_mem _ (hsh.nodesSub k hk3))
    · -- closed
      intro ab hab
      rw [pushDelta_edges] at hab
      rw [pushDelta_nodes]
      exact hcl ab hab
    · -- closed0
      exact hcl0
    · -- term
      intro k hk y hy
      rw [pushDelta_edges, writeDirect_edges, if_pos hb] at hy
      rcases List.mem_cons.mp hy with heq | hmem
      · have h1 : k = subjNode u.subject := (Prod.ext_iff.mp heq).1
        rw [h1] at hk
        exact ha hk
      · exact hsh.term k hk y hmem
  · rw [if_neg hb]
    have hb0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = false := by
      rw [← hadm]
      exact Bool.eq_false_iff.mpr hb
    rw [writeDirect_reject hb0]
    exact hsh

/-- The parallel write-leg fold maintains the shadow. -/
theorem untaintedShadow_writeLeg {Extra : NodeKey → Prop} :
    ∀ (us : List Tuple) (σ σ0 : GraphState), ShadowOver Extra σ σ0 →
      (∀ u ∈ us, ¬ Extra (subjNode u.subject)) →
      ShadowOver Extra (us.foldl (fun acc u => acc.writeLoggedOne u) σ)
        (us.foldl (fun acc u => acc.writeDirect u) σ0) := by
  intro us
  induction us with
  | nil => intro σ σ0 hsh _; exact hsh
  | cons u rest ih =>
    intro σ σ0 hsh hs
    simp only [List.foldl_cons]
    exact ih _ _ (untaintedShadow_writeLoggedOne hsh (hs u List.mem_cons_self))
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

/-- **Admission transfers to the shadow**: the logged fold and the shadow's plain
    fold accept the same writes. -/
theorem untaintedShadow_foldAdmits {Extra : NodeKey → Prop} :
    ∀ (us : List Tuple) (σ σ0 : GraphState), ShadowOver Extra σ σ0 →
      (∀ u ∈ us, ¬ Extra (subjNode u.subject)) →
      FoldAdmits σ us → FoldAdmits σ0 us := by
  intro us
  induction us with
  | nil => intro σ σ0 _ _ _; exact trivial
  | cons u rest ih =>
    intro σ σ0 hsh hs hfa
    obtain ⟨hadm1, hrest⟩ := hfa
    have hadm0 : σ0.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true := by
      rw [← shadow_admitEdge_agree hsh (hs u List.mem_cons_self) (objNode u.object u.relation)]
      exact hadm1
    refine ⟨hadm0, ?_⟩
    -- the fold's next state on the σ side is `writeLoggedOne`'s CORE = `writeDirect`
    have hstep : ShadowOver Extra (σ.writeLoggedOne u) (σ0.writeDirect u) :=
      untaintedShadow_writeLoggedOne hsh (hs u List.mem_cons_self)
    have hfd : FoldAdmits (σ.writeLoggedOne u) rest := by
      -- `FoldAdmits σ (u :: rest)` continues at `σ.writeDirect u`; the logged step's
      -- core equals it (`EvalEq`), and `FoldAdmits` reads only edges/nodes
      have hev : EvalEq (σ.writeLoggedOne u) (σ.writeDirect u) :=
        writeLoggedOne_evalEq (EvalEq.refl σ) u
      exact foldAdmits_evalEq hev rest hrest
    exact ih _ _ hstep (fun x hx => hs x (List.mem_cons_of_mem _ hx)) hfd

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
    state of a cascade keeps the shadow, hence the read bridge. -/
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
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases hsound a b hab with hold | ⟨c, _, _, h2⟩
    · exact hsh.classify (a, b) hold
    · exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
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
    · obtain ⟨dt, on, R, _, hRne', _, hkey⟩ := hk
      have : R = c.predicate := by
        have hp := congrArg NodeKey.pred (hkey.symm.trans h1)
        simpa [objNode_pred, subjNode_pred] using hp
      rw [hcb c hc] at this
      exact hRne' this

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

/-! ### The shadow exists at every W3d state -/

/-- **`reachedByW3d_shadow`** — every W3d state has an untainted-core shadow: a
    rules-ADMITTED state on the CURRENT store agreeing on everything off the derived
    R-nodes. The store-dependent hypotheses sit right of the colon and weaken along
    the chain's prefix stores. -/
theorem reachedByW3d_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    StoreValidRules S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm hprev ih =>
    intro hNK hCO hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
    have hsubj : ∀ u ∈ rewriteClosure S t, ¬ DerNode S (subjNode u.subject) := by
      rintro u hu ⟨dt, on, R, hder, _hRne, _hon, heq⟩
      obtain ⟨hnt, hns⟩ := hterm dt R hder
      have hpne : u.subject.predicate ≠ R :=
        rewriteClosure_subject_pred_ne hnt (hns t List.mem_cons_self) hu
      apply hpne
      have hp := congrArg NodeKey.pred heq
      simpa [subjNode_pred, objNode_pred] using hp
    exact ⟨σ0.writeRules S t,
      ReachedByRulesAdmitted.step t h0
        (untaintedShadow_foldAdmits (rewriteClosure S t) σp σ0 hsh hsubj hadm),
      untaintedShadow_writeLeg (rewriteClosure S t) σp σ0 hsh hsubj⟩
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hNK hCO hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSV hterm
    exact ⟨σ0, h0,
      untaintedShadow_cascade hsh (reachedByRules_of_admitted h0) hSV hNK hCO hjv⟩

/-! ### The W3d read bridge -/

/-- Untainted operand reads agree with the shadow — for EVERY subject and object:
    the probe targets (the operand node, the operand `wAll` node) are never
    `DerNode`s, so all four probes read identically. -/
theorem shadow_graphRec_agree {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) (s : SubjectRef) {dt' : String} (on' : String)
    {r' : String} (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec σ s dt' on' r' = GraphModel.graphRec σ0 s dt' on' r' := by
  have hv1 : ¬ DerNode S (objNode ⟨dt', on'⟩ r') := by
    rintro ⟨dt, on, R, hder, _, _, heq⟩
    have htype : dt' = dt := by
      have := congrArg NodeKey.type heq
      simpa [objNode_type] using this
    have hpred : r' = R := by
      have := congrArg NodeKey.pred heq
      simpa [objNode_pred] using this
    rw [htype, hpred, hder] at hunt
    cases hunt
  -- PRE-WIDENED (4c-ii step 6, 2026-08-31c). This `have` is deliberately STRONGER than
  -- what `shadow_reach_agree` asks for today, which is why the two uses below go through
  -- `Or.inl`. At step 9 `UntaintedShadow` is re-pointed at `ShadowOver (fun k => DerNode
  -- S k ∨ LeafNode S k)`; then `shadow_reach_agree` wants exactly this statement and the
  -- flip is "delete the two `Or.inl` wrappers", not a proof. Same pattern as
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
  -- ⚠ `hv1` is NOT free the same way and must not be bundled into this edit: it needs
  -- `NotLeafName r'` for the OPERAND relation, which `hunt` does not give (a minted leaf
  -- name like `viewer.0` is itself non-derived while `leafPublic` of it is derived), and
  -- the premise cannot be phrased locally because `ReconcileStars.lean::
  -- checkFn_agree_of_graphRec{,_cd}` hand their `hag` callback exactly
  -- `isDerived S (dt,r') = false`. That is scope-doc 11.13 trap (g), still open.
  have hv3 : ¬ (DerNode S (wAllNode dt' r') ∨ LeafNode S (wAllNode dt' r')) := by
    rintro (⟨dt, on, R, _, _, hon, heq⟩ | ⟨ty, on, p, _, _, hon, heq⟩)
    · rw [objNode_plain hon] at heq
      have := congrArg NodeKey.variant heq
      simp [wAllNode] at this
    · rw [objNode_plain hon] at heq
      have := congrArg NodeKey.variant heq
      simp [wAllNode] at this
  unfold GraphModel.graphRec GraphModel.probeNonDerived
  dsimp only
  rw [shadow_reach_agree hsh hv1 (subjNode s), shadow_reach_agree hsh hv1 (wAnyNode s.shape),
    shadow_reach_agree hsh (fun h => hv3 (Or.inl h)) (subjNode s),
    shadow_reach_agree hsh (fun h => hv3 (Or.inl h)) (wAnyNode s.shape)]

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
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hstep : σ.checkFn T s dt on R e = σ0.checkFn T s dt on R e :=
    checkFn_agree_of_graphRec T s dt on R e hco hleafUnt
      (fun s' r' hr' => shadow_graphRec_agree hsh s' on hr')
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

/-- A write leg never touches any residue row. -/
theorem writeLoggedRules_residue (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeLoggedRules S t).residue = σ.residue := by
  rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).residue]
  show ((rewriteClosure S t).foldl (fun acc u => acc.writeDirect u) σ).residue = σ.residue
  generalize rewriteClosure S t = us
  induction us generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih, writeDirect_residue]

/-- **Write legs never touch a derived key's in-edges** (model-level I5
    exclusivity): a routed closure member cannot land on the R-node (a stored `(dt,R)`
    tuple would need a `Direct` arm, a rewrite output a rule onto `(dt,R)` — both dead
    on a `ComputedOnly` derived def / the taint filter), and write legs remove nothing. -/
theorem writeLeg_derived_inedges_eq {σ : GraphState} {S : Schema} {t : Tuple} {T : Store}
    (hSV : StoreValidRules S (t :: T))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  constructor
  · intro h
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges] at h
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) h with hold | ⟨w, hw, _h1, h2⟩
    · exact hold
    · exfalso
      have htype : dt = w.object.type := by
        simpa [objNode_type] using congrArg NodeKey.type h2
      have hrel : R = w.relation := by
        simpa [objNode_pred] using congrArg NodeKey.pred h2
      rcases rewriteClosure_produced hw with heq | ⟨r, hr', hro, hrout⟩
      · rw [heq] at htype hrel
        obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t List.mem_cons_self
        rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
        rw [← hlk', exprDirects_computedOnly hco] at hrs
        simp at hrs
      · exact noRuleOutputs_of_derived hder r hr'
          ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
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
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (h : ReachedByW3d σ S T) (hadm : FoldAdmits σ (rewriteClosure S t))
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
  obtain ⟨σ0', h0', hsh'⟩ := reachedByW3d_shadow h' hNK hCO hSV hterm
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d_shadow h hNK hCO hSVw htermw
  have hclσ := reachedByW3d_edgesClosed h
  have htp' := reachedByW3d_edges_target_plain h' hBS
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFn (t :: T) s dt on R e :=
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSVw hBSw hTSw hCO hMatch hStrat htermw
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
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d σ S T) (hadm : FoldAdmits σ (rewriteClosure S t))
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
      hterm h hadm hlk hder hco hleafUnt hunmapped hs hon
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
    rw [writeLeg_derived_inedges_eq hSV hlk hder hco (subjNode s)] at hedge'
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
    the count law `mem_removeLoggedRules_edges`). -/
theorem removeLoggedOne_edges_subset (σ : GraphState) (u : Tuple) :
    ∀ ab ∈ (σ.removeLoggedOne u).edges, ab ∈ σ.edges := by
  intro ab hab
  unfold GraphState.removeLoggedOne at hab
  split at hab
  · rw [pushDelta_edges, removeEdgeOne_edges] at hab
    exact List.mem_of_mem_erase hab
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
  exact foldl_removeLoggedOne_edges_subset (rewriteClosure S t) σ

/-- One logged retraction only pushes outbox rows. -/
theorem removeLoggedOne_outbox_mono (σ : GraphState) (u : Tuple) :
    ∀ d ∈ σ.outbox, d ∈ (σ.removeLoggedOne u).outbox := by
  intro d hd
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_outbox]
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
    H (rewriteClosure S t) σ rfl
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
            = (σc.removeEdgeOne (subjNode u.subject) (objNode u.object u.relation)).pushDelta
                (objNode u.object u.relation) u.relation true := by
          unfold GraphState.removeLoggedOne; rw [if_pos hp]
        rw [hσ1, pushDelta_edges, removeEdgeOne_edges] at hin1
        have hpeq : ab = (subjNode u.subject, objNode u.object u.relation) := by
          by_contra hne
          exact hin1 ((List.mem_erase_of_ne hne).mpr hin)
        subst hpeq
        refine ⟨⟨(σc.removeEdgeOne (subjNode u.subject) (objNode u.object u.relation)).nextDeltaId,
            objNode u.object u.relation, u.relation, true⟩, ?_, ?_, rfl⟩
        · refine foldl_removeLoggedOne_outbox_mono rest _ _ ?_
          rw [hσ1, pushDelta_outbox]
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
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain) :
    (∀ u, (σ.removeLoggedRules S t).reach u (wAllNode dt r') = false) ∧
    (∀ u, σ.reach u (wAllNode dt r') = false) := by
  have htpp : ∀ ab ∈ (σ.removeLoggedRules S t).edges, ab.2.variant = Variant.plain :=
    fun ab hab => htp ab (removeLoggedRules_edges_subset σ S t ab hab)
  constructor
  · intro u
    cases hc : (σ.removeLoggedRules S t).reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain htpp (reach_sound hc)
      simp [wAllNode] at this
  · intro u
    cases hc : σ.reach u (wAllNode dt r') with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain htp (reach_sound hc)
      simp [wAllNode] at this

/-- **Retraction-leg `graphRec` stability off the mapped keys** (dual of
    `writeLeg_graphRec_stable`): an unmapped derived key's operand read is unchanged by the
    logged retraction, for EVERY subject. The plainness fence `htp` sits on the PRE-state `σ`
    (bigger multiset) — the sole hypothesis-shape change from the write leg. -/
theorem removeLeg_graphRec_stable {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R r' : String} {e : Expr}
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
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
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (s : SubjectRef) :
    (σ.removeLoggedRules S t).checkFn T' s dt on R e = σ.checkFn T' s dt on R e := by
  unfold GraphState.checkFn
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  exact removeLeg_graphRec_stable hclσ htp hlk hder hr' hon hunmapped s

/-- No rewrite-closure member of a derived-def store tuple targets the derived R-node
    `objNode ⟨dt,on⟩ R` (the `writeLeg_derived_inedges_eq` fragment argument, reused for the
    retraction): a stored `(dt,R)` tuple needs a `Direct` arm (dead on `ComputedOnly`), a
    rewrite output `(dt,R)` is forbidden by `noRuleOutputs_of_derived`. -/
theorem rewriteClosure_notarget_derived {S : Schema} {T : Store} {t : Tuple}
    (hSV : StoreValidRules S T) (ht : t ∈ T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (w : Tuple) (hw : w ∈ rewriteClosure S t) :
    objNode w.object w.relation ≠ objNode ⟨dt, on⟩ R := by
  intro h2
  have htype : dt = w.object.type := by
    simpa [objNode_type] using (congrArg NodeKey.type h2).symm
  have hrel : R = w.relation := by
    simpa [objNode_pred] using (congrArg NodeKey.pred h2).symm
  rcases rewriteClosure_produced hw with heq | ⟨r, hr', hro, hrout⟩
  · rw [heq] at htype hrel
    obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t ht
    rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
    rw [← hlk', exprDirects_computedOnly hco] at hrs
    simp at hrs
  · exact noRuleOutputs_of_derived hder r hr' ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩

/-- Membership of `(a,b)` survives one retraction step when no closure member targets `b`. -/
theorem mem_removeLoggedOne_edges_iff_of_ne {σ : GraphState} {u : Tuple} {a b : NodeKey}
    (hne : objNode u.object u.relation ≠ b) :
    ((a, b) ∈ (σ.removeLoggedOne u).edges ↔ (a, b) ∈ σ.edges) := by
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_edges]
    exact mem_removeEdgeOne_edges_of_ne (by intro h; exact hne (congrArg Prod.snd h).symm)
  · exact Iff.rfl

/-- Membership of `(a,b)` survives the retraction fold when no closure member targets `b`. -/
theorem mem_foldl_removeLoggedOne_edges_iff_of_notarget (us : List Tuple) {a b : NodeKey}
    (hnt : ∀ w ∈ us, objNode w.object w.relation ≠ b) :
    ∀ (σ : GraphState),
      ((a, b) ∈ (us.foldl (fun acc u => acc.removeLoggedOne u) σ).edges ↔ (a, b) ∈ σ.edges) := by
  induction us with
  | nil => intro σ; exact Iff.rfl
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih (fun w hw => hnt w (List.mem_cons_of_mem _ hw)) (σ.removeLoggedOne u)]
    exact mem_removeLoggedOne_edges_iff_of_ne (hnt u List.mem_cons_self)

/-- **The retraction never touches a derived key's in-edges** (dual of
    `writeLeg_derived_inedges_eq`): via `noRuleOutputs_of_derived` no rewrite-closure member
    targets a `DerNode`, so no in-edge into `objNode ⟨dt,on⟩ R` is erased. Clean — no path
    surgery, just fold-preservation. -/
theorem removeLeg_derived_inedges_eq {σ : GraphState} {S : Schema} {t : Tuple} {T : Store}
    (hSV : StoreValidRules S T) (ht : t ∈ T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  unfold GraphState.removeLoggedRules
  exact mem_foldl_removeLoggedOne_edges_iff_of_notarget (rewriteClosure S t)
    (fun w hw => rewriteClosure_notarget_derived hSV ht hlk hder hco w hw) σ

end Zanzibar
