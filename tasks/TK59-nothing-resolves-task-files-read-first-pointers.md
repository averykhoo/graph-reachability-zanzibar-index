---
id: TK59
title: nothing resolves task files' Read-first pointers; LINKED_DOCS excludes tasks/
brief:
pri: LATER
size: M
deps: []
related: [TT-1]
parent:
labels: [infra]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07b
updated: 2026-09-07b
closed:
---

The `## Read first` pointers are the only navigation surface a session gets out of a task
file, and nothing resolves them. `REVIEW.md` section 1c raised it as a gap in `task.py
lint`; `INTEGRATION.md` note 26 answered that "the ported `handoff_lint` covers it once the
tree is at `tasks/`, so this closes on graduation and only on graduation." It did not
close, and both records died with `.scratch/tasktool/`.

Measured 2026-09-07: `scripts/handoff_lint.py::LINKED_DOCS` is eight files -- `HANDOFF.md`,
`formal/HANDOFF.md`, `CLAUDE.md`, `README.md`, `docs/README.md`, `docs/spec-deviations.md`,
`docs/latent-gaps.md`, `docs/architecture/overview.md`. `tasks/` is not among them. Every
pointer in every live task file is checked by nothing.

This is the same shape as the anchor-resolution gate `verify.sh lean` already runs over
`CORRESPONDENCE.md`: it does not prove the claims true, only that the pointers resolve --
which is precisely the failure it needs to catch, since a task whose read-first points at a
renamed file sends a session to a dead end at the moment it is trying to start work.

## Traps

- `check_doc_links` resolves paths and notices nothing about a sentence describing a
  structure that no longer exists. Resolving the pointers is worth doing and is NOT the
  same as checking the prose.
- The corpus is large and many pointers carry a section suffix (`section 11.10`, a
  `file::symbol`). Decide deliberately whether the check resolves the path only or the
  anchor too; the anchor form is what makes it bite, and also what makes it expensive.
- A per-task pointer check that fires on a legitimately archived source turns the gate red
  for a fact that is still true. `source` paths are deliberately never existence-checked
  for this reason (`scripts/task.py::SOURCE_PATH`) -- read that reasoning before choosing.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 3
- `scripts/handoff_lint.py` -- `LINKED_DOCS` and `check_doc_links`

## Log

### 2026-09-07b

PLAN AGREED 2026-09-07b (user), not started. Batch 3 of the TK57-TK65 sweep; TK57/TK60/TK61/TK63/TK64/TK65 landed this session, this one did not.

Shape: a NEW check in task.py::LINT_CHECKS, appended as number 14 (13 is retired at the
cutover and never reused). check_read_first: for every OPEN task, each "## Read first"
entry must resolve.

Decisions taken up front, so the next session does not re-litigate them:
  * Resolve markdown links and backticked paths as PATHS; resolve file::symbol by grep.
  * A "path:LINE" citation is checked for the PATH ONLY, never the line. Evidence from
    this session: TK63 cited PROOF_STATUS.md:247 for the do-not-cancel-P4 warning and the
    real line is :5146, and TK64/TK65 both cited line numbers that had drifted by one to
    ten lines. Line numbers rot faster than a check can be worth. Do not gate on them.
  * Do NOT touch the `source` field. task.py::SOURCE_PATH deliberately never
    existence-checks it, and that reasoning still holds: a legitimately archived source
    would turn the gate red for a fact that is still true.
  * Sabotage: rename a cited file, watch check 14 go red, restore. Control: the same run
    on the unrenamed tree must be green, so the red is attributable.

Now cheaper than when filed: verify.sh grew step 4g this session (TK57), so task.py lint
runs INSIDE the gate. Check 14 is therefore gated the moment it is appended, with no
verify.sh change needed.

Do this one BEFORE TK66. TK66 (formal/history directives invisible to the tree) wants a
pointer-resolver of exactly this shape, and is probably an extension of check 14 rather
than its own mechanism.
