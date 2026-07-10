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
    ∨ (∃ c, e = (c, wAnyNode (c.type, c.pred)) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR) := by
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
    · obtain ⟨hv, hn, _, _⟩ := bridgedInConcrete_elim hbc
      exact Or.inr (Or.inr ⟨_, heq, hv, hn⟩)
  · obtain ⟨hv, hn, _, _⟩ := bridgedInConcrete_elim hbc
    exact Or.inr (Or.inr ⟨_, heq, hv, hn⟩)

/-- `writeUsStar`'s edge effect: an edge of `σ.writeUsStar t` is an old edge, the grant
    edge `(subjNode t.subject, objNode t.object t.relation)`, an out-bridge, or an
    in-bridge. -/
theorem writeUsStar_edges_mem {σ : GraphState} {t : Tuple} {e : NodeKey × NodeKey}
    (he : e ∈ (σ.writeUsStar t).edges) :
    e ∈ σ.edges
    ∨ e = (subjNode t.subject, objNode t.object t.relation)
    ∨ (∃ c, e = (wAllNode c.type c.pred, c) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR)
    ∨ (∃ c, e = (c, wAnyNode (c.type, c.pred)) ∧ c.variant = Variant.plain ∧ c.name ≠ STAR) := by
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
      ∨ (b = wAnyNode (a.type, a.pred) ∧ a.variant = Variant.plain ∧ a.name ≠ STAR) := by
  induction h with
  | empty S => intro a b hab; simp [emptyState] at hab
  | @step σ S T t hprev ih =>
    intro a b hab
    rcases writeUsStar_edges_mem hab with hold | hgrant | ⟨c, hc, hcv, hcn⟩ | ⟨c, hc, hcv, hcn⟩
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
      exact Or.inr (Or.inr ⟨hb, hcv, hcn⟩)

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

end Zanzibar
