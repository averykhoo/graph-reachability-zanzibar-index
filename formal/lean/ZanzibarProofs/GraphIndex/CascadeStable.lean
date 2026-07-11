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

end Zanzibar
