---
id: TK57
title: verify.sh has no task.py lint step; 11 of 12 tree checks are outside the gate
brief:
pri: LATER
size: S
deps: []
related: [TT-1]
parent:
labels: [infra]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07
updated: 2026-09-07
closed:
---

`INTEGRATION.md` section 6 step 7 called the `verify.sh` 4g patch "not optional and not a
nicety" and made it graduation condition 21; `START-HERE.md` required it to land in the
same commit as the linter port; `PROOF.md` section 8 item 1 and `PROOF2.md` section 7 item
3 both carried it as THE open dependency. It never landed, and the record that said so
lived only in the deleted `.scratch/tasktool/`.

Measured 2026-09-07: `grep -c 'task\.py' formal/verify.sh` returns **0**. The gate's lean
phase runs `[4a/6]`..`[4f/6]` and no step invokes the task tool. Only the NOW/NEXT capacity
survived into the gate, and only indirectly, through `handoff_lint.py::check_priority_capacities`'s
tree fallback riding 4f. The other eleven `task.py lint` checks -- deps, parents,
filenames, the closed field, labels, `min_parsed`, the banner, parent depth -- reach the
gate only through the pytest tiles, which run the tool's unit tests rather than linting the
live corpus.

The gap is reproducible rather than merely arguable: with a second row flipped to `NOW`,
`task.py lint` fails rc=1 while `handoff_lint.py` reports `clean (7 checks)` rc=0.

## Traps

- Do NOT restate a check count here or in the patch. `task.py::LINT_CHECKS` is the home;
  check 13 was retired at the cutover and its number is never reused, so any prose count
  is wrong within one renumbering.
- The phase is `lean`, which keys off the `t2a` tree id and includes `*.md`. Adding the
  step means the lean verdict restales on any doc edit -- write records first, then re-run.
- Adding a gate phase is exactly what `docs/sabotage-procedure.md` governs: break the
  thing it guards and watch it go red before believing it.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 1 -- the finding and its provenance
- [`docs/gate-runbook.md`](../docs/gate-runbook.md) section 2 -- how the phases are structured
- `docs/tasktool-trial-protocol.md:576` -- an independent record of the same gap

## Log
