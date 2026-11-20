---
type: Task
id: TK-305
title: "TK-185 verifier notes: '...' lookup-filter asymmetry; stale WildcardIndex.check comment; result_keys check-order warning; ensure_schema SchemaMismatch on a bad shape; expand arity message names o_type/o_name"
brief: small HONEST cleanups; the wildcard.py comment is content-pinned, so move the pin deliberately
pri: LATER
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-20a
---

TK-185 verifier notes: small HONEST cleanups left by the 0.1.3 batch (independent verifier, SHIP WITH NOTES, 2026-11-20).

1. `...` lookup-filter asymmetry: `Store.lookup(..., object_type='doc', relation='...')` refuses (`relation='...' names an undeclared relation doc#...`), while `SetEngine.filter_result(se.lookup(...), 'doc', '...')` answers empty. A refusal-surface asymmetry only; no permission answer differs. It was agent D's PROVISIONAL call (`filter_result` is bare=True because it filters both directions). Decide: make them agree, or document the difference.
2. Stale comment: `src/zanzibar/graphindex/wildcard.py::WildcardIndex.check` provenance comment (~line 869, dated 2026-11-20) says "Matches the set engine and the oracle on undeclared names"; the set engine now raises. The body is content-pinned, so the edit moves a pin deliberately.
3. The `result_keys` docstring lacks the check-order warning (a key is `(type, name, predicate)`; check takes `(subject_predicate, subject_type, subject_name, ...)`).
4. `src/zanzibar/store/schema_io.py::ensure_schema` skips `require_shapes` when the schema row exists: a bad shape (3-list, str, dict) then raises `SchemaMismatch`, not `TypeError`. Internal path (not in `zanzibar.store.__all__`); every public caller runs `require_shapes` first. Wrong class, never a wrong answer.
5. `expand`'s arity message names its params `o_type, o_name`, while `lookup_reverse`'s names `object_type, object_name`. Renaming params would break keyword callers; fix the message, not the signature.

## Traps

- none yet

## Read first

- docs/tk185-0.1.3-batch-2026-11-20.md (section "Residual (filed at the close, not fixed here)")

## Log
