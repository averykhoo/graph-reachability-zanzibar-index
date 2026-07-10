import ZanzibarProofs.GraphIndex.DirectCorrect

/-!
# T2b, stage W1a — bare star grants `[user:*]`, ZERO bridges

`SEMANTICS.md` §7.5; ROADMAP "The staged T2 plan", sub-stage **W1a**;
`wildcard-materialization-spec.md §3.2` (the bare-shape rule).

This widens `graph_correct_direct` to allow **bare star grants** in the store:
subject `(T, *, BARE)` tuples — plain OpenFGA `[user:*]`, granting a relation to
*every* subject of type `T`. The design's key observation (spec §3.2) is that a
bare shape needs **no materialized bridge edges**: a bare-concrete subject node
`⟨T, u, BARE, plain⟩` has no in-edges (an in-edge target is an `objNode`, whose
predicate is a *relation* name, never `BARE`), and the star node
`wAny(T,BARE) = ⟨T, *, BARE, wAny⟩` has no in-edges either. So a bare-star grant is
a pure *leading* hop — exactly the read-side `wAny` endpoint substitution of
**probe 2** (`wildcard.py:354-374`) — with no interior hop to bridge.

Concretely, relative to `DirectCorrect.lean` (`StarFreeStore`), the store predicate
weakens from "no stars anywhere" to `BareStarStore` (a star subject must be bare;
objects stay star-free). Two things change:
* **soundness** — a chain may now *start* at `wAny(T,BARE)` (a leading bare-star
  hop); the base of the chain-to-`sem` induction is generalized from "the first
  tuple's subject *is* the query subject" to "*covers* it" (`Covers`), where a
  bare-star grant covers every bare-concrete subject of its type;
* **completeness** — `sem` maps to reachability from `subjNode s` **or** from
  `wAny(s.shape)` (the probe-2 disjunction, `reach_of_semAux_bs`), because a
  bare-star grant is reachable only from the star node, not the plain subject node.

`graph_correct_bareStar` assembles these: probes 3–4 stay dead (objects star-free ⇒
no `wAll` target), probe 1 (plain source) and probe 2 (`wAny`-bare source) are both
live, and probe 2 is provably dead when the query subject is a *userset* (a
userset-`wAny` node is never an edge source, `admitted_edge_source_char`).
-/

namespace Zanzibar

/-! ## W1a fragment predicates -/

/-- **W1a store predicate.** A star subject must be bare (`[T:*]`, no userset
    stars — that is W1c); objects stay star-free (no object wildcards — that is
    W1b). Strictly weaker than `StarFreeStore`. -/
def BareStarStore (T : Store) : Prop :=
  ∀ t ∈ T, (t.subject.name = STAR → t.subject.predicate = BARE) ∧ t.object.name ≠ STAR

/-- No userset stars: any star subject is bare. Both `StarFreeStore` and
    `BareStarStore` imply it; it is exactly what kills the `instances` branch of
    `memberOfGranted`/`directLeaf`. -/
def NoUsersetStar (T : Store) : Prop :=
  ∀ t ∈ T, t.subject.name = STAR → t.subject.predicate = BARE

theorem BareStarStore.noUsersetStar {T : Store} (h : BareStarStore T) : NoUsersetStar T :=
  fun t ht => (h t ht).1

theorem BareStarStore.objStarFree {T : Store} (h : BareStarStore T) :
    ∀ t ∈ T, t.object.name ≠ STAR :=
  fun t ht => (h t ht).2

/-! ## Leaf elimination under `NoUsersetStar` -/

/-- **Flow-through elimination** (no userset stars): a positive `memberOfGranted`
    exhibits a userset grant whose node `rec` answers positively — the `instances`
    (star) branch cannot fire, because a star grant would be bare (first branch,
    `false`). Generalizes `mog_elim` from `StarFreeStore`. -/
