import ZanzibarProofs.GraphIndex.UsStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.Spec.WellDef

/-!
# T2b, stage W1c — the userset-star write-closure and `check = sem`

`SEMANTICS.md` §7.3–7.5; ROADMAP "The staged T2 plan", sub-stage **W1c**;
`wildcard-materialization-spec.md §1.1` (the `concrete → w_any` in-bridge composition).

`UsStarCorrect.lean` proved both semantic cores of the W1c read correspondence *over
the operational facts they consume* — soundness over the grant-or-bridge edge
characterization (`usStarReach_of_trail` + `semAux_of_usStarReach`, a property of any
`UsStarReached` state), completeness over edge-completeness `hEC` and the **guarded**
in-bridge completeness `hib`. This file **assembles** the two halves into
`graph_correct_usStar` (full `check = sem`):

* **Soundness assembly** (`sem_of_usStar_probe`) — needs no closure and no fuel-count.
  The W1b plain-node accounting (`grantReach_of_trail`'s `isPlain`-source bound) does
  **not** transfer: a userset-star grant's source is a `w_any` node, not plain, and an
  in-bridge consumes a `w_any` as a target. Instead we discharge the fuel obligation via
  **`sem_fuel_stable`** (T0a): the chain gives `semAux` at fuel `m` for *some* `m`, and
  `sem` is stable above `fuelBound`, so `sem = semAux (max m fuelBound) = true` by
  `semAux_mono` (up to the max) then stability (down to `sem`). No tight `m ≤ fuelBound`
  bound is needed — the exact gap the ROADMAP flagged for W1c is sidestepped.
* **`UsStarReachedAdmitted`** + **`usStarReachedAdmitted_edge_complete`** (`hEC`) and
  **`usStarReachedAdmitted_inbridge_complete`** (discharging the guarded `hib`) — the W1c
  analog of `WildReachedAdmitted`.
* **`graph_correct_usStar`** — `check = sem` on the userset-star fragment (probe 1 ∨
  probe 2; probes 3,4 dead — objects star-free, no `w_all` target). Probe 2 is LIVE
  (a userset query subject's `wAny(s.shape)` sees userset-star direct grants), unlike
  W1b. Mirror of `graph_correct_bareStar`.
-/

namespace Zanzibar

/-! ## `StoreValid ⇒ StoreDeclared` (for the T0a stability hypothesis) -/

/-- Admission-validity implies the (weaker) `StoreDeclared` clause T0a needs: a stored
    tuple's subject type is named in its relation's `Direct` restrictions. From
    `restrictionMatches`: the matched restriction `r` has `r.1 = subject.type`, and
    `directTypes (.direct rs) = rs.map (·.1)`. -/
theorem storeDeclared_of_storeValid {S : Schema} {T : Store}
    (h : StoreValid S T) : StoreDeclared S T := by
  intro tup htup
  obtain ⟨rs, hlk, hrm⟩ := h tup htup
  refine ⟨Expr.direct rs, hlk, ?_⟩
  unfold restrictionMatches at hrm
  obtain ⟨r, hr, hrmatch⟩ := List.any_eq_true.mp hrm
  simp only [Bool.and_eq_true, beq_iff_eq] at hrmatch
  unfold directTypes
  exact List.mem_map.mpr ⟨r, hr, hrmatch.1.1.symm⟩

/-! ## Soundness assembly — the fuel obligation via T0a stability

`semAux_of_usStarReach` yields a `sem` membership at fuel = the chain length `m`, with
no bound on `m` (the W1c chain over-counts: an in-bridge hop is a separate hop but the
`sem` derivation absorbs it into the following userset-star grant). Rather than
re-derive a tight `m ≤ fuelBound` count (the plain-node argument breaks — a userset-star
grant's source is a `w_any` node), we appeal to fuel-stability: `sem` does not change
above `fuelBound`, so any fuel `≥ fuelBound` computes `sem`, and `semAux_mono` lifts the
fuel-`m` membership to `max m fuelBound ≥ fuelBound`. -/

/-- **`UsStarReach ⇒ sem` at `fuelBound`.** A generalized userset-star chain from a node
    `w` covering the star-free query subject to the concrete query object is a `sem`
    membership — discharging the fuel obligation via `sem_fuel_stable` (no tight
    chain-length bound). -/
theorem sem_of_usStarReach {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    {m : Nat} {w : NodeKey} (hcov : UsCovers q.subject w)
    (hm : UsStarReach T m w (objNode q.object q.relation)) : sem S T q = true := by
  have hsem_m : semAux S q.subject T q m q.object.type q.object.name q.relation = true :=
    semAux_of_usStarReach hWF hPD hSV hUS hm hqs hcov hqo rfl
  have hStrat := stratifiable_pureDirect hPD
  have hDecl := storeDeclared_of_storeValid hSV
  have hmf : m ≤ max m (fuelBound S T) := le_max_left _ _
  have hfbf : fuelBound S T ≤ max m (fuelBound S T) := le_max_right _ _
  have hsem_f := semAux_mono S (pureDirect_noExclAll hPD) q.subject T q hmf _ _ _ hsem_m
  rw [← sem_fuel_stable S T q hStrat hDecl _ hfbf]
  exact hsem_f

/-- **Soundness of the W1c read (forward direction).** From a probe source `w` covering
    the star-free query subject (probe 1 = `subjNode q.subject`, probe 2 =
    `wAnyNode q.subject.shape`), graph reachability to the concrete query object node is
    a `sem` membership. Routes through `usStarReach_of_trail` (existence of a chain) then
    `sem_of_usStarReach` (the fuel-stable discharge). -/
theorem sem_of_usStar_probe {S : Schema} {T : Store} {σ : GraphState} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReached σ S T) {w : NodeKey} (hcov : UsCovers q.subject w)
    (hnr : NReaches σ.edges w (objNode q.object q.relation)) : sem S T q = true := by
  have hwvar : w.variant = Variant.plain ∨ w.variant = Variant.wAny := by
    rcases hcov with h | ⟨_, h⟩
    · subst h; left; rw [subjNode_plain hqs]
    · subst h; right; rfl
  have hvvar : (objNode q.object q.relation).variant = Variant.plain := by
    rw [objNode_plain hqo]
  obtain ⟨l, hl⟩ := trail_of_nreaches hnr
  obtain ⟨m, hm⟩ := usStarReach_of_trail hReach hUS l.length l (le_refl _)
    w (objNode q.object q.relation) hwvar hvvar hl
  exact sem_of_usStarReach hWF hPD hSV hUS hqs hqo hcov hm

/-! ## The pre-grant states and the write as an `ite` -/

/-- The state reached after both endpoint nodes and both out-bridges
    (`ensureBridges`, inert on this object-wildcard-free fragment) — just before the
    in-bridges. -/
def GraphState.usS1 (σ : GraphState) (t : Tuple) : GraphState :=
  (((σ.addNode (subjNode t.subject)).addNode (objNode t.object t.relation)).ensureBridges
    (subjNode t.subject)).ensureBridges (objNode t.object t.relation)

/-- The fully-bridged pre-grant state: `usS1` then both in-bridges (`ensureInBridges`).
    `writeUsStar` adds the guarded grant edge over it. -/
def GraphState.usS2 (σ : GraphState) (t : Tuple) : GraphState :=
  ((σ.usS1 t).ensureInBridges (subjNode t.subject)).ensureInBridges (objNode t.object t.relation)

/-- `writeUsStar` as an explicit `ite` over `usS2` (definitional). -/
theorem writeUsStar_eq_ite (σ : GraphState) (t : Tuple) :
    σ.writeUsStar t =
      if (σ.usS2 t).admitEdge (subjNode t.subject) (objNode t.object t.relation)
      then (σ.usS2 t).addEdge (subjNode t.subject) (objNode t.object t.relation)
      else σ := rfl

@[simp] theorem usS1_schema (σ : GraphState) (t : Tuple) : (σ.usS1 t).schema = σ.schema := by
  unfold GraphState.usS1; simp
@[simp] theorem usS2_schema (σ : GraphState) (t : Tuple) : (σ.usS2 t).schema = σ.schema := by
  unfold GraphState.usS2; simp

/-! ## Edge and node effects of the in-bridge machinery -/

/-- `ensureInBridges` only ever adds edges. -/
theorem ensureInBridges_edges_mono {σ : GraphState} {c : NodeKey} {e : NodeKey × NodeKey}
    (he : e ∈ σ.edges) : e ∈ (σ.ensureInBridges c).edges := by
  unfold GraphState.ensureInBridges
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr]; split
    · rw [addEdge_edges, addNode_edges]; exact List.mem_cons_of_mem _ he
    · rw [addNode_edges]; exact he
  · rw [if_neg (by simpa using hbr)]; exact he

/-- A node of `ensureInBridges` is old or the single `w_any` node it may add. -/
theorem ensureInBridges_nodes_mem {σ : GraphState} {c k : NodeKey}
    (hk : k ∈ (σ.ensureInBridges c).nodes) :
    k ∈ σ.nodes ∨ k = wAnyNode (c.type, c.pred) := by
  unfold GraphState.ensureInBridges at hk
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr] at hk; split at hk
    · rw [addEdge_nodes, addNode_nodes] at hk
      rcases List.mem_cons.mp hk with h | h; exact Or.inr h; exact Or.inl h
    · rw [addNode_nodes] at hk
      rcases List.mem_cons.mp hk with h | h; exact Or.inr h; exact Or.inl h
  · rw [if_neg (by simpa using hbr)] at hk; exact Or.inl hk

/-- A node of `ensureBridges` is old or the single `w_all` node it may add. -/
theorem ensureBridges_nodes_mem {σ : GraphState} {c k : NodeKey}
    (hk : k ∈ (σ.ensureBridges c).nodes) :
    k ∈ σ.nodes ∨ k = wAllNode c.type c.pred := by
  unfold GraphState.ensureBridges at hk
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr] at hk; split at hk
    · rw [addEdge_nodes, addNode_nodes] at hk
      rcases List.mem_cons.mp hk with h | h; exact Or.inr h; exact Or.inl h
    · rw [addNode_nodes] at hk
      rcases List.mem_cons.mp hk with h | h; exact Or.inr h; exact Or.inl h
  · rw [if_neg (by simpa using hbr)] at hk; exact Or.inl hk

