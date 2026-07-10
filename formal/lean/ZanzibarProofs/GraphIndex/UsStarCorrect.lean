import ZanzibarProofs.GraphIndex.UsStarWrite
import ZanzibarProofs.GraphIndex.ObjStarCorrect

/-!
# T2b, stage W1c — userset stars `[group:*#member]`, the edge characterization

`SEMANTICS.md` §7.5; ROADMAP "The staged T2 plan", sub-stage **W1c**;
`wildcard-materialization-spec.md §1.1` (the `concrete → w_any(shape)` in-bridge
composition).

This is the first correspondence increment for W1c. It proves the **structural
fact** the soundness chain classifies each trail hop against: every edge of a
`UsStarReached` state is either a stored **grant** edge, a `concrete → w_any`
**in-bridge** (the new W1c machinery), or a `w_all → concrete` **out-bridge** (W1b,
inert on the object-wildcard-free fragment but retained honestly — `writeUsStar`
calls `ensureBridges` too). The bridge-absorbing chain (analog of `GrantReach`, but
absorbing an *in-bridge* + the userset-star grant out of `w_any`), the
`instances`-branch of `memberOfGranted`, and probe 4 are the deferred next
increments.
-/

namespace Zanzibar

/-! ## W1c fragment predicate -/

/-- **W1c store predicate.** Objects are star-free (no object wildcards — that is
    W1b); subjects may be userset stars `(T,*,P)` with `P ≠ BARE` (the new W1c data)
    or ordinary star-free subjects. A bare star subject `(T,*,'...')` is W1a's
    fragment and is excluded here so the two star-subject shapes stay separated. -/
def UsStarStore (T : Store) : Prop :=
  ∀ t ∈ T, t.object.name ≠ STAR ∧ (t.subject.name = STAR → t.subject.predicate ≠ BARE)

/-! ## The bridged-in-concrete flag decomposed -/

/-- `bridgedInConcrete` decomposed: a bridged-in-concrete node is plain, star-free, of
    a declared subject-wildcard userset shape (hence `pred ≠ BARE`). -/
theorem bridgedInConcrete_elim {σ : GraphState} {c : NodeKey}
    (h : σ.bridgedInConcrete c = true) :
    c.variant = Variant.plain ∧ c.name ≠ STAR ∧ c.pred ≠ BARE ∧
      σ.schema.isSubjectWildcardUserset c.type c.pred = true := by
  unfold GraphState.bridgedInConcrete at h
  simp only [Bool.and_eq_true, beq_iff_eq, bne_iff_ne, ne_eq] at h
  obtain ⟨⟨hv, hn⟩, hsw⟩ := h
  refine ⟨hv, hn, ?_, hsw⟩
  -- pred ≠ BARE from isSubjectWildcardUserset (its first conjunct is `pred != BARE`)
  unfold Schema.isSubjectWildcardUserset at hsw
  simp only [Bool.and_eq_true, bne_iff_ne, ne_eq] at hsw
  exact hsw.1

/-! ## Edge characterization for the userset-star write

The three shapes an edge can take, peeled through `writeUsStar`'s nested bridge
machinery: the grant, an in-bridge (`c → w_any`), or an out-bridge (`w_all → c`). -/

/-- `ensureInBridges`'s edge effect: an edge is either an old edge or the single
    in-bridge `c → wAnyNode (c.type, c.pred)` (with `c` bridged-in-concrete). -/
theorem ensureInBridges_edges_mem {σ : GraphState} {c : NodeKey} {e : NodeKey × NodeKey}
    (he : e ∈ (σ.ensureInBridges c).edges) :
    e ∈ σ.edges ∨ (e = (c, wAnyNode (c.type, c.pred)) ∧ σ.bridgedInConcrete c = true) := by
  unfold GraphState.ensureInBridges at he
  by_cases hbr : σ.bridgedInConcrete c = true
  · rw [if_pos hbr] at he
    split at he
    · rw [addEdge_edges, addNode_edges] at he
      rcases List.mem_cons.mp he with heq | hmem
      · exact Or.inr ⟨heq, hbr⟩
      · exact Or.inl hmem
    · rw [addNode_edges] at he; exact Or.inl he
  · rw [if_neg (by simpa using hbr)] at he; exact Or.inl he

/-- An edge of a state produced by the two `ensureBridges` (out) then two
    `ensureInBridges` (in) is old, an out-bridge for some plain concrete, or an
    in-bridge for some plain concrete. Peels the four bridge layers. -/