theorem mog_elim_nus {rec : Rec} {T : Store} {q : Query} {rs : List Restriction}
    {ot on rel : String} (hNUS : NoUsersetStar T)
    (h : memberOfGranted rec T q (grantsOf T rs ot on rel) = true) :
    ∃ g ∈ grantsOf T rs ot on rel, g.subject.predicate ≠ BARE ∧
      g.subject.name ≠ STAR ∧
      rec g.subject.type g.subject.name g.subject.predicate = true := by
  unfold memberOfGranted at h
  obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
  have hgT : g ∈ T := (grantsOf_elim hg).1
  by_cases hpb : (g.subject.predicate == BARE) = true
  · rw [if_pos hpb] at hgt; exact absurd hgt (by simp)
  · have hpb' : g.subject.predicate ≠ BARE := by simpa using hpb
    have hstar : g.subject.name ≠ STAR := fun hs => hpb' (hNUS g hgT hs)
    rw [if_neg hpb, if_pos (by simpa using hstar)] at hgt
    exact ⟨g, hg, hpb', hstar, hgt⟩

/-- **Direct-leaf elimination, bare-star aware** (no userset stars, star-free query
    subject): a positive `directLeaf` is one of three things — an *exact* grant
    match (`g.subject = s`), a *bare-star* grant covering a bare-concrete `s`, or a
    flow-through. The userset-star disjunct is killed by `NoUsersetStar`. This is
    the W1a generalization of `directLeaf_elim` (whose 2-way conclusion is false
    once bare-star grants can match a concrete subject). -/
theorem directLeaf_elim_bs {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hNUS : NoUsersetStar T)
    (hs : s.name ≠ STAR)
    (h : directLeaf rec s T q rs ot on rel = true) :
    (∃ g ∈ grantsOf T rs ot on rel, g.subject = s)
    ∨ (s.predicate = BARE ∧ ∃ g ∈ grantsOf T rs ot on rel,
        g.subject.name = STAR ∧ g.subject.predicate = BARE ∧ g.subject.type = s.type)
    ∨ memberOfGranted rec T q (grantsOf T rs ot on rel) = true := by
  unfold directLeaf at h
  rw [if_neg (by simpa using hs)] at h
  by_cases hp : (s.predicate == BARE) = true
  · rw [if_pos hp, Bool.or_eq_true] at h
    have hsp : s.predicate = BARE := by simpa using hp
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩ | ⟨⟨h1, h2⟩, h3⟩
      · exact Or.inl ⟨_, hg, by simp_all⟩
      · exact Or.inr (Or.inl ⟨hsp, _, hg, by simp_all⟩)
    · exact Or.inr (Or.inr h)
  · rw [if_neg hp, Bool.or_eq_true] at h
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      have hgT : g ∈ T := (grantsOf_elim hg).1
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩ | ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩
      · exact Or.inl ⟨_, hg, by simp_all⟩
      · exact absurd (hNUS _ hgT (by simpa using h1)) (by simpa using h2)
    · exact Or.inr (Or.inr h)

/-! ## Userset lifting, bare-star aware -/

/-- **Userset-lifting** (bare-star aware). Identical content to `semAux_lift` — if
    `s ∈ s'` and `s' ∈ v` then `s ∈ v` — but over `BareStarStore` (the userset `s'`
    it lifts through has `predicate ≠ BARE`, so the extra bare-star match of
    `directLeaf_elim_bs` is vacuous). -/
theorem semAux_lift_bs {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hPD : PureDirect S) (hBS : BareStarStore T)
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
      rcases directLeaf_elim_bs hBS.noUsersetStar hs'n h' with
        ⟨g, hg, hgs⟩ | ⟨hsp, _⟩ | hmog
      · apply directLeaf_of_mog
        refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
        rw [hgs]
        exact semAux_mono S (pureDirect_noExclAll hPD) s T q
          (Nat.le_add_left f₀ f) _ _ _ hmem
      · exact absurd hsp hs'p
      · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_nus hBS.noUsersetStar hmog
        exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))

/-! ## The base hop: a bare-star grant covers every bare-concrete subject of its type -/

