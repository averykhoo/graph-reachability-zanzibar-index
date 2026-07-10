import ZanzibarProofs.GraphIndex.ObjStarWrite
import ZanzibarProofs.GraphIndex.BareStarCorrect

/-!
# T2b, stage W1b — object wildcards `[T:*]`, the read-correspondence SEMANTIC CORES

`SEMANTICS.md` §7.5; ROADMAP "The staged T2 plan", sub-stage **W1b**;
`wildcard-materialization-spec.md §3.4` (the `w_all → concrete` bridge composition).

This file proves **both semantic halves** of the W1b read correspondence on the
object-wildcard fragment (subjects star-free, objects may be `T:*`). Unlike W1a
(bare star *subjects*, zero bridges), W1b materializes `w_all → concrete` **bridge**
edges (`ObjStarWrite.lean`), so a graph path interleaves *grant* hops and *bridge*
hops. The absorbing idea (both directions): a `grant-into-w_all` + `bridge-out` pair
is a single generalized grant against a **concrete** object, keyed through
`matchingObjects` (a `T:*` grant is in `grantsOf` for every concrete object of type
`T`, `Semantics.matchingObjects`).

**Soundness** (graph path ⇒ no more than `sem`):

* `GrantReach` — a bridge-absorbing membership chain: each hop is a stored grant
  whose object matches a *concrete* object name via `matchingObjects` (so a
  wildcard grant + its bridge is one hop), plus a terminal `starBase` hop landing
  on the `w_all` node itself (the read's probe-3 endpoint).
* `semAux_of_grantReach` — a `GrantReach` is a `sem` membership (the bridge-aware
  analog of `semAux_of_chainN`), via the userset-lifting lemma.
* `grantReach_of_trail` — every graph trail from a star-free subject node is a
  `GrantReach`, peeling grant (1 edge) or grant+bridge (2 edges) at each step,
  classified by the edge characterization `wildReached_grant_or_bridge`.

**Completeness** (`sem` ⇒ probe 1 ∨ probe 3):

* `reach_of_semAux_os` — a `sem` membership is reachability to the concrete object
  node (probe 1) or its `w_all` node (probe 3); a `T:*` direct match hits probe 3,
  a flow-through threads a bridge hop when the recursion reached the userset via
  its own `w_all` node.

Both cores are stated over the *operational facts they consume* — soundness over
the edge characterization (a derived property of `WildReached`); completeness over
edge-completeness `hEC` + the bridge hypothesis `hbr`. The **admitted,
bridge-complete write-closure** that discharges completeness's `hEC`/`hbr`, and the
**fuel-bounded assembly** of soundness's chain length (`m ≤ fuelBound`), are the
deferred next increments; neither core needs bridge-completeness threaded through
its own induction.
-/

namespace Zanzibar

/-! ## W1b fragment predicate -/

/-- **W1b store predicate.** Subjects are star-free (no subject wildcards — that is
    W1a/W1c); objects may be `T:*` (object wildcards). Strictly weaker than
    `StarFreeStore` on the subject side, strictly wider on the object side. -/
def ObjStarStore (T : Store) : Prop := ∀ t ∈ T, t.subject.name ≠ STAR

/-! ## `matchingObjects` and `wAllNode` helpers -/

/-- A concrete object name matches a `'*'` (object-wildcard) grant object:
    `STAR ∈ matchingObjects on` for concrete `on` (`matchingObjects on = [on, *]`). -/
theorem matchingObjects_star_mem {on : String} (h : on ≠ STAR) :
    (matchingObjects on).contains STAR = true := by
  unfold matchingObjects
  rw [if_neg h]
  simp

/-- `wAllNode` is injective in its `(type, relation)` pair. -/
theorem wAllNode_inj {t r t' r' : String} (h : wAllNode t r = wAllNode t' r') :
    t = t' ∧ r = r' := by
  unfold wAllNode at h
  simp only [NodeKey.mk.injEq] at h
  exact ⟨h.1, h.2.2.1⟩

/-- A `w_all` node's fields expose its `(type, relation)`; its variant is `wAll`. -/
@[simp] theorem wAllNode_type (t r : String) : (wAllNode t r).type = t := rfl
@[simp] theorem wAllNode_pred (t r : String) : (wAllNode t r).pred = r := rfl
@[simp] theorem wAllNode_variant (t r : String) : (wAllNode t r).variant = Variant.wAll := rfl

/-- A star-free subject's `subjNode` is a `plain` node. -/
theorem isPlain_subjNode {s : SubjectRef} (h : s.name ≠ STAR) :
    NodeKey.isPlain (subjNode s) = true := by
  unfold NodeKey.isPlain subjNode; rw [if_neg h]; rfl

/-- A `w_all` node is never `plain`. -/
theorem isPlain_wAllNode (t r : String) : NodeKey.isPlain (wAllNode t r) = false := by
  unfold NodeKey.isPlain wAllNode; rfl

/-! ## The bridged-concrete flag decomposed -/

/-- `bridgedConcrete` decomposed: a bridged-concrete node is plain, star-free, and
    of a declared object-wildcard shape. -/
theorem bridgedConcrete_elim {σ : GraphState} {c : NodeKey}
    (h : σ.bridgedConcrete c = true) :
    c.variant = Variant.plain ∧ c.name ≠ STAR ∧
      σ.schema.isObjectWildcard c.type c.pred = true := by
  unfold GraphState.bridgedConcrete at h
  simp only [Bool.and_eq_true, beq_iff_eq, bne_iff_ne, ne_eq] at h
  exact ⟨h.1.1, h.1.2, h.2⟩

/-! ## Edge characterization for the bridge-materializing write

Every edge of a `WildReached` state is either a **grant** edge (a stored tuple's
`subjNode t.subject → objNode t.object t.relation`, subject star-free) or a
**bridge** edge (`wAllNode c.type c.pred → c`, `c` a plain concrete node). This is
the structural fact soundness classifies each trail hop against. -/

/-- `ensureBridges`'s edge effect: an edge is either an old edge or the single
    bridge `wAllNode c.type c.pred → c` (with `c` bridged-concrete). -/
theorem ensureBridges_edges_mem {σ : GraphState} {c : NodeKey} {e : NodeKey × NodeKey}
    (he : e ∈ (σ.ensureBridges c).edges) :
    e ∈ σ.edges ∨ (e = (wAllNode c.type c.pred, c) ∧ σ.bridgedConcrete c = true) := by
  unfold GraphState.ensureBridges at he
  by_cases hbr : σ.bridgedConcrete c = true
  · rw [if_pos hbr] at he
    split at he
    · rw [addEdge_edges, addNode_edges] at he
      rcases List.mem_cons.mp he with heq | hmem
      · exact Or.inr ⟨heq, hbr⟩
      · exact Or.inl hmem
    · rw [addNode_edges] at he; exact Or.inl he
  · rw [if_neg (by simpa using hbr)] at he; exact Or.inl he

/-- `writeWild`'s edge effect: an edge of `σ.writeWild t` is either an old edge, the
    grant edge `(subjNode t.subject, objNode t.object t.relation)`, or a bridge for
    one of the two endpoints. -/
theorem writeWild_edges_mem {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ (σ.writeWild t).edges) :
    e ∈ σ.edges
    ∨ e = (subjNode t.subject, objNode t.object t.relation)
    ∨ (∃ c, e = (wAllNode c.type c.pred, c) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR) := by
  unfold GraphState.writeWild at he
  dsimp only at he
  set a := subjNode t.subject with ha
  set b := objNode t.object t.relation with hb
  split at he
  · -- accepted grant: (a,b) :: (bridges) :: (endpoint nodes, no edges)
    rw [addEdge_edges] at he
    rcases List.mem_cons.mp he with heq | hmem
    · exact Or.inr (Or.inl heq)
    · -- e is in the doubly-bridged state's edges
      rcases ensureBridges_edges_mem hmem with hb2 | ⟨hbridge, hbc⟩
      · rcases ensureBridges_edges_mem hb2 with ha2 | ⟨hbridge, hbc⟩
        · rw [addNode_edges, addNode_edges] at ha2; exact Or.inl ha2
        · obtain ⟨hv, hn, _⟩ := bridgedConcrete_elim hbc
          exact Or.inr (Or.inr ⟨_, hbridge, hv, hn⟩)
      · obtain ⟨hv, hn, _⟩ := bridgedConcrete_elim hbc
        exact Or.inr (Or.inr ⟨_, hbridge, hv, hn⟩)
  · exact Or.inl he

/-- **Grant-or-bridge edge characterization.** Every edge of a `WildReached` state
    over an object-star store is either a stored grant (subject star-free) or a
    `w_all → concrete` bridge. By induction over the bridge-materializing write
    path. -/
theorem wildReached_grant_or_bridge {σ : GraphState} {S : Schema} {T : Store}
    (h : WildReached σ S T) (hOS : ObjStarStore T) :
    ∀ a b, (a, b) ∈ σ.edges →
      (∃ t ∈ T, a = subjNode t.subject ∧ t.subject.name ≠ STAR ∧
        b = objNode t.object t.relation)
      ∨ (a = wAllNode b.type b.pred ∧ b.variant = Variant.plain ∧ b.name ≠ STAR) := by
  induction h with
  | empty S => intro a b hab; simp [emptyState] at hab
  | @step σ S T t hprev ih =>
    intro a b hab
    have hOS' : ObjStarStore T := fun t' ht' => hOS t' (List.mem_cons_of_mem _ ht')
    rcases writeWild_edges_mem hab with hold | hgrant | ⟨c, hc, hcv, hcn⟩
    · rcases ih hOS' a b hold with ⟨t', ht', h1, h2, h3⟩ | hbridge
      · exact Or.inl ⟨t', List.mem_cons_of_mem _ ht', h1, h2, h3⟩
      · exact Or.inr hbridge
    · obtain ⟨rfl, rfl⟩ := Prod.ext_iff.mp hgrant
      exact Or.inl ⟨t, List.mem_cons_self, rfl, hOS t List.mem_cons_self, rfl⟩
    · simp only [Prod.mk.injEq] at hc
      obtain ⟨ha, hb⟩ := hc
      subst hb
      exact Or.inr ⟨ha, hcv, hcn⟩

/-! ## Object-star leaf lemmas

The subject-side leaf lemmas (`mog_elim`, `directLeaf_elim`, the lift) need only
that grant *subjects* are star-free — which `ObjStarStore` supplies. Object
wildcards live entirely on the object side and do not touch these. -/

/-- `mog_elim` over an object-star store (subjects star-free ⇒ no `instances`). -/
theorem mog_elim_os {rec : Rec} {T : Store} {q : Query} {rs : List Restriction}
    {ot on rel : String} (hOS : ObjStarStore T)
    (h : memberOfGranted rec T q (grantsOf T rs ot on rel) = true) :
    ∃ g ∈ grantsOf T rs ot on rel, g.subject.predicate ≠ BARE ∧
      g.subject.name ≠ STAR ∧
      rec g.subject.type g.subject.name g.subject.predicate = true := by
  unfold memberOfGranted at h
  obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
  have hstar : g.subject.name ≠ STAR := hOS g (grantsOf_elim hg).1
  by_cases hpb : (g.subject.predicate == BARE) = true
  · rw [if_pos hpb] at hgt; exact absurd hgt (by simp)
  · rw [if_neg hpb, if_pos (by simpa using hstar)] at hgt
    exact ⟨g, hg, by simpa using hpb, hstar, hgt⟩

/-- `directLeaf_elim` over an object-star store (subjects star-free). -/
theorem directLeaf_elim_os {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hOS : ObjStarStore T)
    (hs : s.name ≠ STAR)
    (h : directLeaf rec s T q rs ot on rel = true) :
    (∃ g ∈ grantsOf T rs ot on rel, g.subject = s) ∨
      memberOfGranted rec T q (grantsOf T rs ot on rel) = true := by
  unfold directLeaf at h
  rw [if_neg (by simpa using hs)] at h
  by_cases hp : (s.predicate == BARE) = true
  · rw [if_pos hp, Bool.or_eq_true] at h
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      have hgstar : g.subject.name ≠ STAR := hOS g (grantsOf_elim hg).1
      have hsp : s.predicate = BARE := by simpa using hp
      refine Or.inl ⟨g, hg, ?_⟩
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq,
        beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩ | ⟨⟨h1, _⟩, _⟩
      · simp_all
      · exact absurd h1 hgstar
    · exact Or.inr h
  · rw [if_neg hp, Bool.or_eq_true] at h
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      have hgstar : g.subject.name ≠ STAR := hOS g (grantsOf_elim hg).1
      refine Or.inl ⟨g, hg, ?_⟩
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq,
        beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩ | ⟨⟨⟨h1, _⟩, _⟩, _⟩
      · simp_all
      · exact absurd h1 hgstar
    · exact Or.inr h

/-- **Userset lifting over an object-star store** (subjects star-free). Identical
    content to `semAux_lift`; the object-wildcard grants live on the object side and
    do not perturb the subject-flow-through absorption. -/
theorem semAux_lift_os {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hPD : PureDirect S) (hOS : ObjStarStore T)
    (hs'n : s'.name ≠ STAR) (hs'p : s'.predicate ≠ BARE)
    {f₀ : Nat} (hmem : semAux S s T q f₀ s'.type s'.name s'.predicate = true) :
    ∀ (f : Nat) (ot on r : String),
      semAux S s' T q f ot on r = true →
      semAux S s T q (f + f₀) ot on r = true := by
  intro f
  induction f with
  | zero => intro ot on r h; simp [semAux] at h
  | succ f ih =>
    intro ot on r h
    have hgoalfuel : f + 1 + f₀ = (f + f₀) + 1 := by omega
    rw [hgoalfuel, semAux, step]
    rw [semAux, step] at h
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      obtain ⟨rs, rfl⟩ := pureDirect_lookup hPD hlk
      have h' : directLeaf (semAux S s' T q f) s' T q rs ot on r = true := h
      show directLeaf (semAux S s T q (f + f₀)) s T q rs ot on r = true
      rcases directLeaf_elim_os hOS hs'n h' with ⟨g, hg, hgs⟩ | hmog
      · apply directLeaf_of_mog
        refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
        rw [hgs]
        exact semAux_mono S (pureDirect_noExclAll hPD) s T q
          (Nat.le_add_left f₀ f) _ _ _ hmem
      · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_os hOS hmog
        exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))

