import ZanzibarProofs.SetEngine.MemberSet

/-!
# MemberSet algebra correctness — the workhorse lemmas for T1

`SEMANTICS.md` §6, `theory.md:143-159`. Each operation's extension equals the
set-theoretic operation on the operands' extensions, and its star set folds by the
matching boolean on shape sets. These are exactly the properties
`setengine/memberset.py`'s brute-force property suite checks; here they are proved
once and reused by T1.

All three extensional laws are immediate from `ext_normalize` (already proved),
because every operation is `normalize (⟨op⟩ of the extensions) (⟨op⟩ of the stars)`.
-/

namespace Zanzibar
namespace MemberSet

variable {Id : Type} [DecidableEq Id] (pop : Shape → Finset Id) (a b : MemberSet Id)

/-- **Union extension law.** `ext (a ∪ b) = ext a ∪ ext b`. -/
@[simp] theorem ext_union : ext pop (union pop a b) = ext pop a ∪ ext pop b := by
  unfold union; rw [ext_normalize]

/-- **Intersection extension law.** `ext (a ∩ b) = ext a ∩ ext b`. -/
@[simp] theorem ext_intersect : ext pop (intersect pop a b) = ext pop a ∩ ext pop b := by
  unfold intersect; rw [ext_normalize]

/-- **Subtraction extension law.** `ext (a \ b) = ext a \ ext b`. -/
@[simp] theorem ext_subtract : ext pop (subtract pop a b) = ext pop a \ ext pop b := by
  unfold subtract; rw [ext_normalize]

/-- **Union star law** (`memberset.py:26`). -/
@[simp] theorem stars_union : (union pop a b).stars = a.stars ∪ b.stars := rfl

/-- **Intersection star law** (`memberset.py:27`). -/
@[simp] theorem stars_intersect : (intersect pop a b).stars = a.stars ∩ b.stars := rfl

/-- **Subtraction star law** (`memberset.py:28`). -/
@[simp] theorem stars_subtract : (subtract pop a b).stars = a.stars \ b.stars := rfl

/-- Intensional `'*'`-query law for union: covered iff covered in either
    (`SEMANTICS.md` §5.6, first row). -/
theorem containsStar_union (shape : Shape) :
    containsStar (union pop a b) shape = (containsStar a shape || containsStar b shape) := by
  simp [containsStar, stars_union, Finset.mem_union]

/-- Intensional `'*'`-query law for intersection: covered iff covered in both. -/
theorem containsStar_intersect (shape : Shape) :
    containsStar (intersect pop a b) shape = (containsStar a shape && containsStar b shape) := by
  simp [containsStar, stars_intersect, Finset.mem_inter]

/-- Intensional `'*'`-query law for subtraction: covered iff covered in A and not B
    — the corner that makes a concrete-only exclusion NOT defeat a `'*'` query
    (`SEMANTICS.md` §5.6). -/
theorem containsStar_subtract (shape : Shape) :
    containsStar (subtract pop a b) shape = (containsStar a shape && !containsStar b shape) := by
  simp [containsStar, stars_subtract, Finset.mem_sdiff]

end MemberSet
end Zanzibar