/-- **Leaf introduction, bare-star.** A bare-star grant `g = (T,*,BARE)` answers the
    leaf positively for *any* bare-concrete subject `s` of type `T` — the second
    disjunct of `directLeaf`'s bare-concrete branch (`SEMANTICS.md §5.4`, a pure
    type-match, no recursion). -/
theorem directLeaf_grant_bareStar {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} {g : Tuple}
    (hg : g ∈ grantsOf T rs ot on rel) (hgstar : g.subject.name = STAR)
    (hgbare : g.subject.predicate = BARE) (hgtype : g.subject.type = s.type)
    (hs : s.name ≠ STAR) (hsp : s.predicate = BARE) :
    directLeaf rec s T q rs ot on rel = true := by
  unfold directLeaf
  rw [if_neg (by simpa using hs), if_pos (by simpa using hsp), Bool.or_eq_true]
  exact Or.inl (List.any_eq_true.mpr ⟨g, hg, by simp [hgstar, hgbare, hgtype]⟩)

/-- One bare-star grant is a fuel-1 `sem` membership of its object node, for any
    bare-concrete subject of the grant's type. -/
theorem semAux_one_of_bareStar {S : Schema} {T : Store} {q : Query} {t : Tuple}
    {s : SubjectRef} (hSV : StoreValid S T) (hBS : BareStarStore T) (ht : t ∈ T)
    (htstar : t.subject.name = STAR) (htbare : t.subject.predicate = BARE)
    (htype : t.subject.type = s.type) (hs : s.name ≠ STAR) (hsp : s.predicate = BARE) :
    semAux S s T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  show directLeaf (semAux S s T q 0) s T q rs
    t.object.type t.object.name t.relation = true
  refine directLeaf_grant_bareStar ?_ htstar htbare htype hs hsp
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hBS.objStarFree t ht)) hrm

/-- One plain-subject tuple is a fuel-1 `sem` membership of its object node — the
    `semAux_one_of_tuple` fact with the tuple's star-freeness supplied explicitly
    (its subject is plain here even though the store may hold bare-star tuples). -/
theorem semAux_one_of_tuple_bs {S : Schema} {T : Store} {q : Query} {t : Tuple}
    (hSV : StoreValid S T) (hBS : BareStarStore T) (ht : t ∈ T)
    (htsub : t.subject.name ≠ STAR) :
    semAux S t.subject T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  show directLeaf (semAux S t.subject T q 0) t.subject T q rs
    t.object.type t.object.name t.relation = true
  refine directLeaf_grant_self ?_ rfl htsub
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hBS.objStarFree t ht)) hrm

/-! ## The chain base: `Covers` -/

/-- A star-free subject `s` is *covered* by a graph node `u` (the potential chain
    start) when `u` is `s`'s own plain node, or (if `s` is bare-concrete) the
    bare-star node `wAny(s.shape)` a `[T:*]` grant emanates from. Generalizes the
    equality `subjNode s = u` of `graph_correct_direct` to allow the leading
    bare-star hop of probe 2. -/
def Covers (s : SubjectRef) (u : NodeKey) : Prop :=
  u = subjNode s ∨ (s.predicate = BARE ∧ u = wAnyNode s.shape)

/-- **Base hop.** The first tuple of a chain whose start `subjNode t.subject`
    covers `s` is a fuel-1 `sem` membership of its object node for `s`: either
    `t.subject = s` (plain) or `t` is a bare-star grant of `s`'s type. -/
