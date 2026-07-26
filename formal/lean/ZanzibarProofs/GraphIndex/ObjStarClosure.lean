import ZanzibarProofs.GraphIndex.ObjStarCorrect

/-!
# T2b, stage W1b — the admitted, bridge-complete write-closure

`SEMANTICS.md` §7.3–7.5; ROADMAP "The staged T2 plan", sub-stage **W1b**;
`wildcard-materialization-spec.md §3.4`.

`ObjStarCorrect.lean` proved both semantic cores of the W1b read correspondence
*over the operational facts they consume* — soundness over the grant-or-bridge edge
characterization (a property of any `WildReached` state), completeness over
edge-completeness `hEC` and the bridge hypothesis `hbr`. This file **discharges
those operational hypotheses** by building the composed-system write-closure — the
W1b analog of `ReachedByAdmitted` — and proving the two facts hold on it:

* **`WildReachedAdmitted`** — reachable by bridge-materializing writes whose grant
  edge *and* subject-endpoint bridge passed cycle-rejection (the "no
  wildcard-own-shape cycle" fragment). Faithful to the composed system, where a
  cycle-rejected grant rolls the whole write back (so the store never holds it).
* **`wildReachedAdmitted_edge_complete`** (`hEC`) — every stored grant's edge is
  present (mirror of `admitted_edge_complete`).
* **`wall_reach_isObjectWildcard`** (Lemma A) — a reachable `w_all(T,R)` node forces
  `S.isObjectWildcard T R` (its only in-edges are object-wildcard grants, which
  `ObjStarValid` puts on a declared object-wildcard shape).
* **`wildReachedAdmitted_bridge_complete`** (bridge-completeness) — every stored
  grant whose *subject* shape is a declared object-wildcard has its materialized
  `w_all → concrete` bridge. Combined with Lemma A this discharges `hbr`.

The write-effect plumbing (`writeWildPre`, edge-monotonicity, the grant/bridge
creation lemmas) sits at the top; the closure and its two completeness facts below.
-/

namespace Zanzibar

/-! ## The pre-grant (fully bridged) state and the write as an `ite` -/

/-- The state `writeWild` reaches *just before* the guarded grant edge: both
    endpoint nodes added and both endpoints' out-bridges materialized
    (bridge-before-grant). Naming the intermediate lets the closure state the grant
    admission over it and lets the edge lemmas avoid re-deriving the `let` chain. -/
def GraphState.writeWildPre (σ : GraphState) (t : Tuple) : GraphState :=
  (((σ.addNode (subjNode t.subject)).addNode (objNode t.object t.relation)).ensureBridges
    (subjNode t.subject)).ensureBridges (objNode t.object t.relation)

/-- `writeWild` as an explicit `ite` over `writeWildPre` (definitional: `writeWildPre`
    is exactly `writeWild`'s `let`-bound `σ1`). -/
theorem writeWild_eq_ite (σ : GraphState) (t : Tuple) :
    σ.writeWild t =
      if (σ.writeWildPre t).admitEdge (subjNode t.subject) (objNode t.object t.relation)
      then (σ.writeWildPre t).addEdge (subjNode t.subject) (objNode t.object t.relation)
      else σ := rfl

/-! ## Edge monotonicity through the bridge machinery -/

/-- `ensureBridges` only ever adds edges. -/
theorem ensureBridges_edges_mono {σ : GraphState} {c : NodeKey} {e : NodeKey × NodeKey}
    (he : e ∈ σ.edges) : e ∈ (σ.ensureBridges c).edges := by
  unfold GraphState.ensureBridges
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr]
    split
    · rw [addEdge_edges, addNode_edges]; exact List.mem_cons_of_mem _ he
    · rw [addNode_edges]; exact he
  · rw [if_neg (by simpa using hbr)]; exact he

/-- Old edges survive `writeWildPre`. -/
theorem writeWildPre_edges_mono {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ σ.edges) : e ∈ (σ.writeWildPre t).edges := by
  unfold GraphState.writeWildPre
  exact ensureBridges_edges_mono (ensureBridges_edges_mono (by simpa using he))

/-- Old edges survive the whole write (accepted or rejected). -/
theorem writeWild_edges_mono {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ σ.edges) : e ∈ (σ.writeWild t).edges := by
  rw [writeWild_eq_ite]
  split
  · rw [addEdge_edges]; exact List.mem_cons_of_mem _ (writeWildPre_edges_mono he)
  · exact he

/-- An admitted grant materializes its edge. -/
theorem writeWild_grant_edge {σ : GraphState} {t : Tuple}
    (hadm : (σ.writeWildPre t).admitEdge (subjNode t.subject) (objNode t.object t.relation) = true) :
    (subjNode t.subject, objNode t.object t.relation) ∈ (σ.writeWild t).edges := by
  rw [writeWild_eq_ite, if_pos hadm, addEdge_edges]
  exact List.mem_cons_self

/-- An admitted, bridged-concrete endpoint gets its `w_all → c` bridge. -/
theorem ensureBridges_creates_bridge {σ : GraphState} {c : NodeKey}
    (hbc : σ.bridgedConcrete c = true)
    (hadm : (σ.addNode (wAllNode c.type c.pred)).admitEdge (wAllNode c.type c.pred) c = true) :
    (wAllNode c.type c.pred, c) ∈ (σ.ensureBridges c).edges := by
  unfold GraphState.ensureBridges
  rw [if_pos hbc, if_pos hadm, addEdge_edges]
  exact List.mem_cons_self

/-! ## The admitted bridge-materializing write-closure -/

/-- **`WildReachedAdmitted σ S T`** — the composed-system reachable-state closure at
    the object-wildcard fragment's scope. Each write's grant edge (`hadmGrant`) and
    its *subject-endpoint bridge* (`hadmSub`) passed cycle-rejection. Requiring
    `hadmSub` carves out the "no wildcard-own-shape cycle on subjects" fragment on
    which bridge-completeness holds; the object-endpoint bridge is handled internally
    by `ensureBridges` (both outcomes are valid states, so it is not required). -/
inductive WildReachedAdmitted : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : WildReachedAdmitted (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hprev : WildReachedAdmitted σ S T)
      (hadmSub : (((σ.addNode (subjNode t.subject)).addNode
          (objNode t.object t.relation)).addNode
          (wAllNode t.subject.type t.subject.predicate)).admitEdge
          (wAllNode t.subject.type t.subject.predicate) (subjNode t.subject) = true)
      (hadmGrant : (σ.writeWildPre t).admitEdge
          (subjNode t.subject) (objNode t.object t.relation) = true) :
      WildReachedAdmitted (σ.writeWild t) S (t :: T)

/-- Admitted writes are a special case of the bridge-materializing closure. -/
theorem wildReached_of_admitted {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) : WildReached σ S T := by
  induction h with
  | empty S => exact WildReached.empty S
  | step t _ _ _ ih => exact WildReached.step t ih

/-- The schema is fixed along the closure. -/
theorem wildReachedAdmitted_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) : σ.schema = S := by
  induction h with
  | empty S => rfl
  | step t _ _ _ ih => rw [writeWild_schema]; exact ih