/-- An admitted, bridged-in concrete endpoint gets its `c → w_any` in-bridge. -/
theorem ensureInBridges_creates_bridge {σ : GraphState} {c : NodeKey}
    (hbc : σ.bridgedInConcrete c = true)
    (hadm : (σ.addNode (wAnyNode (c.type, c.pred))).admitEdge c (wAnyNode (c.type, c.pred)) = true) :
    (c, wAnyNode (c.type, c.pred)) ∈ (σ.ensureInBridges c).edges := by
  unfold GraphState.ensureInBridges
  rw [if_pos hbc, if_pos hadm, addEdge_edges]
  exact List.mem_cons_self

/-- Old edges survive the whole userset-star write (accepted or rejected). -/
theorem writeUsStar_edges_mono {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ σ.edges) : e ∈ (σ.writeUsStar t).edges := by
  rw [writeUsStar_eq_ite]
  split
  · rw [addEdge_edges]
    refine List.mem_cons_of_mem _ ?_
    unfold GraphState.usS2 GraphState.usS1
    exact ensureInBridges_edges_mono (ensureInBridges_edges_mono
      (ensureBridges_edges_mono (ensureBridges_edges_mono (by simpa using he))))
  · exact he

/-- An admitted grant materializes its edge. -/
theorem writeUsStar_grant_edge {σ : GraphState} {t : Tuple}
    (hadm : (σ.usS2 t).admitEdge (subjNode t.subject) (objNode t.object t.relation) = true) :
    (subjNode t.subject, objNode t.object t.relation) ∈ (σ.writeUsStar t).edges := by
  rw [writeUsStar_eq_ite, if_pos hadm, addEdge_edges]
  exact List.mem_cons_self

