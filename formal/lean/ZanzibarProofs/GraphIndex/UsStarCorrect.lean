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

end Zanzibar
