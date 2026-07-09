import ZanzibarProofs.Spec.Confine
import ZanzibarProofs.Spec.FuelStable
import Mathlib.Data.Finset.Prod
import Mathlib.Data.Finset.Card

/-!
# T0a stabilization — the untainted (monotone) phase

`SEMANTICS.md` §8 (T0a); ROADMAP "T0a" (option (a), no spec change). This file
delivers the untainted half of the convergence argument:

1. **Generic chain stabilization** (`chain_stabilizes`): a monotone,
   deterministic (`equal once ⇒ equal forever`), bounded `Finset` chain starting
   at `∅` is stable from its cardinality bound on. Reused twice (taint fixpoint,
   evaluation true-set).
2. **Taint closure** (`untainted_closed`): `taintedKeys` is a genuine fixpoint of
   `taintStep`, so an untainted declared key has a boolean-free definition and
   references only untainted keys — the untainted fragment is *closed* and
   *exclusion-free*.
3. **Relative monotonicity** (`semAux_mono_untainted`): at untainted atoms with
   relevant names, one more unit of fuel never retracts a positive answer. Proved
   by MASKING: zero `rec` outside the consulted atom space (`evalE_congr` shows
   the evaluation cannot tell), then apply the *global* positive-fragment
   monotonicity `evalE_mono` to the masked recs — no second leaf induction.
4. **Counting stabilization** (`untainted_stable`): the true-set of untainted
   relevant atoms is monotone and deterministic, hence stable from
   `|atomsU| = |untainted keys| · |relevant names|` on — pointwise stability of
   every untainted atom.

The tainted phase (Kahn rank induction) and the final assembly live in
`Spec/WellDef.lean`.
-/

namespace Zanzibar

/-! ## Generic monotone-chain stabilization -/

/-- A monotone, deterministic, `N`-bounded `Finset` chain from `∅` is stable at
    `N`: it can strictly grow at most `N` times, and determinism makes any
    non-strict step final. -/
theorem chain_stabilizes {α : Type} [DecidableEq α] (F : Nat → Finset α) (N : Nat)
    (mono : ∀ i, F i ⊆ F (i + 1))
    (det : ∀ i, F i = F (i + 1) → F (i + 1) = F (i + 2))
    (base : F 0 = ∅)
    (bound : ∀ i, (F i).card ≤ N) :
    F N = F (N + 1) := by
  have key : ∀ i, F i = F (i + 1) ∨ i + 1 ≤ (F (i + 1)).card := by
    intro i
    induction i with
    | zero =>
        by_cases h : F 0 = F (0 + 1)
        · exact Or.inl h
        · refine Or.inr ?_
          have hlt : (F 0).card < (F (0 + 1)).card :=
            Finset.card_lt_card ((mono 0).ssubset_of_ne h)
          have h0 : (F 0).card = 0 := by rw [base]; exact Finset.card_empty
          omega
    | succ i ih =>
        by_cases h : F (i + 1) = F (i + 1 + 1)
        · exact Or.inl h
        · refine Or.inr ?_
          have hlt : (F (i + 1)).card < (F (i + 1 + 1)).card :=
            Finset.card_lt_card ((mono (i + 1)).ssubset_of_ne h)
          rcases ih with heq | hcard
          · exact absurd (det i heq) h
          · omega
  rcases key N with h | h
  · exact h
  · exact absurd (bound (N + 1)) (by omega)

/-- Once a deterministic chain takes one non-strict step, it is constant forever. -/
theorem chain_persists {α : Type} (F : Nat → Finset α)
    (det : ∀ i, F i = F (i + 1) → F (i + 1) = F (i + 2)) {i : Nat}
    (h : F i = F (i + 1)) : ∀ j, i ≤ j → F j = F (j + 1) := by
  intro j hij
  induction j, hij using Nat.le_induction with
  | base => exact h
  | succ n hn ih => exact det n ih

private theorem bool_eq_of_true_iff {a b : Bool} (h : a = true ↔ b = true) : a = b := by
  cases a <;> cases b <;> simp_all

/-! ## The taint fixpoint — untainted keys form a closed, exclusion-free fragment -/

