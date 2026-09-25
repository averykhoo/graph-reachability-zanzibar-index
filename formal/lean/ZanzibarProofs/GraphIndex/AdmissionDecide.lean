import ZanzibarProofs.GraphIndex.FragmentDecide

/-!
# `GraphAdmission` is decidable — the other half of the headline premise (`TK104`)

Every headline theorem takes `(hA : GraphAdmission S T) (hF : W4Fragment S T)`.
`FragmentDecide.lean` (`DW-1`) decided the second bundle; this module decides the first, so
the WHOLE premise can be asked of a concrete `(S, T)`:

* `graphAdmissionB S T : Bool` with the EXACT equivalence
  `graphAdmissionB_iff : graphAdmissionB S T = true ↔ GraphAdmission S T` (soundness and
  completeness), hence `instance : Decidable (GraphAdmission S T)`;
* `graphAdmissionFieldsB` — the same fourteen conjuncts BY FIELD NAME, in declaration order;
* `headlinePremiseB_iff : headlinePremiseB S T = true ↔ GraphAdmission S T ∧ W4Fragment S T`.

The field-by-field sizing that preceded this module
(`docs/tk104-graphadmission-scope-2026-09-24.md` §0) found ten fields LOUD in Python, two
MIXED but shadowed by `W4Fragment`, and two SILENT (`matchDecl`, `ranked`). This decider is
what a Python report of the two SILENT fields gets differential-pinned to.

## The one real proof: `RewriteRanked`

`RulesSaturate.lean::RewriteRanked S` is `∃ rrank, (∀ r ∈ schemaRewrites S, rrank (match) <
rrank (out)) ∧ ∀ k, rrank k ≤ |S.keys|` — an existential over functions on ALL string pairs.
It is decided by constructing a CANONICAL candidate and checking it:

* `rkF rules n k` is the longest rule-walk of length `≤ n` that ENDS at `k`
  (`rkF (n+1) k = max over rules with out = k of rkF n (match) + 1`, and `0` if there are none);
