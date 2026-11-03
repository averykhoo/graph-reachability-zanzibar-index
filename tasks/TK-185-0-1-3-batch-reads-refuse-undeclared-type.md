---
type: Task
id: TK-185
aliases: [TK185]
title: '0.1.3 batch: reads refuse undeclared type/relation, trial fixes C3-C8, mypy drift'
brief: 'DECIDED plan on the row (Log 2026-11-01): C4/C3/C6 code, reads ERROR on undeclared type/relation (C5+C7), wording, TK183'
pri: NOW
state: open
size: L
deps: []
related: [TK179, TK178, TK184]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-11-01
taskpy_moved: '2026-11-01'
taskpy_updated: '2026-11-01'
---

From the 0.1.2 fresh-user install trial (`docs/pypi-trial-0.1.2-2026-11-01.md`): 0 BROKEN, 8 CONFUSING / DOC GAP. C4 is its own row. This row holds the rest. Each needs a decision: fix the behaviour or fix the wording. Equivalence is unaffected; no wrong permission answer was found.

- **C5 (most important): a result key fed back into `check` silently answers False.** `result_keys` yields `(type, name, predicate)` but the six-part call is `(subject_predicate, subject_type, subject_name, ...)`, so `check(*key, "viewer", "doc", "1")` is False where the right order is True. Re-run FIRST-HAND against `src/` 2026-11-01: `check(*('user','alice','...'), 'viewer','doc','1') -> False`, `check('...','user','alice',...) -> True`. The write side refuses the same misorder. Options: a doc warning on `result_keys`; a helper that turns a key into a check call; or treat a predicate that is a declared TYPE name (or a type that is `...`) as a TypeError on reads.
- **C1 / C8: wording.** A write's non-string relation (`add_tuple("user:a", None, "doc:1")`) and a non-string `store_id` (`Store(s, 123, ...)`) are `AdmissionRejected`, not `TypeError`. Re-run FIRST-HAND, both confirmed. This is deliberate (TK179 kept write identifiers on `AdmissionRejected`), but the 0.1.2 release notes read as "every public argument ... TypeError". Fix the wording in CHANGELOG/userdocs, or move the type part to TypeError.
- **C2:** `None` as a subject predicate means bare on reads, is refused on writes, and means "no filter" on `lookup_reverse(subject_predicate=None)`. Document it in one place.
- **C3:** `ShapeNoLongerAccepted` for a malformed or undeclared `object_wildcard_shapes` entry: the rewrite is only in `e.instead`, not in `str(e)` (the exceptions reference says the message ends with it), and the class name implies an older release accepted it.
- **C6:** `SetEngine.check` / `lookup` have no `"user:a"` short form, and the missing-argument error is Python's own; `Store` gives a friendly message for the same mistake.
- **C7:** a typo'd relation on a read answers False. This is documented; consider a warning.
- Also from the trial: 6 public attributes have no docstring (`SchemaInfo.bridged_in_shapes` / `bridged_out_shapes`, `Entity.wildcard`, `CompiledBooleans.derived_families` / `leaf_families`, `Node.predicate_or_ellipsis`), and `how-to/test-permissions` needs pytest, which is not a dependency, without saying so.

## Read first
- docs/pypi-trial-0.1.2-2026-11-01.md

## Log

### 2026-11-01

Promoted to NOW at the 0.1.2 write-back (TK178 closed): C5 is the one trial finding where a plausible call (check(*key, ...)) silently gives the wrong-looking answer. Decide fix-vs-document per bullet, smallest first; C4 is TK184.

**THE 0.1.3 BATCH -- the decided plan (user 2026-11-01: "Okay to all your recommendations, put them all in a task up next").** Everything from the 0.1.2 install trial (`docs/pypi-trial-0.1.2-2026-11-01.md`) is here; `TK184` (C4) and `TK183` (mypy drift) are folded in and closed. Release 0.1.3 ONLY on the user's word, after the full gate. Do it in this order:

