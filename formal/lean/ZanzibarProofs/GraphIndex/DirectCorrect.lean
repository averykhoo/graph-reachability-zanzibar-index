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

/-- A pure-direct schema is trivially stratifiable (no tainted keys: Kahn on the
    empty node set succeeds immediately). Supplies `setEngine_correct`'s
    hypothesis in the fragment corollaries (T3/T6). -/
theorem stratifiable_pureDirect {S : Schema} (h : PureDirect S) : Stratifiable S := by
  unfold Stratifiable stratify
  rw [taintedKeys_pureDirect h]
  simp [kahn]

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

/-! ## The userset-lifting lemma — the semantic heart of T2b

Membership propagates through a userset: if `s ∈ s'` (the userset, as a node) and
`s' ∈ v`, then `s ∈ v`. By fuel induction: every **direct match** of `s'` at a
grant `g` (`g.subject = s'`) is absorbed by `s`'s `memberOfGranted` flow-through
on the *same* grant — `g`'s userset node IS `s'`'s node, answered by `hmem` plus
fuel monotonicity; and every **flow-through** of `s'` is a flow-through of `s` by
the fuel IH. This is exactly why consecutive chain hops sharing a node
(`objNode = subjNode`, the flow-through identity) compose into `sem` membership. -/

theorem semAux_lift {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hPD : PureDirect S) (hSF : StarFreeStore T)
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
      rcases directLeaf_elim hSF hs'n h' with ⟨g, hg, hgs⟩ | hmog
      · -- direct match of s' at g: absorb via s's flow-through on the same g
        apply directLeaf_of_mog
        refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
        rw [hgs]
        exact semAux_mono S (pureDirect_noExclAll hPD) s T q
          (Nat.le_add_left f₀ f) _ _ _ hmem
      · -- flow-through of s': the same grant flows for s by the fuel IH
        obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim hSF hmog
        exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))

/-! ## Soundness: a membership chain is a `sem` membership -/

/-- One stored tuple is a fuel-1 `sem` membership of its own object node (the
    chain's base hop: a direct self-grant, no recursion). -/
theorem semAux_one_of_tuple {S : Schema} {T : Store} {q : Query} {t : Tuple}
    (hSV : StoreValid S T) (hSF : StarFreeStore T) (ht : t ∈ T) :
    semAux S t.subject T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨rs, hlk, hrm⟩ := hSV t ht
  rw [semAux, step]
  rw [hlk]
  show directLeaf (semAux S t.subject T q 0) t.subject T q rs
    t.object.type t.object.name t.relation = true
  refine directLeaf_grant_self ?_ rfl (hSF t ht).1
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hSF t ht).2) hrm

/-- **Soundness core.** A length-`n` membership chain from `subjNode s` to
    `objNode ⟨ot, on⟩ r` is a `sem` membership at fuel `n` — by chain induction:
    the base hop is a self-grant (`semAux_one_of_tuple`), and each further hop
    lifts through its userset (`semAux_lift` with `f₀ = 1`). -/
theorem semAux_of_chainN {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T)
    (hSF : StarFreeStore T) :
    ∀ {n : Nat} {u v : NodeKey}, TupleChainN T n u v →
      ∀ {s : SubjectRef}, s.name ≠ STAR → subjNode s = u →
      ∀ {ot on r : String}, on ≠ STAR → objNode ⟨ot, on⟩ r = v →
      semAux S s T q n ot on r = true := by
  intro n u v hchain
  induction hchain with
  | single t ht =>
    intro s hsn hsu ot on r hon hov
    have hs' : s = t.subject := subjNode_inj hsn (hSF t ht).1 hsu
    subst hs'
    obtain ⟨hobj, hrel⟩ := objNode_inj hon (hSF t ht).2 hov
    subst hrel
    have h1 := semAux_one_of_tuple (q := q) hSV hSF ht
    rw [← hobj] at h1
    exact h1
  | @cons t ht n v rest ih =>
    intro s hsn hsu ot on r hon hov
    have hs' : s = t.subject := subjNode_inj hsn (hSF t ht).1 hsu
    subst hs'
    -- the userset subject sitting at t's object node
    have hs'n : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ≠ STAR :=
      (hSF t ht).2
    have hs'p : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate ≠ BARE := by
      obtain ⟨rs, hlk, _⟩ := hSV t ht
      exact lookup_rel_ne_bare hWF hlk
    have hsub : subjNode (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef) =
        objNode t.object t.relation :=
      (objNode_eq_subjNode (hSF t ht).2).symm
    have hmem1 : semAux S t.subject T q 1
        (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).type
        (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name
        (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate = true :=
      semAux_one_of_tuple hSV hSF ht
    exact semAux_lift hPD hSF hs'n hs'p hmem1 n ot on r (ih hs'n hsub hon hov)

/-! ## Completeness: a `sem` membership is graph reachability -/

/-- **Completeness core.** By fuel induction: a direct match contributes the
    grant's own materialized edge (edge-completeness), and a flow-through
    prepends the recursion's path via the `objNode = subjNode` identity. -/
theorem nreaches_of_semAux {S : Schema} {T : Store} {q : Query} {σ : GraphState}
    (hPD : PureDirect S) (hSF : StarFreeStore T)
    (hEC : ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges)
    {s : SubjectRef} (hs : s.name ≠ STAR) :
    ∀ (f : Nat) (ot on r : String), semAux S s T q f ot on r = true →
      NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r) := by
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
      rcases directLeaf_elim hSF hs h' with ⟨g, hg, hgs⟩ | hmog
      · -- direct match: the grant's own edge
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hSF g hgT).2
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        rw [hobj, hgrel, hgs] at hedge
        exact NReaches.edge hedge
      · -- flow-through: recursion's path, extended by the grant's edge
        obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim hSF hmog
        obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
        have hmid := ih _ _ _ hrec
        rw [objNode_eq_subjNode hps] at hmid
        have hedge := hEC g hgT
        have hgon' : g.object.name = on := matchingObjects_elim hgon (hSF g hgT).2
        have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
        rw [hobj, hgrel] at hedge
        exact hmid.tail hedge

/-! ## Wildcard probes are dead on star-free data -/

/-- Every edge endpoint of an admitted star-free state is a plain node. -/
theorem admitted_edges_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByAdmitted σ S T) (hSF : StarFreeStore T) :
    ∀ e ∈ σ.edges, e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain := by
  intro e he
  obtain ⟨t, htT, h1, h2⟩ :=
    reachedByDirect_edge_sound (reachedByDirect_of_admitted h) e.1 e.2 he
  constructor
  · rw [h1, subjNode_plain (hSF t htT).1]
  · rw [h2, objNode_plain (hSF t htT).2]