* the candidate is `rkF rules (B + 1)`, `B = |S.keys|`, and `rankCheck` tests the two
  clauses on it, the bound only at rule out-keys (every other key's candidate is `0`).

Soundness is trivial: the candidate IS the witness (`rkF_eq_zero_or_outKey` covers the
keys the check does not visit). Completeness, from any `rrank`:
`rkF_le_rank` (every walk climbs `rrank` strictly, so `rkF n ≤ rrank ≤ B`),
`rkF_mono` (`rkF n ≤ rkF (n+1)`), and `rkF_jump` (a value can only CHANGE at step `n+1` by
becoming exactly `n+1`). At `n = B` a change would put a value at `B+1 > B`, so the iteration
is stationary there, and a stationary candidate climbs strictly along every rule.

The executable form `rkL` tabulates each layer as an association list over the rules'
out-keys, so the compiled `zcli` evaluates it in `O(B · |rules|²)` rather than the
`|rules|^B` a closure-recursive `rkF` would cost; `lookD_rkL` proves the table equal to
`rkF` pointwise, so no reasoning ever happens on the table.

## The other thirteen

Six are bounded-quantifier nests over decidable atoms, decided by `decide` against their own
statement. `wf` and `ttuNotLeaf` are re-shaped (`WF` is a one-field structure, `TtuTargetsSat`
an unbounded `∀ tr` fixed by `r.kind`, read off as `ttuTargets`). `storeValid`
(`StoreValidRulesD`) has an unbounded `∃ e` fixed by `S.lookup` and an `∃ rs` over a list,
read as a `match` and an `any` — exact with no `NodupKeys` premise, the same reason
`FragmentDecide.lean`'s `lookupAll` is.
-/

namespace Zanzibar

/-! ## A list maximum with the four facts the rank proof needs -/

/-- `max` of `f` over `l`, `0` on the empty list. -/
def maxOf {α : Type} (l : List α) (f : α → Nat) : Nat :=
  l.foldr (fun a acc => max (f a) acc) 0

theorem maxOf_cons {α : Type} (a : α) (l : List α) (f : α → Nat) :
    maxOf (a :: l) f = max (f a) (maxOf l f) := rfl

theorem le_maxOf {α : Type} {f : α → Nat} {a : α} :
    ∀ {l : List α}, a ∈ l → f a ≤ maxOf l f
  | [], ha => by simp at ha
  | b :: t, ha => by
      rw [maxOf_cons]
      rcases List.mem_cons.mp ha with rfl | h
      · exact Nat.le_max_left _ _
      · exact Nat.le_trans (le_maxOf h) (Nat.le_max_right _ _)

theorem maxOf_le {α : Type} {f : α → Nat} {B : Nat} :
    ∀ {l : List α}, (∀ a ∈ l, f a ≤ B) → maxOf l f ≤ B
  | [], _ => Nat.zero_le _
  | b :: t, h => by
      rw [maxOf_cons]
      exact Nat.max_le.mpr ⟨h b List.mem_cons_self,
        maxOf_le (fun a ha => h a (List.mem_cons_of_mem _ ha))⟩

theorem maxOf_cases {α : Type} {f : α → Nat} :
    ∀ (l : List α), maxOf l f = 0 ∨ ∃ a ∈ l, maxOf l f = f a
  | [] => Or.inl rfl
  | b :: t => by
      rw [maxOf_cons]
      rcases Nat.le_total (maxOf t f) (f b) with h | h
      · exact Or.inr ⟨b, List.mem_cons_self, Nat.max_eq_left h⟩
      · rw [Nat.max_eq_right h]
        rcases maxOf_cases t with h0 | ⟨a, ha, he⟩
        · exact Or.inl h0
        · exact Or.inr ⟨a, List.mem_cons_of_mem _ ha, he⟩

theorem maxOf_mono {α : Type} {f g : α → Nat} {l : List α} (h : ∀ a ∈ l, f a ≤ g a) :
    maxOf l f ≤ maxOf l g :=
  maxOf_le fun a ha => Nat.le_trans (h a ha) (le_maxOf ha)

/-! ## The canonical rank candidate `rkF` and its three lemmas -/

/-- A rule's MATCH key, the shape `RewriteRanked` ranks below the out key. -/
def RRule.matchKey (r : RRule) : String × String := (r.objectType, r.matchRel)

/-- A rule's OUT key. -/
def RRule.outKey (r : RRule) : String × String := (r.objectType, r.outRel)

/-- One rule's contribution to key `k`'s next-layer rank: `r (match) + 1` if the rule
    OUTPUTS `k`, else `0`. -/
def rankTerm (k : String × String) (r : String × String → Nat) (ru : RRule) : Nat :=
  if ru.outKey = k then r ru.matchKey + 1 else 0

/-- **The longest rule-walk of length `≤ n` ending at `k`** — the mathematical candidate.
    Never evaluated (it is exponential as a closure); `rkL` is the table it equals. -/
def rkF (rules : List RRule) : Nat → String × String → Nat
  | 0, _ => 0
  | n + 1, k => maxOf rules (rankTerm k (rkF rules n))

/-- **Every rank function bounds the candidate from above.** A walk climbs `rrank` by at
    least one per rule, so its length is at most the rank of its end. -/
theorem rkF_le_rank {rules : List RRule} {rrank : String × String → Nat}
    (hlt : ∀ ru ∈ rules, rrank ru.matchKey < rrank ru.outKey) :
    ∀ n k, rkF rules n k ≤ rrank k
  | 0, _ => Nat.zero_le _
  | n + 1, k => by
      show maxOf rules (rankTerm k (rkF rules n)) ≤ rrank k
      refine maxOf_le fun ru hru => ?_
      unfold rankTerm
      split
      · rename_i hk
        have h1 := rkF_le_rank hlt n ru.matchKey
        have h2 := hlt ru hru
        rw [hk] at h2
        omega
      · exact Nat.zero_le _

/-- **The layers only grow.** -/
theorem rkF_mono (rules : List RRule) : ∀ n k, rkF rules n k ≤ rkF rules (n + 1) k
  | 0, _ => Nat.zero_le _
  | n + 1, k => by
      show maxOf rules (rankTerm k (rkF rules n)) ≤ maxOf rules (rankTerm k (rkF rules (n + 1)))
      refine maxOf_mono fun ru _ => ?_
      unfold rankTerm
      split
      · have := rkF_mono rules n ru.matchKey
        omega
      · exact Nat.le_refl _

/-- **A value can only change by becoming exactly the layer index.** If layer `n+1` beats
    layer `n` at `k`, the new value is `n + 1`: the maximising rule's match key must itself
    have changed at the layer below, and by induction it changed to `n`. -/
theorem rkF_jump (rules : List RRule) :
    ∀ n k, rkF rules n k < rkF rules (n + 1) k → rkF rules (n + 1) k = n + 1
  | 0, k, h => by
      have hle : rkF rules (0 + 1) k ≤ 1 := by
        show maxOf rules (rankTerm k (rkF rules 0)) ≤ 1
        refine maxOf_le fun ru _ => ?_
        unfold rankTerm
        split
        · show 0 + 1 ≤ 1
          exact Nat.le_refl _
        · exact Nat.zero_le _
      have h0 : rkF rules 0 k = 0 := rfl
      omega
  | n + 1, k, h => by
      have hdef : rkF rules (n + 1 + 1) k = maxOf rules (rankTerm k (rkF rules (n + 1))) := rfl
      rcases maxOf_cases (f := rankTerm k (rkF rules (n + 1))) rules with h0 | ⟨ru, hru, he⟩
      · omega
      · by_cases hk : ru.outKey = k
        · rw [show rankTerm k (rkF rules (n + 1)) ru = rkF rules (n + 1) ru.matchKey + 1 from
            if_pos hk] at he
          -- the same rule, one layer down, lower-bounds layer `n+1` at `k`
          have hlow : rankTerm k (rkF rules n) ru ≤ rkF rules (n + 1) k := le_maxOf hru
          rw [show rankTerm k (rkF rules n) ru = rkF rules n ru.matchKey + 1 from
            if_pos hk] at hlow
          have hj := rkF_jump rules n ru.matchKey (by omega)
          omega
        · rw [show rankTerm k (rkF rules (n + 1)) ru = 0 from if_neg hk] at he
          omega

/-- A key no rule outputs has candidate `0`; otherwise it IS some rule's out key. This is
    what lets `rankCheck` visit only out keys and still bound `∀ k`. -/
theorem rkF_eq_zero_or_outKey (rules : List RRule) (n : Nat) (k : String × String) :
    rkF rules (n + 1) k = 0 ∨ ∃ ru ∈ rules, ru.outKey = k := by
  rcases maxOf_cases (f := rankTerm k (rkF rules n)) rules with h0 | ⟨ru, hru, he⟩
  · exact Or.inl h0
  · unfold rankTerm at he
    split at he
    · rename_i hk
      exact Or.inr ⟨ru, hru, hk⟩
    · exact Or.inl he

/-! ## The check, and its exact `_iff` against the `RewriteRanked` shape -/

/-- Check the two `RewriteRanked` clauses on a candidate `c`, the bound at out keys only. -/
def rankCheck (rules : List RRule) (B : Nat) (c : String × String → Nat) : Bool :=
  rules.all fun ru => decide (c ru.matchKey < c ru.outKey) && decide (c ru.outKey ≤ B)

/-- **The candidate decides the existential EXACTLY**, for any rule list and bound. -/
theorem rankCheck_rkF_iff (rules : List RRule) (B : Nat) :
    rankCheck rules B (rkF rules (B + 1)) = true ↔
      ∃ rrank : String × String → Nat,
        (∀ ru ∈ rules, rrank ru.matchKey < rrank ru.outKey) ∧ ∀ k, rrank k ≤ B := by
  unfold rankCheck
  simp only [List.all_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  constructor
  · -- soundness: the candidate is the witness
    intro h
    refine ⟨rkF rules (B + 1), fun ru hru => (h ru hru).1, fun k => ?_⟩
    rcases rkF_eq_zero_or_outKey rules B k with h0 | ⟨ru, hru, hk⟩
    · rw [h0]; exact Nat.zero_le _
    · rw [← hk]; exact (h ru hru).2
  · -- completeness: bounded by any rank, hence stationary at layer `B + 1`
    rintro ⟨rrank, hlt, hle⟩ ru hru
    have hbnd : ∀ k, rkF rules (B + 1) k ≤ B := fun k =>
      Nat.le_trans (rkF_le_rank hlt (B + 1) k) (hle k)
    refine ⟨?_, hbnd ru.outKey⟩
    have hstat : rkF rules (B + 1) ru.matchKey = rkF rules B ru.matchKey := by
      have hm := rkF_mono rules B ru.matchKey
      rcases Nat.lt_or_ge (rkF rules B ru.matchKey) (rkF rules (B + 1) ru.matchKey) with hlt' | hge
      · have := rkF_jump rules B ru.matchKey hlt'
        have := hbnd ru.matchKey
        omega
      · omega
    have hup : rankTerm ru.outKey (rkF rules B) ru ≤ rkF rules (B + 1) ru.outKey := le_maxOf hru
    unfold rankTerm at hup
    rw [if_pos rfl] at hup
    omega

/-! ## The executable table `rkL`, proved equal to `rkF` -/

/-- Association-list lookup, `0` on a miss (the `Schema.lookup` idiom: first match). -/
def lookD (l : List ((String × String) × Nat)) (k : String × String) : Nat :=
  match l.find? (fun p => decide (p.1 = k)) with
  | some p => p.2
  | none => 0

theorem lookD_map (g : String × String → Nat) (k : String × String) :
    ∀ ks : List (String × String),
      lookD (ks.map fun k' => (k', g k')) k = if k ∈ ks then g k else 0
  | [] => by simp [lookD]
  | a :: t => by
      have ih := lookD_map g k t
      unfold lookD at ih ⊢
      by_cases h : a = k
      · subst h
        simp
      · have hk : ¬ k = a := fun h' => h h'.symm
        simp only [List.map_cons, List.find?_cons, h, decide_false]
        rw [ih]
        simp [hk]

/-- Layer `n` as a table over the rules' out keys. `prev` is let-bound so the compiled
    evaluator computes each layer once. -/
def rkL (rules : List RRule) : Nat → List ((String × String) × Nat)
  | 0 => []
  | n + 1 =>
    let prev := rkL rules n
    (rules.map RRule.outKey).map fun k => (k, maxOf rules (rankTerm k (lookD prev)))

/-- **The table IS the candidate**, pointwise. -/
theorem lookD_rkL (rules : List RRule) : ∀ n k, lookD (rkL rules n) k = rkF rules n k
  | 0, k => by simp [rkL, rkF, lookD]
  | n + 1, k => by
      have ih : lookD (rkL rules n) = rkF rules n := funext (lookD_rkL rules n)
      show lookD ((rules.map RRule.outKey).map fun k' =>
          (k', maxOf rules (rankTerm k' (lookD (rkL rules n))))) k = rkF rules (n + 1) k
      rw [ih, lookD_map]
      split
      · rfl
      · rename_i hk
        show 0 = maxOf rules (rankTerm k (rkF rules n))
        refine (Nat.le_zero.mp (maxOf_le fun ru hru => ?_)).symm
        unfold rankTerm
        rw [if_neg (fun (he : ru.outKey = k) => hk (he ▸ List.mem_map_of_mem hru))]

/-- **Executable `RewriteRanked`.** -/
def rankedB (S : Schema) : Bool :=
  rankCheck (schemaRewrites S) S.keys.length
    (lookD (rkL (schemaRewrites S) (S.keys.length + 1)))

theorem rankedB_iff (S : Schema) : rankedB S = true ↔ RewriteRanked S := by
  unfold rankedB
  rw [show lookD (rkL (schemaRewrites S) (S.keys.length + 1))
      = rkF (schemaRewrites S) (S.keys.length + 1) from
      funext (lookD_rkL _ _), rankCheck_rkF_iff]
  rfl

/-! ## The thirteen other fields -/

def admWfB (S : Schema) : Bool := S.defs.all fun p => !(p.1.2.toList.contains '.')

theorem admWfB_iff (S : Schema) : admWfB S = true ↔ WF S := by
  unfold admWfB
  rw [List.all_eq_true]
  constructor
  · intro h
    exact ⟨fun p hp => by have := h p hp; unfold relNameOK; simpa using this⟩
  · intro h p hp
    have := h.relNames p hp
    unfold relNameOK at this
    simpa using this

def admNodupB (S : Schema) : Bool := decide ((S.defs.map (·.1)).Nodup)

theorem admNodupB_iff (S : Schema) : admNodupB S = true ↔ NodupKeys S := by
  unfold admNodupB NodupKeys
  exact decide_eq_true_iff

def admStratB (S : Schema) : Bool := (stratify S).isSome

theorem admStratB_iff (S : Schema) : admStratB S = true ↔ Stratifiable S := Iff.rfl

def admTtuDirectB (S : Schema) : Bool :=
  decide (∀ d ∈ S.defs, ∀ tt ∈ exprTtus d.2,
    ∀ d' ∈ S.defs, d'.1 = (d.1.1, tt.2) → directsOnly d'.2 = true)

theorem admTtuDirectB_iff (S : Schema) : admTtuDirectB S = true ↔ TtuTuplesetsDirect S := by
  unfold admTtuDirectB TtuTuplesetsDirect
  exact decide_eq_true_iff

def admMatchDeclB (S : Schema) : Bool :=
  decide (∀ r ∈ schemaRewrites S, (r.objectType, r.matchRel) ∈ S.keys ∧
    isDerived S (r.objectType, r.matchRel) = false)

theorem admMatchDeclB_iff (S : Schema) : admMatchDeclB S = true ↔ RewriteMatchDeclared S := by
  unfold admMatchDeclB RewriteMatchDeclared
  exact decide_eq_true_iff

def admObjWildB (S : Schema) : Bool :=
  decide (∀ tr ∈ S.objectWildcards, isDerived S tr = false)

theorem admObjWildB_iff (S : Schema) :
    admObjWildB S = true ↔ ∀ tr ∈ S.objectWildcards, isDerived S tr = false :=
  decide_eq_true_iff

def admUsWildB (S : Schema) : Bool :=
  decide (∀ k ∈ taintedKeys S, S.isSubjectWildcardUserset k.1 k.2 = false)

theorem admUsWildB_iff (S : Schema) :
    admUsWildB S = true ↔ ∀ k ∈ taintedKeys S, S.isSubjectWildcardUserset k.1 k.2 = false :=
  decide_eq_true_iff

/-- One stored tuple against `StoreValidRulesD`'s two disjuncts. The `∃ e` is fixed by
    `S.lookup` (a `match`), and the `isDerived` test picks the disjunct, since the two
    disjuncts' first conjuncts partition on it. -/
def storeTupleOkB (S : Schema) (t : Tuple) : Bool :=
  match S.lookup (t.object.type, t.relation) with
  | none => false
  | some e =>
    if isDerived S (t.object.type, t.relation) then
      t.subject.predicate == BARE &&
        (exprDirectsAll e).any fun rs => restrictionMatches rs t && rs.all fun r => r.2.1 == BARE
    else (exprDirects e).any fun rs => restrictionMatches rs t

theorem storeTupleOkB_iff (S : Schema) (t : Tuple) :
    storeTupleOkB S t = true ↔
      ((isDerived S (t.object.type, t.relation) = false ∧
        ∃ e rs, S.lookup (t.object.type, t.relation) = some e ∧
          rs ∈ exprDirects e ∧ restrictionMatches rs t = true)
      ∨ (isDerived S (t.object.type, t.relation) = true ∧ t.subject.predicate = BARE ∧
        ∃ e rs, S.lookup (t.object.type, t.relation) = some e ∧
          rs ∈ exprDirectsAll e ∧ restrictionMatches rs t = true ∧ (∀ r ∈ rs, r.2.1 = BARE))) := by
  unfold storeTupleOkB
  cases hl : S.lookup (t.object.type, t.relation) with
  | none => simp
  | some e =>
    cases hd : isDerived S (t.object.type, t.relation) <;>
      simp [List.any_eq_true, List.all_eq_true]

def admStoreValidB (S : Schema) (T : Store) : Bool := T.all (storeTupleOkB S)

theorem admStoreValidB_iff (S : Schema) (T : Store) :
    admStoreValidB S T = true ↔ StoreValidRulesD S T := by
  unfold admStoreValidB StoreValidRulesD
  simp only [List.all_eq_true, storeTupleOkB_iff]

def admTtuNotLeafB (S : Schema) : Bool :=
  (schemaRewrites S).all fun r => (ttuTargets r).all fun tr => decide (NotLeafName tr)

theorem admTtuNotLeafB_iff (S : Schema) :
    admTtuNotLeafB S = true ↔ TtuTargetsSat S NotLeafName := by
  unfold admTtuNotLeafB TtuTargetsSat
  simp only [List.all_eq_true, decide_eq_true_eq]
  refine forall_congr' fun r => imp_congr_right fun _ => ?_
  unfold ttuTargets
  cases r.kind with
  | computed => simp
  | ttu tr => simp

def admDirectRestrNotLeafB (S : Schema) : Bool := decide (DirectRestrictionsNotLeaf S)
def admComputedRefsNotLeafB (S : Schema) : Bool := decide (ComputedRefsNotLeaf S)
def admNoLeafSubjectsB (S : Schema) : Bool := decide (NoLeafSubjects S)
def admKeysNonemptyB (S : Schema) : Bool := S.keys.all (fun k => k.2 != "")

/-! ## The decider -/

/-- The fourteen `GraphAdmission` conjuncts, by FIELD NAME, in declaration order. -/
def graphAdmissionFieldsB (S : Schema) (T : Store) : List (String × Bool) :=
  [("wf", admWfB S),
   ("nodup", admNodupB S),
   ("strat", admStratB S),
   ("ttuDirect", admTtuDirectB S),
   ("matchDecl", admMatchDeclB S),
   ("ranked", rankedB S),
   ("objWild", admObjWildB S),
   ("usWild", admUsWildB S),
   ("storeValid", admStoreValidB S T),
   ("ttuNotLeaf", admTtuNotLeafB S),
   ("directRestrNotLeaf", admDirectRestrNotLeafB S),
   ("computedRefsNotLeaf", admComputedRefsNotLeafB S),
   ("noLeafSubjects", admNoLeafSubjectsB S),
   ("keysNonempty", admKeysNonemptyB S)]

/-- **Executable `GraphAdmission`.** -/
def graphAdmissionB (S : Schema) (T : Store) : Bool :=
  (graphAdmissionFieldsB S T).all (·.2)

/-- **`GraphAdmission` is decided EXACTLY by `graphAdmissionB`** — soundness and completeness. -/
theorem graphAdmissionB_iff (S : Schema) (T : Store) :
    graphAdmissionB S T = true ↔ GraphAdmission S T := by
  unfold graphAdmissionB graphAdmissionFieldsB admDirectRestrNotLeafB admComputedRefsNotLeafB
    admNoLeafSubjectsB admKeysNonemptyB
  simp only [List.all_cons, List.all_nil, Bool.and_true, Bool.and_eq_true, decide_eq_true_eq]
  constructor
  · rintro ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14⟩
    exact ⟨(admWfB_iff S).mp h1, (admNodupB_iff S).mp h2, (admStratB_iff S).mp h3,
      (admTtuDirectB_iff S).mp h4, (admMatchDeclB_iff S).mp h5, (rankedB_iff S).mp h6,
      (admObjWildB_iff S).mp h7, (admUsWildB_iff S).mp h8, (admStoreValidB_iff S T).mp h9,
      (admTtuNotLeafB_iff S).mp h10, h11, h12, h13, h14⟩
  · intro h
    exact ⟨(admWfB_iff S).mpr h.wf, (admNodupB_iff S).mpr h.nodup,
      (admStratB_iff S).mpr h.strat, (admTtuDirectB_iff S).mpr h.ttuDirect,
      (admMatchDeclB_iff S).mpr h.matchDecl, (rankedB_iff S).mpr h.ranked,
      (admObjWildB_iff S).mpr h.objWild, (admUsWildB_iff S).mpr h.usWild,
      (admStoreValidB_iff S T).mpr h.storeValid, (admTtuNotLeafB_iff S).mpr h.ttuNotLeaf,
      h.directRestrNotLeaf, h.computedRefsNotLeaf, h.noLeafSubjects, h.keysNonempty⟩

instance instDecidableGraphAdmission (S : Schema) (T : Store) : Decidable (GraphAdmission S T) :=
  decidable_of_iff _ (graphAdmissionB_iff S T)

/-- The names of the fields `(S, T)` FAILS, in declaration order — `[]` iff admitted. -/
def graphAdmissionFailures (S : Schema) (T : Store) : List String :=
  ((graphAdmissionFieldsB S T).filter (fun p => !p.2)).map (·.1)

theorem graphAdmissionFailures_nil_iff (S : Schema) (T : Store) :
    graphAdmissionFailures S T = [] ↔ GraphAdmission S T := by
  rw [← graphAdmissionB_iff]
  unfold graphAdmissionFailures graphAdmissionB
  simp only [List.map_eq_nil_iff, List.filter_eq_nil_iff, Bool.not_eq_true', Bool.not_eq_false,
    List.all_eq_true]

/-- **The WHOLE headline premise**, `GraphAdmission ∧ W4Fragment`, as one Bool. -/
def headlinePremiseB (S : Schema) (T : Store) : Bool := graphAdmissionB S T && w4FragmentB S T

theorem headlinePremiseB_iff (S : Schema) (T : Store) :
    headlinePremiseB S T = true ↔ GraphAdmission S T ∧ W4Fragment S T := by
  unfold headlinePremiseB
  rw [Bool.and_eq_true, graphAdmissionB_iff, w4FragmentB_iff]

/-! ## Evidence pins (`TK104`)

The `_iff` lemmas prove the decider CORRECT. These pins show it is USABLE (the kernel
evaluates it by `decide` at real schemas) and that it DISCRIMINATES. A decider stuck at
`false` fails the positives. A decider stuck at `true`, or one that confuses two fields,
fails the per-field controls, and each control pins the EXACT failure list. Every control
is `W4Witness.Sx`/`Tx` with one edit, except where the field needs a witness the tree
already has (`SxUsWild`, `SxLeafRef`, `SnlBadLeaf`).

`chainS` is the first admitted witness in the tree with a NON-ZERO rank. Every hand-proved
`GraphAdmission` before this module discharged `ranked` with `⟨fun _ => 0, …⟩`, which works
only because none of those schemas has a rewrite chain. So `RewriteRanked`'s content was
never exercised at a witness until `rank_needs_iteration` below. -/

namespace AdmissionDecideWitness

open W4Witness (Sx Tx)

/-! ### Positives: the six schema/store pairs the tree hand-proves admitted, plus `chainS` -/

theorem accepts_Sx : graphAdmissionFailures Sx Tx = [] := by decide
theorem accepts_Sy : graphAdmissionFailures W4WitnessUnion.Sy W4WitnessUnion.Ty = [] := by decide
theorem accepts_Sd : graphAdmissionFailures W4WitnessDirect.Sd W4WitnessDirect.Td = [] := by decide
theorem accepts_Sd4 :
    graphAdmissionFailures W4WitnessDirect.Sd W4WitnessDirect.Td4 = [] := by decide
theorem accepts_SlV : graphAdmissionFailures LeafRuleWitness.SlV [] = [] := by decide
theorem accepts_Sw : graphAdmissionFailures LeafWitness.Sw [LeafWitness.tw] = [] := by decide

/-- A three-deep computed chain `owner → editor → viewer` on `doc`, nested folders through
    a TTU self-recursion (`viewer from parent`, the in-scope control from the `TK104`
    sizing), and a derived `can_view := viewer but not banned` on top. -/
def chainS : Schema :=
  ⟨[(("doc", "owner"), .direct [("user", BARE, false)]),
    (("doc", "editor"), .union (.direct [("user", BARE, false)]) (.computed "owner")),
    (("doc", "viewer"), .union (.direct [("user", BARE, false)]) (.computed "editor")),
    (("folder", "parent"), .direct [("folder", BARE, false)]),
    (("folder", "viewer"), .union (.direct [("user", BARE, false)]) (.ttu "viewer" "parent")),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "can_view"), .excl (.computed "viewer") (.computed "banned"))], []⟩

theorem accepts_chainS : graphAdmissionFailures chainS [] = [] := by decide

/-- The whole headline premise holds at `chainS`, by one `decide`. -/
theorem premise_chainS : GraphAdmission chainS [] ∧ W4Fragment chainS [] := by decide

/-- The candidate really climbs: `doc#viewer` is at rank 2. -/
theorem rank_viewer_chainS :
    lookD (rkL (schemaRewrites chainS) (chainS.keys.length + 1)) ("doc", "viewer") = 2 := by
  decide

/-- **The all-zero rank every earlier witness used is REFUTED at `chainS`**, so `ranked`'s
    positive there is carried by the iteration, not by a constant. -/
theorem rank_needs_iteration :
    rankCheck (schemaRewrites chainS) chainS.keys.length (fun _ => 0) = false := by decide

/-- **The TIGHT case: a walk as long as the bound allows.** `zz → a1 → a2 → a3` has length
    `3 = |keys|`, which needs an undeclared start (so `matchDecl` fails, and only it). The
    candidate must iterate to the full `|keys| + 1` layers or it refuses this in-range rank:
    a layer count of `|keys| - 1` leaves `a2` and `a3` tied. -/
def tightS : Schema :=
  ⟨[(("doc", "a1"), .computed "zz"),
    (("doc", "a2"), .computed "a1"),
    (("doc", "a3"), .computed "a2")], []⟩
theorem rank_tight : graphAdmissionFailures tightS [] = ["matchDecl"] := by decide

/-- The instance, not just the Bool, closes a `GraphAdmission` goal by `decide`. -/
theorem admission_Sx_by_decide : GraphAdmission Sx Tx := by decide

/-! ### Negatives: one control per field, each pinning its exact failure list -/

/-- `Sx` plus the given definitions. -/
def ext (extra : List ((String × String) × Expr)) : Schema := ⟨Sx.defs ++ extra, []⟩

/-- `wf`: a declared relation name with a `'.'`. -/
theorem refutes_wf :
    graphAdmissionFailures (ext [(("doc", "x.y"), .direct [("user", BARE, false)])]) Tx
      = ["wf"] := by decide

/-- `nodup`: `doc#a` declared twice. -/
theorem refutes_nodup :
    graphAdmissionFailures (ext [(("doc", "a"), .direct [("user", BARE, false)])]) Tx
      = ["nodup"] := by decide

/-- `strat`: two derived defs that subtract into each other. -/
def S3 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.computed "s") (.computed "b")),
    (("doc", "s"), .excl (.computed "r") (.computed "b"))], []⟩