/-- A **new plain** node of a userset-star write is one of the two endpoints (the
    bridge machinery only adds `w_all` / `w_any` nodes, which are not plain). -/
theorem writeUsStar_new_plain_node {σ : GraphState} {t : Tuple} {c : NodeKey}
    (hc : c ∈ (σ.writeUsStar t).nodes) (hpl : c.variant = Variant.plain) :
    c ∈ σ.nodes ∨ c = subjNode t.subject ∨ c = objNode t.object t.relation := by
  have hne_wAny : ∀ sh : Shape, c ≠ wAnyNode sh := by
    intro sh h; rw [h] at hpl; simp [wAnyNode] at hpl
  have hne_wAll : ∀ x r, c ≠ wAllNode x r := by
    intro x r h; rw [h] at hpl; simp [wAllNode] at hpl
  rw [writeUsStar_eq_ite] at hc
  split at hc
  case isFalse => exact Or.inl hc
  rw [addEdge_nodes] at hc
  have hc2 : c ∈ (σ.usS2 t).nodes := hc
  -- peel usS2 = usS1 ▸ ensureInBridges a ▸ ensureInBridges b
  unfold GraphState.usS2 at hc2
  rcases ensureInBridges_nodes_mem hc2 with hc1b | h; swap
  · exact absurd h (hne_wAny _)
  rcases ensureInBridges_nodes_mem hc1b with hc1 | h; swap
  · exact absurd h (hne_wAny _)
  -- hc1 : c ∈ (σ.usS1 t).nodes ; peel usS1
  unfold GraphState.usS1 at hc1
  rcases ensureBridges_nodes_mem hc1 with hc0b | h; swap
  · exact absurd h (hne_wAll _ _)
  rcases ensureBridges_nodes_mem hc0b with hc0 | h; swap
  · exact absurd h (hne_wAll _ _)
  -- hc0 : c ∈ ((σ.addNode a).addNode b).nodes
  rw [addNode_nodes, addNode_nodes] at hc0
  rcases List.mem_cons.mp hc0 with h | h
  · exact Or.inr (Or.inr h)
  · rcases List.mem_cons.mp h with h | h
    · exact Or.inr (Or.inl h)
    · exact Or.inl h

