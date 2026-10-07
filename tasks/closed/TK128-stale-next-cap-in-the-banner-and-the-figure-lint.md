---
id: TK128
title: stale NEXT cap in the banner, and the figure lint misses "cap of N" phrasing
brief: banner says NEXT cap 3 (it is 5); extend check_restated_counts to catch "cap of N"
pri: LATER
size: S
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07c
moved: 2026-10-07d
updated: 2026-10-07d
closed: 2026-10-07d
---

Item 1 of the 2026-10-07 cross-repo context audit (`e8b340b`). The `HANDOFF.md` banner says the
NEXT tier has a "cap of 3", but the cap has been 5 since 2026-10-04 (`tasks/config.json`
budgets, `handoff_lint.py::NEXT_MAX`). Fix the text, AND extend
`scripts/handoff_lint.py::check_restated_counts` so a "cap of N" phrasing is caught: it passed
this one.

## Traps

- (!) A new lint pattern needs its sabotage (`docs/sabotage-procedure.md`): plant the stale
  phrasing and watch the check go red before trusting it.

## Read first

- [`docs/context-audit-2026-10-07.md`](../docs/context-audit-2026-10-07.md) item 1 (measured 2026-10-07).

## Log

### 2026-10-07d

LANDED (uncommitted, 2026-10-07d): banner cap number deleted and pointed at tasks/config.json budgets; same fix at docs/README.md sec 4 (correct 5, dropped anyway) and docs/tasktool-spec.md op table (stale NEXT<=3, found by the widened census). scripts/handoff_lint.py::check_restated_counts now judges NOW/NEXT caps against TIER_CAPS (= NEXT_MAX) via _restated_caps / _CAP_PATTERNS, BEFORE the dated escape (the stale banner line carried 2026-09-22, which is why it survived). 5 permanent tests in tests/test_handoff_lint_count_guard.py (tier caps section) incl. the real stale line as planted sabotage; in-memory 9-mutation sweep 9/9 caught, recorded in that module. handoff_lint clean, task lint clean, 89 handoff_lint tests pass. RED until regenerated: formal/FINAL_REVIEW.md counts block (+5 tests; doc_counts --generate). Next: gate, commit, close.

fix-hk review pass (2026-10-07d): the first version missed the BOUND-FIRST phrasing (at most three NEXT) and a wrapped one, and the walk was blind to docs/tasktool-spec.md lines 144-522 because a prose line starting with three backticks (line 93) toggled the fence state. Fixed: scripts/handoff_lint.py::_CAP_PATTERNS bound-first pattern, _restated_caps(ln, nxt) for wrapped caps, _is_fence (CommonMark: a backtick info string may not contain a backtick). Stale caps deleted at docs/tasktool-spec.md (field table, check 5, JSON example), docs/gate-runbook.md 4f, scripts/task.py::check_pri_budget docstring, formal/verify.sh 4f comment, handoff_lint module docstring. Retro control: the check on HEAD e8b340b docs now reports gate-runbook 304 and 451 (wrapped), tasktool-spec 157, 343, 425. 3 new tests in tests/test_handoff_lint_count_guard.py, sweep M1-M7 7/7 red (table in the module). Not changed: scripts/task.py::CONFIG_DEFAULTS budgets NEXT 3 and budgets.get(NEXT, 3) fallbacks (code defaults, shipped config overrides). Next: gate, commit, close.

Done 2026-10-07d. Stale NEXT cap removed from the banner, docs/README.md, docs/tasktool-spec.md, gate-runbook, verify.sh and task.py docstrings (pointing at tasks/config.json budgets). handoff_lint.py::check_restated_counts now checks tier caps (_CAP_PATTERNS: prose, comparison, bound-first; wrapped lines) against TIER_CAPS before the dated escape; _is_fence fixed a fence misdetection that hid tasktool-spec.md:144-522 from the scan. Sabotage: permanent tests in tests/test_handoff_lint_count_guard.py. Residual: task.py::CONFIG_DEFAULTS still defaults NEXT to 3 (unreached with the shipped config). Evidence (agent reports, moved-text tables, sabotage sweeps): docs/history/context-caps-housekeeping-2026-10-07.md. Gated with the 2026-10-07d commit.