theorem refutes_strat : graphAdmissionFailures S3 Tx = ["strat"] := by decide

/-- `ttuDirect`: a TTU whose tupleset relation `p` is computed, not direct. -/
theorem refutes_ttuDirect :
    graphAdmissionFailures (ext [(("doc", "p"), .computed "a"), (("doc", "v"), .ttu "a" "p")]) Tx
      = ["ttuDirect"] := by decide

/-- `matchDecl` (SILENT in Python): a computed reference to an undeclared relation. -/
theorem refutes_matchDecl :
    graphAdmissionFailures
      (ext [(("doc", "c"), .union (.direct [("user", BARE, false)]) (.computed "zz"))]) Tx
      = ["matchDecl"] := by decide

/-- `matchDecl`, the TTU half: an undeclared tupleset relation. -/
theorem refutes_matchDecl_ttu :
    graphAdmissionFailures (ext [(("doc", "v"), .ttu "a" "zz")]) Tx = ["matchDecl"] := by decide

/-- `ranked` (SILENT in Python): an untainted computed two-cycle `c ↔ d`. -/
theorem refutes_ranked :
    graphAdmissionFailures
      (ext [(("doc", "c"), .union (.direct [("user", BARE, false)]) (.computed "d")),
            (("doc", "d"), .union (.direct [("user", BARE, false)]) (.computed "c"))]) Tx
      = ["ranked"] := by decide