/-! ## A stored userset-star grant's shape is a declared subject-wildcard userset -/

/-- A stored userset-star grant `g = (T,*,P)` (`P ≠ BARE`) of an admission-valid store
    has `S.isSubjectWildcardUserset T P = true`: the grant matched a `Direct` restriction
    `(T,P,true)` (subject wildcard), and that restriction occurs in the schema. This is
    the `bridged_in_shapes` membership `bridgedInConcrete` tests. -/
theorem isSWU_of_storeValid {S : Schema} {T : Store} (hSV : StoreValid S T) {g : Tuple}
    (hg : g ∈ T) (hgstar : g.subject.name = STAR) (hpb : g.subject.predicate ≠ BARE) :
    S.isSubjectWildcardUserset g.subject.type g.subject.predicate = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV g hg
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = (g.object.type, g.relation)) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    rw [hf] at hlk
    simp only [Option.map_some, Option.some.injEq] at hlk
    have hpmem : p ∈ S.defs := List.mem_of_find?_eq_some hf
    unfold restrictionMatches at hrm
    obtain ⟨r, hr, hrmatch⟩ := List.any_eq_true.mp hrm
    simp only [Bool.and_eq_true, beq_iff_eq] at hrmatch
    obtain ⟨⟨htype, hpred⟩, hstar⟩ := hrmatch
    have hr22 : r.2.2 = true := by rw [hgstar] at hstar; simpa using hstar
    have hreq : (g.subject.type, g.subject.predicate, true) = r := by
      rw [htype, hpred, ← hr22]
    unfold Schema.isSubjectWildcardUserset
    rw [Bool.and_eq_true]
    refine ⟨by simpa [bne_iff_ne] using hpb, ?_⟩
    refine List.any_eq_true.mpr ⟨p, hpmem, ?_⟩
    rw [hlk]
    have hER : exprRestrictions (Expr.direct rs) = rs := rfl
    rw [hER, List.contains_eq_mem, decide_eq_true_eq, hreq]
    exact hr

