---
type: Task
id: TK-184
aliases: [TK184]
title: object_wildcard_shapes as a list of lists raises a raw unhashable-type TypeError
brief: 'object_wildcard_shapes=[["folder","viewer"]] -> raw "unhashable type: list", argument not named (0.1.2 trial C4)'
pri: LATER
state: closed
status: deprecated
size: S
deps: []
related: [TK179, TK178]
parent:
labels: []
source: hand
source_hash:
created: 2026-11-01
taskpy_moved: '2026-11-01'
taskpy_updated: '2026-11-01'
taskpy_closed: '2026-11-01'
---

From the 0.1.2 fresh-user install trial, finding C4 (`docs/pypi-trial-0.1.2-2026-11-01.md`). Re-run FIRST-HAND against `src/` 2026-11-01: `parse_openfga_schema(SCHEMA, object_wildcard_shapes=[["folder", "viewer"]])` raises `TypeError: unhashable type: 'list'`, which does not name the argument. 0.1.2 promises a `TypeError` NAMING the argument for a wrong type. REPO-READ by the trial agent: `src/zanzibar/schema/argcheck.py::require_shapes` calls `frozenset(value)` before checking entries.

Next action: check each entry is a tuple/pair BEFORE building the frozenset (or catch the TypeError there and re-raise naming `object_wildcard_shapes` and the offending entry); pin it in the TK179 census test; sabotage it red. Consider whether a 2-element list should simply be accepted as a pair.

## Read first
- docs/pypi-trial-0.1.2-2026-11-01.md
- src/zanzibar/schema/argcheck.py

## Log

### 2026-11-01

Folded into TK185 (user 2026-11-01: all trial fixes in one row). Decision recorded there, item 1: accept a 2-element list as a pair, else a TypeError naming object_wildcard_shapes.