/-- **One generalized grant is a fuel-1 `sem` membership.** A grant `t` whose object
    matches the concrete object name `on` (`on ∈ matchingObjects`, covering both a
    concrete grant and a `T:*` wildcard grant) is a fuel-1 membership of the
    *concrete* object node for the grant's (star-free) subject. This is the hop that
    absorbs a `grant-into-w_all` + `bridge-out`. -/
theorem semAux_one_of_grant {S : Schema} {T : Store} {q : Query} {t : Tuple}
    (hSV : StoreValid S T) (hOS : ObjStarStore T) (ht : t ∈ T)
    {on : String} (hmatch : (matchingObjects on).contains t.object.name = true) :
    semAux S t.subject T q 1 t.object.type on t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  show directLeaf (semAux S t.subject T q 0) t.subject T q rs
    t.object.type on t.relation = true
  refine directLeaf_grant_self ?_ rfl (hOS t ht)
  exact grantsOf_intro ht rfl rfl hmatch hrm

/-! ## `GrantReach` — the bridge-absorbing membership chain -/

/-- **A bridge-absorbing generalized grant chain.** `GrantReach T n u v`: the plain
    node `u` reaches `v` via `n` generalized grant hops, where each hop is a stored
    grant whose object matches a *concrete* object name through `matchingObjects`
    (so a wildcard grant together with its materialized `w_all → concrete` bridge is
    a single hop, `hop`/`base`), plus a terminal `starBase` hop landing directly on
    the grant's own `w_all` node (the read's probe-3 endpoint). Every intermediate
    node is concrete (`subjNode` of a concrete userset); only the final target may
    be a `w_all` node. -/