/-- `ranked`, the self-loop `c := [user] or c`. -/
theorem refutes_ranked_self :
    graphAdmissionFailures
      (ext [(("doc", "c"), .union (.direct [("user", BARE, false)]) (.computed "c"))]) Tx
      = ["ranked"] := by decide

/-- `objWild`: an object-wildcard shape on the derived `doc#r`. -/
theorem refutes_objWild : graphAdmissionFailures ⟨Sx.defs, [("doc", "r")]⟩ Tx = ["objWild"] := by
  decide

/-- `usWild`: a wildcard userset `[doc:*#r]` over the derived `doc#r`. -/
theorem refutes_usWild : graphAdmissionFailures W4Witness.SxUsWild Tx = ["usWild"] := by decide

/-- `storeValid`: a stored tuple on an undeclared relation. -/
theorem refutes_storeValid :
    graphAdmissionFailures Sx [⟨⟨"user", "alice", BARE⟩, "zz", ⟨"doc", "1"⟩⟩]
      = ["storeValid"] := by decide

/-- `storeValid`, the derived half: a bare write on a derived `Direct` arm whose restriction
    list also carries a userset (`[user, group#member]`). `StoreValidRulesD` wants the whole
    list bare, so even `user:alice` fails (the sizing's subtle probe). -/
def SdU : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "approver"),
      .excl (.direct [("user", BARE, false), ("group", "member", false)]) (.computed "banned"))],
   []⟩
