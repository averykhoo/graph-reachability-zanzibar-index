---
id: TK185
title: 0.1.2 install trial doc gaps: result-key order trap, write-type wording, shape messages
brief: 0.1.2 trial: C5 result key -> check(*key) silently False; C1/C8/C2/C3/C6/C7 wording and consistency
pri: NOW
size: M
deps: []
related: [TK179, TK178, TK184]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-11-01
moved: 2026-11-01
updated: 2026-11-01
closed:
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