inductive GrantReach (T : Store) : Nat → NodeKey → NodeKey → Prop where
  | base (t : Tuple) (ht : t ∈ T) {on : String} (hon : on ≠ STAR)
      (hmatch : (matchingObjects on).contains t.object.name = true) :
      GrantReach T 1 (subjNode t.subject) (objNode ⟨t.object.type, on⟩ t.relation)
  | starBase (t : Tuple) (ht : t ∈ T) (hstar : t.object.name = STAR) :
      GrantReach T 1 (subjNode t.subject) (wAllNode t.object.type t.relation)
  | hop (t : Tuple) (ht : t ∈ T) {on : String} (hon : on ≠ STAR)
      (hmatch : (matchingObjects on).contains t.object.name = true)
      {n : Nat} {v : NodeKey}
      (rest : GrantReach T n (subjNode ⟨t.object.type, on, t.relation⟩) v) :
      GrantReach T (n + 1) (subjNode t.subject) v

/-- `v` matches the concrete query object `(ot, on, r)`: either it is the concrete
    object node, or the `w_all` node covering it. -/
def matchesObj (v : NodeKey) (ot on r : String) : Prop :=
  v = objNode ⟨ot, on⟩ r ∨ v = wAllNode ot r

/-! ## `GrantReach ⇒ sem` — soundness's semantic half -/

