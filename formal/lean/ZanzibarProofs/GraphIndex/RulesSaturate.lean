import ZanzibarProofs.GraphIndex.RulesCorrect

/-!
# Rewrite-closure saturation (ROADMAP W2, completeness prerequisite)

The W2 completeness direction (`sem ⇒ reach`) needs, for the `computed` case, that the
materialised rewrite-closure is **closed under one more rewrite step**: if a graph path
reaches an `r'`-tuple `w` (some `w ∈ rewriteClosure S t`) and the schema has a
`computed r'` arm on the queried relation `r`, the rewritten `r`-tuple `⟨w.subject, r,
w.object⟩` must ALSO be a materialised closure tuple, so the path extends to the `r`-node.

**Attack-first (2026-07-10, machine-checked `#eval`, then deleted): saturation HOLDS at
the write model's `|keys|+1` bound** — tested against adversarial schemas including
mutual-`ttu` cycles and predicate-ratcheting unions whose *distinct* reachable-tuple
count exceeds `|keys|+1`. The bound that matters is the **rewrite DEPTH** (the length of
a chain of rewrite steps), not the count: each step advances the relation to a rule
`outRel`, so along an acyclic rewrite graph the relations are strictly ranked and a chain
has length ≤ `|keys|`. `|keys|+1` closure levels therefore capture every reachable tuple
*and* leave the top level's rewrite-step image already inside — saturation.

The provable path is a **rank argument** under rewrite-acyclicity (`RewriteRanked`, a
faithful fragment condition: the Python compiler stratifies / rejects computed-userset
cycles). NB the empirical finding is broader — saturation held even for the cyclic
schemas, which `RewriteRanked` excludes — so `RewriteRanked` is sufficient, not necessary;
it is the honest hypothesis under which the depth bound is provable. Carry it into W4.
-/

namespace Zanzibar

/-- The rewrite key of a tuple: `(object type, relation)` — the pair the rewrite rules
    range over (rewrites preserve the object type; only the relation and subject move). -/
def rwKey (w : Tuple) : String × String := (w.object.type, w.relation)

/-- **`RewriteRanked S`** — the schema's rewrite graph on relations is acyclic: there is a
    rank on keys that every rewrite rule strictly increases (`matchRel` key below `outRel`
    key) and which is bounded by `|keys|`. Faithful to the Python compiler's
    stratification (computed-userset / TTU cycles are rejected). A strictly-increasing,
    `|keys|`-bounded rank forces every rewrite chain to have length ≤ `|keys|`, so the
    `|keys|+1`-level closure saturates. -/
def RewriteRanked (S : Schema) : Prop :=
  ∃ rrank : (String × String) → Nat,
    (∀ r ∈ schemaRewrites S,
      rrank (r.objectType, r.matchRel) < rrank (r.objectType, r.outRel)) ∧
    (∀ k, rrank k ≤ S.keys.length)

/-! ## The iterated rewrite step and its layer algebra -/

/-- `stepN S k` applies `rewriteStep`-flatMap `k` times — the `k`-th rewrite layer. -/
def stepN (S : Schema) : Nat → List Tuple → List Tuple
  | 0, cur => cur
  | k + 1, cur => (stepN S k cur).flatMap (rewriteStep S)

/-- Iteration commutes with a leading step: `step^{k+1} = step^k ∘ step`. -/
theorem stepN_step_comm (S : Schema) :
    ∀ (k : Nat) (cur : List Tuple),
      stepN S (k + 1) cur = stepN S k (cur.flatMap (rewriteStep S)) := by
  intro k
  induction k with
  | zero => intro cur; rfl
  | succ m ih =>
    intro cur
    show (stepN S (m + 1) cur).flatMap (rewriteStep S) = stepN S (m + 1) (cur.flatMap (rewriteStep S))
    rw [ih cur]
    rfl

