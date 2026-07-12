import Mathlib.Data.Finset.Basic
import Mathlib.Data.List.Basic

/-!
# Core identifiers and sentinels

See `SEMANTICS.md` §2.1. Identifiers are opaque strings; two sentinels are
distinguished. `ValidIdent` is taken as an OPAQUE predicate (the spec does not
re-derive the charset regex — plan §2.1); no proof unfolds it or derives
structural facts from it.
-/

namespace Zanzibar

/-- The wildcard-name sentinel `"*"`. May appear as a subject/object *name*. -/
def STAR : String := "*"

/-- The bare-subject-predicate sentinel `"..."`. May appear as a subject
    *predicate*. -/
def BARE : String := "..."

theorem star_ne_bare : STAR ≠ BARE := by decide

/-- Charset+length validity of an identifier (`validate_write_identifiers`,
    `zanzibar_utils_v1.py:22-57`). Deliberately OPAQUE: no proof unfolds it and no
    structural lemmas are derived from it. It enters the theorems only through the
    carried hypothesis `AllValid` (`SetEngine/Correct.lean`) — retained in the
    T1/T3 statements but unused by their proofs, and (being opaque) NOT
    dischargeable for a concrete store inside the model (cf. the `W4Witness` note
    in `FullScope.lean`). Star/bare sentinel distinctions are made by explicit
    store hypotheses (`StarFreeStore`, `BareStarStore`, …), never via
    `ValidIdent`. -/
opaque ValidIdent : String → Prop

end Zanzibar
