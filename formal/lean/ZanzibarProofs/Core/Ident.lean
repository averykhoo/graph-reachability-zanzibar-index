import Mathlib.Data.Finset.Basic
import Mathlib.Data.List.Basic

/-!
# Core identifiers and sentinels

See `SEMANTICS.md` §2.1. Identifiers are opaque strings; two sentinels are
distinguished. Star/bare sentinel distinctions are made by explicit store
hypotheses (`StarFreeStore`, `BareStarStore`, …), never by a validity predicate.

**No identifier-validity predicate (since 2026-09-06).** This file used to declare
`opaque ValidIdent : String → Prop` — the charset+length validity of
`zanzibar_utils_v1.py::validate_write_identifiers` — which entered the theorems only
through `AllValid` (`SetEngine/Correct.lean`), a hypothesis of T1/T3/T6a that no
proof ever used and that, being built on an opaque, could not be discharged for any
non-empty concrete store; it was the sole reason the headline `backend_equivalence`
had no instantiation. Both declarations were deleted together with that hypothesis
(the tree now carries NO `opaque`). The Python write-validation correspondence lives
where a proof actually consumes it: `GraphAdmission.keysNonempty`
(`FullScope.lean`; the `FullScope.lean::GraphAdmission` row of `CORRESPONDENCE.md` §6).
-/

namespace Zanzibar

/-- The wildcard-name sentinel `"*"`. May appear as a subject/object *name*. -/
def STAR : String := "*"

/-- The bare-subject-predicate sentinel `"..."`. May appear as a subject
    *predicate*. -/
def BARE : String := "..."

theorem star_ne_bare : STAR ≠ BARE := by decide

end Zanzibar
