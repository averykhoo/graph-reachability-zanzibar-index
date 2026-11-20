---
type: Task
id: TK-304
title: lookup_reverse/expand list a userset key (TTU target whose type doesn't declare the relation) that check() now refuses (TK-185 D03)
brief: prune identically in BOTH backends; read-algorithm change, so CORRESPONDENCE/Lean check first; never edit the oracle
pri: NEXT
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-20a
---

lookup_reverse/expand list a userset key (TTU target whose type doesn't declare the relation) that check() now refuses (TK-185 D03).

Since 0.1.3 (TK-185, DEC-16) a read naming an undeclared type or relation is refused. D03 is half closed:

- Repro (independent verifier, first-hand, 2026-11-20): schema with `viewer from parent`, `parent: [folder, team]`, and `team` declaring no `viewer`. `lookup_reverse('viewer', 'doc', '4')` and `expand` return `('team', 't1', 'viewer')` on both backends, while `check('viewer', 'team', 't1', 'viewer', 'doc', '4')` is refused (`UndeclaredTypeOrRelation`) on Store sync, stalled, tokened-lagging and SetEngine.
- So a list call can return a key that `check` refuses to take back.
- Both backends behave identically, so EQUIVALENCE holds. The CHANGELOG `### Changed` for 0.1.3 discloses it.
- Fix direction: prune such usersets from `lookup_reverse` / `expand` output in BOTH backends, identically. That changes the read algorithms and the Lean-modelled `expand` shape, so check `formal/CORRESPONDENCE.md` and the Lean model (CLAUDE.md, Perf work and the Lean model) before landing; the lookup oracle (`tests/test_lookup_oracle.py`) must agree.
- Rank (rerank 2026-11-20a): NEXT. EQUIV across read surfaces, and RELEASE: a 0.1.3 user can hit it.

## Traps

- Never edit an oracle result or golden to make the pruning pass; if the oracle disagrees, the spec question goes on this row first.

## Read first

- docs/tk185-0.1.3-batch-2026-11-20.md (section "Residual (filed at the close, not fixed here)")
- docs/decisions (DEC-16)

## Log
