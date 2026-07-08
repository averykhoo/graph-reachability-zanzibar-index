import ZanzibarProofs.Core.Store
import ZanzibarProofs.SetEngine.MemberSet

/-!
# The set-engine model — `check`

`SEMANTICS.md` §6.3. The set engine evaluates the AST pointwise, using the
`MemberSet` algebra at `Direct` leaves and boolean folds
(Union→`union`, Intersection→`intersect`, Exclusion→`subtract`) at operators.

**Phase status.** For Phase 1 this is an `opaque` placeholder so theorem statements
compile without making T1 vacuous. **Phase 3 replaces this declaration with the
real MemberSet-expand model** (`setengine/engine.py` mirror) and proves T1 using
the `MemberSet` algebra lemmas.
-/

namespace Zanzibar
namespace SetEngineModel

/-- The set-engine `check`. Opaque placeholder (Phase 3 supplies the definition). -/
opaque check : Schema → Store → Query → Bool

end SetEngineModel
end Zanzibar