theorem bridgeLayers_edges_mem {σ : GraphState} {a b : NodeKey} {e : NodeKey × NodeKey}
    (he : e ∈ (((((σ.addNode a).addNode b).ensureBridges a).ensureBridges b).ensureInBridges a
              |>.ensureInBridges b).edges) :
    e ∈ σ.edges
    ∨ (∃ c, e = (wAllNode c.type c.pred, c) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR)
    ∨ (∃ c, e = (c, wAnyNode (c.type, c.pred)) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR
        ∧ c.pred ≠ BARE) := by
  -- in-bridge on b
  rcases ensureInBridges_edges_mem he with h1 | ⟨heq, hbc⟩
  · -- in-bridge on a
    rcases ensureInBridges_edges_mem h1 with h2 | ⟨heq, hbc⟩
    · -- out-bridge on b
      rcases ensureBridges_edges_mem h2 with h3 | ⟨heq, hbc⟩
      · -- out-bridge on a
        rcases ensureBridges_edges_mem h3 with h4 | ⟨heq, hbc⟩
        · rw [addNode_edges, addNode_edges] at h4; exact Or.inl h4
        · obtain ⟨hv, hn, _⟩ := bridgedConcrete_elim hbc
          exact Or.inr (Or.inl ⟨_, heq, hv, hn⟩)
      · obtain ⟨hv, hn, _⟩ := bridgedConcrete_elim hbc
        exact Or.inr (Or.inl ⟨_, heq, hv, hn⟩)
    · obtain ⟨hv, hn, hp, _⟩ := bridgedInConcrete_elim hbc
      exact Or.inr (Or.inr ⟨_, heq, hv, hn, hp⟩)
  · obtain ⟨hv, hn, hp, _⟩ := bridgedInConcrete_elim hbc
    exact Or.inr (Or.inr ⟨_, heq, hv, hn, hp⟩)

/-- `writeUsStar`'s edge effect: an edge of `σ.writeUsStar t` is an old edge, the grant
    edge `(subjNode t.subject, objNode t.object t.relation)`, an out-bridge, or an
    in-bridge. -/
theorem writeUsStar_edges_mem {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ (σ.writeUsStar t).edges) :
    e ∈ σ.edges
    ∨ e = (subjNode t.subject, objNode t.object t.relation)
    ∨ (∃ c, e = (wAllNode c.type c.pred, c) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR)
    ∨ (∃ c, e = (c, wAnyNode (c.type, c.pred)) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR
        ∧ c.pred ≠ BARE) := by
  unfold GraphState.writeUsStar at he
  dsimp only at he
  split at he
  · rw [addEdge_edges] at he
    rcases List.mem_cons.mp he with heq | hmem
    · exact Or.inr (Or.inl heq)
    · rcases bridgeLayers_edges_mem hmem with h | hout | hin
      · exact Or.inl h
      · exact Or.inr (Or.inr (Or.inl hout))
      · exact Or.inr (Or.inr (Or.inr hin))
  · exact Or.inl he

/-- **Grant-or-bridge edge characterization for W1c.** Every edge of a `UsStarReached`
    state is either a stored **grant** edge (`subjNode t.subject → objNode t.object
    t.relation`), a `w_all → concrete` **out-bridge**, or a `concrete → w_any`
    **in-bridge**. By induction over the userset-star write path. This is the
    structural fact the soundness chain (deferred) classifies each trail hop against. -/
theorem usStarReached_grant_or_bridge {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) :
    ∀ a b, (a, b) ∈ σ.edges →
      (∃ t ∈ T, a = subjNode t.subject ∧ b = objNode t.object t.relation)
      ∨ (a = wAllNode b.type b.pred ∧ b.variant = Variant.plain ∧ b.name ≠ STAR)
      ∨ (b = wAnyNode (a.type, a.pred) ∧ a.variant = Variant.plain ∧ a.name ≠ STAR
          ∧ a.pred ≠ BARE) := by
  induction h with
  | empty S => intro a b hab; simp [emptyState] at hab
  | @step σ S T t hprev ih =>
    intro a b hab
    rcases writeUsStar_edges_mem hab with hold | hgrant | ⟨c, hc, hcv, hcn⟩ | ⟨c, hc, hcv, hcn, hcp⟩
    · rcases ih a b hold with ⟨t', ht', h1, h2⟩ | hout | hin
      · exact Or.inl ⟨t', List.mem_cons_of_mem _ ht', h1, h2⟩
      · exact Or.inr (Or.inl hout)
      · exact Or.inr (Or.inr hin)
    · obtain ⟨rfl, rfl⟩ := Prod.ext_iff.mp hgrant
      exact Or.inl ⟨t, List.mem_cons_self, rfl, rfl⟩
    · simp only [Prod.mk.injEq] at hc
      obtain ⟨ha, hb⟩ := hc
      subst hb
      exact Or.inr (Or.inl ⟨ha, hcv, hcn⟩)
    · simp only [Prod.mk.injEq] at hc
      obtain ⟨ha, hb⟩ := hc
      subst ha
      exact Or.inr (Or.inr ⟨hb, hcv, hcn, hcp⟩)

/-! ## `instances` excludes the star sentinel

