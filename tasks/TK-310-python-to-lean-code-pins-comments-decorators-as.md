---
type: Task
id: TK-310
title: Python-to-Lean code pins (comments/decorators) as the route to a proven-equivalent G-1
brief: 'aspiration only (DEC-23): revisit when a comprehensive proof is feasible'
pri: SOMEDAY
state: open
deps: []
goals: [G-1]
source: session 2026-11-24b
created: 2026-11-24
moved: 2026-11-24b
updated: 2026-11-24b
---

Python-to-Lean code pins (comments, decorators or similar) as the route to a "proven equivalent" G-1.

The owner, DEC-23 (2026-11-24): "G1 is an attempt mostly because we haven't been able to write a comprehensive proof yet, if it was easy enough I think we would strengthen the goal to say we want it proven equivalent with code pins to lean from python comments or decorators or something". An aspiration, not a current goal (docs/charter.md G-1). Revisit only if a comprehensive proof becomes feasible (e.g. models optimized for Lean, DEC-22).

The existing, partial form: the `file::symbol` anchors in `formal/CORRESPONDENCE.md`, asserted to resolve by `formal/conformance/anchor_check.py` (`formal/verify.sh` lean phase). They live in the doc, not in the Python, and keep the map navigable, not true.

## Traps
- A pin that only proves a pointer resolves is not a proof that the claim is true (CORRESPONDENCE.md).

## Read first
- `docs/decisions/DEC-23-charter-follow-up-orm-backend-abstraction-fuzz.md`
- `formal/CORRESPONDENCE.md`

## Log