/-- A `stepN` layer at depth `≤ n` embeds in the `n`-level closure. -/
theorem mem_aux_of_stepN (S : Schema) :
    ∀ (n k : Nat) (cur : List Tuple), k ≤ n →
      ∀ {w : Tuple}, w ∈ stepN S k cur → w ∈ rewriteClosureAux S n cur := by
  intro n
  induction n with
  | zero =>
    intro k cur hk w hw
    obtain rfl : k = 0 := Nat.le_zero.mp hk
    exact hw
  | succ m ih =>
    intro k cur hk w hw
    rw [rewriteClosureAux, List.mem_append]
    cases k with
    | zero => exact Or.inl hw
    | succ k' =>
      refine Or.inr (ih k' _ (Nat.le_of_succ_le_succ hk) ?_)
      rw [← stepN_step_comm]; exact hw

/-- Conversely, every closure member sits at some layer of depth `≤ n`. -/
theorem stepN_of_mem_aux (S : Schema) :
    ∀ (n : Nat) (cur : List Tuple) {w : Tuple}, w ∈ rewriteClosureAux S n cur →
      ∃ k, k ≤ n ∧ w ∈ stepN S k cur := by
  intro n
  induction n with
  | zero => intro cur w hw; exact ⟨0, Nat.le_refl 0, hw⟩
  | succ m ih =>
    intro cur w hw
    rw [rewriteClosureAux, List.mem_append] at hw
    rcases hw with hin | hrec
    · exact ⟨0, Nat.zero_le _, hin⟩
    · obtain ⟨k, hk, hmem⟩ := ih _ hrec
      refine ⟨k + 1, Nat.succ_le_succ hk, ?_⟩
      rw [stepN_step_comm]; exact hmem

/-- One more rewrite step from a layer-`k` tuple lands in layer `k+1`. -/
theorem mem_stepN_succ {S : Schema} {k : Nat} {cur : List Tuple} {w u : Tuple}
    (hw : w ∈ stepN S k cur) (hu : u ∈ rewriteStep S w) : u ∈ stepN S (k + 1) cur := by
  show u ∈ (stepN S k cur).flatMap (rewriteStep S)
  exact List.mem_flatMap.mpr ⟨w, hw, hu⟩

/-! ## The rank strictly increases along a rewrite step -/

/-- `applyRRule` succeeds only when the tuple matches the rule's `(matchRel, objectType)`. -/
theorem applyRRule_match {r : RRule} {t u : Tuple} (h : applyRRule r t = some u) :
    t.relation = r.matchRel ∧ t.object.type = r.objectType := by
  unfold applyRRule at h
  split at h
  · assumption
  · simp at h

/-- **A rewrite step strictly increases the rank** (under `RewriteRanked`): the step fires
    a rule taking `w`'s key `(ot, matchRel)` to `u`'s key `(ot, outRel)`, and the rank
    hypothesis ranks the former below the latter. -/
theorem rwKey_rank_lt {S : Schema} {rrank : (String × String) → Nat}
    (hinc : ∀ r ∈ schemaRewrites S,
      rrank (r.objectType, r.matchRel) < rrank (r.objectType, r.outRel))
    {w u : Tuple} (hu : u ∈ rewriteStep S w) :
    rrank (rwKey w) < rrank (rwKey u) := by
  unfold rewriteStep at hu
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp hu
  obtain ⟨hrel, hot⟩ := applyRRule_match hap
  obtain ⟨hout_ot, hout_rel⟩ := applyRRule_outRel hap
  have hkw : rwKey w = (r.objectType, r.matchRel) := by
    unfold rwKey; rw [hrel, hot]
  have hku : rwKey u = (r.objectType, r.outRel) := by
    unfold rwKey; rw [hout_ot, hout_rel]
  rw [hkw, hku]
  exact hinc r hr

/-- **Layer rank grows with depth**: if every tuple of `cur` has rank ≥ `b`, then every
    tuple at layer `k` has rank ≥ `b + k` — each step bumps the rank by ≥ 1. -/
theorem stepN_rank_ge {S : Schema} {rrank : (String × String) → Nat}
    (hinc : ∀ r ∈ schemaRewrites S,
      rrank (r.objectType, r.matchRel) < rrank (r.objectType, r.outRel)) (b : Nat) :
    ∀ (k : Nat) (cur : List Tuple), (∀ v ∈ cur, b ≤ rrank (rwKey v)) →
      ∀ w ∈ stepN S k cur, b + k ≤ rrank (rwKey w) := by
  intro k
  induction k with
  | zero => intro cur hcur w hw; rw [Nat.add_zero]; exact hcur w hw
  | succ m ih =>
    intro cur hcur w hw
    change w ∈ (stepN S m cur).flatMap (rewriteStep S) at hw
    obtain ⟨x, hx, hwx⟩ := List.mem_flatMap.mp hw
    have hxr : b + m ≤ rrank (rwKey x) := ih cur hcur x hx
    have hstep : rrank (rwKey x) < rrank (rwKey w) := rwKey_rank_lt hinc hwx
    omega

/-! ## Saturation -/

/-- **The rewrite-closure is closed under one more rewrite step** (under `RewriteRanked`).
    A closure tuple `w` sits at some layer `k ≤ |keys|+1`; its rank is ≥ `k` and ≤ `|keys|`,
    forcing `k ≤ |keys|`; so a further step lands `u` in layer `k+1 ≤ |keys|+1`, still
    inside the `|keys|+1`-level closure. This is the operational fact the `computed` case
    of completeness consults: the graph does materialise the rewritten tuple. -/
theorem rewriteClosure_saturated {S : Schema} (hR : RewriteRanked S) {t w u : Tuple}
    (hw : w ∈ rewriteClosure S t) (hu : u ∈ rewriteStep S w) :
    u ∈ rewriteClosure S t := by
  obtain ⟨rrank, hinc, hbound⟩ := hR
  unfold rewriteClosure at hw ⊢
  obtain ⟨k, hk, hmem⟩ := stepN_of_mem_aux S (S.keys.length + 1) [t] hw
  -- rank ≥ k (depth) and ≤ |keys| force k ≤ |keys|
  have hrank_ge : 0 + k ≤ rrank (rwKey w) :=
    stepN_rank_ge hinc 0 k [t] (fun _ _ => Nat.zero_le _) w hmem
  have hrank_le : rrank (rwKey w) ≤ S.keys.length := hbound _
  have hk' : k ≤ S.keys.length := by omega
  -- so u is in layer k+1 ≤ |keys|+1
  exact mem_aux_of_stepN S (S.keys.length + 1) (k + 1) [t]
    (Nat.succ_le_succ hk') (mem_stepN_succ hmem hu)

end Zanzibar
