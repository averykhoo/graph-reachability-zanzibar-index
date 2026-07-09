import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.Spec.FuelStable

/-!
# T2b on the star-free pure-direct fragment — `graph_correct_direct`

`SEMANTICS.md` §7.5, §8 (T2b); ROADMAP "Plan of record (2026-07-10)".

The abstract `graph_correct` is FALSE as stated (the thin `WriteStep` admits junk
states — see ROADMAP). This file proves the genuine read = `sem` correspondence on
the first honest fragment where the operational write model (`Write.lean`) is
faithful end-to-end:

* **pure-direct schema** (`PureDirect`): every definition is a `Direct` leaf — no
  boolean structure, no `computed`, no TTU. Such a schema is untainted
  (`isDerived_pureDirect`), so the read routes to `probeNonDerived`.
* **admission-valid store** (`StoreValid`): each stored tuple's
  `(object.type, relation)` is declared and its subject matches a restriction —
  the Python write-admission gate (`validate_write_identifiers` + leaf routing).
* **star-free data/query** (`StarFreeStore`, `q.*.name ≠ STAR`): wildcards need
  materialized `*` bridges, which the write model does not build yet (the read-side
  `wAny`/`wAll` promotion only covers the *first* hop). Deferred extension.
* **admitted writes** (`ReachedByAdmitted`): every write passed cycle-rejection.
  Faithful to the composed system: a rejected write raises and rolls back the
  store insert too, so a real store never holds a rejected tuple.

The semantic core is the **userset-lifting lemma** (`semAux_lift`): membership
propagates through a userset — if `s ∈ s'` and `s' ∈ v` then `s ∈ v` — because
every direct-match of `s'` at a grant is absorbed by `s`'s `memberOfGranted`
flow-through on the same grant. Chains (`TupleChainN`) then map to `sem` by
induction (soundness), and `sem` maps to graph reachability by fuel induction
(completeness), giving `graph_correct_direct`.
-/

namespace Zanzibar

/-! ## The fragment predicates -/

/-- Every definition of the schema is a bare `Direct` leaf. -/
def PureDirect (S : Schema) : Prop :=
  ∀ p ∈ S.defs, ∃ rs, p.2 = Expr.direct rs

/-- Admission-validity of the store against the schema: each tuple's
    `(object.type, relation)` is a declared `Direct` leaf whose restrictions the
    tuple's subject matches. This is the Python write-admission gate. -/
def StoreValid (S : Schema) (T : Store) : Prop :=
  ∀ t ∈ T, ∃ rs, S.lookup (t.object.type, t.relation) = some (Expr.direct rs) ∧
    restrictionMatches rs t = true

/-- No wildcard names anywhere in the store. -/
def StarFreeStore (T : Store) : Prop :=
  ∀ t ∈ T, t.subject.name ≠ STAR ∧ t.object.name ≠ STAR

/-- A successful lookup lands on a `Direct` leaf (pure-direct schema). -/
theorem pureDirect_lookup {S : Schema} (h : PureDirect S) {k : Key} {e : Expr}
    (hlk : S.lookup k = some e) : ∃ rs, e = Expr.direct rs := by
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    rw [hf] at hlk
    simp only [Option.map_some, Option.some.injEq] at hlk
    obtain ⟨rs, hrs⟩ := h p (List.mem_of_find?_eq_some hf)
    exact ⟨rs, hlk ▸ hrs⟩

/-- A pure-direct schema is exclusion-free (so `semAux` is fuel-monotone on it). -/
theorem pureDirect_noExclAll {S : Schema} (h : PureDirect S) : S.noExclAll := by
  intro k e hlk
  obtain ⟨rs, rfl⟩ := pureDirect_lookup h hlk
  trivial

/-- A declared relation name is never the `BARE` sentinel (`WF.relNames`: declared
    names contain no `'.'`, and `BARE = "..."`). -/