The `∃`-witness population `instances T q t` (`Core/Store.lean`, `universeOf` with
endpoints excluded) is built only from tuple-position names guarded by `≠ STAR`, so
no member is the `STAR` sentinel. This is what lets an `instances` witness `inst`
name a *concrete* node `⟨t, inst, P, plain⟩` (so `objNode ⟨t,inst⟩ P = subjNode
⟨t,inst,P⟩`, the flow-through identity, and the concrete's in-bridge exists). -/

/-- No `instances` witness is the `STAR` sentinel (every universe name passes a
    `≠ STAR` guard). Mirrors `instances_subset_storedNames`'s foldr peeling. -/
theorem instances_ne_star (T : Store) (q : Query) (t : String) :
    ∀ x ∈ instances T q t, x ≠ STAR := by
  intro x hx
  unfold instances universeOf at hx
  simp only [if_neg (Bool.false_ne_true), List.append_nil, List.mem_dedup] at hx
  induction T with
  | nil => simp at hx
  | cons tup rest ih =>
      simp only [List.foldr_cons] at hx
      have hsplit : ∀ {y : String} {acc : List String},
          y ∈ (if tup.object.type = t ∧ tup.object.name ≠ STAR
                then tup.object.name :: acc else acc) →
          (y = tup.object.name ∧ tup.object.name ≠ STAR) ∨ y ∈ acc := by
        intro y acc hy
        split at hy
        · rename_i hg
          rcases List.mem_cons.mp hy with h | h
          · exact Or.inl ⟨h, hg.2⟩
          · exact Or.inr h
        · exact Or.inr hy
      rcases hsplit hx with ⟨rfl, hne⟩ | hx1
      · exact hne
      · have hsplit2 : (x = tup.subject.name ∧ tup.subject.name ≠ STAR) ∨
            x ∈ rest.foldr (fun tup acc =>
              let acc := if tup.subject.type = t ∧ tup.subject.name ≠ STAR
                         then tup.subject.name :: acc else acc
              if tup.object.type = t ∧ tup.object.name ≠ STAR
              then tup.object.name :: acc else acc) [] := by
          split at hx1
          · rename_i hg
            rcases List.mem_cons.mp hx1 with h | h
            · exact Or.inl ⟨h, hg.2⟩
            · exact Or.inr h
          · exact Or.inr hx1
        rcases hsplit2 with ⟨rfl, hne⟩ | hx2
        · exact hne
        · exact ih hx2

/-! ## Userset-star leaf eliminations

The subject-side leaf lemmas, generalized to admit the userset-star grant disjunct
that W1a/W1b killed (`directLeaf_elim_bs`'s `NoUsersetStar`, `mog_elim_os`'s
star-free subjects). For a userset-star grant `g = (T,*,P)` (`P ≠ BARE`):
* it **directly matches** a userset query subject `s = (T, sn, P)` of the same shape
  (`directLeaf`'s userset-branch second disjunct) — a leading hop that read-probe 2
  (`wAny(s.shape)`) covers, exactly as W1a's bare-star direct match, but non-bare;
* it **flows through** over `instances T q T` (`memberOfGranted`'s `instances`-branch)
  — the in-bridge-absorbed hop. -/

/-- **Direct-leaf elimination, userset-star aware** (userset-star store, star-free
    query subject). A positive `directLeaf` is an *exact* grant match, a *userset-star*
    grant of the query subject's shape (only when `s` is itself a userset), or a
    flow-through. The bare-*star* disjunct of `directLeaf`'s bare-concrete branch is
    killed by `UsStarStore` (a store star subject is non-bare). Generalizes
    `directLeaf_elim_os`/`directLeaf_elim_bs`. -/
theorem directLeaf_elim_us {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hUS : UsStarStore T)
    (hs : s.name ≠ STAR)
    (h : directLeaf rec s T q rs ot on rel = true) :
    (∃ g ∈ grantsOf T rs ot on rel, g.subject = s)
    ∨ (s.predicate ≠ BARE ∧ ∃ g ∈ grantsOf T rs ot on rel,
        g.subject.name = STAR ∧ g.subject.type = s.type ∧ g.subject.predicate = s.predicate)
    ∨ memberOfGranted rec T q (grantsOf T rs ot on rel) = true := by
  unfold directLeaf at h
  rw [if_neg (by simpa using hs)] at h
  by_cases hp : (s.predicate == BARE) = true
  · rw [if_pos hp, Bool.or_eq_true] at h
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      have hgT : g ∈ T := (grantsOf_elim hg).1
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩ | ⟨⟨h1, h2⟩, h3⟩
      · exact Or.inl ⟨_, hg, by simp_all⟩
      · exact absurd h2 ((hUS _ hgT).2 h1)
    · exact Or.inr (Or.inr h)
  · rw [if_neg hp, Bool.or_eq_true] at h
    have hsp : s.predicate ≠ BARE := by simpa using hp
    rcases h with h | h
    · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
      have hgT : g ∈ T := (grantsOf_elim hg).1
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩ | ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩
      · exact Or.inl ⟨_, hg, by simp_all⟩
      · exact Or.inr (Or.inl ⟨hsp, _, hg, h1, h3, h4⟩)
    · exact Or.inr (Or.inr h)

/-- **Flow-through elimination, userset-star aware** (userset-star store). A positive
    `memberOfGranted` is either a *plain* userset grant whose node `rec` answers
    positively, or a *userset-star* grant with a positive `instances` witness — the
    `instances`-branch that `mog_elim`/`mog_elim_os` (star-free subjects) could not
    fire. A bare grant contributes `false` and is excluded. Needs no store hypothesis
    (the bare branch is unconditionally `false`). -/
theorem mog_elim_us {rec : Rec} {T : Store} {q : Query} {rs : List Restriction}
    {ot on rel : String}
    (h : memberOfGranted rec T q (grantsOf T rs ot on rel) = true) :
    (∃ g ∈ grantsOf T rs ot on rel, g.subject.predicate ≠ BARE ∧ g.subject.name ≠ STAR ∧
      rec g.subject.type g.subject.name g.subject.predicate = true)
    ∨ (∃ g ∈ grantsOf T rs ot on rel, g.subject.predicate ≠ BARE ∧ g.subject.name = STAR ∧
      ∃ inst ∈ instances T q g.subject.type,
        rec g.subject.type inst g.subject.predicate = true) := by
  unfold memberOfGranted at h
  obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
  by_cases hpb : (g.subject.predicate == BARE) = true
  · rw [if_pos hpb] at hgt; exact absurd hgt (by simp)
  · have hpb' : g.subject.predicate ≠ BARE := by simpa using hpb
    rw [if_neg hpb] at hgt
    by_cases hstar : (g.subject.name != STAR) = true
    · rw [if_pos hstar] at hgt
      exact Or.inl ⟨g, hg, hpb', by simpa using hstar, hgt⟩
    · rw [if_neg hstar] at hgt
      have hgstar : g.subject.name = STAR := by simpa using hstar
      obtain ⟨inst, hinst, hrec⟩ := List.any_eq_true.mp hgt
      exact Or.inr ⟨g, hg, hpb', hgstar, inst, hinst, hrec⟩

/-! ## `sem ⇒ probe 1 ∨ probe 2` — the completeness semantic core (W1c)

The completeness half of the W1c read correspondence: for a star-free query subject
`s`, a `sem` membership is reachability from `subjNode s` (probe 1) **or** from
`wAny(s.shape)` (probe 2). This fuses the two earlier stages:
* the **probe-2 disjunction** is W1a's (`reach_of_semAux_bs`) — a userset-star grant
  directly matching `s` is reachable only from the `wAny(s.shape)` node (a query-only
  subject has no in-bridge, so probe 1 cannot see it — the attack-first
  endpoint-exclusion finding);
* the **bridge-threaded flow-through** is W1b's (`reach_of_semAux_os`), but with the
  `concrete → w_any` **in-bridge**: a userset-star flow-through reaches a concrete
  instance node `subjNode ⟨T,inst,P⟩`, then its in-bridge into `wAny(T,P)`, then the
  grant edge out of `wAny(T,P)`.

Stated over the two operational facts it consumes — edge-completeness (`hEC`) and
**in-bridge completeness** (`hib`, every `instances` witness of a userset-star grant
has its `concrete → w_any` bridge) — deferring the admitted, bridge-complete
write-closure that discharges them to the next increment, exactly as
`reach_of_semAux_os` defers to `hEC`/`hbr`. -/

/-- **Completeness core (W1c).** For a star-free query subject `s = q.subject`, a
    `sem` membership is reachability from `subjNode s` (probe 1) **or** from
    `wAny(s.shape)` (probe 2). An exact grant match hits probe 1; a userset-star
    grant of `s`'s shape hits probe 2 (`wAny(s.shape) → objNode`); a plain
    flow-through extends the recursion by the grant edge; a userset-star flow-through
    threads the concrete instance's in-bridge (`hib`) then the grant edge out of the
    `w_any` node. -/
theorem reach_of_semAux_us {S : Schema} {T : Store} {q : Query}
    {edges : List (NodeKey × NodeKey)}
    (hPD : PureDirect S) (hUS : UsStarStore T) (hqs : q.subject.name ≠ STAR)
    (hEC : ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ edges)
    (hib : ∀ g ∈ T, g.subject.name = STAR → g.subject.predicate ≠ BARE →
      ∀ inst ∈ instances T q g.subject.type,
        (subjNode ⟨g.subject.type, inst, g.subject.predicate⟩,
          wAnyNode (g.subject.type, g.subject.predicate)) ∈ edges) :
    ∀ (f : Nat) (ot on r : String),
      semAux S q.subject T q f ot on r = true →
      NReaches edges (subjNode q.subject) (objNode ⟨ot, on⟩ r)
      ∨ NReaches edges (wAnyNode q.subject.shape) (objNode ⟨ot, on⟩ r) := by
  set s := q.subject with hs_def
  have hsn : s.name ≠ STAR := hqs
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
      rcases directLeaf_elim_us hUS hsn h' with
        ⟨g, hg, hgs⟩ | ⟨hsp, g, hg, hgstar, hgtype, hgpred⟩ | hmog
      · -- exact match: the grant's own edge from subjNode s (probe 1)
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hUS g hgT).1
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        rw [hobj, hgrel, hgs] at hedge
        exact Or.inl (NReaches.edge hedge)
      · -- userset-star direct match: the grant's edge from wAny(s.shape) (probe 2)
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hUS g hgT).1
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        have hsubj : subjNode g.subject = wAnyNode s.shape := by
          rw [subjNode, if_pos hgstar]
          simp only [wAnyNode, SubjectRef.shape, hgtype, hgpred]
        rw [hobj, hgrel, hsubj] at hedge
        exact Or.inr (NReaches.edge hedge)
      · -- flow-through: recurse (same subject), then extend by the grant('s in-bridge +) edge
        rcases mog_elim_us hmog with
          ⟨g, hg, hpb, hps, hrec⟩ | ⟨g, hg, hpb, hgstar, inst, hinst, hrec⟩
        · -- plain userset flow: reach subjNode g.subject, extend by the grant edge
          obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
          have hmid := ih g.subject.type g.subject.name g.subject.predicate hrec
          rw [objNode_eq_subjNode hps] at hmid
          have hedge := hEC g hgT
          have hgon' : g.object.name = on := matchingObjects_elim hgon (hUS g hgT).1
          have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
          rw [hobj, hgrel] at hedge
          rcases hmid with hL | hR
          · exact Or.inl (hL.tail hedge)
          · exact Or.inr (hR.tail hedge)
        · -- userset-star flow: reach the concrete instance node, in-bridge, then the grant
          obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
          have hinstne : inst ≠ STAR := instances_ne_star T q g.subject.type inst hinst
          have hmid := ih g.subject.type inst g.subject.predicate hrec
          rw [objNode_eq_subjNode hinstne] at hmid
          have hbridge := hib g hgT hgstar hpb inst hinst
          have hgsubj : subjNode g.subject =
              wAnyNode (g.subject.type, g.subject.predicate) := by
            rw [subjNode, if_pos hgstar]; rfl
          have hedge := hEC g hgT
          rw [hgsubj] at hedge
          have hgon' : g.object.name = on := matchingObjects_elim hgon (hUS g hgT).1
          have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
          rw [hobj, hgrel] at hedge
          rcases hmid with hL | hR
          · exact Or.inl ((hL.tail hbridge).tail hedge)
          · exact Or.inr ((hR.tail hbridge).tail hedge)

/-! ## Soundness infrastructure — the userset-star-aware lift

The soundness half (graph path ⇒ `sem`) must, like W1b's `semAux_of_grantReach`,
lift membership through consecutive chain hops. The new content over W1b: an
intermediate userset node `s'` may match a **userset-star** grant `g = (T,*,P)`
directly (its shape equals `g`'s), and absorbing that into the outer subject `s`'s
membership goes through `memberOfGranted`'s **`instances`-branch** — which fires for
`s` with witness `s'.name` precisely when `s'.name ∈ instances T q s'.type`. So the
W1c lift (`semAux_lift_us`) carries an instances hypothesis on `s'` that
`semAux_lift_os` (star-free intermediates) did not need. Every intermediate the chain
lifts through is a tuple object name, hence in `instances` (`objectName_mem_instances`),
so the hypothesis is always dischargeable. -/

/-- **Flow-through introduction via a userset-star grant.** A userset-star grant
    `g = (T,*,P)` (`P ≠ BARE`) with a positive `instances` witness makes
    `memberOfGranted` positive — the `instances`-branch introduction (dual of
    `mog_intro`'s plain-userset branch). -/
theorem mog_intro_star {rec : Rec} {T : Store} {q : Query} {grants : List Tuple}
    {g : Tuple} (hg : g ∈ grants) (hpb : g.subject.predicate ≠ BARE)
    (hps : g.subject.name = STAR) {inst : String}
    (hinst : inst ∈ instances T q g.subject.type)
    (hrec : rec g.subject.type inst g.subject.predicate = true) :
    memberOfGranted rec T q grants = true := by
  unfold memberOfGranted
  refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
  rw [if_neg (by simpa using hpb), if_neg (by simp [hps])]
  exact List.any_eq_true.mpr ⟨inst, hinst, hrec⟩

/-- **A tuple's object name is in `instances`.** A star-free object position of a
    stored tuple is a member of the `∃`-witness population for its type (`instances`
    includes tuple positions, excludes only query endpoints). This is what discharges
    the `instances` hypothesis of `semAux_lift_us` at every `hop` intermediate. -/
theorem objectName_mem_instances {T : Store} {q : Query} {t : Tuple} (ht : t ∈ T)
    (hne : t.object.name ≠ STAR) : t.object.name ∈ instances T q t.object.type := by
  unfold instances universeOf
  simp only [if_neg (Bool.false_ne_true), List.append_nil, List.mem_dedup]
  induction T with
  | nil => simp at ht
  | cons tup rest ih =>
      simp only [List.foldr_cons]
      have hlift : ∀ {acc : List String},
          t.object.name ∈ acc →
          t.object.name ∈ (if tup.object.type = t.object.type ∧ tup.object.name ≠ STAR
              then tup.object.name ::
                (if tup.subject.type = t.object.type ∧ tup.subject.name ≠ STAR
                 then tup.subject.name :: acc else acc)
              else (if tup.subject.type = t.object.type ∧ tup.subject.name ≠ STAR
                 then tup.subject.name :: acc else acc)) := by
        intro acc hacc
        split
        · exact List.mem_cons_of_mem _ (by split <;> [exact List.mem_cons_of_mem _ hacc; exact hacc])
        · split <;> [exact List.mem_cons_of_mem _ hacc; exact hacc]
      rcases List.mem_cons.mp ht with rfl | hmem
      · rw [if_pos ⟨rfl, hne⟩]; exact List.mem_cons_self
      · exact hlift (ih hmem)

/-- **Leaf introduction, userset-star.** A userset-star grant `g = (T,*,P)` answers
    the leaf positively for *any* userset subject `s` of the same shape `(T,P)` — the
    second disjunct of `directLeaf`'s userset branch (`SEMANTICS.md §5.4`, a pure
    shape-match, no recursion). The userset analog of `directLeaf_grant_bareStar`. -/
theorem directLeaf_grant_usStar {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} {g : Tuple}
    (hg : g ∈ grantsOf T rs ot on rel) (hgstar : g.subject.name = STAR)
    (hgtype : g.subject.type = s.type) (hgp : g.subject.predicate = s.predicate)
    (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE) :
    directLeaf rec s T q rs ot on rel = true := by
  unfold directLeaf
  rw [if_neg (by simpa using hs), if_neg (by simpa using hsp), Bool.or_eq_true]
  refine Or.inl (List.any_eq_true.mpr ⟨g, hg, ?_⟩)
  have hgpne : g.subject.predicate ≠ BARE := by rw [hgp]; exact hsp
  simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq]
  exact Or.inr ⟨⟨⟨hgstar, hgpne⟩, hgtype⟩, hgp⟩

/-- One userset-star grant is a fuel-1 `sem` membership of its object node, for any
    userset subject of the grant's shape. The base hop when the chain source is the
    `wAny(s.shape)` node (probe 2). -/
theorem semAux_one_of_usStarGrant {S : Schema} {T : Store} {q : Query} {t : Tuple}
    {s : SubjectRef} (hSV : StoreValid S T) (hUS : UsStarStore T) (ht : t ∈ T)
    (htstar : t.subject.name = STAR) (htype : t.subject.type = s.type)
    (htp : t.subject.predicate = s.predicate) (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE) :
    semAux S s T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  show directLeaf (semAux S s T q 0) s T q rs
    t.object.type t.object.name t.relation = true
  refine directLeaf_grant_usStar ?_ htstar htype htp hs hsp
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hUS t ht).1) hrm