/-- **`GrantReach` is a `sem` membership.** A generalized grant chain of length `n`
    from a star-free subject node to a node matching the concrete query object is a
    `sem` membership at fuel `n`. Base hops are self-grants (`semAux_one_of_grant`,
    keyed through `matchingObjects`); each `hop` lifts through its concrete userset
    (`semAux_lift_os`, `f₀ = 1`). This is the bridge-aware analog of
    `semAux_of_chainN`. -/
theorem semAux_of_grantReach {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hOS : ObjStarStore T) :
    ∀ {n : Nat} {u v : NodeKey}, GrantReach T n u v →
      ∀ {s : SubjectRef}, s.name ≠ STAR → subjNode s = u →
      ∀ {ot on r : String}, on ≠ STAR → matchesObj v ot on r →
      semAux S s T q n ot on r = true := by
  intro n u v hgr
  induction hgr with
  | base t ht hon hmatch =>
    intro s hsn hsu ot onq r hqon hmv
    have hts : s = t.subject := subjNode_inj hsn (hOS t ht) hsu
    subst hts
    -- the target is the concrete node ⟨t.object.type, on⟩ t.relation (plain);
    -- so `matchesObj` picks the concrete disjunct.
    rcases hmv with hEq | hStar
    · -- concrete match: identify (ot, onq, r) with (t.object.type, on, t.relation)
      rw [objNode_plain hon, objNode_plain hqon] at hEq
      simp only [NodeKey.mk.injEq] at hEq
      obtain ⟨hot, hon', hr, -⟩ := hEq
      subst hot; subst hon'; subst hr
      exact semAux_one_of_grant hSV hOS ht hmatch
    · -- concrete node ≠ w_all node
      rw [objNode_plain hon, wAllNode] at hStar
      simp [NodeKey.mk.injEq] at hStar
  | starBase t ht hstar =>
    intro s hsn hsu ot onq r hqon hmv
    have hts : s = t.subject := subjNode_inj hsn (hOS t ht) hsu
    subst hts
    rcases hmv with hEq | hStar
    · -- w_all node ≠ concrete node
      rw [objNode_plain hqon, wAllNode] at hEq
      simp [NodeKey.mk.injEq] at hEq
    · obtain ⟨hot, hr⟩ := wAllNode_inj hStar.symm
      subst hot; subst hr
      -- wildcard grant matches every concrete object of its type
      exact semAux_one_of_grant hSV hOS ht (by rw [hstar]; exact matchingObjects_star_mem hqon)
  | @hop t ht on hon hmatch n v rest ih =>
    intro s hsn hsu ot onq r hqon hmv
    have hts : s = t.subject := subjNode_inj hsn (hOS t ht) hsu
    subst hts
    set s' : SubjectRef := ⟨t.object.type, on, t.relation⟩ with hs'def
    have hs'n : s'.name ≠ STAR := hon
    have hs'p : s'.predicate ≠ BARE := by
      obtain ⟨rs, hlk, _⟩ := hSV t ht
      exact lookup_rel_ne_bare hWF hlk
    have hmem1 : semAux S t.subject T q 1 s'.type s'.name s'.predicate = true :=
      semAux_one_of_grant hSV hOS ht hmatch
    have htail : semAux S s' T q n ot onq r = true := ih hs'n rfl hqon hmv
    exact semAux_lift_os hPD hOS hs'n hs'p hmem1 n ot onq r htail