theorem refutes_storeValid_derived :
    graphAdmissionFailures SdU W4WitnessDirect.Td = ["storeValid"] := by decide

/-- `ttuNotLeaf`: an untainted TTU targets the minted leaf name `a.0`. It CANNOT fail alone:
    `CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects` derives it from
    `noLeafSubjects`, so its control pins the pair. -/
theorem refutes_ttuNotLeaf :
    graphAdmissionFailures
      (ext [(("doc", "p"), .direct [("doc", BARE, false)]), (("doc", "v"), .ttu "a.0" "p")]) Tx
      = ["ttuNotLeaf", "noLeafSubjects"] := by decide

/-- `directRestrNotLeaf`: a `Direct` restriction whose predicate is a leaf name. -/
theorem refutes_directRestrNotLeaf :
    graphAdmissionFailures (ext [(("doc", "c"), .direct [("group", "member.0", false)])]) Tx
      = ["directRestrNotLeaf"] := by decide

/-- `computedRefsNotLeaf`: `Sx` with one operand re-pointed at `leafPred "a" 0`. -/
theorem refutes_computedRefsNotLeaf :
    graphAdmissionFailures W4Witness.SxLeafRef Tx = ["computedRefsNotLeaf"] := by decide

/-- `noLeafSubjects` ALONE: the derived arm's TTU target is a leaf name, which only the
    leaf-routed rule set sees (`admissionNameShape_does_not_give_noLeafSubjects`). -/
theorem refutes_noLeafSubjects :
    graphAdmissionFailures LeafRuleWitness.SnlBadLeaf [] = ["noLeafSubjects"] := by decide

/-- `keysNonempty`: a declared relation named `""`. -/
theorem refutes_keysNonempty :
    graphAdmissionFailures (ext [(("doc", ""), .direct [("user", BARE, false)])]) Tx
      = ["keysNonempty"] := by decide

/-- **The joint Bool reads BOTH halves.** `FragmentDecideWitness.S6` (three derived strata) is
    ADMITTED but outside `W4Fragment`, so `headlinePremiseB` must refuse it: a premise Bool
    that read only `GraphAdmission` would say `true` here. -/
theorem premise_reads_both_halves :
    graphAdmissionB FragmentDecideWitness.S6 Tx = true ∧
      headlinePremiseB FragmentDecideWitness.S6 Tx = false := by decide

/-- The instance closes a NEGATIVE goal too. -/
theorem outside_S3_by_decide : ¬ GraphAdmission S3 Tx := by decide

end AdmissionDecideWitness

end Zanzibar
