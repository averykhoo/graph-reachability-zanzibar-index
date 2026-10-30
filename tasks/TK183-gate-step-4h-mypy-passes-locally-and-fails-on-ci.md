---
id: TK183
title: gate step 4h (mypy) passes locally and fails on CI: library type stubs are not pinned
brief: mypy verdict depends on unpinned sqlmodel/SQLAlchemy/pydantic: local 4h green, CI 4h red (0.1.2 cut)
pri: LATER
size: S
deps: []
related: [TK182, TK178]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-30c
moved: 2026-10-30c
updated: 2026-10-30c
closed:
---

Found 2026-10-30c while preparing 0.1.2. The local gate was green on `540bb50`, but CI's `verify.sh lean` step 4h failed:
`src/zanzibar/graphindex/processor.py:1263: error: Argument "object_node_id" to "Residue" has incompatible type "int | None"; expected "int"  [arg-type]`
(gate run 41046990420, job 124033379901; the publish dry run 41047013422 failed the same way).

Cause (first-hand, reproduced in a throwaway venv): `scripts/lint_gate.py` pins mypy and ruff EXACTLY, but mypy reads its types from the libraries, and those are unpinned. Local env: sqlmodel 0.0.39 / SQLAlchemy 2.0.51 / pydantic 2.13.4, and mypy is clean. CI installs the newest: sqlmodel 0.0.48 / SQLAlchemy 2.1.6 / pydantic 2.14.2, whose typed model `__init__` exposes the error. Same mypy 2.4.1 both sides.

The finding was fixed in the 0.1.2 cut (`persisted_id(node)`, no runtime change). What stays open: a green LOCAL lint step does not promise a green CI lint step. CI catching dependency drift is by design (CLAUDE.md: CI installs newest, local pinned), so this may be "document it" rather than "pin it". Decide between: (a) document in docs/gate-runbook.md that 4h depends on library versions; (b) have lint_gate.py print the sqlmodel/SQLAlchemy/pydantic versions it ran with, so a CI/local disagreement is readable from the log; (c) pin those libraries for the lint step only. Do not pin them for the test run: that would hide exactly the drift CI is for.

## Log
