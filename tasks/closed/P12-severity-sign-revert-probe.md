---
id: P12
title: severity-sign revert probe
brief:
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: board
source_hash: b599fc1ce75d
created: 2026-08-16
moved: 2026-09-27d
updated: 2026-09-27d
closed: 2026-09-27d
---

severity-sign revert probe

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`spec-deviations.md`](docs/spec-deviations.md) 2026-08-10 entry

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-27d

P12 MEASURED, doc docs/p12-severity-sign-revert-probe-2026-09-27.md (ACTIVE-PLAN; spec-deviations ## 2026-09-27b). LANDED: the 2026-08-09 sibling (OWC x star-parent x TTU, fixed by I14 in 33242de = docs c042056) on the LITERAL pre-fix tree 33242de^ is fail-OPEN under every negated consumer the graph compiles and fail-CLOSED under positive ones (B: access OPEN 12 / viewer CLOSED 24 of 3072 queries; D: OPEN 6 / CLOSED 24; E: OPEN 6 / CLOSED 36; post-fix 0). The consumer the 08-10 entry proposed (negated TTU directly over the shape) is a D4 compile refusal. Permanent pin tests/test_p12_severity_sign.py (14 tests) simulates the revert by no-op _ensure_entity_middles; simulation reproduced the literal counts exactly for B/D/E. Mutation sweep M0-M6 all as expected (in the doc). Side finding: paranoia=residue (the recommended production level) does NOT catch an I14 regression, only full/fixpoint -- pinned; whether residue should gain I14 is an open cost question, not filed. RED: nothing known; tests-tile 1/4 PASSED in the worktree, 2-4 pending at comment time; lean/conf-tile not run (no .lake in worktree). NEXT: orchestrator merges, runs lean + conf-tiles, closes P12 citing ## 2026-09-27b, freezes the doc.

MEASURED, prediction held (5eff958). The 2026-08-09 sibling, run on the literal pre-fix tree 33242de^ (the twin of the cited c042056^, which is not in master's history), is fail-OPEN under every negated consumer the graph compiles and fail-CLOSED under positive ones. Case B (access: [user] but not viewer): access OPEN 12, viewer CLOSED 24 of 3072 queries; post-fix 0. The consumer the 2026-08-10 entry proposed (negated TTU over owc_star_ttu) is a D4 compile refusal on both trees. tests/test_p12_severity_sign.py (14 tests) pins the sign by simulating the revert, and the simulation reproduced the literal counts exactly for B/D/E (36/30/42). Adversarially verified with an independent literal revert: ACCEPT. Side finding filed as TK118 (paranoia=residue does not catch an I14 regression). Map: docs/p12-severity-sign-revert-probe-2026-09-27.md; spec-deviations 2026-09-27b.
