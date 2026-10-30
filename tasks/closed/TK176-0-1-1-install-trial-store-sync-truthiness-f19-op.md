---
id: TK176
title: 0.1.1 install trial: Store(sync=) truthiness (F19), ops= type (F10), docs re-run (F5), note (F17)
brief: 0.1.1 trial F19 sync= truthiness (BROKEN), F10 ops= str, F5 docs re-run, F17 self-parent note; fixed, unreleased
pri: LATER
size: S
deps: []
related: [TK174]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Source docs/pypi-trial-0.1.1-2026-10-30.md; F19 + F10 re-run first-hand against src first. F19 (BROKEN): Store/Store.adopt sync= picked the mode by truthiness (None/0 -> async silently); store/_store.py::_check_open_args now refuses a non-bool with TypeError before any statement. F10: setops.py::require_setops, called by Store, Store.adopt and SetEngine (adopt had its own inline check; Store.__init__ had none despite the adopt comment). F5: 14 userdocs pages now unlink their SQLite file first (errors.md already did; PYPI_README untouched, its re-run is stable and publish.yml parses it). F17: 0.1.1 self-parent note says when it applies (recursive from-chain still refused as a cycle). Pin tests/test_tk176_open_arg_types.py, 3 sabotages red (tails in its docstring). Under CHANGELOG [Unreleased]; ships with TK178.
