import Mathlib.Data.Finset.Basic
import Mathlib.Data.Finset.Lattice.Basic
import Mathlib.Data.Finset.Union
import ZanzibarProofs.Core.Refs

/-!
# The `MemberSet` star-closed set algebra

`SEMANTICS.md` §6, transcribed from `setengine/memberset.py`. A `MemberSet`
represents a subject set that may be co-finite relative to declared star shapes.

Extensional meaning over a population `pop : Shape → Finset Id`:
`ext(M) = pos ∪ (starpop(stars) \ neg)`, with `pos` winning over `neg`
(`setengine/memberset.py` module docstring, and `setengine/memberset.py::_ext`).
Normal-form invariant (from `setengine/memberset.py::_normalize`):
`pos ∩ starpop = ∅` and `neg ⊆ starpop`.

Ids are modeled as an abstract type with decidable equality (the interner /
roaring representation is out of scope — plan §1).
-/

namespace Zanzibar

variable {Id : Type} [DecidableEq Id]

/-- A star-closed member set. `stars` holds covered shapes (intensional); `pos`
    holds concrete ids not under any star; `neg` holds star-covered exclusions. -/
structure MemberSet (Id : Type) where
  pos : Finset Id
  stars : Finset Shape
  neg : Finset Id
deriving DecidableEq

namespace MemberSet

/-- The population of a set of shapes: `⋃_{σ∈stars} pop(σ)`
    (`setengine/memberset.py::_starpop`). -/
def starpop (pop : Shape → Finset Id) (stars : Finset Shape) : Finset Id :=
  stars.biUnion pop

/-- The extensional meaning `pos ∪ (starpop \ neg)` (`setengine/memberset.py::_ext`). -/
def ext (pop : Shape → Finset Id) (m : MemberSet Id) : Finset Id :=
  m.pos ∪ (starpop pop m.stars \ m.neg)

/-- Renormalize an extensional target `E` with star set `S` into canonical form:
    `pos = E \ starpop`, `neg = starpop \ E` (`setengine/memberset.py::_normalize`). -/
def normalize (pop : Shape → Finset Id) (E : Finset Id) (S : Finset Shape) : MemberSet Id :=
  let sp := starpop pop S
  { pos := E \ sp, stars := S, neg := sp \ E }

/-- `union` (`setengine/memberset.py::union`): `E = ext a ∪ ext b`,
    `stars = a.stars ∪ b.stars`. -/
def union (pop : Shape → Finset Id) (a b : MemberSet Id) : MemberSet Id :=
  normalize pop (ext pop a ∪ ext pop b) (a.stars ∪ b.stars)

/-- `intersect` (`setengine/memberset.py::intersect`): `E = ext a ∩ ext b`,
    `stars = a.stars ∩ b.stars`. -/
def intersect (pop : Shape → Finset Id) (a b : MemberSet Id) : MemberSet Id :=
  normalize pop (ext pop a ∩ ext pop b) (a.stars ∩ b.stars)

/-- `subtract` (`setengine/memberset.py::subtract`): `E = ext a \ ext b`,
    `stars = a.stars \ b.stars`. -/
def subtract (pop : Shape → Finset Id) (a b : MemberSet Id) : MemberSet Id :=
  normalize pop (ext pop a \ ext pop b) (a.stars \ b.stars)

/-- The empty member set (`setengine/memberset.py::empty`). -/
def empty : MemberSet Id := { pos := ∅, stars := ∅, neg := ∅ }

/-- A single concrete member (`setengine/memberset.py::singleton_entity`). -/
def singletonEntity (uid : Id) : MemberSet Id := { pos := {uid}, stars := ∅, neg := ∅ }

/-- A single covered star shape (`setengine/memberset.py::star`). -/
def star (shape : Shape) : MemberSet Id := { pos := ∅, stars := {shape}, neg := ∅ }

/-- `contains_star` — intensional shape membership
    (`setengine/memberset.py::MemberSet.contains_star`). -/
def containsStar (m : MemberSet Id) (shape : Shape) : Bool := shape ∈ m.stars

/-- `_contains(uid, shape)` — the ghost-safe INTENSIONAL membership: covered if in
    `pos`, or if `shape ∈ stars` and not excluded
    (`setengine/memberset.py::MemberSet._contains`). Note this
    uses `shape ∈ stars` (not `uid ∈ starpop`), so a ghost never mentioned in any
    tuple is still covered — the distinction from `ext` that matters for `'*'` and
    ghost queries. -/
def containsShape (m : MemberSet Id) (uid : Id) (shape : Shape) : Bool :=
  decide (uid ∈ m.pos) || (decide (shape ∈ m.stars) && decide (uid ∉ m.neg))

/-- `contains_entity`: a concrete entity is covered by the BARE star of its type
    (`setengine/memberset.py::MemberSet.contains_entity`). -/
def containsEntity (m : MemberSet Id) (uid : Id) (utype : String) : Bool :=
  m.containsShape uid (utype, BARE)

/-- `contains_userset` (`setengine/memberset.py::MemberSet.contains_userset`). -/
def containsUserset (m : MemberSet Id) (uid : Id) (shape : Shape) : Bool :=
  m.containsShape uid shape

/-! ### Algebra lemmas (the workhorses of T1) — first one proved; rest in `Algebra.lean`. -/

/-- Renormalization preserves the extension: `ext (normalize E S) = E`,
    unconditionally — the core correctness of the one recipe
    (the renormalisation recipe in `setengine/memberset.py`'s module docstring,
    implemented by `::_normalize`). -/
theorem ext_normalize (pop : Shape → Finset Id) (E : Finset Id) (S : Finset Shape) :
    ext pop (normalize pop E S) = E := by
  ext x
  simp only [ext, normalize, starpop, Finset.mem_union, Finset.mem_sdiff]
  tauto

end MemberSet
end Zanzibar
