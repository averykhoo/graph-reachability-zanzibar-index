import Mathlib.Data.Finset.Basic
import Mathlib.Data.List.Basic

/-!
# Core identifiers and sentinels

See `SEMANTICS.md` §2.1. Identifiers are opaque strings; two sentinels are
distinguished. `ValidIdent` is taken as a predicate (the spec does not re-derive
the charset regex — plan §2.1); we only rely on the two structural facts recorded
below.
-/

namespace Zanzibar

/-- The wildcard-name sentinel `"*"`. May appear as a subject/object *name*. -/
def STAR : String := "*"

/-- The bare-subject-predicate sentinel `"..."`. May appear as a subject
    *predicate*. -/
def BARE : String := "..."

theorem star_ne_bare : STAR ≠ BARE := by decide

/-- Charset+length validity of an identifier (`validate_write_identifiers`,
    `zanzibar_utils_v1.py:22-57`). Kept abstract: the spec relies only on the two
    structural consequences `ValidIdent.ne_star` / `ValidIdent.ne_bare` below,
    supplied per-store as hypotheses, not on the concrete regex. -/
opaque ValidIdent : String → Prop

end Zanzibar