/-- A path's source node is an edge source. -/
theorem nreaches_source_plain {edges : List (NodeKey × NodeKey)}
    (hpl : ∀ e ∈ edges, e.1.variant = Variant.plain) {u v : NodeKey}
    (hr : NReaches edges u v) : u.variant = Variant.plain := by
  cases hr with
  | edge he => exact hpl _ he
  | head he _ => exact hpl _ he

/-- A path's target node is an edge target. -/
theorem nreaches_target_plain {edges : List (NodeKey × NodeKey)}
    (hpl : ∀ e ∈ edges, e.2.variant = Variant.plain) {u v : NodeKey}
    (hr : NReaches edges u v) : v.variant = Variant.plain := by
  induction hr with
  | edge he => exact hpl _ he
  | head _ _ ih => exact ih

/-! ## T2b on the fragment, assembled -/

/-- **T2b, star-free pure-direct fragment (a genuine end-to-end instance).**
    On any state reached by admitted untainted writes of an admission-valid,
    star-free store, the graph read answers exactly the specification, for every
    star-free query. Soundness routes probe 1 through `reach ↔ NReaches`, trail
    compression, `TupleChainN`, and the chain⇒`sem` induction (fuel fits
    `fuelBound`); completeness routes `sem` back through `nreaches_of_semAux`
    and `reach_complete`. The wildcard probes 2–4 are dead (star-free data
    materializes no `wAny`/`wAll` endpoint). -/
theorem graph_correct_direct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hInv : Inv S σ := (reachedByDirect_inv (reachedByDirect_of_admitted hReach)).1
  have hcl := hInv.edgesClosed
  have hplain := admitted_edges_plain hReach hSF
  -- the read routes to the non-derived probe (pure-direct = untainted)
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
    unfold GraphModel.check
    rw [hInv.schemaEq, isDerived_pureDirect hPD]
    simp
  -- the wildcard probes are dead
  have hpAny : ∀ v, σ.reach (wAnyNode q.subject.shape) v = false := by
    intro v
    cases hcase : σ.reach (wAnyNode q.subject.shape) v with
    | false => rfl
    | true =>
      exfalso
      have hsrc := nreaches_source_plain (fun e he => (hplain e he).1) (reach_sound hcase)
      simp [wAnyNode] at hsrc
  have hpAll : ∀ u, σ.reach u (wAllNode q.object.type q.relation) = false := by
    intro u
    cases hcase : σ.reach u (wAllNode q.object.type q.relation) with
    | false => rfl
    | true =>
      exfalso
      have htgt := nreaches_target_plain (fun e he => (hplain e he).2) (reach_sound hcase)
      simp [wAllNode] at htgt
  have hprobe : GraphModel.probeNonDerived σ q =
      σ.reach (subjNode q.subject) (objNode q.object q.relation) := by
    unfold GraphModel.probeNonDerived
    simp [hpAny, hpAll]
  -- forward: a probe hit is a sem membership
  have hfwd : σ.reach (subjNode q.subject) (objNode q.object q.relation) = true →
      sem S T q = true := by
    intro hr
    obtain ⟨l, hl⟩ := trail_of_nreaches (reach_sound hr)
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
    have hsem := semAux_of_chainN (q := q) hWF hPD hSV hSF hchain hqs rfl hqo rfl
    unfold sem
    exact semAux_mono S (pureDirect_noExclAll hPD) q.subject T q hfb _ _ _ hsem
  -- backward: a sem membership is a probe hit
  have hbwd : sem S T q = true →
      σ.reach (subjNode q.subject) (objNode q.object q.relation) = true := by
    intro hsem
    unfold sem at hsem
    have hnr := nreaches_of_semAux hPD hSF (admitted_edge_complete hReach) hqs
      _ _ _ _ hsem
    exact reach_complete hcl hnr
  rw [hroute, hprobe]
  cases hrch : σ.reach (subjNode q.subject) (objNode q.object q.relation) with
  | true => exact (hfwd hrch).symm
  | false =>
    cases hsem : sem S T q with
    | false => rfl
    | true => exact absurd (hbwd hsem) (by simp [hrch])

end Zanzibar