/-- **Userset-star-aware userset lifting.** Membership propagates through a userset
    `s'`: if `s ∈ s'` (fuel `f₀`) and `s' ∈ v` (fuel `f`) then `s ∈ v`. Over a
    userset-star store: an intermediate `s'` may match a **userset-star** grant
    directly, and `s` absorbs that via `memberOfGranted`'s `instances`-branch (witness
    `s'.name`, needing `hs'inst`); the plain-userset and flow-through cases are as
    `semAux_lift_os`. This is the semantic heart of W1c soundness. -/
theorem semAux_lift_us {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hPD : PureDirect S) (hUS : UsStarStore T)
    (hs'n : s'.name ≠ STAR) (hs'p : s'.predicate ≠ BARE)
    (hs'inst : s'.name ∈ instances T q s'.type)
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
      rcases directLeaf_elim_us hUS hs'n h' with
        ⟨g, hg, hgs⟩ | ⟨_, g, hg, hgstar, hgtype, hgpred⟩ | hmog
      · -- exact match of s' at g (g plain userset): absorb via s's plain flow-through
        apply directLeaf_of_mog
        refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
        rw [hgs]
        exact semAux_mono S (pureDirect_noExclAll hPD) s T q
          (Nat.le_add_left f₀ f) _ _ _ hmem
      · -- userset-star direct match of s' at g: absorb via s's instances flow-through
        apply directLeaf_of_mog
        have hgpne : g.subject.predicate ≠ BARE := by rw [hgpred]; exact hs'p
        refine mog_intro_star hg hgpne hgstar (inst := s'.name) (by rw [hgtype]; exact hs'inst) ?_
        rw [hgtype, hgpred]
        exact semAux_mono S (pureDirect_noExclAll hPD) s T q
          (Nat.le_add_left f₀ f) _ _ _ hmem
      · -- flow-through of s': the same grant flows for s by the fuel IH
        rcases mog_elim_us hmog with
          ⟨g, hg, hpb, hps, hrec⟩ | ⟨g, hg, hpb, hgstar, inst, hinst, hrec⟩
        · exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))
        · exact directLeaf_of_mog (mog_intro_star hg hpb hgstar hinst (ih _ _ _ hrec))