theorem semAux_one_covers {S : Schema} {T : Store} {q : Query} {t : Tuple}
    {s : SubjectRef} (hSV : StoreValid S T) (hBS : BareStarStore T) (ht : t ∈ T)
    (hs : s.name ≠ STAR) (hcov : Covers s (subjNode t.subject)) :
    semAux S s T q 1 t.object.type t.object.name t.relation = true := by
  rcases hcov with hEq | ⟨hsp, hWany⟩
  · -- plain: subjNode t.subject = subjNode s (plain) ⇒ t.subject = s
    have htsub : t.subject.name ≠ STAR := by
      intro hstar
      rw [subjNode, if_pos hstar, subjNode_plain hs] at hEq
      simp [NodeKey.mk.injEq] at hEq
    have hts : t.subject = s := subjNode_inj htsub hs hEq
    rw [← hts]
    exact semAux_one_of_tuple_bs hSV hBS ht htsub
  · -- bare-star: subjNode t.subject = wAny(s.shape) ⇒ t bare-star of s.type
    rw [wAnyNode, SubjectRef.shape] at hWany
    have htstar : t.subject.name = STAR := by
      by_contra hne
      rw [subjNode, if_neg hne] at hWany
      simp [NodeKey.mk.injEq] at hWany
    rw [subjNode, if_pos htstar] at hWany
    simp only [NodeKey.mk.injEq] at hWany
    obtain ⟨htype, -, htbare, -⟩ := hWany
    exact semAux_one_of_bareStar hSV hBS ht htstar (by rw [htbare, hsp]) htype hs hsp

/-! ## Soundness: a covered chain is a `sem` membership -/

/-- **Soundness core (W1a).** A length-`n` chain whose start `u` *covers* the
    star-free query subject `s` is a `sem` membership at fuel `n`. The base hop
    uses `semAux_one_covers` (plain or bare-star); each further hop lifts through
    its userset (`semAux_lift_bs`, `f₀ = 1`) — exactly as `semAux_of_chainN`, with
    the coverage generalization at the first hop. -/
theorem semAux_of_chainN_bs {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hBS : BareStarStore T) :
    ∀ {n : Nat} {u v : NodeKey}, TupleChainN T n u v →
      ∀ {s : SubjectRef}, s.name ≠ STAR → Covers s u →
      ∀ {ot on r : String}, on ≠ STAR → objNode ⟨ot, on⟩ r = v →
      semAux S s T q n ot on r = true := by
  intro n u v hchain
  induction hchain with
  | single t ht =>
    intro s hsn hcov ot on r hon hov
    obtain ⟨hobj, hrel⟩ := objNode_inj hon (hBS.objStarFree t ht) hov
    subst hrel
    have h1 := semAux_one_covers (q := q) hSV hBS ht hsn hcov
    rw [← hobj] at h1
    exact h1
  | @cons t ht n v rest ih =>
    intro s hsn hcov ot on r hon hov
    have hoObj : t.object.name ≠ STAR := hBS.objStarFree t ht
    have hmem1 := semAux_one_covers (q := q) hSV hBS ht hsn hcov
    have hs'n : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ≠ STAR := hoObj
    have hs'p : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate ≠ BARE := by
      obtain ⟨rs, hlk, _⟩ := hSV t ht
      exact lookup_rel_ne_bare hWF hlk
    have hsub : Covers (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef)
        (objNode t.object t.relation) := Or.inl (objNode_eq_subjNode hoObj)
    have htail := ih (s := ⟨t.object.type, t.object.name, t.relation⟩) hs'n hsub hon hov
    exact semAux_lift_bs hPD hBS hs'n hs'p hmem1 n ot on r htail

/-! ## Completeness: a `sem` membership is a probe-1 ∨ probe-2 reachability -/

/-- **Completeness core (W1a).** For a star-free query subject `s`, a `sem`
    membership is reachability from `subjNode s` **or** from `wAny(s.shape)` — the
    probe-1 ∨ probe-2 disjunction. A bare-star direct match contributes the star
    node's edge (right disjunct); an exact match and a flow-through keep the
    subject fixed and preserve whichever disjunct the recursion produced. -/