/-! ## `trail ⇒ GrantReach` — soundness's reachability half -/

/-- **Every graph trail from a star-free subject node is a `GrantReach`, with the
    chain length bounded by the count of `plain` trail vertices.** Strong induction
    on the trail length: a first edge out of a plain node is a grant
    (`wildReached_grant_or_bridge`; bridges have `w_all` sources). If it lands on a
    concrete node, recurse (`hop`); if on a `w_all` node, the next edge is its
    bridge, and grant+bridge is absorbed into one hop against the bridged concrete
    (`base`/`hop`). A path terminating on a `w_all` node is a `starBase`. The count
    bound holds because every hop's *source* is a `plain` node (the query subject or
    a concrete userset) — `w_all` nodes are consumed mid-hop by a bridge, never as a
    source — so each hop accounts for one distinct plain vertex of the trail. This is
    what fits the chain length under `fuelBound` (`w_all` nodes, up to `2|T|` of them,
    would otherwise inflate a crude `nodes.length` bound past the bound). -/
theorem grantReach_of_trail {S : Schema} {T : Store} {σ : GraphState}
    (h : WildReached σ S T) (hOS : ObjStarStore T) :
    ∀ (n : Nat) (l : List NodeKey), l.length ≤ n →
      ∀ (s : SubjectRef) (v : NodeKey), s.name ≠ STAR →
        Trail σ.edges (subjNode s) v l →
        ∃ m, GrantReach T m (subjNode s) v ∧
          m ≤ (subjNode s :: l).countP NodeKey.isPlain := by
  have hchar := wildReached_grant_or_bridge h hOS
  intro n
  induction n with
  | zero =>
    intro l hlen s v hs ht
    -- l = [] : a single grant edge
    cases l with
    | cons x xs => simp only [List.length_cons] at hlen; omega
    | nil =>
      have hedge : (subjNode s, v) ∈ σ.edges := ht
      have hcnt : 1 ≤ (subjNode s :: ([] : List NodeKey)).countP NodeKey.isPlain := by
        rw [List.countP_cons]; simp [isPlain_subjNode hs]
      rcases hchar _ _ hedge with ⟨t, htT, h1, hts, h2⟩ | ⟨hbr, _, _⟩
      · -- grant edge from subjNode s
        have hs_eq : s = t.subject := subjNode_inj hs hts h1
        subst hs_eq
        subst h2
        by_cases hobj : t.object.name = STAR
        · refine ⟨1, ?_, hcnt⟩
          have : objNode t.object t.relation = wAllNode t.object.type t.relation := by
            unfold objNode wAllNode; rw [if_pos hobj]
          rw [this]; exact GrantReach.starBase t htT hobj
        · refine ⟨1, ?_, hcnt⟩
          have : objNode t.object t.relation =
              objNode (⟨t.object.type, t.object.name⟩ : ObjectRef) t.relation := rfl
          rw [this]
          exact GrantReach.base t htT hobj (matchingObjects_self _ hobj)
      · -- bridge edge: source is w_all, but subjNode s is plain — impossible
        rw [subjNode_plain hs] at hbr
        rw [wAllNode] at hbr
        simp [NodeKey.mk.injEq] at hbr
  | succ n ih =>
    intro l hlen s v hs ht
    cases l with
    | nil =>
      -- same as the zero base case (single edge)
      have hedge : (subjNode s, v) ∈ σ.edges := ht
      have hcnt : 1 ≤ (subjNode s :: ([] : List NodeKey)).countP NodeKey.isPlain := by
        rw [List.countP_cons]; simp [isPlain_subjNode hs]
      rcases hchar _ _ hedge with ⟨t, htT, h1, hts, h2⟩ | ⟨hbr, _, _⟩
      · have hs_eq : s = t.subject := subjNode_inj hs hts h1
        subst hs_eq; subst h2
        by_cases hobj : t.object.name = STAR
        · refine ⟨1, ?_, hcnt⟩
          have : objNode t.object t.relation = wAllNode t.object.type t.relation := by
            unfold objNode wAllNode; rw [if_pos hobj]
          rw [this]; exact GrantReach.starBase t htT hobj
        · refine ⟨1, ?_, hcnt⟩
          exact GrantReach.base t htT hobj (matchingObjects_self _ hobj)
      · rw [subjNode_plain hs, wAllNode] at hbr; simp [NodeKey.mk.injEq] at hbr
    | cons x xs =>
      obtain ⟨hfst, htail⟩ := ht
      -- the source subjNode s contributes one plain vertex to the head count
      have hheadcnt : ∀ (ys : List NodeKey),
          (subjNode s :: ys).countP NodeKey.isPlain = ys.countP NodeKey.isPlain + 1 := by
        intro ys; rw [List.countP_cons]; simp [isPlain_subjNode hs]
      rcases hchar _ _ hfst with ⟨t, htT, h1, hts, h2⟩ | ⟨hbr, _, _⟩
      · -- first hop is a grant from subjNode s to x = objNode t.object t.relation
        have hs_eq : s = t.subject := subjNode_inj hs hts h1
        subst hs_eq
        by_cases hobj : t.object.name = STAR
        · -- x is the w_all node; the next edge (from a w_all node) is its bridge
          have hxwall : x = wAllNode t.object.type t.relation := by
            rw [h2]; unfold objNode wAllNode; rw [if_pos hobj]
          -- peel the bridge out of x
          cases xs with
          | nil =>
            -- Trail σ.edges x v [] : a single bridge edge x → v
            have hbedge : (x, v) ∈ σ.edges := htail
            rcases hchar _ _ hbedge with ⟨t', ht'T, hb1, hb2, hb3⟩ | ⟨hvbr, hvv, hvn⟩
            · -- a grant from x, but x is a w_all node ⇒ impossible (grant sources plain)
              rw [hxwall, subjNode_plain (hOS t' ht'T)] at hb1
              rw [wAllNode] at hb1; simp [NodeKey.mk.injEq] at hb1
            · -- bridge x → v with x = wAllNode v.type v.pred, v concrete
              rw [hxwall] at hvbr
              obtain ⟨htype, hpred⟩ := wAllNode_inj hvbr.symm
              -- v = ⟨t.object.type, v.name, t.relation, plain⟩ = objNode ⟨.,v.name⟩ t.relation
              refine ⟨1, ?_, ?_⟩
              · have hvobj : v = objNode (⟨t.object.type, v.name⟩ : ObjectRef) t.relation := by
                  rw [objNode_plain hvn]
                  have : v = ⟨v.type, v.name, v.pred, v.variant⟩ := rfl
                  rw [this, htype, hpred, hvv]
                rw [hvobj]
                exact GrantReach.base t htT hvn
                  (by rw [hobj]; exact matchingObjects_star_mem hvn)
              · -- count: [subjNode s, x] has ≥ 1 plain vertex (subjNode s itself)
                rw [hheadcnt]; omega
          | cons y ys =>
            obtain ⟨hbfst, hbtail⟩ := htail
            -- first tail edge x → y is the bridge (x is w_all)
            rcases hchar _ _ hbfst with ⟨t', ht'T, hb1, hb2, hb3⟩ | ⟨hvbr, hvv, hvn⟩
            · rw [hxwall, subjNode_plain (hOS t' ht'T), wAllNode] at hb1
              simp [NodeKey.mk.injEq] at hb1
            · -- bridge x → y, y concrete of shape (t.object.type, t.relation)
              rw [hxwall] at hvbr
              obtain ⟨htype, hpred⟩ := wAllNode_inj hvbr.symm
              have hyeq : y = subjNode ⟨t.object.type, y.name, t.relation⟩ := by
                rw [subjNode_plain hvn]
                have : y = ⟨y.type, y.name, y.pred, y.variant⟩ := rfl
                rw [this, htype, hpred, hvv]
              have hyn : y.name ≠ STAR := hvn
              have hlen' : ys.length ≤ n := by
                simp only [List.length_cons] at hlen; omega
              rw [hyeq] at hbtail
              obtain ⟨m, hm, hmb⟩ := ih ys hlen' _ v hyn hbtail
              refine ⟨m + 1, ?_, ?_⟩
              · exact GrantReach.hop t htT hvn
                  (by rw [hobj]; exact matchingObjects_star_mem hvn) hm
              · -- count: subjNode s (plain, +1), x = w_all (+0), then y :: ys as in `hmb`
                have hxnp : NodeKey.isPlain x = false := by rw [hxwall]; exact isPlain_wAllNode _ _
                have hx0 : (x :: y :: ys).countP NodeKey.isPlain
                    = (y :: ys).countP NodeKey.isPlain := by
                  rw [List.countP_cons, hxnp]; simp
                rw [hheadcnt, hx0]
                rw [← hyeq] at hmb
                omega
        · -- x is a concrete node = subjNode of the userset ⟨t.object.type, t.object.name, t.relation⟩
          have hxsubj : x = subjNode ⟨t.object.type, t.object.name, t.relation⟩ := by
            rw [h2]; exact objNode_eq_subjNode hobj
          have hlen' : xs.length ≤ n := by
            simp only [List.length_cons] at hlen; omega
          rw [hxsubj] at htail
          obtain ⟨m, hm, hmb⟩ := ih xs hlen' _ v hobj htail
          refine ⟨m + 1, ?_, ?_⟩
          · exact GrantReach.hop t htT hobj (matchingObjects_self _ hobj) hm
          · -- count: subjNode s (plain, +1), then x = subjNode userset :: xs as in `hmb`
            rw [hheadcnt]
            rw [← hxsubj] at hmb
            omega
      · rw [subjNode_plain hs, wAllNode] at hbr; simp [NodeKey.mk.injEq] at hbr

