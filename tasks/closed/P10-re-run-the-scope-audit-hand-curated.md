---
id: P10
title: re-run the scope audit, hand-curated
brief:
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 5765e5e69346
created: 2026-08-16
moved: 2026-09-27d
updated: 2026-09-27d
closed: 2026-09-27d
---

re-run the scope audit, hand-curated

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [fan-out runbook](docs/subagent-fanout-runbook.md), final §

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-27d

Re-run done 2026-09-27/28. The 2026-08-10 run's transcripts were gone, so candidates were re-discovered: 225 raw hits, the rule-2 predicate applied by hand, 12 curated, each audited and adversarially verified (every verifier upheld its audit). Result: 9 HOLE, 3 SOUND. Filed: TK111 (NEXT, live fail-open: a poison row stalls async catch_up and untokened check serves a revoked ALLOW -- reproduced first-hand by the orchestrator), TK112 (NEXT, fan-out cap vs revocation, same stale-ALLOW mechanism, reproduced first-hand), TK113 (remove_node divergence), TK114 (non-stratifiable negation), TK115 (JSON front end), TK116 and TK117 (coverage). Comments on ASK-2, TK109, P23, SD-1, TK33. Side finding fixed: tests/test_invariants_docstring_matches_body.py now skips .claude (worktree copies turned it red; sabotaged both ways). Map: docs/p10-scope-audit-2026-09-27.md.