/-! ## `hEC` — edge-completeness -/

/-- **Edge-completeness** (`hEC`): every stored grant's materialized edge is present
    (no write was rejected). Mirror of `admitted_edge_complete`. -/
theorem wildReachedAdmitted_edge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) :
    ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges := by
  induction h with
  | empty S => intro t ht; simp at ht
  | step t _ _ hadmGrant ih =>
    intro t' ht'
    rcases List.mem_cons.mp ht' with rfl | hmem
    · exact writeWild_grant_edge hadmGrant
    · exact writeWild_edges_mono (ih t' hmem)

/-! ## Lemma A — a reachable `w_all` node has a declared object-wildcard shape -/

/-- Admission-validity of object wildcards: a `T:*` tuple is on a declared
    object-wildcard shape (`setengine/engine.py::SetEngine._validate` step (1) and
    `index_v4/wildcard.py::WildcardIndex._resolve`'s object-wildcard gating; the shape
    must be declared for a
    wildcard grant to be written). -/
def ObjStarValid (S : Schema) (T : Store) : Prop :=
  ∀ t ∈ T, t.object.name = STAR → S.isObjectWildcard t.object.type t.relation = true

/-- Every path has a last edge (into its target). -/
theorem nreaches_last_edge {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ x, (x, v) ∈ edges := by
  induction h with
  | edge he => exact ⟨_, he⟩
  | head _ _ ih => exact ih

/-- **Lemma A.** A reachable `w_all(T,R)` node forces `S.isObjectWildcard T R`. Its
    only in-edges are grant edges from object-wildcard grants (bridge targets are
    plain), and `ObjStarValid` puts such a grant on a declared object-wildcard
    shape. -/
theorem wall_reach_isObjectWildcard {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReached σ S T) (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    {u : NodeKey} {T0 R0 : String}
    (hr : NReaches σ.edges u (wAllNode T0 R0)) :
    S.isObjectWildcard T0 R0 = true := by
  obtain ⟨x, hx⟩ := nreaches_last_edge hr
  rcases wildReached_grant_or_bridge h hOS x (wAllNode T0 R0) hx with
    ⟨t, htT, _, _, h2⟩ | ⟨_, hv, _⟩
  · -- grant edge: wAllNode T0 R0 = objNode t.object t.relation ⇒ object is `T0:*`
    have hostar : t.object.name = STAR := by
      by_contra hc
      rw [objNode_plain hc, wAllNode] at h2
      simp [NodeKey.mk.injEq] at h2
    have hobj : objNode t.object t.relation = wAllNode t.object.type t.relation := by
      unfold objNode wAllNode; rw [if_pos hostar]
    rw [hobj] at h2
    obtain ⟨hT, hR⟩ := wAllNode_inj h2
    have hvalid := hOV t htT hostar
    rw [hT, hR]; exact hvalid
  · -- bridge edge: target `wAllNode T0 R0` would be plain — impossible
    rw [wAllNode] at hv; simp at hv

/-! ## Bridge-completeness -/

/-- The subject-endpoint bridge of a new write is materialized when the subject
    shape is a declared object-wildcard: `writeWildPre` runs `ensureBridges` on the
    subject endpoint (bridgedConcrete, since the shape is object-wildcard), and both
    that bridge and the grant are admitted. -/
theorem writeWild_subjBridge {σ : GraphState} {t : Tuple}
    (hsub : t.subject.name ≠ STAR)
    (hshape : σ.schema.isObjectWildcard t.subject.type t.subject.predicate = true)
    (hadmSub : (((σ.addNode (subjNode t.subject)).addNode
        (objNode t.object t.relation)).addNode
        (wAllNode t.subject.type t.subject.predicate)).admitEdge
        (wAllNode t.subject.type t.subject.predicate) (subjNode t.subject) = true)
    (hadmGrant : (σ.writeWildPre t).admitEdge
        (subjNode t.subject) (objNode t.object t.relation) = true) :
    (wAllNode t.subject.type t.subject.predicate, subjNode t.subject) ∈ (σ.writeWild t).edges := by
  rw [writeWild_eq_ite, if_pos hadmGrant, addEdge_edges]
  apply List.mem_cons_of_mem
  unfold GraphState.writeWildPre
  apply ensureBridges_edges_mono
  have hbc : ((σ.addNode (subjNode t.subject)).addNode
      (objNode t.object t.relation)).bridgedConcrete (subjNode t.subject) = true := by
    unfold GraphState.bridgedConcrete
    rw [subjNode_plain hsub]
    simp only [addNode_schema, beq_self_eq_true, Bool.true_and, bne_iff_ne, ne_eq,
      Bool.and_eq_true]
    exact ⟨hsub, hshape⟩
  have hbridge := ensureBridges_creates_bridge hbc (by
    simpa only [subjNode_type, subjNode_pred] using hadmSub)
  simpa only [subjNode_type, subjNode_pred] using hbridge

/-- **Bridge-completeness.** Every stored grant whose *subject* shape is a declared
    object-wildcard has its materialized `w_all → concrete` bridge. New writes create
    the subject bridge (`writeWild_subjBridge`); old bridges persist
    (`writeWild_edges_mono`). This is the invariant that (with Lemma A) discharges
    `hbr`. -/
theorem wildReachedAdmitted_bridge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) :
    ∀ g ∈ T, g.subject.name ≠ STAR →
      S.isObjectWildcard g.subject.type g.subject.predicate = true →
      (wAllNode g.subject.type g.subject.predicate, subjNode g.subject) ∈ σ.edges := by
  induction h with
  | empty S => intro g hg; simp at hg
  | @step σ S T t hprev hadmSub hadmGrant ih =>
    intro g hg hgn hgshape
    rcases List.mem_cons.mp hg with rfl | hmem
    · -- new tuple: its subject bridge is created
      have hsch : σ.schema = S := wildReachedAdmitted_schema hprev
      exact writeWild_subjBridge hgn (by rw [hsch]; exact hgshape) hadmSub hadmGrant
    · -- old tuple: bridge persists
      exact writeWild_edges_mono (ih g hmem hgn hgshape)

/-! ## `hbr` discharged, and the completeness theorem -/

/-- **`hbr` discharged.** For any stored grant `g` (star-free subject) whose `w_all`
    node is reachable from the query subject, the bridge `w_all → subjNode g.subject`
    is present: reachability of the `w_all` node forces the object-wildcard shape
    (Lemma A), and bridge-completeness then supplies the bridge. -/
theorem wildReachedAdmitted_hbr {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    {q : Query} :
    ∀ g ∈ T, g.subject.name ≠ STAR →
      NReaches σ.edges (subjNode q.subject)
        (wAllNode g.subject.type g.subject.predicate) →
      (wAllNode g.subject.type g.subject.predicate, subjNode g.subject) ∈ σ.edges := by
  intro g hg hgn hreachW
  have hsch : σ.schema = S := wildReachedAdmitted_schema h
  have hshape : S.isObjectWildcard g.subject.type g.subject.predicate = true :=
    wall_reach_isObjectWildcard (wildReached_of_admitted h) hOS hOV hreachW
  exact wildReachedAdmitted_bridge_complete h g hg hgn hshape

/-- **Completeness of the W1b read (probe 1 ∨ probe 3), operationally closed.** On
    any state reached by admitted bridge-materializing writes of an object-star,
    admission-valid, object-wildcard-valid store, a `sem` membership at a concrete
    query object is reachability from `subjNode q.subject` to the concrete object
    node (probe 1) or its `w_all` node (probe 3). `reach_of_semAux_os`'s two
    operational hypotheses are now discharged: `hEC` by edge-completeness, `hbr` by
    Lemma A + bridge-completeness. -/
theorem graph_complete_objStar {S : Schema} {T : Store} {σ : GraphState} {q : Query}
    (hPD : PureDirect S) (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    (hqs : q.subject.name ≠ STAR) (hReach : WildReachedAdmitted σ S T)
    {ot on r : String} (hon : on ≠ STAR)
    (hsem : semAux S q.subject T q (fuelBound S T) ot on r = true) :
    NReaches σ.edges (subjNode q.subject) (objNode ⟨ot, on⟩ r)
    ∨ NReaches σ.edges (subjNode q.subject) (wAllNode ot r) :=
  reach_of_semAux_os hPD hOS hqs
    (wildReachedAdmitted_edge_complete hReach)
    (wildReachedAdmitted_hbr hReach hOS hOV)
    (fuelBound S T) ot on r hon hsem

/-! ## Soundness assembly — the fuel bound and the dead wildcard probes

The completeness half (above) needs no fuel bound. The soundness half does:
`semAux_of_grantReach` gives a `sem` membership at fuel = the `GrantReach` length
`m`, and the top-level theorem needs `m ≤ fuelBound`. The crude `m ≤ nodes.length`
is too weak — `writeWild` adds up to 4 nodes per tuple (2 endpoints + 2 `w_all`), so
`nodes.length ≤ 4|T|`, exceeding `fuelBound = |keys|(2|T|+4)` when `|keys| = 1`. The
tight bound is `m ≤ 2|T| + 1`: a `GrantReach` hop's *source* is always a `plain`
node (`grantReach_of_trail`'s count bound), and there are ≤ `2|T|` distinct plain
nodes (`w_all` nodes never count) — `wildReachedAdmitted_plainNodes`. -/

/-- Every non-empty path has a first edge (out of its source). -/
theorem nreaches_first_edge {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ w, (u, w) ∈ edges := by
  cases h with
  | edge he => exact ⟨_, he⟩
  | head he _ => exact ⟨_, he⟩

/-- An edge source in a `WildReached` state over an object-star store is never a
    `w_any` node: it is either a (star-free) `subjNode` grant source (`plain`) or a
    `w_all` bridge source. Kills read probes 2 and 4 (`w_any` subject). -/
theorem wildReached_edge_source_ne_wAny {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReached σ S T) (hOS : ObjStarStore T) :
    ∀ a b, (a, b) ∈ σ.edges → a.variant ≠ Variant.wAny := by
  intro a b hab
  rcases wildReached_grant_or_bridge h hOS a b hab with ⟨t, _, h1, hts, _⟩ | ⟨hbr, _, _⟩
  · rw [h1, subjNode_plain hts]; simp
  · rw [hbr, wAllNode]; simp

/-- A `GrantReach` chain witnesses at least one stored tuple. -/
theorem grantReach_mem {T : Store} {n : Nat} {u v : NodeKey}
    (h : GrantReach T n u v) : ∃ t, t ∈ T := by
  cases h with
  | base t ht _ => exact ⟨t, ht⟩
  | starBase t ht => exact ⟨t, ht⟩
  | hop t ht _ _ => exact ⟨t, ht⟩

/-! ## Plain-node accounting: at most `2|T|` plain nodes -/

/-- `ensureBridges` never changes the *plain*-node count: it only ever prepends a
    `w_all` node (or nothing), and `w_all` nodes are not plain. -/
theorem ensureBridges_plainCount (σ : GraphState) (c : NodeKey) :
    (σ.ensureBridges c).nodes.countP NodeKey.isPlain
      = σ.nodes.countP NodeKey.isPlain := by
  unfold GraphState.ensureBridges
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr]
    split
    · rw [addEdge_nodes, addNode_nodes, List.countP_cons, isPlain_wAllNode]; simp
    · rw [addNode_nodes, List.countP_cons, isPlain_wAllNode]; simp
  · rw [if_neg (by simpa using hbr)]

/-- A single `writeWild` adds at most **two** plain nodes (the two endpoints; the
    up-to-two `w_all` nodes are not plain, and the grant edge adds none). -/
theorem writeWild_plainCount_le (σ : GraphState) (t : Tuple) :
    (σ.writeWild t).nodes.countP NodeKey.isPlain
      ≤ σ.nodes.countP NodeKey.isPlain + 2 := by
  rw [writeWild_eq_ite]
  split
  · rw [addEdge_nodes]
    unfold GraphState.writeWildPre
    rw [ensureBridges_plainCount, ensureBridges_plainCount, addNode_nodes, addNode_nodes]
    simp only [List.countP_cons]
    split_ifs <;> omega
  · omega

/-- **At most `2|T|` plain nodes.** Each admitted write adds ≤ 2 plain nodes, so a
    `WildReachedAdmitted` state has `plain`-node count ≤ `2·|T|`. This is the tight
    bound the soundness fuel argument needs (the `w_all` nodes, up to `2|T|` of them,
    do not count — they are never `GrantReach` hop sources). -/
theorem wildReachedAdmitted_plainNodes {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReachedAdmitted σ S T) :
    σ.nodes.countP NodeKey.isPlain ≤ 2 * T.length := by
  induction h with
  | empty S => simp [emptyState]
  | @step σ S T t hprev hadmSub hadmGrant ih =>
    have hstep := writeWild_plainCount_le σ t
    simp only [List.length_cons]
    omega

/-! ## T2b on the W1b (object-wildcard) fragment, assembled -/

/-- **T2b, object-wildcard fragment (W1b), the full `check = sem`.** On any state
    reached by admitted bridge-materializing writes of an admission-valid,
    object-wildcard-valid, object-star store (subjects star-free, objects may be
    `T:*`), the graph read answers exactly `sem` for every star-free query. Probes 2,4
    are dead (`w_any` subject is never an edge source, `wildReached_edge_source_ne_wAny`);
    probe 1 (concrete object) and probe 3 (`w_all` object) are handled by the
    bridge-absorbing `GrantReach` soundness chain (forward, fuel `m ≤ 2|T|+1 ≤
    fuelBound`) and `graph_complete_objStar` (backward). This closes the W1b read
    correspondence end-to-end. -/
theorem graph_correct_objStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T)
    (hOS : ObjStarStore T) (hOV : ObjStarValid S T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : WildReachedAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hWR : WildReached σ S T := wildReached_of_admitted hReach
  have hInv : StructInv S σ := wildReached_structInv hWR
  have hcl := hInv.edgesClosed
  have hsch : σ.schema = S := wildReachedAdmitted_schema hReach
  -- the read routes to probeNonDerived (pure-direct = untainted)
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
    unfold GraphModel.check
    rw [hsch, isDerived_pureDirect hPD]; simp
  -- probes 2,4 are dead: a w_any node is never an edge source
  have hpAny : ∀ v, σ.reach (wAnyNode q.subject.shape) v = false := by
    intro v
    cases hcase : σ.reach (wAnyNode q.subject.shape) v with
    | false => rfl
    | true =>
      exfalso
      obtain ⟨w, hw⟩ := nreaches_first_edge (reach_sound hcase)
      exact wildReached_edge_source_ne_wAny hWR hOS _ _ hw rfl
  have hqob : (q.object.name != STAR) = true := by simp only [bne_iff_ne, ne_eq]; exact hqo
  have hprobe : GraphModel.probeNonDerived σ q =
      (σ.reach (subjNode q.subject) (objNode q.object q.relation)
       || σ.reach (subjNode q.subject) (wAllNode q.object.type q.relation)) := by
    unfold GraphModel.probeNonDerived
    simp [hpAny, hqob]
  -- forward: a probe-1 or probe-3 hit is a sem membership
  have hfwd : ∀ w, (w = objNode q.object q.relation ∨ w = wAllNode q.object.type q.relation) →
      NReaches σ.edges (subjNode q.subject) w → sem S T q = true := by
    intro w hw hnr
    obtain ⟨l, hl⟩ := trail_of_nreaches hnr
    obtain ⟨l', hl', hnd'⟩ := trail_compress_nodup l.length l (le_refl _) hl
    have hsub' : ∀ x ∈ l', x ∈ σ.nodes := trail_verts_mem hcl l' _ _ hl'
    obtain ⟨m, hgr, hmb⟩ :=
      grantReach_of_trail hWR hOS l'.length l' (le_refl _) q.subject w hqs hl'
    -- fuel bound: m ≤ plain vertices ≤ 2|T| + 1 ≤ fuelBound
    have hcount : (subjNode q.subject :: l').countP NodeKey.isPlain ≤ 2 * T.length + 1 := by
      rw [List.countP_cons]
      have h1 : l'.countP NodeKey.isPlain ≤ σ.nodes.countP NodeKey.isPlain :=
        nodup_countP_le hnd' hsub'
      have h2 : σ.nodes.countP NodeKey.isPlain ≤ 2 * T.length :=
        wildReachedAdmitted_plainNodes hReach
      split <;> omega
    obtain ⟨t0, ht0⟩ := grantReach_mem hgr
    obtain ⟨rs0, hlk0, -⟩ := hSV t0 ht0
    have hkeys := lookup_keys_nonempty hlk0
    have hfb : m ≤ fuelBound S T := by
      unfold fuelBound
      have hb : T.length * 2 + 4 ≤ S.keys.length * (T.length * 2 + 4) := by
        conv_lhs => rw [← Nat.one_mul (T.length * 2 + 4)]
        exact Nat.mul_le_mul_right _ hkeys
      omega
    have hmatch : matchesObj w q.object.type q.object.name q.relation := by
      rcases hw with h | h
      · exact Or.inl (by rw [h])
      · exact Or.inr h
    have hsem_m := semAux_of_grantReach (q := q) hWF hPD hSV hOS hgr hqs rfl hqo hmatch
    unfold sem
    exact semAux_mono S (pureDirect_noExclAll hPD) q.subject T q hfb _ _ _ hsem_m
  -- backward: a sem membership hits probe 1 or probe 3 (graph_complete_objStar)
  have hbwd : sem S T q = true →
      NReaches σ.edges (subjNode q.subject) (objNode q.object q.relation)
      ∨ NReaches σ.edges (subjNode q.subject) (wAllNode q.object.type q.relation) := by
    intro hsem
    have hsem' : semAux S q.subject T q (fuelBound S T)
        q.object.type q.object.name q.relation = true := hsem
    rcases graph_complete_objStar hPD hOS hOV hqs hReach hqo hsem' with h | h
    · exact Or.inl h
    · exact Or.inr h
  rw [hroute, hprobe]
  cases hsemc : sem S T q with
  | true =>
    rcases hbwd hsemc with h | h
    · rw [reach_complete hcl h, Bool.true_or]
    · rw [reach_complete hcl h, Bool.or_true]
  | false =>
    have hn1 : σ.reach (subjNode q.subject) (objNode q.object q.relation) = false := by
      cases hc : σ.reach (subjNode q.subject) (objNode q.object q.relation) with
      | false => rfl
      | true =>
        have := hfwd _ (Or.inl rfl) (reach_sound hc)
        rw [hsemc] at this; exact absurd this (by simp)
    have hn2 : σ.reach (subjNode q.subject) (wAllNode q.object.type q.relation) = false := by
      cases hc : σ.reach (subjNode q.subject) (wAllNode q.object.type q.relation) with
      | false => rfl
      | true =>
        have := hfwd _ (Or.inr rfl) (reach_sound hc)
        rw [hsemc] at this; exact absurd this (by simp)
    rw [hn1, hn2]; rfl

end Zanzibar
