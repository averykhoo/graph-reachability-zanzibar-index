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
moved: 2026-10-20b
updated: 2026-10-20b
closed:
---

tuplestr.py::parse_user only rejects an empty, double-#, or ... predicate; nothing checks the predicate charset, so the docs claim that such strings are malformed is false on reads. Also B7 (docs only): is_valid_identifier("...") is True and its docstring implies otherwise; type ... parses (harmless, parity holds). Fix: apply the identifier charset to the predicate in parse_user; fix the docstring.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B8 (`docs/tk151-repros-2026-10-20/B8.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log