/-! ## `UsStarReach` — the in-bridge-absorbing membership chain

The soundness half's chain (analog of W1b's `GrantReach`). A hop is a stored grant
(`base`/`hop`, whose source `subjNode t.subject` is *plain* for a concrete-subject
grant or the `w_any` node for a userset-star grant), or a `concrete → w_any`
**in-bridge** (`inbridge`) — the new W1c machinery. Crucially, the in-bridge carries
**no** instance witness: a concrete node reaching a userset-star grant through its
in-bridge always corresponds to that node matching the grant *directly* in `sem` (a
pure shape-match, unconditionally valid), so soundness never needs `instances`. The
instance condition matters only for *completeness* (`reach_of_semAux_us`'s `hib`),
where a `sem` flow-through demands a genuine witness. -/

/-- **The bridge-absorbing membership chain (W1c).** `UsStarReach T n u v`: `u`
    reaches `v` via `n` generalized hops — a stored grant (`base`/`hop`) or a
    `concrete → w_any` in-bridge (`inbridge`). Objects are star-free, so every target
    is a concrete `objNode`; the source `u` may be a plain node or a `w_any` node (a
    userset-star grant's source, or an in-bridge's target). -/
inductive UsStarReach (T : Store) : Nat → NodeKey → NodeKey → Prop where
  | base (t : Tuple) (ht : t ∈ T) :
      UsStarReach T 1 (subjNode t.subject) (objNode t.object t.relation)
  | hop (t : Tuple) (ht : t ∈ T) (hon : t.object.name ≠ STAR) {n : Nat} {v : NodeKey}
      (rest : UsStarReach T n (subjNode ⟨t.object.type, t.object.name, t.relation⟩) v) :
      UsStarReach T (n + 1) (subjNode t.subject) v
  | inbridge (c : SubjectRef) (hcn : c.name ≠ STAR) (hcp : c.predicate ≠ BARE)
      {n : Nat} {v : NodeKey}
      (rest : UsStarReach T n (wAnyNode (c.type, c.predicate)) v) :
      UsStarReach T (n + 1) (subjNode c) v

/-- A star-free subject `s` is *covered* by a chain-start node `u`: `u` is `s`'s own
    plain node, or (if `s` is a userset) the `wAny(s.shape)` node a `[T:*#P]` grant
    emanates from. Generalizes the equality `subjNode s = u` to the leading userset-star
    hop of probe 2 (the userset analog of W1a's `Covers`). -/
def UsCovers (s : SubjectRef) (u : NodeKey) : Prop :=
  u = subjNode s ∨ (s.predicate ≠ BARE ∧ u = wAnyNode s.shape)

/-- One plain-subject tuple is a fuel-1 `sem` membership of its object node (the base
    hop for a concrete-subject grant). -/
theorem semAux_one_of_tuple_us {S : Schema} {T : Store} {q : Query} {t : Tuple}
    (hSV : StoreValid S T) (hUS : UsStarStore T) (ht : t ∈ T)
    (htsub : t.subject.name ≠ STAR) :
    semAux S t.subject T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  show directLeaf (semAux S t.subject T q 0) t.subject T q rs
    t.object.type t.object.name t.relation = true
  refine directLeaf_grant_self ?_ rfl htsub
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hUS t ht).1) hrm