1. **C4 (was TK184), code.** `object_wildcard_shapes=[["folder", "viewer"]]` -> raw `TypeError: unhashable type: 'list'` (first-hand 2026-11-01). DECIDED: ACCEPT a 2-element list as a pair (JSON-loaded config produces lists); anything else is a TypeError NAMING `object_wildcard_shapes` and the entry. Site: `src/zanzibar/schema/argcheck.py::require_shapes` (it calls `frozenset(value)` before checking entries). Pin in `tests/test_tk179_public_arg_census.py` or a new test; sabotage red.
2. **C3, code.** `ShapeNoLongerAccepted` for a malformed or undeclared shape entry: put the rewrite (`e.instead`) INTO `str(e)`; `userdocs/reference/exceptions.md` already says the message ends with the rewrite. Keep the class (TK147 kept it for these on purpose).
3. **C6, code.** `SetEngine.check` / `lookup` with the 3-part `"user:a"` form give Python's own missing-argument error. DECIDED: give the same friendly "takes 6 arguments ..." error `Store` gives; do NOT add the short form to `SetEngine`.
4. **C5 + C7, the user's decision (2026-11-01): a READ naming an undeclared TYPE or RELATION is an ERROR, not a warning and not a silent False.** User: "An undeclared relation type - seems reasonable to error or warn loudly?" -> error (a warning still returns the silent False and gets filtered). Unknown NAMES (`doc:999`) still match nothing: asking about an object that does not exist yet is normal. This catches C5 (`check(*result_key, ...)` puts a NAME where the type goes: `('user','alice','...')` -> subject type `alice`) and C7 (typo'd relation). Design points to settle on the row, by the session (CLAUDE.md "Who decides"):
   - Exception: a `ValueError` subclass exported from `zanzibar` (TK164: refusals are ValueErrors; exceptions only from `zanzibar`), message naming what IS declared, and -- when the misplaced value matches a declared type or `...` sits in the name slot -- a hint that a result key is `(type, name, predicate)` while the six-part call is `(subject_predicate, subject_type, subject_name, ...)`.
   - Surfaces: `check` / `lookup` / `lookup_reverse` / `expand` on BOTH `Store` and `SetEngine`, subject and object side, and filters. Both backends must refuse identically (equivalence); `Store.check`'s set-engine fallback must not change the answer.
   - Undeclared subject PREDICATE on a userset subject (`group:eng#nosuch`): include it (it is a relation).
   - TRAP: the validation matrix / lookup oracle / hypothesis grids may deliberately include undeclared names and expect False. This is a deliberate user-decided behaviour change, so update those expectations deliberately and say so in the commit; the oracle itself (`tests/oracle.py`) keeps its independence and need not refuse. Never edit an oracle result to make a refactor pass -- here the SPEC changed, which is different; record it.
   - Docs to rewrite (all say reads are lenient about undeclared relations): `userdocs/explanation/semantics-vs-openfga.md` "Writes are strict, reads are lenient", `userdocs/reference/tuple-strings.md` same heading, `userdocs/how-to/errors.md` ~line 87, `userdocs/reference/exceptions.md` (AdmissionRejected row, "A read is not refused this way"), `src/zanzibar/schema/tuplestr.py` docstring ~line 154. CHANGELOG `### Changed`, flagged as a behaviour change.
   - Also add to the `result_keys` docstring/docs that keys are `(type, name, predicate)`.
5. **C1 / C8, wording only.** A write's non-string relation and a non-string `store_id` stay `AdmissionRejected` (the 0.1.0 promise for write identifiers; changing the class would break callers catching it). Fix the 0.1.2 wording in `userdocs/reference/changelog.md` and add a CHANGELOG `### Documentation` line: "a wrong type is a TypeError, EXCEPT a write identifier, which is AdmissionRejected".
6. **C2, docs.** `None` as subject predicate: bare on reads, refused on writes, "no filter" on `lookup_reverse(subject_predicate=None)`. Document all three in ONE place (tuple-strings reference), link from the others.
7. **Docs gaps.** Docstrings for `SchemaInfo.bridged_in_shapes` / `bridged_out_shapes`, `Entity.wildcard`, `CompiledBooleans.derived_families` / `leaf_families`, `Node.predicate_or_ellipsis` (`tests/test_tk169_public_docstrings.py` may be the place to pin). `userdocs/how-to/test-permissions` says it needs `pip install pytest`.
8. **TK183 (folded), gate.** `scripts/lint_gate.py` prints the sqlmodel / SQLAlchemy / pydantic versions it ran mypy with, so a local-green / CI-red split is readable from the log. Do NOT pin those libraries for the test run (CI's newest-deps install is how drift is caught). Optionally a line in `docs/gate-runbook.md`.
9. Full gate (+ fuzz sweep: item 4 changes read behaviour), commit, push, publish dry run; then ASK for the `v0.1.3` tag; babysit, PyPI, install trial + `installed_smoke.py` (the smoke script should gain the item-4 refusal).
