import ZanzibarProofs.Core.Ident

/-!
# References, tuples, shapes

The domain of `SEMANTICS.md` §2.2, transcribed from the oracle's tuple layout
(`tests/oracle.py:54-67`). A subject's `predicate = BARE` marks a bare entity;
any other value is a userset relation. A `name = STAR` marks a wildcard.
-/

namespace Zanzibar

/-- An object reference `(type, name)`. `name = STAR` ⇒ object wildcard. -/
structure ObjectRef where
  type : String
  name : String
deriving DecidableEq, Repr, Inhabited

/-- A subject reference `(type, name, predicate)`. `name = STAR` ⇒ subject
    wildcard; `predicate = BARE` ⇒ bare entity, else a userset relation. -/
structure SubjectRef where
  type : String
  name : String
  predicate : String
deriving DecidableEq, Repr, Inhabited

/-- A stored relation tuple. -/
structure Tuple where
  subject : SubjectRef
  relation : String
  object : ObjectRef
deriving DecidableEq, Repr, Inhabited

/-- A shape `(type, predicate)`: bare `(T, BARE)` or userset `(T, P)`.
    See `memberset.py:42`, `wildcard-materialization-spec.md §1.1`. -/
abbrev Shape := String × String

/-- The shape of a subject reference. -/
def SubjectRef.shape (s : SubjectRef) : Shape := (s.type, s.predicate)

/-- Is this subject the wildcard sentinel? -/
def SubjectRef.isStar (s : SubjectRef) : Bool := s.name = STAR

/-- Is this subject a bare entity (as opposed to a userset)? -/
def SubjectRef.isBare (s : SubjectRef) : Bool := s.predicate = BARE

/-- Is this object the wildcard sentinel? -/
def ObjectRef.isStar (o : ObjectRef) : Bool := o.name = STAR

end Zanzibar