/-- **Base hop.** A grant `t` whose source `subjNode t.subject` *covers* the star-free
    subject `s` is a fuel-1 `sem` membership of its object node for `s`: either
    `s = t.subject` (a plain concrete-subject grant) or `t` is a userset-star grant of
    `s`'s shape (probe-2 leading hop). -/
theorem semAux_one_covers_us {S : Schema} {T : Store} {q : Query} {t : Tuple}
    {s : SubjectRef} (hSV : StoreValid S T) (hUS : UsStarStore T) (ht : t ∈ T)
    (hsn : s.name ≠ STAR) (hcov : UsCovers s (subjNode t.subject)) :
    semAux S s T q 1 t.object.type t.object.name t.relation = true := by
  rcases hcov with hEq | ⟨hsp, hWany⟩
  · -- subjNode t.subject = subjNode s
    by_cases htstar : t.subject.name = STAR
    · rw [subjNode, if_pos htstar, subjNode_plain hsn] at hEq
      simp [NodeKey.mk.injEq] at hEq
    · have hts : t.subject = s := subjNode_inj htstar hsn hEq
      rw [← hts]; exact semAux_one_of_tuple_us hSV hUS ht htstar
  · -- s covers via wAny: subjNode t.subject = wAnyNode s.shape ⇒ t userset-star of s's shape
    have htstar : t.subject.name = STAR := by
      by_contra hne
      rw [subjNode_plain hne, wAnyNode, SubjectRef.shape] at hWany
      simp [NodeKey.mk.injEq] at hWany
    rw [subjNode, if_pos htstar, wAnyNode, SubjectRef.shape] at hWany
    simp only [NodeKey.mk.injEq] at hWany
    obtain ⟨htype, -, htp, -⟩ := hWany
    exact semAux_one_of_usStarGrant hSV hUS ht htstar htype htp hsn hsp