/-! ## The admitted, bridge-complete userset-star write-closure -/

/-- **`UsStarReachedAdmitted σ S T`** — reachable by userset-star bridge-materializing
    writes whose grant edge (`hadmGrant`) and — for each concrete, bridged-in endpoint
    — its `c → w_any` in-bridge passed cycle-rejection (`hadmInA`, `hadmInB`, guarded by
    `bridgedInConcrete`). This carves out the "no in-bridge cycle" fragment on which
    in-bridge completeness holds (the W1c analog of `WildReachedAdmitted`'s `hadmSub`).
    A cycle-rejected grant rolls the whole write back, so the store never holds it. -/
inductive UsStarReachedAdmitted : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : UsStarReachedAdmitted (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hprev : UsStarReachedAdmitted σ S T)
      (hadmInA : (σ.usS1 t).bridgedInConcrete (subjNode t.subject) = true →
        ((σ.usS1 t).addNode (wAnyNode ((subjNode t.subject).type, (subjNode t.subject).pred))).admitEdge
          (subjNode t.subject) (wAnyNode ((subjNode t.subject).type, (subjNode t.subject).pred)) = true)
      (hadmInB : ((σ.usS1 t).ensureInBridges (subjNode t.subject)).bridgedInConcrete
          (objNode t.object t.relation) = true →
        (((σ.usS1 t).ensureInBridges (subjNode t.subject)).addNode
          (wAnyNode ((objNode t.object t.relation).type, (objNode t.object t.relation).pred))).admitEdge
          (objNode t.object t.relation)
          (wAnyNode ((objNode t.object t.relation).type, (objNode t.object t.relation).pred)) = true)
      (hadmGrant : (σ.usS2 t).admitEdge (subjNode t.subject) (objNode t.object t.relation) = true) :
      UsStarReachedAdmitted (σ.writeUsStar t) S (t :: T)

/-- Admitted writes are a special case of the userset-star write-closure. -/
theorem usStarReached_of_admitted {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReachedAdmitted σ S T) : UsStarReached σ S T := by
  induction h with
  | empty S => exact UsStarReached.empty S
  | step t _ _ _ _ ih => exact UsStarReached.step t ih

/-- The schema is fixed along the closure. -/
theorem usStarReachedAdmitted_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReachedAdmitted σ S T) : σ.schema = S :=
  (usStarReached_structInv (usStarReached_of_admitted h)).schemaEq

/-! ## `hEC` — edge-completeness -/

/-- **Edge-completeness** (`hEC`): every stored grant's edge is present (no write was
    rejected). Mirror of `wildReachedAdmitted_edge_complete`. -/
