import ZanzibarProofs.GraphIndex.Cascade

/-!
# Fan-out completeness — write-leg operand stability off the mapped keys (ROADMAP W3d-1b)

`index_v4/processor.py:585-652` (`_map_deltas_to_keys`) + `core.py:_emit`: a write
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
edge's head is the `wAll` node, whose name is `STAR`, which `_map_deltas_to_keys`
skips (`processor.py:604-605`). The Python system is immune because its closure
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
    `_emit` (`core.py:31-44`): a flip inserts its row inside the same transaction. -/
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
          u.relation⟩, List.mem_cons_self, ?_, ?_⟩
        · show σ.watermark < (σc.writeDirect u).nextDeltaId
          have h1 : (σc.writeDirect u).nextDeltaId
              = max (σc.writeDirect u).maxOutboxId (σc.writeDirect u).watermark + 1 := rfl
          have h2 : (σc.writeDirect u).watermark = σc.watermark :=
            writeDirect_watermark σc u
          omega
        · show (⟨(σc.writeDirect u).nextDeltaId, objNode u.object u.relation,
            u.relation⟩ : Delta).node = ab'.2
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
    `affectedKeys` skips the star-named head (`processor.py:604-605`). The store
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
  refine List.mem_flatMap.mpr ⟨objNode ⟨dt, on⟩ r', hobj, ?_⟩
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
    obtain ⟨v, hv, hkv⟩ := List.mem_flatMap.mp hkd
    exact List.mem_flatMap.mpr ⟨v, affectedObjects_writeLeg_mono hclσ' d v hv, hkv⟩

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

/-- **The untainted-core shadow relation.** `σ`'s edges are `σ0`'s plus edges into
    terminal `DerNode`s; both endpoint-closed; `σ0`'s core embeds. -/
structure UntaintedShadow (S : Schema) (σ σ0 : GraphState) : Prop where
  classify : ∀ ab ∈ σ.edges, ab ∈ σ0.edges ∨ DerNode S ab.2
  sub : ∀ ab ∈ σ0.edges, ab ∈ σ.edges
  nodesSub : ∀ k ∈ σ0.nodes, k ∈ σ.nodes
  closed : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes
  closed0 : ∀ ab ∈ σ0.edges, ab.1 ∈ σ0.nodes ∧ ab.2 ∈ σ0.nodes
  term : ∀ k, DerNode S k → ∀ y, (k, y) ∉ σ.edges

/-- **Reach agreement off the `DerNode`s**: a probe into a non-`DerNode` target reads
    the same on `σ` and its shadow — extra edges are trailing hops onto terminal
    nodes the path can neither traverse nor end at. -/
theorem shadow_reach_agree {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) {v : NodeKey} (hv : ¬ DerNode S v) (x : NodeKey) :
    σ.reach x v = σ0.reach x v := by
  cases h1 : σ.reach x v <;> cases h0 : σ0.reach x v
  · rfl
  · exfalso
    have := reach_complete hsh.closed (NReaches.mono_subset hsh.sub (reach_sound h0))
    rw [h1] at this
    cases this
  · exfalso
    rcases nreaches_factor (P := fun ab => DerNode S ab.2) hsh.classify (reach_sound h1)
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
    subject node, which is never a `DerNode` on the fragment. -/
theorem shadow_admitEdge_agree {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) {a : NodeKey} (ha : ¬ DerNode S a) (b : NodeKey) :
    σ.admitEdge a b = σ0.admitEdge a b := by
  unfold GraphState.admitEdge
  rw [shadow_reach_agree hsh ha b]

/-- One parallel step: the logged write on `σ`, the plain write on the shadow —
    admission agrees, so the shadow relation is maintained. -/
theorem untaintedShadow_writeLoggedOne {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) {u : Tuple}
    (ha : ¬ DerNode S (subjNode u.subject)) :
    UntaintedShadow S (σ.writeLoggedOne u) (σ0.writeDirect u) := by
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
theorem untaintedShadow_writeLeg {S : Schema} :
    ∀ (us : List Tuple) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      (∀ u ∈ us, ¬ DerNode S (subjNode u.subject)) →
      UntaintedShadow S (us.foldl (fun acc u => acc.writeLoggedOne u) σ)
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
theorem untaintedShadow_foldAdmits {S : Schema} :
    ∀ (us : List Tuple) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      (∀ u ∈ us, ¬ DerNode S (subjNode u.subject)) →
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
    have hstep : UntaintedShadow S (σ.writeLoggedOne u) (σ0.writeDirect u) :=
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

/-- **A cascade leg preserves the shadow** (the shadow state is untouched): pass
    edges are `DerNode`-targeted, removals never hit shadow edges (a rules state has
    no in-edge at a `RootBoolean` derived R-node), sources stay off the `DerNode`s
    (bare candidates vs non-bare derived relations). -/