theorem reach_of_semAux_bs {S : Schema} {T : Store} {q : Query} {σ : GraphState}
    (hPD : PureDirect S) (hBS : BareStarStore T)
    (hEC : ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges)
    {s : SubjectRef} (hs : s.name ≠ STAR) :
    ∀ (f : Nat) (ot on r : String), semAux S s T q f ot on r = true →
      NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r)
      ∨ NReaches σ.edges (wAnyNode s.shape) (objNode ⟨ot, on⟩ r) := by
  intro f
  induction f with
  | zero => intro ot on r h; simp [semAux] at h
  | succ f ih =>
    intro ot on r h
    rw [semAux, step] at h
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      obtain ⟨rs, rfl⟩ := pureDirect_lookup hPD hlk
      have h' : directLeaf (semAux S s T q f) s T q rs ot on r = true := h
      rcases directLeaf_elim_bs hBS.noUsersetStar hs h' with
        ⟨g, hg, hgs⟩ | ⟨hsp, g, hg, hgstar, hgbare, hgtype⟩ | hmog
      · -- exact match: the grant's own edge from subjNode s
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS.objStarFree g hgT)
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        rw [hobj, hgrel, hgs] at hedge
        exact Or.inl (NReaches.edge hedge)
      · -- bare-star match: the grant's edge from wAny(s.shape)
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS.objStarFree g hgT)
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        have hsubj : subjNode g.subject = wAnyNode s.shape := by
          rw [subjNode, if_pos hgstar]
          simp only [wAnyNode, SubjectRef.shape, hgbare, hgtype, hsp]
        rw [hobj, hgrel, hsubj] at hedge
        exact Or.inr (NReaches.edge hedge)
      · -- flow-through: recurse (same subject), extend by the grant's edge
        obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_nus hBS.noUsersetStar hmog
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hmid := ih _ _ _ hrec
        rw [objNode_eq_subjNode hps] at hmid
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS.objStarFree g hgT)
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        rw [hobj, hgrel] at hedge
        rcases hmid with hL | hR
        · exact Or.inl (hL.tail hedge)
        · exact Or.inr (hR.tail hedge)

/-! ## Edge-endpoint variants on a bare-star admitted state -/

/-- Every edge *source* of an admitted `BareStarStore` state is either a plain node
    or a bare-star `wAny` node (`pred = BARE`). No userset-`wAny` node is ever an
    edge source — that would need a userset-star tuple, which `BareStarStore`
    forbids. This is what makes probe 2 dead for a userset query subject. -/
theorem admitted_edge_source_char {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) (hBS : BareStarStore T) :
    ∀ e ∈ σ.edges, e.1.variant = Variant.plain ∨
      (e.1.variant = Variant.wAny ∧ e.1.pred = BARE) := by
  intro e he
  obtain ⟨t, htT, h1, _⟩ :=
    reachedByDirect_edge_sound (reachedByDirect_of_admitted h) e.1 e.2 he
  by_cases hst : t.subject.name = STAR
  · exact Or.inr (by rw [h1, subjNode, if_pos hst]; exact ⟨rfl, (hBS t htT).1 hst⟩)
  · exact Or.inl (by rw [h1, subjNode, if_neg hst])

/-- Every edge *target* is plain (objects star-free). -/
theorem admitted_edges_target_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) (hBS : BareStarStore T) :
    ∀ e ∈ σ.edges, e.2.variant = Variant.plain := by
  intro e he
  obtain ⟨t, htT, _, h2⟩ :=
    reachedByDirect_edge_sound (reachedByDirect_of_admitted h) e.1 e.2 he
  rw [h2, objNode_plain (hBS.objStarFree t htT)]

/-- A path's source has an edge-source variant. -/
theorem nreaches_source_char {edges : List (NodeKey × NodeKey)}
    (hpl : ∀ e ∈ edges, e.1.variant = Variant.plain ∨
      (e.1.variant = Variant.wAny ∧ e.1.pred = BARE))
    {u v : NodeKey} (hr : NReaches edges u v) :
    u.variant = Variant.plain ∨ (u.variant = Variant.wAny ∧ u.pred = BARE) := by
  cases hr with
  | edge he => exact hpl _ he
  | head he _ => exact hpl _ he

/-! ## T2b on the W1a fragment, assembled -/

/-- **T2b, bare-star fragment (W1a).** On any state reached by admitted untainted
    writes of an admission-valid store that allows bare star grants (`[T:*]`,
    objects star-free), the graph read answers exactly `sem`, for every star-free
    query. Probes 3–4 are dead (no `wAll` target); probe 1 (plain) and probe 2
    (`wAny`-bare) are handled by `Covers`/`semAux_of_chainN_bs` (soundness) and
    `reach_of_semAux_bs` (completeness); probe 2 is provably dead for a userset
    query subject (`admitted_edge_source_char`). -/