theorem usStarReachedAdmitted_edge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReachedAdmitted σ S T) :
    ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges := by
  induction h with
  | empty S => intro t ht; simp at ht
  | step t _ _ _ hadmGrant ih =>
    intro t' ht'
    rcases List.mem_cons.mp ht' with rfl | hmem
    · exact writeUsStar_grant_edge hadmGrant
    · exact writeUsStar_edges_mono (ih t' hmem)

/-! ## In-bridge completeness — the invariant discharging the guarded `hib` -/

/-- `bridgedInConcrete` depends only on the schema (and `c`'s intrinsic fields). -/
theorem bridgedInConcrete_schema_eq {σ σ' : GraphState} (h : σ.schema = σ'.schema)
    (c : NodeKey) : σ.bridgedInConcrete c = σ'.bridgedInConcrete c := by
  unfold GraphState.bridgedInConcrete; rw [h]

/-- **In-bridge completeness invariant.** In the admitted closure, every **live**
    concrete, bridged-in node `c` has its `c → w_any` in-bridge. Proof: a bridgedIn
    node is plain, so it enters `σ.nodes` only as a write *endpoint* (never a `w_all` /
    `w_any` node), and that write ran `ensureInBridges` on it, which — with the closure's
    admission guard — materialized the bridge. Old-node bridges persist monotonically. -/
theorem usStarReachedAdmitted_inbridge_live {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReachedAdmitted σ S T) :
    ∀ c, σ.bridgedInConcrete c = true → c ∈ σ.nodes →
      (c, wAnyNode (c.type, c.pred)) ∈ σ.edges := by
  induction h with
  | empty S => intro c _ hc; simp [emptyState] at hc
  | @step σ S T t hprev hadmInA hadmInB hadmGrant ih =>
    intro c hbc hcn
    have hsc : (σ.writeUsStar t).schema = σ.schema := writeUsStar_schema σ t
    have hbcσ : σ.bridgedInConcrete c = true := by
      rwa [bridgedInConcrete_schema_eq hsc] at hbc
    have hpl : c.variant = Variant.plain := by
      unfold GraphState.bridgedInConcrete at hbcσ
      simp only [Bool.and_eq_true, beq_iff_eq] at hbcσ; exact hbcσ.1.1
    rcases writeUsStar_new_plain_node hcn hpl with hold | rfl | rfl
    · exact writeUsStar_edges_mono (ih c hbcσ hold)
    · -- c = subjNode t.subject : the a-endpoint in-bridge
      have hbc_a : (σ.usS1 t).bridgedInConcrete (subjNode t.subject) = true := by
        rw [bridgedInConcrete_schema_eq (by simp : (σ.usS1 t).schema = σ.schema)]; exact hbcσ
      have hbridge := ensureInBridges_creates_bridge hbc_a (hadmInA hbc_a)
      -- lift through ensureInBridges b, then the grant addEdge
      have h1 : (subjNode t.subject,
          wAnyNode ((subjNode t.subject).type, (subjNode t.subject).pred))
          ∈ (σ.usS2 t).edges := by
        unfold GraphState.usS2; exact ensureInBridges_edges_mono hbridge
      rw [writeUsStar_eq_ite, if_pos hadmGrant, addEdge_edges]
      exact List.mem_cons_of_mem _ h1
    · -- c = objNode t.object t.relation : the b-endpoint in-bridge
      have hbc_b : ((σ.usS1 t).ensureInBridges (subjNode t.subject)).bridgedInConcrete
          (objNode t.object t.relation) = true := by
        rw [bridgedInConcrete_schema_eq
          (by simp : ((σ.usS1 t).ensureInBridges (subjNode t.subject)).schema = σ.schema)]
        exact hbcσ
      have hbridge := ensureInBridges_creates_bridge hbc_b (hadmInB hbc_b)
      have h1 : (objNode t.object t.relation,
          wAnyNode ((objNode t.object t.relation).type, (objNode t.object t.relation).pred))
          ∈ (σ.usS2 t).edges := by
        unfold GraphState.usS2; exact hbridge
      rw [writeUsStar_eq_ite, if_pos hadmGrant, addEdge_edges]
      exact List.mem_cons_of_mem _ h1

/-- **`hib` discharged.** For a stored userset-star grant `g = (T,*,P)` and an
    `instances` witness `inst` whose concrete node `⟨T,inst,P⟩` already has an in-edge,
    the materialized `⟨T,inst,P⟩ → w_any(T,P)` bridge is present. The in-edge forces the
    node live (endpoint-closure), its shape is `bridgedInConcrete` (`isSWU_of_storeValid`
    + `inst ≠ STAR`), and the invariant supplies the bridge. -/
theorem usStarReachedAdmitted_hib {σ : GraphState} {S : Schema} {T : Store} {q : Query}
    (h : UsStarReachedAdmitted σ S T) (hSV : StoreValid S T) :
    ∀ g ∈ T, g.subject.name = STAR → g.subject.predicate ≠ BARE →
      ∀ inst ∈ instances T q g.subject.type,
        (∃ x, (x, subjNode ⟨g.subject.type, inst, g.subject.predicate⟩) ∈ σ.edges) →
        (subjNode ⟨g.subject.type, inst, g.subject.predicate⟩,
          wAnyNode (g.subject.type, g.subject.predicate)) ∈ σ.edges := by
  intro g hg hgstar hpb inst hinst ⟨x, hx⟩
  have hStruct : StructInv S σ := usStarReached_structInv (usStarReached_of_admitted h)
  have hsc : σ.schema = S := hStruct.schemaEq
  have hinstne : inst ≠ STAR := instances_ne_star T q g.subject.type inst hinst
  set c : NodeKey := subjNode ⟨g.subject.type, inst, g.subject.predicate⟩ with hc_def
  have hcplain : c = ⟨g.subject.type, inst, g.subject.predicate, Variant.plain⟩ := by
    rw [hc_def, subjNode_plain hinstne]
  have hctype : c.type = g.subject.type := by rw [hcplain]
  have hcpred : c.pred = g.subject.predicate := by rw [hcplain]
  -- c is bridgedInConcrete
  have hbc : σ.bridgedInConcrete c = true := by
    have hswu := isSWU_of_storeValid hSV hg hgstar hpb
    unfold GraphState.bridgedInConcrete
    rw [hsc, hcplain]
    simp only [Bool.and_eq_true]
    refine ⟨⟨rfl, ?_⟩, hswu⟩
    simpa [bne_iff_ne] using hinstne
  -- c is live (target of an edge)
  have hcn : c ∈ σ.nodes := (hStruct.edgesClosed (x, c) hx).2
  have hbridge := usStarReachedAdmitted_inbridge_live h c hbc hcn
  rw [hctype, hcpred] at hbridge
  exact hbridge

/-! ## Dead probes and edge-source shape (for the top-level assembly) -/

/-- No edge targets a `w_all` node: grant/out-bridge targets are concrete (plain,
    objects star-free), in-bridge targets are `w_any`. So probes 3,4 are dead. -/
theorem usStarReached_edge_target_ne_wAll {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) (hUS : UsStarStore T) :
    ∀ a b, (a, b) ∈ σ.edges → b.variant ≠ Variant.wAll := by
  intro a b hab
  rcases usStarReached_grant_or_bridge h a b hab with ⟨t, htT, _, h2⟩ | ⟨_, hbv, _⟩ | ⟨hb, _, _, _⟩
  · rw [h2, objNode_plain (hUS t htT).1]; simp
  · rw [hbv]; simp
  · rw [hb, wAnyNode]; simp

/-- Every edge *source* is a plain node, a `w_any` node with a non-bare predicate (a
    userset-star grant's source), or a `w_all` node (an out-bridge's source). A
    bare-`w_any` node is never a source — that needs a bare-star grant, forbidden by
    `UsStarStore`. This makes probe 2 dead for a *bare* query subject (live for a
    userset one). -/
theorem usStarReached_edge_source_char {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) (hUS : UsStarStore T) :
    ∀ a b, (a, b) ∈ σ.edges →
      a.variant = Variant.plain ∨ (a.variant = Variant.wAny ∧ a.pred ≠ BARE)
      ∨ a.variant = Variant.wAll := by
  intro a b hab
  rcases usStarReached_grant_or_bridge h a b hab with ⟨t, htT, h1, _⟩ | ⟨ha, _, _⟩ | ⟨_, hav, _, _⟩
  · by_cases hst : t.subject.name = STAR
    · refine Or.inr (Or.inl ⟨?_, ?_⟩)
      · rw [h1, subjNode, if_pos hst]
      · rw [h1, subjNode, if_pos hst]
        simpa [wAnyNode, SubjectRef.shape] using (hUS t htT).2 hst
    · exact Or.inl (by rw [h1, subjNode_plain hst])
  · exact Or.inr (Or.inr (by rw [ha, wAllNode]))
  · exact Or.inl hav

/-! ## T2b on the W1c (userset-star) fragment, assembled -/

/-- **T2b, userset-star fragment (W1c), the full `check = sem`.** On any state reached
    by admitted bridge-materializing userset-star writes of an admission-valid store
    with userset-star subject grants (`[T:*#P]`, objects star-free), the graph read
    answers exactly `sem` for every star-free query. Probes 3,4 are dead (no `w_all`
    target, `usStarReached_edge_target_ne_wAll`); probe 1 (concrete subject) and probe 2
    (`w_any(shape)`, **live** for a userset query subject via userset-star direct grants)
    are handled by the soundness assembly `sem_of_usStar_probe` (forward, fuel via T0a
    stability) and `reach_of_semAux_us` (backward, `hEC`/`hib` discharged by the admitted
    closure). Probe 2 is dead for a *bare* query subject
    (`usStarReached_edge_source_char`). Mirror of `graph_correct_bareStar`. -/
theorem graph_correct_usStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReachedAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hWR : UsStarReached σ S T := usStarReached_of_admitted hReach
  have hStruct : StructInv S σ := usStarReached_structInv hWR
  have hcl := hStruct.edgesClosed
  have hsch : σ.schema = S := hStruct.schemaEq
  have htgt := usStarReached_edge_target_ne_wAll hWR hUS
  have hsrc := usStarReached_edge_source_char hWR hUS
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
    unfold GraphModel.check; rw [hsch, isDerived_pureDirect hPD]; simp
  have hpAll : ∀ u, σ.reach u (wAllNode q.object.type q.relation) = false := by
    intro u
    cases hc : σ.reach u (wAllNode q.object.type q.relation) with
    | false => rfl
    | true =>
      exfalso
      obtain ⟨x, hx⟩ := nreaches_last_edge (reach_sound hc)
      exact htgt x _ hx rfl
  have hqsb : (q.subject.name != STAR) = true := by simp only [bne_iff_ne, ne_eq]; exact hqs
  have hprobe : GraphModel.probeNonDerived σ q =
      (σ.reach (subjNode q.subject) (objNode q.object q.relation)
       || σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation)) := by
    unfold GraphModel.probeNonDerived; simp [hpAll, hqsb]
  have hfwd : ∀ w, UsCovers q.subject w →
      NReaches σ.edges w (objNode q.object q.relation) → sem S T q = true :=
    fun w hcov hnr => sem_of_usStar_probe hWF hPD hSV hUS hqs hqo hWR hcov hnr
  have hbwd : sem S T q = true →
      σ.reach (subjNode q.subject) (objNode q.object q.relation) = true
      ∨ σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) = true := by
    intro hsem
    unfold sem at hsem
    rcases reach_of_semAux_us hPD hUS hqs (usStarReachedAdmitted_edge_complete hReach)
        (usStarReachedAdmitted_hib hReach hSV) _ _ _ _ hsem with hL | hR
    · exact Or.inl (reach_complete hcl hL)
    · exact Or.inr (reach_complete hcl hR)
  rw [hroute, hprobe]
  cases hsemc : sem S T q with
  | true =>
    rcases hbwd hsemc with h | h
    · rw [h, Bool.true_or]
    · rw [h, Bool.or_true]
  | false =>
    have hn1 : σ.reach (subjNode q.subject) (objNode q.object q.relation) = false := by
      cases hc : σ.reach (subjNode q.subject) (objNode q.object q.relation) with
      | false => rfl
      | true =>
        have := hfwd (subjNode q.subject) (Or.inl rfl) (reach_sound hc)
        rw [hsemc] at this; exact absurd this (by simp)
    have hn2 : σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) = false := by
      cases hc : σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) with
      | false => rfl
      | true =>
        have hnr := reach_sound hc
        obtain ⟨w', hw'⟩ := nreaches_first_edge hnr
        rcases hsrc _ _ hw' with hpl | ⟨_, hpred⟩ | hwall
        · simp [wAnyNode] at hpl
        · have hqp : q.subject.predicate ≠ BARE := by
            simpa [wAnyNode, SubjectRef.shape] using hpred
          have := hfwd (wAnyNode q.subject.shape) (Or.inr ⟨hqp, rfl⟩) hnr
          rw [hsemc] at this; exact absurd this (by simp)
        · simp [wAnyNode] at hwall
    rw [hn1, hn2]; rfl

end Zanzibar
