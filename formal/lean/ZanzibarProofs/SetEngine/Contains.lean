import ZanzibarProofs.SetEngine.Algebra

/-!
# Intensional membership (`containsShape`) distribution — the corrected T1 core

`SEMANTICS.md` §5.6, §6. The T1 proof needs `containsShape` (the ghost-safe
intensional membership the set engine's `check` uses) to distribute over the
boolean operations. This file supplies those laws — but **not** in the naive form
the earlier ROADMAP proposed.

**Correction (this file's reason to exist).** The naive law
`containsShape (op a b) uid shape = containsShape a uid shape ⟨op⟩ containsShape b uid shape`
is **FALSE** under `WF` alone. Concretely (verified by `#eval`), for
`a = {stars := {σ}}`, `b = {stars := {shape}, neg := {uid}}` with `uid ∈ pop σ`
and `σ ≠ shape`, both operands answer `false` for `shape` but `union a b` answers
`true` — merging the star sets recovers `uid` via `shape`. Both `a`, `b` are `WF`.

The fix is the missing modeling invariant `PopFocus`: the set engine always queries
a subject at *its own* shape, and populations partition the id space by shape, so
the only `σ` with `uid ∈ pop σ` is `shape` itself. Under `PopFocus`:

* **union** distributes with just `WFp` on the operands;
* **intersect / subtract** additionally need `Grounded` (a concrete positive member
  lies in its own population) — without it a positive *ghost* is dropped by the
  extensional meet/difference. Both are again verified false without it.

These are the honest hypotheses T1's concrete model must establish for each node.
-/

namespace Zanzibar
namespace MemberSet

variable {Id : Type} [DecidableEq Id]

/-- Well-formedness of a member set relative to a population: `pos` avoids the star
    population and `neg` lives inside it (the `_normalize` normal form,
    `memberset.py:99-105`). -/
def WFp (pop : Shape → Finset Id) (m : MemberSet Id) : Prop :=
  Disjoint m.pos (starpop pop m.stars) ∧ m.neg ⊆ starpop pop m.stars

/-- Every operation output is `WFp` (all three are `normalize`s). -/
theorem wfp_normalize (pop : Shape → Finset Id) (E : Finset Id) (S : Finset Shape) :
    WFp pop (normalize pop E S) := by
  constructor
  · rw [Finset.disjoint_left]
    intro x hx hx2
    simp only [normalize, Finset.mem_sdiff] at hx
    exact hx.2 hx2
  · intro x hx
    simp only [normalize, Finset.mem_sdiff] at hx
    exact hx.1

theorem wfp_union (pop : Shape → Finset Id) (a b : MemberSet Id) :
    WFp pop (union pop a b) := wfp_normalize _ _ _

theorem wfp_intersect (pop : Shape → Finset Id) (a b : MemberSet Id) :
    WFp pop (intersect pop a b) := wfp_normalize _ _ _

theorem wfp_subtract (pop : Shape → Finset Id) (a b : MemberSet Id) :
    WFp pop (subtract pop a b) := wfp_normalize _ _ _

/-- `pop` is focused at `(uid, shape)`: the only shape whose population contains
    `uid` is `shape` itself. Holds in `check` because a subject is queried at its
    own shape and populations partition the id space by shape. -/
def PopFocus (pop : Shape → Finset Id) (uid : Id) (shape : Shape) : Prop :=
  ∀ σ, uid ∈ pop σ → σ = shape

/-- A member set is `pos`-grounded at `(uid, shape)`: a concrete positive member
    equal to `uid` lies in the population of `shape`. True of sets arising from real
    expansion (`pos` comes from existing entities, which are in `pop`). Needed for
    intersect/subtract (not union): otherwise a positive ghost is dropped. -/
def Grounded (pop : Shape → Finset Id) (uid : Id) (shape : Shape) (m : MemberSet Id) : Prop :=
  uid ∈ m.pos → uid ∈ pop shape

/-- Under `PopFocus`, star-population membership collapses to the focused shape. -/
theorem mem_starpop_focus {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (h : PopFocus pop uid shape) (S : Finset Shape) :
    uid ∈ starpop pop S ↔ (shape ∈ S ∧ uid ∈ pop shape) := by
  unfold starpop
  rw [Finset.mem_biUnion]
  constructor
  · rintro ⟨σ, hσS, hσ⟩
    have := h σ hσ; subst this; exact ⟨hσS, hσ⟩
  · rintro ⟨hS, hp⟩; exact ⟨shape, hS, hp⟩

/-- `containsShape` after a `normalize`, in atomic form. -/
theorem containsShape_normalize (pop : Shape → Finset Id) (E : Finset Id)
    (S : Finset Shape) (uid : Id) (shape : Shape) :
    containsShape (normalize pop E S) uid shape = true ↔
      (uid ∈ E ∧ uid ∉ starpop pop S) ∨
      (shape ∈ S ∧ ¬(uid ∈ starpop pop S ∧ uid ∉ E)) := by
  simp only [containsShape, normalize, Bool.or_eq_true, Bool.and_eq_true,
    decide_eq_true_eq, Finset.mem_sdiff]

/-- Bool equality from a `= true` iff. -/
theorem bool_ext {x y : Bool} (h : x = true ↔ y = true) : x = y := by
  cases x <;> cases y <;> simp_all

/-- Membership in `ext` broken into atoms via `PopFocus`. -/
theorem mem_ext_focus {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (h : PopFocus pop uid shape) (m : MemberSet Id) :
    uid ∈ ext pop m ↔ uid ∈ m.pos ∨ (shape ∈ m.stars ∧ uid ∈ pop shape ∧ uid ∉ m.neg) := by
  simp only [ext, Finset.mem_union, Finset.mem_sdiff]
  rw [mem_starpop_focus h]
  tauto

/-- Atom-level consequences of `WFp` at the focused `(uid, shape)`. -/
theorem wfp_atoms {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (hf : PopFocus pop uid shape) {m : MemberSet Id} (w : WFp pop m) :
    (uid ∈ m.neg → shape ∈ m.stars ∧ uid ∈ pop shape) ∧
    (uid ∈ m.pos → ¬(shape ∈ m.stars ∧ uid ∈ pop shape)) := by
  refine ⟨fun h => (mem_starpop_focus hf m.stars).mp (w.2 h), fun h hc => ?_⟩
  exact (Finset.disjoint_left.mp w.1 h) ((mem_starpop_focus hf m.stars).mpr hc)

/-- **T1 distribution — union.** Under `PopFocus` (query at own shape) and `WFp`
    operands, `containsShape` distributes over `union`. FALSE without `PopFocus`. -/
theorem containsShape_union_focus {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (hf : PopFocus pop uid shape) {a b : MemberSet Id}
    (wa : WFp pop a) (wb : WFp pop b) :
    containsShape (union pop a b) uid shape =
      (containsShape a uid shape || containsShape b uid shape) := by
  obtain ⟨ha1, ha2⟩ := wfp_atoms hf wa
  obtain ⟨hb1, hb2⟩ := wfp_atoms hf wb
  apply bool_ext
  unfold union
  rw [containsShape_normalize]
  simp only [mem_starpop_focus hf, Finset.mem_union, mem_ext_focus hf,
    containsShape, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  by_cases hpa : uid ∈ a.pos <;> by_cases hsa : shape ∈ a.stars <;>
    by_cases hna : uid ∈ a.neg <;> by_cases hpb : uid ∈ b.pos <;>
    by_cases hsb : shape ∈ b.stars <;> by_cases hnb : uid ∈ b.neg <;>
    by_cases hps : uid ∈ pop shape <;> simp_all

/-- **T1 distribution — intersect.** Needs `PopFocus`, `WFp`, and `Grounded`. -/
theorem containsShape_intersect_focus {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (hf : PopFocus pop uid shape) {a b : MemberSet Id}
    (wa : WFp pop a) (wb : WFp pop b) (ga : Grounded pop uid shape a)
    (gb : Grounded pop uid shape b) :
    containsShape (intersect pop a b) uid shape =
      (containsShape a uid shape && containsShape b uid shape) := by
  obtain ⟨ha1, ha2⟩ := wfp_atoms hf wa
  obtain ⟨hb1, hb2⟩ := wfp_atoms hf wb
  apply bool_ext
  unfold intersect
  rw [containsShape_normalize]
  simp only [mem_starpop_focus hf, Finset.mem_inter,
    mem_ext_focus hf, containsShape, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  unfold Grounded at ga gb
  by_cases hpa : uid ∈ a.pos <;> by_cases hsa : shape ∈ a.stars <;>
    by_cases hna : uid ∈ a.neg <;> by_cases hpb : uid ∈ b.pos <;>
    by_cases hsb : shape ∈ b.stars <;> by_cases hnb : uid ∈ b.neg <;>
    by_cases hps : uid ∈ pop shape <;> simp_all

/-- **T1 distribution — subtract.** Needs `PopFocus`, `WFp`, and `Grounded`. -/
theorem containsShape_subtract_focus {pop : Shape → Finset Id} {uid : Id} {shape : Shape}
    (hf : PopFocus pop uid shape) {a b : MemberSet Id}
    (wa : WFp pop a) (wb : WFp pop b) (ga : Grounded pop uid shape a)
    (gb : Grounded pop uid shape b) :
    containsShape (subtract pop a b) uid shape =
      (containsShape a uid shape && !containsShape b uid shape) := by
  obtain ⟨ha1, ha2⟩ := wfp_atoms hf wa
  obtain ⟨hb1, hb2⟩ := wfp_atoms hf wb
  apply bool_ext
  unfold subtract
  rw [containsShape_normalize]
  simp only [mem_starpop_focus hf, Finset.mem_sdiff,
    mem_ext_focus hf, containsShape, Bool.or_eq_true, Bool.and_eq_true, Bool.not_eq_true',
    decide_eq_true_eq]
  unfold Grounded at ga gb
  by_cases hpa : uid ∈ a.pos <;> by_cases hsa : shape ∈ a.stars <;>
    by_cases hna : uid ∈ a.neg <;> by_cases hpb : uid ∈ b.pos <;>
    by_cases hsb : shape ∈ b.stars <;> by_cases hnb : uid ∈ b.neg <;>
    by_cases hps : uid ∈ pop shape <;> simp_all

end MemberSet
end Zanzibar