/-! ## `UsStarReach ⇒ sem` — soundness's semantic half -/

/-- **`UsStarReach` is a `sem` membership.** A generalized chain of length `n` from a
    node covering the star-free subject `s` to the concrete query object node is a
    `sem` membership at fuel `n`. Base/hop hops use `semAux_one_covers_us` +
    `semAux_lift_us` (the intermediate userset is a tuple object, hence in `instances`,
    discharging the lift's hypothesis); an in-bridge hop from `c` recognizes `c`
    matching the userset-star grant directly (`UsCovers`'s `wAny` disjunct) and bumps
    fuel by one (`semAux_mono`). The bridge-aware analog of `semAux_of_grantReach`. -/
theorem semAux_of_usStarReach {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T) :
    ∀ {n : Nat} {u v : NodeKey}, UsStarReach T n u v →
      ∀ {s : SubjectRef}, s.name ≠ STAR → UsCovers s u →
      ∀ {ot on r : String}, on ≠ STAR → v = objNode ⟨ot, on⟩ r →
      semAux S s T q n ot on r = true := by
  intro n u v hch
  induction hch with
  | base t ht =>
    intro s hsn hcov ot on r hon hveq
    have htobj : t.object.name ≠ STAR := (hUS t ht).1
    rw [objNode_plain htobj, objNode_plain hon] at hveq
    simp only [NodeKey.mk.injEq] at hveq
    obtain ⟨hot, hon', hr, -⟩ := hveq
    rw [← hot, ← hon', ← hr]
    exact semAux_one_covers_us hSV hUS ht hsn hcov
  | @hop t ht hon' n v rest ih =>
    intro s hsn hcov ot on r hon hveq
    have hmem1 := semAux_one_covers_us (q := q) hSV hUS ht hsn hcov
    have hc'n : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ≠ STAR := hon'
    have hc'p : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate ≠ BARE := by
      obtain ⟨rs, hlk, _⟩ := hSV t ht
      exact lookup_rel_ne_bare hWF hlk
    have hc'inst : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ∈
        instances T q (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).type :=
      objectName_mem_instances ht hon'
    have htail := ih (s := ⟨t.object.type, t.object.name, t.relation⟩) hc'n (Or.inl rfl) hon hveq
    exact semAux_lift_us hPD hUS hc'n hc'p hc'inst hmem1 n ot on r htail
  | @inbridge c hcn hcp n v rest ih =>
    intro s hsn hcov ot on r hon hveq
    have hsc : s = c := by
      rcases hcov with hEq | ⟨_, hWany⟩
      · exact (subjNode_inj hcn hsn hEq).symm
      · exfalso; rw [subjNode_plain hcn, wAnyNode, SubjectRef.shape] at hWany
        simp [NodeKey.mk.injEq] at hWany
    subst hsc
    have hcov2 : UsCovers s (wAnyNode (s.type, s.predicate)) :=
      Or.inr ⟨hcp, by rw [SubjectRef.shape]⟩
    have htail := ih (s := s) hsn hcov2 hon hveq
    exact semAux_mono S (pureDirect_noExclAll hPD) s T q (Nat.le_succ n) _ _ _ htail

/-! ## `trail ⇒ UsStarReach` — soundness's reachability half -/

/-- **Every graph trail from a plain-or-`wAny` node to a concrete node is a
    `UsStarReach`.** Strong induction on the trail length: classify each first edge via
    the edge characterization — a **grant** (`base`/`hop`, the object node continuing as
    a userset subject), an **out-bridge** (source `w_all`, impossible from a plain/`wAny`
    node), or an **in-bridge** (`inbridge`, `c → w_any`, continuing from the `w_any`
    node). A path terminating on a `w_any` node is excluded because the target is a
    concrete (plain) node. No fuel bound is threaded here (the tight bound — where a
    userset-star grant's source is `w_any`, not plain — is the deferred assembly
    increment). -/
theorem usStarReach_of_trail {σ : GraphState} {S : Schema} {T : Store}
    (h : UsStarReached σ S T) (hUS : UsStarStore T) :
    ∀ (k : Nat) (l : List NodeKey), l.length ≤ k →
      ∀ (u v : NodeKey),
        (u.variant = Variant.plain ∨ u.variant = Variant.wAny) →
        v.variant = Variant.plain →
        Trail σ.edges u v l →
        ∃ m, UsStarReach T m u v := by
  have hchar := usStarReached_grant_or_bridge h
  intro k
  induction k with
  | zero =>
    intro l hlen u v hu hv ht
    cases l with
    | cons x xs => simp only [List.length_cons] at hlen; omega
    | nil =>
      have hedge : (u, v) ∈ σ.edges := ht
      rcases hchar u v hedge with ⟨t, htT, h1, h2⟩ | ⟨hout, _, _⟩ | ⟨hin, _, _, _⟩
      · subst h1; subst h2; exact ⟨1, UsStarReach.base t htT⟩
      · exfalso; rw [hout] at hu; rcases hu with h | h <;> simp [wAllNode] at h
      · exfalso; rw [hin] at hv; simp [wAnyNode] at hv
  | succ k ih =>
    intro l hlen u v hu hv ht
    cases l with
    | nil =>
      have hedge : (u, v) ∈ σ.edges := ht
      rcases hchar u v hedge with ⟨t, htT, h1, h2⟩ | ⟨hout, _, _⟩ | ⟨hin, _, _, _⟩
      · subst h1; subst h2; exact ⟨1, UsStarReach.base t htT⟩
      · exfalso; rw [hout] at hu; rcases hu with h | h <;> simp [wAllNode] at h
      · exfalso; rw [hin] at hv; simp [wAnyNode] at hv
    | cons x xs =>
      obtain ⟨hfst, htail⟩ := ht
      have hlen' : xs.length ≤ k := by simp only [List.length_cons] at hlen; omega
      rcases hchar u x hfst with ⟨t, htT, h1, h2⟩ | ⟨hout, _, _⟩ | ⟨hin, hcv, hcn, hcp⟩
      · -- grant u → x
        subst h1
        have htobj : t.object.name ≠ STAR := (hUS t htT).1
        have hx : x = subjNode ⟨t.object.type, t.object.name, t.relation⟩ := by
          rw [h2]; exact objNode_eq_subjNode htobj
        have hxvar : (subjNode (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef)).variant
            = Variant.plain := by rw [subjNode_plain htobj]
        rw [hx] at htail
        obtain ⟨m, hm⟩ := ih xs hlen' _ v (Or.inl hxvar) hv htail
        exact ⟨m + 1, UsStarReach.hop t htT htobj hm⟩
      · -- out-bridge u → x: source w_all, contradicts hu
        exfalso; rw [hout] at hu; rcases hu with h | h <;> simp [wAllNode] at h
      · -- in-bridge u → x: x = wAny(u.type,u.pred), u plain concrete
        have hxwany : x.variant = Variant.wAny := by rw [hin]; rfl
        obtain ⟨m, hm⟩ := ih xs hlen' x v (Or.inr hxwany) hv htail
        have hueq : u = subjNode ⟨u.type, u.name, u.pred⟩ := by
          rw [subjNode_plain (s := ⟨u.type, u.name, u.pred⟩) hcn, ← hcv]
        rw [hueq]
        rw [hin] at hm
        exact ⟨m + 1, UsStarReach.inbridge ⟨u.type, u.name, u.pred⟩ hcn hcp hm⟩

end Zanzibar