/-! ## `sem ⇒ probe 1 ∨ probe 3` — the completeness semantic core

The completeness half of the W1b read correspondence: a `sem` membership at a
concrete query object is reachability from `subjNode s` to *either* the concrete
object node (probe 1) *or* the `w_all` node covering it (probe 3). Mirrors W1a's
`reach_of_semAux_bs`, but the disjunction is on the **object** side (probe 3, a
wildcard grant lands on the `w_all` node) rather than the subject side, and the
flow-through recursion may reach a userset via its **own** `w_all` node — which
must be threaded through a `w_all → concrete` **bridge** hop to continue.

Like the soundness core, this lemma is stated over the two operational facts it
consumes — edge-completeness (`hEC`, every stored grant's edge is present) and a
bridge hypothesis (`hbr`, a grant subject reachable via its `w_all` node has its
materialized bridge) — deferring the write-closure that discharges them (the
admitted, bridge-complete closure) to the next increment, exactly as
`grantReach_of_trail` defers to the edge characterization it consumes. -/

/-- **Completeness core (W1b).** For a star-free query subject `s` and concrete
    query object name, a `sem` membership is reachability from `subjNode s` to the
    concrete object node (probe 1) **or** its `w_all` node (probe 3). A direct
    match on a concrete grant hits probe 1, on a `T:*` grant hits probe 3; a
    flow-through prepends the recursion's path — through a bridge hop when the
    recursion reached the userset via its own `w_all` node. -/
theorem reach_of_semAux_os {S : Schema} {T : Store} {q : Query} {edges : List (NodeKey × NodeKey)}
    (hPD : PureDirect S) (hOS : ObjStarStore T) (hqs : q.subject.name ≠ STAR)
    (hEC : ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ edges)
    (hbr : ∀ g ∈ T, g.subject.name ≠ STAR →
      NReaches edges (subjNode q.subject)
        (wAllNode g.subject.type g.subject.predicate) →
      (wAllNode g.subject.type g.subject.predicate, subjNode g.subject) ∈ edges) :
    ∀ (f : Nat) (ot on r : String), on ≠ STAR →
      semAux S q.subject T q f ot on r = true →
      NReaches edges (subjNode q.subject) (objNode ⟨ot, on⟩ r)
      ∨ NReaches edges (subjNode q.subject) (wAllNode ot r) := by
  set s := q.subject with hs_def
  have hsn : s.name ≠ STAR := hqs
  intro f
  induction f with
  | zero => intro ot on r hon h; simp [semAux] at h
  | succ f ih =>
    intro ot on r hon h
    rw [semAux, step] at h
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      obtain ⟨rs, rfl⟩ := pureDirect_lookup hPD hlk
      have h' : directLeaf (semAux S s T q f) s T q rs ot on r = true := h
      rcases directLeaf_elim_os hOS hsn h' with ⟨g, hg, hgs⟩ | hmog
      · -- direct match: the grant's own edge, to the concrete node or its w_all node
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        by_cases hostar : g.object.name = STAR
        · -- w_all target (probe 3)
          have hobj : objNode g.object g.relation = wAllNode ot r := by
            unfold objNode wAllNode; rw [if_pos hostar, hgrel, hgot]
          rw [hobj, hgs] at hedge
          exact Or.inr (NReaches.edge hedge)
        · -- concrete target (probe 1)
          have hgon' : g.object.name = on := matchingObjects_elim hgon hostar
          have hobj : objNode g.object g.relation = objNode (⟨ot, on⟩ : ObjectRef) r := by
            rw [objNode_plain hostar, objNode_plain hon]
            have : g.object = (⟨g.object.type, g.object.name⟩ : ObjectRef) := rfl
            rw [this, hgot, hgon', hgrel]
          rw [hobj, hgs] at hedge
          exact Or.inl (NReaches.edge hedge)
      · -- flow-through: recurse (same subject), then extend by the grant's edge
        obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_os hOS hmog
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        -- IH on the userset node of g (concrete, star-free)
        have hrec' : semAux S s T q f g.subject.type g.subject.name g.subject.predicate = true :=
          hrec
        have hmid := ih g.subject.type g.subject.name g.subject.predicate hps hrec'
        -- objNode of g's subject-userset = subjNode g.subject (flow-through)
        have hflow : objNode (⟨g.subject.type, g.subject.name⟩ : ObjectRef) g.subject.predicate =
            subjNode g.subject := objNode_eq_subjNode hps
        rw [hflow] at hmid
        -- reach to subjNode g.subject (directly, or via the bridge from its w_all node)
        have hreachSub : NReaches edges (subjNode s) (subjNode g.subject) := by
          rcases hmid with hL | hR
          · exact hL
          · exact hR.tail (hbr g hgT hps hR)
        -- extend by g's grant edge, to the concrete node or its w_all node
        have hedge := hEC g hgT
        by_cases hostar : g.object.name = STAR
        · have hobj : objNode g.object g.relation = wAllNode ot r := by
            unfold objNode wAllNode; rw [if_pos hostar, hgrel, hgot]
          rw [hobj] at hedge
          exact Or.inr (hreachSub.tail hedge)
        · have hgon' : g.object.name = on := matchingObjects_elim hgon hostar
          have hobj : objNode g.object g.relation = objNode (⟨ot, on⟩ : ObjectRef) r := by
            rw [objNode_plain hostar, objNode_plain hon]
            have : g.object = (⟨g.object.type, g.object.name⟩ : ObjectRef) := rfl
            rw [this, hgot, hgon', hgrel]
          rw [hobj] at hedge
          exact Or.inl (hreachSub.tail hedge)

end Zanzibar
