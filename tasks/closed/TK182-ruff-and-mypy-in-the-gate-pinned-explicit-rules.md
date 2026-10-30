---
id: TK182
title: ruff and mypy in the gate (pinned, explicit rules), every finding fixed
brief: ruff (correctness rules) + mypy on src in verify.sh lean and CI, pinned; fix every finding behaviour-preserving
pri: NEXT
size: M
deps: []
related: [TK178, TK179]
parent:
labels: [infra]
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

Map: docs/tk182-lint-typecheck-plan-2026-10-30.md (tool measurements + decision). DECIDED: ruff with explicit correctness select (F, E9, B, PLE) over src/tests/scripts/formal/conformance/benchmarks, __init__ re-exports exempt; mypy (not pyrefly: same order of findings, speed irrelevant at 35 files, mypy is the typing-spec reference most downstream checkers agree with) on src/zanzibar; both pinned exact in a lint extra; run inside verify.sh lean, provisioned in gate.yml. Next action: config + fix ruff, then mypy file by file (invariants.py holds 174 of 275).

Map: docs/tk182-lint-typecheck-plan-2026-10-30.md (measurements, decision, outcome). ruff 0.17.3 (select F, E9, B, PLE; docs/ and formal/probes|history excluded as frozen evidence; __init__ re-exports exempt from F401) + mypy 2.4.1 over src/zanzibar, pinned exactly in the pyproject lint extra and requirements.txt (CI installs them with requirements.txt; no workflow edit), run by scripts/lint_gate.py as verify.sh lean step 4h, which refuses a missing tool or another version. Every finding fixed behaviour-preserving (agents mypy-A/B/C, ruff-rest); 69 anchored bodies re-reviewed (0 behaviour change) and the content pin regenerated. Sabotage L1 type error / L2 unused import / L3 pin mismatch all red.
