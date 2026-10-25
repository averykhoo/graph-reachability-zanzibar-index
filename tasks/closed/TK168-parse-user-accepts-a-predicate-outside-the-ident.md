---
id: TK168
title: parse_user accepts a predicate outside the identifier charset ("user:a#b:c")
brief: reads accept group:g#b:c and answer empty/False; writes refuse with AdmissionRejected
pri: LATER
size: S
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-23e
updated: 2026-10-23e
closed: 2026-10-23e
---

tuplestr.py::parse_user only rejects an empty, double-#, or ... predicate; nothing checks the predicate charset, so the docs claim that such strings are malformed is false on reads. Also B7 (docs only): is_valid_identifier("...") is True and its docstring implies otherwise; type ... parses (harmless, parity holds). Fix: apply the identifier charset to the predicate in parse_user; fix the docstring.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B8 (`docs/tk151-repros-2026-10-20/B8.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-23e

FIXED 2026-10-23e: src/zanzibar/schema/tuplestr.py::parse_user now refuses a ":" in the relation part with MalformedTupleString (reads and writes alike), the same shape rule the name already had. Other off-charset predicate characters (e.g. a space) stay read-lenient / write-refused, as for names: only ":" makes the split ambiguous. B7 half: errors.py::is_valid_identifier docstring corrected ("..." IS in the charset; reserved by position). PINNED: tests/test_tk123_call_forms.py::test_malformed_strings_are_refused gains user:a#b:c and group:*#b:c; sabotage (drop the check) -> exactly those 2 failed, 34 passed. Docs updated: userdocs reference/tuple-strings.md (rule, table row, examples), reference/exceptions.md (table + directive), explanation/semantics-vs-openfga.md; CHANGELOG [Unreleased] Fixed. Targeted tests green; full gate not yet run (CPU busy with another job).