theorem lookup_rel_ne_bare {S : Schema} (hWF : WF S) {a b : String} {e : Expr}
    (hlk : S.lookup (a, b) = some e) : b ≠ BARE := by
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = (a, b)) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    have hkey : p.1 = (a, b) := by
      have := List.find?_some hf
      simpa using this
    have hok := hWF.relNames p (List.mem_of_find?_eq_some hf)
    rw [hkey] at hok
    intro hb
    exact hok (hb ▸ (by simp [BARE, String.contains] : (BARE).contains '.' = true))

/-- A successful lookup implies the schema declares at least one key. -/
theorem lookup_keys_nonempty {S : Schema} {k : Key} {e : Expr}
    (hlk : S.lookup k = some e) : 1 ≤ S.keys.length := by
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    have hp := List.mem_of_find?_eq_some hf
    have hlen : 0 < S.defs.length := List.length_pos_of_mem hp
    have hkeys : S.keys.length = S.defs.length := by simp [Schema.keys]
    omega

/-! ## Pure-direct schemas are untainted -/

/-- One taint round from the empty set stalls: nothing is base-tainted (every
    definition is a boolean-free `Direct` leaf) and nothing references a tainted
    key (the set is empty). -/
theorem taintStep_pureDirect {S : Schema} (h : PureDirect S) :
    taintStep S [] = [] := by
  unfold taintStep
  rw [List.filter_eq_nil_iff]
  intro k hk
  have hbase : baseTaint S k = false := by
    unfold baseTaint
    cases hlk : S.lookup k with
    | none => rfl
    | some e =>
      obtain ⟨rs, rfl⟩ := pureDirect_lookup h hlk
      rfl
  simp [hbase]

/-- Iterating from a fixpoint stays there. -/
theorem iterate_fixed {α : Type} {f : α → α} {x : α} (hx : f x = x) :
    ∀ n, iterate f n x = x := by
  intro n
  induction n with
  | zero => rfl
  | succ n ih => rw [iterate, hx]; exact ih

/-- A pure-direct schema has no tainted keys. -/
theorem taintedKeys_pureDirect {S : Schema} (h : PureDirect S) :
    taintedKeys S = [] := by
  unfold taintedKeys
  cases hn : S.keys.length with
  | zero => rfl
  | succ n =>
    rw [iterate, taintStep_pureDirect h]
    exact iterate_fixed (taintStep_pureDirect h) n

/-- No relation of a pure-direct schema is derived: the read routes to
    `probeNonDerived`. -/
theorem isDerived_pureDirect {S : Schema} (h : PureDirect S) (k : Key) :
    isDerived S k = false := by
  unfold isDerived
  rw [taintedKeys_pureDirect h]
  rfl

/-! ## Star-free node keys: plain forms, injectivity -/

/-- A star-free subject's node is the plain key. -/
theorem subjNode_plain {s : SubjectRef} (h : s.name ≠ STAR) :
    subjNode s = ⟨s.type, s.name, s.predicate, Variant.plain⟩ := by
  unfold subjNode; rw [if_neg h]

/-- A star-free object's node is the plain key. -/
theorem objNode_plain {o : ObjectRef} {R : String} (h : o.name ≠ STAR) :
    objNode o R = ⟨o.type, o.name, R, Variant.plain⟩ := by
  unfold objNode; rw [if_neg h]