theorem untaintedShadow_cascade {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs : List W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) :
    UntaintedShadow S (runCascade S T σ jobs) σ0 := by
  rcases runCascade_cases S T σ jobs with hrc | hrc
  · rw [hrc]
    have hev := reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs
    -- shadow edges never sit at a job's R-node (RootBoolean ⇒ no rules in-edge)
    have hnojob : ∀ ab ∈ σ0.edges, ∀ j ∈ jobs, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R := by
      intro ab hab j hj heq
      obtain ⟨_, _, _, _, _, _, hder, hlke, _⟩ := hjv j hj
      have hroot : RootBoolean j.e :=
        hRootB ⟨(j.dt, j.R), j.e⟩ (mem_defs_of_lookup hlke) hder
      have hno := reachedByRules_RootBoolean_no_inedge (on := j.on) hSV hNK hlke hroot h0 ab.1
      rw [← heq] at hno
      exact hno hab
    refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
    · -- classify
      intro ab hab
      have hab' : ab ∈ (reconcileJobsL S T σ jobs).edges := hab
      rw [hev.edges] at hab'
      obtain ⟨a, b⟩ := ab
      rcases reconcileJobsD_edge_sound jobs σ a b hab' with hold | ⟨j, hj, c, _, _, h2⟩
      · exact hsh.classify (a, b) hold
      · obtain ⟨hRne, _, _, _, _, _, hder, _, hon⟩ := hjv j hj
        exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
    · -- sub
      intro ab hab
      show ab ∈ (reconcileJobsL S T σ jobs).edges
      rw [hev.edges]
      exact reconcileJobsD_edge_pres_target jobs σ ab (hnojob ab hab) (hsh.sub ab hab)
    · -- nodesSub
      intro k hk
      show k ∈ (reconcileJobsL S T σ jobs).nodes
      rw [hev.nodes]
      exact reconcileJobsD_nodes_mono jobs σ k (hsh.nodesSub k hk)
    · -- closed
      intro ab hab
      have hab' : ab ∈ (reconcileJobsL S T σ jobs).edges := hab
      rw [hev.edges] at hab'
      have := edgesClosed_reconcileJobsD jobs σ hsh.closed ab hab'
      show ab.1 ∈ (reconcileJobsL S T σ jobs).nodes
        ∧ ab.2 ∈ (reconcileJobsL S T σ jobs).nodes
      rw [hev.nodes]
      exact this
    · -- term
      intro k hk y hy
      have hy' : (k, y) ∈ (reconcileJobsL S T σ jobs).edges := hy
      rw [hev.edges] at hy'
      rcases reconcileJobsD_edge_sound jobs σ k y hy' with hold | ⟨j, hj, c, hc, h1, _⟩
      · exact hsh.term k hk y hold
      · obtain ⟨dt, on, R, _, hRne, _, hkey⟩ := hk
        obtain ⟨_, hcb, _, _, _, _, _, _, _⟩ := hjv j hj
        have : R = c.predicate := by
          have hp := congrArg NodeKey.pred (hkey.symm.trans h1)
          simpa [objNode_pred, subjNode_pred] using hp
        rw [hcb c hc] at this
        exact hRne this
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
    (∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2) →
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
    intro hNK hRootB hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hRootB
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
    intro hNK hRootB hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hRootB hSV hterm
    exact ⟨σ0, h0,
      untaintedShadow_cascade hsh (reachedByRules_of_admitted h0) hSV hNK hRootB hjv⟩

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
  have hv3 : ¬ DerNode S (wAllNode dt' r') := by
    rintro ⟨dt, on, R, _, _, hon, heq⟩
    rw [objNode_plain hon] at heq
    have := congrArg NodeKey.variant heq
    simp [wAllNode] at this
  unfold GraphModel.graphRec GraphModel.probeNonDerived
  dsimp only
  rw [shadow_reach_agree hsh hv1 (subjNode s), shadow_reach_agree hsh hv1 (wAnyNode s.shape),
    shadow_reach_agree hsh hv3 (subjNode s), shadow_reach_agree hsh hv3 (wAnyNode s.shape)]

/-- **The W3d read bridge (`checkFn_eq_sem_w3d`)**: the compiled pass guard equals
    `sem` at EVERY W3d state — through the untainted-core shadow (`checkFn` reads
    only untainted operands; `checkFn_eq_sem_bs` at the rules-admitted shadow).
    Subject-generic up to star-BARE subjects. -/
theorem checkFn_eq_sem_w3d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
  exact checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
    (ReachedByW3aAdmitted.base h0) hlk hco hleafUnt hs hon

end Zanzibar