theorem graph_correct_bareStar (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hBS : BareStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hInv : Inv S σ := (reachedByDirect_inv (reachedByDirect_of_admitted hReach)).1
  have hcl := hInv.edgesClosed
  have hsrc := admitted_edge_source_char hReach hBS
  have htgt := admitted_edges_target_plain hReach hBS
  -- the read routes to probeNonDerived (pure-direct = untainted)
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
    unfold GraphModel.check
    rw [hInv.schemaEq, isDerived_pureDirect hPD]; simp
  -- probes 3,4 are dead (targets are never wAll on star-free objects)
  have hpAll : ∀ u, σ.reach u (wAllNode q.object.type q.relation) = false := by
    intro u
    cases hcase : σ.reach u (wAllNode q.object.type q.relation) with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain (fun e he => htgt e he) (reach_sound hcase)
      simp [wAllNode] at this
  have hqsb : (q.subject.name != STAR) = true := by simp only [bne_iff_ne, ne_eq]; exact hqs
  have hprobe : GraphModel.probeNonDerived σ q =
      (σ.reach (subjNode q.subject) (objNode q.object q.relation)
       || σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation)) := by
    unfold GraphModel.probeNonDerived
    simp [hpAll, hqsb]
  -- forward: a probe hit (from a covering source) is a sem membership
  have hfwd : ∀ w, Covers q.subject w →
      NReaches σ.edges w (objNode q.object q.relation) → sem S T q = true := by
    intro w hcov hnr
    obtain ⟨l, hl⟩ := trail_of_nreaches hnr
    have hsub : ∀ x ∈ l, x ∈ σ.nodes := trail_verts_mem hcl l _ _ hl
    obtain ⟨l', hl', hlen⟩ := trail_compress l.length l (le_refl _) hl hsub
    have hchain := chainN_of_trail
      (reachedByDirect_edge_sound (reachedByDirect_of_admitted hReach)) l' _ _ hl'
    obtain ⟨t0, ht0⟩ := chainN_mem hchain
    obtain ⟨rs0, hlk0, -⟩ := hSV t0 ht0
    have hkeys := lookup_keys_nonempty hlk0
    have hnodes := admitted_nodes_length hReach
    have hfb : l'.length + 1 ≤ fuelBound S T := by
      unfold fuelBound
      have h2T : l'.length ≤ 2 * T.length := hnodes ▸ hlen
      have hbase : T.length * 2 + 4 ≤ S.keys.length * (T.length * 2 + 4) := by
        conv_lhs => rw [← Nat.one_mul (T.length * 2 + 4)]
        exact Nat.mul_le_mul_right _ hkeys
      omega
    have hsem := semAux_of_chainN_bs (q := q) hWF hPD hSV hBS hchain hqs hcov hqo rfl
    unfold sem
    exact semAux_mono S (pureDirect_noExclAll hPD) q.subject T q hfb _ _ _ hsem
  -- backward: a sem membership hits probe 1 or probe 2
  have hbwd : sem S T q = true →
      σ.reach (subjNode q.subject) (objNode q.object q.relation) = true
      ∨ σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) = true := by
    intro hsem
    unfold sem at hsem
    rcases reach_of_semAux_bs hPD hBS (admitted_edge_complete hReach) hqs _ _ _ _ hsem with hL | hR
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
        have hchar := nreaches_source_char (fun e he => hsrc e he) hnr
        have hbare : q.subject.predicate = BARE := by
          rcases hchar with hpl | ⟨_, hpred⟩
          · simp [wAnyNode] at hpl
          · simpa [wAnyNode, SubjectRef.shape] using hpred
        have := hfwd (wAnyNode q.subject.shape) (Or.inr ⟨hbare, rfl⟩) hnr
        rw [hsemc] at this; exact absurd this (by simp)
    rw [hn1, hn2]; rfl

end Zanzibar