/-- On star-free subjects, `subjNode` is injective. -/
theorem subjNode_inj {s s' : SubjectRef} (hs : s.name ≠ STAR) (hs' : s'.name ≠ STAR)
    (h : subjNode s = subjNode s') : s = s' := by
  rw [subjNode_plain hs, subjNode_plain hs'] at h
  cases s; cases s'
  simpa using h

/-- On star-free objects, `objNode` is injective in the pair `(object, relation)`. -/
theorem objNode_inj {o o' : ObjectRef} {R R' : String} (ho : o.name ≠ STAR)
    (ho' : o'.name ≠ STAR) (h : objNode o R = objNode o' R') : o = o' ∧ R = R' := by
  rw [objNode_plain ho, objNode_plain ho'] at h
  cases o; cases o'
  simp only [NodeKey.mk.injEq] at h
  exact ⟨by simp [h.1, h.2.1], h.2.2.1⟩

/-- The userset flow-through node identity: a star-free `(type, name)` carrying
    relation `p` is the same node whether reached as an *object* (`objNode`) or
    left as a userset *subject* (`subjNode`). This is what makes consecutive chain
    hops compose. -/
theorem objNode_eq_subjNode {ty nm p : String} (h : nm ≠ STAR) :
    objNode ⟨ty, nm⟩ p = subjNode ⟨ty, nm, p⟩ := by
  rw [objNode_plain (o := ⟨ty, nm⟩) h, subjNode_plain (s := ⟨ty, nm, p⟩) h]

/-! ## The admitted-writes closure

`ReachedByDirect` (Write.lean) silently no-ops a rejected write while still
prepending the tuple to the store — faithful to `writeDirect` alone, but not to
the composed system, where the raised rejection rolls back the store insert too.
`ReachedByAdmitted` is the composed-system closure: every write passed the
cycle-rejection admission probe. On it the edge set is *complete* for the store
(`admitted_edge_complete`), which the read-completeness direction of T2b needs. -/

/-- `σ` is reached from empty by admitted (`admitEdge = true`) direct writes. -/
inductive ReachedByAdmitted : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByAdmitted (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hprev : ReachedByAdmitted σ S T)
      (hadm : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true) :
      ReachedByAdmitted (σ.writeDirect t) S (t :: T)

/-- Admitted writes are a special case of the untainted write-closure. -/
theorem reachedByDirect_of_admitted {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) : ReachedByDirect σ S T := by
  induction h with
  | empty S => exact ReachedByDirect.empty S
  | step t _ _ ih => exact ReachedByDirect.step t ih

/-- **Edge-completeness.** Every stored tuple's materialized edge is present —
    the converse of `reachedByDirect_edge_sound`, available exactly because no
    write was rejected. -/
theorem admitted_edge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) :
    ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges := by
  induction h with
  | empty S => intro t ht; simp at ht
  | step t _ hadm ih =>
    intro t' ht'
    rw [writeDirect_edges, if_pos hadm]
    rcases List.mem_cons.mp ht' with rfl | hmem
    · exact List.mem_cons_self
    · exact List.mem_cons_of_mem _ (ih t' hmem)

/-- An admitted write adds exactly two endpoint nodes, so the node count is
    `2·|T|` — this is what bounds the compressed chain length under `fuelBound`. -/
theorem admitted_nodes_length {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) : σ.nodes.length = 2 * T.length := by
  induction h with
  | empty S => rfl
  | step t _ hadm ih =>
    unfold GraphState.writeDirect
    simp only [hadm, if_true, addEdge_nodes, addNode_nodes, List.length_cons, ih,
      List.length_cons]
    omega

/-! ## Length-indexed membership chains -/

/-- A stored-tuple membership chain of length `n` (its hop count): `TupleChain`
    with the length exposed, so the soundness induction can hand `sem` an explicit
    fuel. -/
inductive TupleChainN (T : Store) : Nat → NodeKey → NodeKey → Prop where
  | single (t : Tuple) (ht : t ∈ T) :
      TupleChainN T 1 (subjNode t.subject) (objNode t.object t.relation)
  | cons (t : Tuple) (ht : t ∈ T) {n : Nat} {v : NodeKey}
      (rest : TupleChainN T n (objNode t.object t.relation) v) :
      TupleChainN T (n + 1) (subjNode t.subject) v

/-- A trail over tuple-materialized edges is a membership chain, of length the
    trail's edge count. -/
theorem chainN_of_trail {edges : List (NodeKey × NodeKey)} {T : Store}
    (hsound : ∀ a b, (a, b) ∈ edges →
      ∃ t ∈ T, a = subjNode t.subject ∧ b = objNode t.object t.relation) :
    ∀ (l : List NodeKey) (u v : NodeKey), Trail edges u v l →
      TupleChainN T (l.length + 1) u v := by
  intro l
  induction l with
  | nil =>
    intro u v ht
    obtain ⟨t, htT, rfl, rfl⟩ := hsound u v ht
    exact TupleChainN.single t htT
  | cons x xs ih =>
    intro u v ht
    obtain ⟨hux, htail⟩ := ht
    obtain ⟨t, htT, rfl, rfl⟩ := hsound u x hux
    exact TupleChainN.cons t htT (ih _ v htail)

/-- A chain contains at least one stored tuple (whose lookup pins the schema
    non-empty, for the `fuelBound` arithmetic). -/
theorem chainN_mem {T : Store} {n : Nat} {u v : NodeKey}
    (h : TupleChainN T n u v) : ∃ t, t ∈ T := by
  cases h with
  | single t ht => exact ⟨t, ht⟩
  | cons t ht _ => exact ⟨t, ht⟩

/-! ## Grant-set and leaf lemmas

The `directLeaf`/`memberOfGranted` interface the two directions of the
correspondence share: membership/decomposition of `grantsOf`, introducing a leaf
answer from a self-grant or a flow-through, and eliminating a leaf answer into
one of the two. -/

/-- Unpack membership in a grant set. -/
theorem grantsOf_elim {T : Store} {rs : List Restriction} {ot on rel : String}
    {g : Tuple} (hg : g ∈ grantsOf T rs ot on rel) :
    g ∈ T ∧ g.relation = rel ∧ g.object.type = ot ∧
      (matchingObjects on).contains g.object.name = true ∧
      restrictionMatches rs g = true := by
  unfold grantsOf at hg
  obtain ⟨hT, hcond⟩ := List.mem_filter.mp hg
  simp only [Bool.and_eq_true, beq_iff_eq] at hcond
  exact ⟨hT, hcond.1.1.1, hcond.1.1.2, hcond.1.2, hcond.2⟩

/-- Pack membership in a grant set. -/
theorem grantsOf_intro {T : Store} {rs : List Restriction} {ot on rel : String}
    {g : Tuple} (hT : g ∈ T) (h1 : g.relation = rel) (h2 : g.object.type = ot)
    (h3 : (matchingObjects on).contains g.object.name = true)
    (h4 : restrictionMatches rs g = true) : g ∈ grantsOf T rs ot on rel := by
  unfold grantsOf
  refine List.mem_filter.mpr ⟨hT, ?_⟩
  simp only [Bool.and_eq_true, beq_iff_eq]
  exact ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩

/-- A star-free name matched by `matchingObjects on` is `on` itself. -/
theorem matchingObjects_elim {on nm : String}
    (h : (matchingObjects on).contains nm = true) (hnm : nm ≠ STAR) : nm = on := by
  unfold matchingObjects at h
  by_cases ho : on = STAR
  · rw [if_pos ho] at h
    simp only [List.contains_cons, List.contains_nil, Bool.or_false, beq_iff_eq] at h
    exact absurd h hnm
  · rw [if_neg ho] at h
    simp only [List.contains_cons, List.contains_nil, Bool.or_false, Bool.or_eq_true,
      beq_iff_eq] at h
    rcases h with h | h
    · exact h
    · exact absurd h hnm

/-- A concrete name is matched by its own `matchingObjects`. -/
theorem matchingObjects_self (on : String) (h : on ≠ STAR) :
    (matchingObjects on).contains on = true := by
  unfold matchingObjects
  rw [if_neg h]
  simp

/-- **Leaf introduction, self-grant.** A grant whose subject IS the (star-free)
    query subject answers the leaf positively — for any `rec`. -/
theorem directLeaf_grant_self {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} {g : Tuple}
    (hg : g ∈ grantsOf T rs ot on rel) (hsubj : g.subject = s) (hs : s.name ≠ STAR) :
    directLeaf rec s T q rs ot on rel = true := by
  subst hsubj
  unfold directLeaf
  rw [if_neg (by simpa using hs)]
  by_cases hp : (g.subject.predicate == BARE) = true
  · rw [if_pos hp, Bool.or_eq_true]
    refine Or.inl (List.any_eq_true.mpr ⟨g, hg, ?_⟩)
    simp [hs, hp]
  · rw [if_neg hp, Bool.or_eq_true]
    refine Or.inl (List.any_eq_true.mpr ⟨g, hg, ?_⟩)
    have hp' : g.subject.predicate ≠ BARE := by simpa using hp
    simp [hs, hp']

/-- **Leaf introduction, flow-through.** A positive `memberOfGranted` answers the
    leaf positively for any subject (every branch of `directLeaf` carries the
    flow-through disjunct). -/
theorem directLeaf_of_mog {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String}
    (h : memberOfGranted rec T q (grantsOf T rs ot on rel) = true) :
    directLeaf rec s T q rs ot on rel = true := by
  unfold directLeaf
  by_cases h1 : (s.name == STAR) = true
  · rw [if_pos h1]; simp [h]
  · rw [if_neg h1]
    by_cases h2 : (s.predicate == BARE) = true
    · rw [if_pos h2]; simp [h]
    · rw [if_neg h2]; simp [h]

/-- **Flow-through introduction.** A userset grant (star-free, non-bare subject)
    whose userset node `rec` answers positively makes `memberOfGranted` positive. -/
theorem mog_intro {rec : Rec} {T : Store} {q : Query} {grants : List Tuple}
    {g : Tuple} (hg : g ∈ grants) (hpb : g.subject.predicate ≠ BARE)
    (hps : g.subject.name ≠ STAR)
    (hrec : rec g.subject.type g.subject.name g.subject.predicate = true) :
    memberOfGranted rec T q grants = true := by
  unfold memberOfGranted
  refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
  rw [if_neg (by simpa using hpb), if_pos (by simpa using hps)]
  exact hrec

/-- **Flow-through elimination** (star-free store): a positive `memberOfGranted`
    exhibits a userset grant whose node `rec` answers positively — the star
    (`instances`) branch cannot fire. -/
theorem mog_elim {rec : Rec} {T : Store} {q : Query} {rs : List Restriction}
    {ot on rel : String} (hSF : StarFreeStore T)
    (h : memberOfGranted rec T q (grantsOf T rs ot on rel) = true) :
    ∃ g ∈ grantsOf T rs ot on rel, g.subject.predicate ≠ BARE ∧
      g.subject.name ≠ STAR ∧
      rec g.subject.type g.subject.name g.subject.predicate = true := by
  unfold memberOfGranted at h
  obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
  have hstar : g.subject.name ≠ STAR := (hSF g (grantsOf_elim hg).1).1
  by_cases hpb : (g.subject.predicate == BARE) = true
  · rw [if_pos hpb] at hgt; exact absurd hgt (by simp)
  · rw [if_neg hpb, if_pos (by simpa using hstar)] at hgt
    exact ⟨g, hg, by simpa using hpb, hstar, hgt⟩

/-- **Direct-match elimination** (star-free store and subject): a positive
    match-disjunct of `directLeaf`'s bare/userset branch exhibits a grant whose
    subject IS the query subject. Stated over the two concrete `any`-predicates
    `directLeaf` uses. -/
theorem directLeaf_elim {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hSF : StarFreeStore T)
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
      have hgstar : g.subject.name ≠ STAR := (hSF g (grantsOf_elim hg).1).1
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
      have hgstar : g.subject.name ≠ STAR := (hSF g (grantsOf_elim hg).1).1
      refine Or.inl ⟨g, hg, ?_⟩
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq,
        beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩ | ⟨⟨⟨h1, _⟩, _⟩, _⟩
      · simp_all
      · exact absurd h1 hgstar
    · exact Or.inr h

end Zanzibar
