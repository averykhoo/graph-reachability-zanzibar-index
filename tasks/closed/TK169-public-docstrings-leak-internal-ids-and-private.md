---
id: TK169
title: public docstrings leak internal ids and private paths, and some are stale or missing
brief: help() shows task ids / private paths; paranoia comments say Default ON; fan-out messages name unreachable args
pri: LATER
size: M
deps: []
related: [TK151]
parent:
labels: [docs]
source: docs/tk151-diataxis-plan-2026-10-20.md
source_hash:
created: 2026-10-20b
moved: 2026-10-28
updated: 2026-10-28
closed: 2026-10-28
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-23b

From the TK151 fable review 2026-10-23 (docs/tk151-fable-review-2026-10-23.md rec 7): the StaleRead message in src/zanzibar/store/source.py says evaluator; userdocs how-to/errors.md carries a one-line gloss for it. Say set engine in the message, then drop the gloss.

### 2026-10-23e

PART DONE 2026-10-23e (the rec-7 slice named in this row): both StaleRead raise sites (src/zanzibar/store/_store.py::Store, src/zanzibar/store/source.py::TupleSource.check) now say "(set engine at log id N)"; TupleSource.check says "call refresh_evaluator()". Gloss dropped from userdocs/how-to/errors.md. CHANGELOG [Unreleased] Fixed. PINNED: tests/test_tk123_safety_messages.py::test_stale_read_names_the_set_engine_not_the_evaluator; sabotage (restore "evaluator at" in source.py) -> that 1 test failed, 37 passed. Historical quotes of the old text (tests/test_tk166_foreign_token.py docstring, docs/tk151-repros-2026-10-20/README.md) left as recorded output. STILL OPEN (the row title): public docstrings leaking internal ids / private paths, stale or missing ones -- needs a census first.

### 2026-10-28

DONE: census docs/tk169-docstring-census-2026-10-28.md (66 findings, FROZEN), all fixed across schema/graphindex/setengine/store docstrings and a few messages; guard tests/test_tk169_public_docstrings.py walks 188 public docstrings (floor 180) and refuses task ids / private paths / session dates, sabotaged red (leak and empty walk). Docstring-only, AST-diffed by the reviewer.