/-- `iterate` unfolds at the top as well as at the bottom. -/
theorem iterate_succ' {α : Type} (f : α → α) :
    ∀ (n : Nat) (x : α), iterate f (n + 1) x = f (iterate f n x) := by
  intro n
  induction n with
  | zero => intro x; rfl
  | succ m ih =>
      intro x
      show iterate f (m + 1) (f x) = f (iterate f (m + 1) x)
      rw [ih (f x)]
      rfl

/-- The taint iteration chain. `taintedKeys S = taintChain S S.keys.length`. -/
def taintChain (S : Schema) (i : Nat) : List Key := iterate (taintStep S) i []

theorem taintChain_succ (S : Schema) (i : Nat) :
    taintChain S (i + 1) = taintStep S (taintChain S i) :=
  iterate_succ' (taintStep S) i []

theorem taintStep_subset_keys (S : Schema) (cur : List Key) :
    ∀ k ∈ taintStep S cur, k ∈ S.keys := fun _ hk => List.mem_of_mem_filter hk

theorem taintStep_mono (S : Schema) {cur cur' : List Key}
    (h : ∀ k, k ∈ cur → k ∈ cur') :
    ∀ k ∈ taintStep S cur, k ∈ taintStep S cur' := by
  intro k hk
  unfold taintStep at hk ⊢
  rw [List.mem_filter] at hk ⊢
  refine ⟨hk.1, ?_⟩
  rcases Bool.or_eq_true .. |>.mp hk.2 with hb | hr
  · exact Bool.or_eq_true .. |>.mpr (Or.inl hb)
  · refine Bool.or_eq_true .. |>.mpr (Or.inr ?_)
    obtain ⟨b, hbmem, hbc⟩ := List.any_eq_true.mp hr
    refine List.any_eq_true.mpr ⟨b, hbmem, ?_⟩
    rw [List.contains_eq_mem, decide_eq_true_eq] at hbc ⊢
    exact h b hbc

/-- Membership-equivalent inputs give *equal* `taintStep` outputs (the predicate
    reads the input only through `contains`). -/
theorem taintStep_congr (S : Schema) {cur cur' : List Key}
    (h : ∀ k, k ∈ cur ↔ k ∈ cur') : taintStep S cur = taintStep S cur' := by
  unfold taintStep
  refine List.filter_congr (fun k _ => ?_)
  have hany : ((refsOf S k).any fun r => cur.contains r)
      = ((refsOf S k).any fun r => cur'.contains r) := by
    refine anyCongr (fun b _ => ?_)
    rw [List.contains_eq_mem, List.contains_eq_mem]
    exact Bool.decide_congr (h b)
  rw [hany]

theorem taintChain_subset_keys (S : Schema) :
    ∀ i, ∀ k ∈ taintChain S i, k ∈ S.keys := by
  intro i
  cases i with
  | zero => intro k hk; simp [taintChain, iterate] at hk
  | succ n =>
      rw [taintChain_succ]
      exact taintStep_subset_keys S _

theorem taintChain_mono (S : Schema) :
    ∀ i, ∀ k, k ∈ taintChain S i → k ∈ taintChain S (i + 1) := by
  intro i
  induction i with
  | zero => intro k hk; simp [taintChain, iterate] at hk
  | succ n ih =>
      rw [taintChain_succ, taintChain_succ]
      exact taintStep_mono S ih

/-- **The taint fixpoint.** After `|S.keys|` rounds the taint set is closed:
    one more `taintStep` changes nothing (membership). -/
theorem taintedKeys_fixed (S : Schema) :
    ∀ k, k ∈ taintStep S (taintedKeys S) ↔ k ∈ taintedKeys S := by
  have hchain := chain_stabilizes (fun i => (taintChain S i).toFinset) S.keys.length
    (fun i => by
      intro k hk
      rw [List.mem_toFinset] at hk ⊢
      exact taintChain_mono S i k hk)
    (fun i heq => by
      have hiff : ∀ k, k ∈ taintChain S i ↔ k ∈ taintChain S (i + 1) := by
        intro k
        rw [← List.mem_toFinset, ← List.mem_toFinset (l := taintChain S (i + 1)), heq]
      have : taintChain S (i + 1) = taintChain S (i + 2) := by
        rw [taintChain_succ, taintChain_succ]
        exact taintStep_congr S hiff
      rw [this])
    (by simp [taintChain, iterate])
    (fun i => by
      refine le_trans (Finset.card_le_card ?_) (List.toFinset_card_le S.keys)
      intro k hk
      rw [List.mem_toFinset] at hk ⊢
      exact taintChain_subset_keys S i k hk)
  intro k
  have : k ∈ taintChain S S.keys.length ↔ k ∈ taintChain S (S.keys.length + 1) := by
    rw [← List.mem_toFinset, ← List.mem_toFinset (l := taintChain S _), hchain]
  rw [show taintedKeys S = taintChain S S.keys.length from rfl, ← taintChain_succ]
  exact this.symm

/-- **Untainted closure.** An untainted declared key has a boolean-free definition
    and references only untainted keys. -/
theorem untainted_closed (S : Schema) {k : Key} (hk : k ∈ S.keys)
    (hu : k ∉ taintedKeys S) :
    baseTaint S k = false ∧ ∀ b ∈ refsOf S k, b ∉ taintedKeys S := by
  have hnotstep : k ∉ taintStep S (taintedKeys S) :=
    fun h => hu ((taintedKeys_fixed S k).mp h)
  constructor
  · by_contra hb
    have hbt : baseTaint S k = true := by revert hb; cases baseTaint S k <;> simp
    refine hnotstep ?_
    unfold taintStep
    rw [List.mem_filter]
    exact ⟨hk, by rw [hbt]; rfl⟩
  · intro b hb hbt
    refine hnotstep ?_
    unfold taintStep
    rw [List.mem_filter]
    refine ⟨hk, Bool.or_eq_true .. |>.mpr (Or.inr ?_)⟩
    refine List.any_eq_true.mpr ⟨b, hb, ?_⟩
    rw [List.contains_eq_mem, decide_eq_true_eq]
    exact hbt

/-- A boolean-free expression is exclusion-free. -/
theorem noExcl_of_not_containsBool : ∀ e : Expr, containsBool e = false → e.noExcl := by
  intro e
  induction e with
  | union a b iha ihb =>
      intro h
      simp only [containsBool, Bool.or_eq_false_iff] at h
      exact ⟨iha h.1, ihb h.2⟩
  | inter a b _ _ => intro h; simp [containsBool] at h
  | excl a b _ _ => intro h; simp [containsBool] at h
  | direct rs => intro _; trivial
  | computed r => intro _; trivial
  | ttu tr ts => intro _; trivial

/-- A declared key's definition is reachable. -/
theorem lookup_some_of_mem (S : Schema) {k : String × String} (hk : k ∈ S.keys) :
    ∃ e, S.lookup k = some e := by
  unfold Schema.lookup
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | some pe => exact ⟨pe.2, rfl⟩
  | none =>
      obtain ⟨p, hp, hpk⟩ := List.mem_map.mp hk
      have := List.find?_eq_none.mp hf p hp
      simp [hpk] at this

/-! ## Relative monotonicity at untainted atoms (masked) -/

/-- At an untainted declared key, with a relevant name, one more unit of fuel never
    retracts a positive answer. The mask trick: replace `semAux f` / `semAux (f+1)`
    by their restrictions to the consulted atom space (`evalE_congr` — evaluation
    can't tell), where the fuel-`f` values imply the fuel-`f+1` values (IH at
    untainted keys, constant-false at undeclared), then run `evalE_mono`. -/
theorem semAux_mono_untainted (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) :
    ∀ f (t r : String), (t, r) ∈ S.keys → (t, r) ∉ taintedKeys S →
      ∀ m, m ∈ relevantNames T q →
      semAux S q.subject T q f t m r = true →
      semAux S q.subject T q (f + 1) t m r = true := by
  intro f
  induction f with
  | zero => intro t r _ _ m _ h; simp [semAux] at h
  | succ f ih =>
      intro t r hk hu m hm h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hbt, hrefs⟩ := untainted_closed S hk hu
      have hne : e.noExcl := by
        refine noExcl_of_not_containsBool e ?_
        unfold baseTaint at hbt
        rw [hlk] at hbt
        exact hbt
      -- the consultation mask
      set P : Rec := fun t' m' r' =>
        decide ((t', r') ∈ exprRefs S t e) && decide (m' = m ∨ m' ∈ storedNames T)
        with hP
      set A : Rec := fun t' m' r' => semAux S q.subject T q f t' m' r' && P t' m' r'
        with hA
      set B : Rec := fun t' m' r' => semAux S q.subject T q (f + 1) t' m' r' && P t' m' r'
        with hB
      have hmask : ∀ (rec : Rec) t' m' r', (t', r') ∈ exprRefs S t e →
          (m' = m ∨ m' ∈ storedNames T) →
          (rec t' m' r' && P t' m' r') = rec t' m' r' := by
        intro rec t' m' r' hk' hm'
        rw [hP]
        simp only [decide_eq_true hk', decide_eq_true hm', Bool.and_true]
      have hAgree1 : evalE A q.subject T q t m r e
          = evalE (semAux S q.subject T q f) q.subject T q t m r e :=
        evalE_congr S T q hDecl q.subject t m r e
          (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
      have hAgree2 : evalE B q.subject T q t m r e
          = evalE (semAux S q.subject T q (f + 1)) q.subject T q t m r e :=
        evalE_congr S T q hDecl q.subject t m r e
          (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
      have hle : RecLe A B := by
        intro t' m' r' hAt
        rw [hA, hB] at *
        simp only [Bool.and_eq_true] at hAt ⊢
        obtain ⟨hsem, hPt⟩ := hAt
        refine ⟨?_, hPt⟩
        have hPt' := hPt
        rw [hP] at hPt'
        simp only [Bool.and_eq_true, decide_eq_true_eq] at hPt'
        obtain ⟨hkey, hname⟩ := hPt'
        by_cases hdecl' : (t', r') ∈ S.keys
        · have hu' : (t', r') ∉ taintedKeys S := by
            refine hrefs (t', r') ?_
            show (t', r') ∈ refsOf S (t, r)
            unfold refsOf
            rw [hlk]
            exact hkey
          have hm'' : m' ∈ relevantNames T q := by
            rcases hname with rfl | hs
            · exact hm
            · exact List.mem_cons_of_mem _ hs
          exact ih t' r' hdecl' hu' m' hm'' hsem
        · rw [semAux_undeclared S q.subject T q hdecl' f m'] at hsem
          exact absurd hsem (by simp)
      rw [semAux, step, hlk] at h ⊢
      have h1 : evalE A q.subject T q t m r e = true := by rw [hAgree1]; exact h
      have h2 := evalE_mono hle q.subject T q t m r e hne h1
      rwa [hAgree2] at h2

/-! ## Counting stabilization of the untainted fragment -/

/-- The untainted declared keys. -/
def untaintedKeysF (S : Schema) : Finset Key :=
  S.keys.toFinset \ (taintedKeys S).toFinset

/-- The finite atom space the untainted evaluation lives on. -/
def atomsU (S : Schema) (T : Store) (q : Query) : Finset (Key × String) :=
  untaintedKeysF S ×ˢ (relevantNames T q).toFinset

/-- The untainted relevant atoms true at fuel `f`. -/
def trueSet (S : Schema) (T : Store) (q : Query) (f : Nat) : Finset (Key × String) :=
  (atomsU S T q).filter (fun a => semAux S q.subject T q f a.1.1 a.2 a.1.2 = true)

theorem mem_atomsU {S : Schema} {T : Store} {q : Query} {a : Key × String}
    (ha : a ∈ atomsU S T q) :
    (a.1 ∈ S.keys ∧ a.1 ∉ taintedKeys S) ∧ a.2 ∈ relevantNames T q := by
  unfold atomsU untaintedKeysF at ha
  rw [Finset.mem_product, Finset.mem_sdiff, List.mem_toFinset, List.mem_toFinset,
    List.mem_toFinset] at ha
  exact ha

theorem trueSet_mono (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    (f : Nat) : trueSet S T q f ⊆ trueSet S T q (f + 1) := by
  intro a ha
  rw [trueSet, Finset.mem_filter] at ha ⊢
  obtain ⟨haU, hsem⟩ := ha
  obtain ⟨⟨hk, hu⟩, hm⟩ := mem_atomsU haU
  exact ⟨haU, semAux_mono_untainted S T q hDecl f a.1.1 a.1.2 hk hu a.2 hm hsem⟩

/-- Determinism: a level on which the untainted true-set is unchanged is followed
    only by unchanged levels — the next level is a function (`step_congr`) of the
    current one on the (closed) untainted atom space. -/
theorem trueSet_det (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    (f : Nat) (heq : trueSet S T q f = trueSet S T q (f + 1)) :
    trueSet S T q (f + 1) = trueSet S T q (f + 2) := by
  have hstable : ∀ a ∈ atomsU S T q,
      semAux S q.subject T q f a.1.1 a.2 a.1.2
        = semAux S q.subject T q (f + 1) a.1.1 a.2 a.1.2 := by
    intro a ha
    refine bool_eq_of_true_iff ?_
    constructor
    · intro ht
      have : a ∈ trueSet S T q f := by rw [trueSet, Finset.mem_filter]; exact ⟨ha, ht⟩
      rw [heq, trueSet, Finset.mem_filter] at this
      exact this.2
    · intro ht
      have : a ∈ trueSet S T q (f + 1) := by
        rw [trueSet, Finset.mem_filter]; exact ⟨ha, ht⟩
      rw [← heq, trueSet, Finset.mem_filter] at this
      exact this.2
  unfold trueSet
  refine Finset.filter_congr (fun a ha => ?_)
  obtain ⟨⟨hk, hu⟩, hm⟩ := mem_atomsU ha
  obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
  have hrefs := (untainted_closed S hk hu).2
  have hstep : semAux S q.subject T q (f + 1) a.1.1 a.2 a.1.2
      = semAux S q.subject T q (f + 2) a.1.1 a.2 a.1.2 := by
    show step S q.subject T q (semAux S q.subject T q f) a.1.1 a.2 a.1.2
      = step S q.subject T q (semAux S q.subject T q (f + 1)) a.1.1 a.2 a.1.2
    refine step_congr S T q hDecl q.subject a.1.1 a.2 a.1.2 (fun t' m' r' hk' hm' => ?_)
    by_cases hdecl' : (t', r') ∈ S.keys
    · have hu' : (t', r') ∉ taintedKeys S := hrefs (t', r') hk'
      have hm'' : m' ∈ relevantNames T q := by
        rcases hm' with rfl | hs
        · exact hm
        · exact List.mem_cons_of_mem _ hs
      exact hstable ((t', r'), m') (by
        unfold atomsU untaintedKeysF
        rw [Finset.mem_product, Finset.mem_sdiff, List.mem_toFinset, List.mem_toFinset,
          List.mem_toFinset]
        exact ⟨⟨hdecl', hu'⟩, hm''⟩)
    · rw [semAux_undeclared S q.subject T q hdecl' f m',
        semAux_undeclared S q.subject T q hdecl' (f + 1) m']
  rw [hstep]

/-- **Untainted stabilization.** From fuel `|atomsU|` on, every untainted declared
    atom with a relevant name is fuel-stable. -/
theorem untainted_stable (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) :
    ∀ f, (atomsU S T q).card ≤ f →
      ∀ t r, (t, r) ∈ S.keys → (t, r) ∉ taintedKeys S →
      ∀ m ∈ relevantNames T q,
      semAux S q.subject T q f t m r = semAux S q.subject T q (f + 1) t m r := by
  have hstab := chain_stabilizes (trueSet S T q) (atomsU S T q).card
    (trueSet_mono S T q hDecl) (trueSet_det S T q hDecl) (by
      unfold trueSet
      refine Finset.filter_false_of_mem (fun a _ => ?_)
      simp [semAux])
    (fun i => Finset.card_le_card (Finset.filter_subset _ _))
  intro f hf t r hk hu m hm
  have hpers := chain_persists (trueSet S T q) (trueSet_det S T q hDecl) hstab f hf
  have ha : ((t, r), m) ∈ atomsU S T q := by
    unfold atomsU untaintedKeysF
    rw [Finset.mem_product, Finset.mem_sdiff, List.mem_toFinset, List.mem_toFinset,
      List.mem_toFinset]
    exact ⟨⟨hk, hu⟩, hm⟩
  refine bool_eq_of_true_iff ?_
  constructor
  · intro ht
    have : ((t, r), m) ∈ trueSet S T q f := by
      rw [trueSet, Finset.mem_filter]; exact ⟨ha, ht⟩
    rw [hpers, trueSet, Finset.mem_filter] at this
    exact this.2
  · intro ht
    have : ((t, r), m) ∈ trueSet S T q (f + 1) := by
      rw [trueSet, Finset.mem_filter]; exact ⟨ha, ht⟩
    rw [← hpers, trueSet, Finset.mem_filter] at this
    exact this.2

end Zanzibar
