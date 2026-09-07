---
id: TK58
title: count_guard never graduated: no mechanical guard against a restated corpus count
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

`REVIEW.md` blocker 6 found restated corpus counts already rotted across five files -- the
repo's own `ZT-P3-5` defect class recurring inside the tool built to cure it. The fix had
two halves. The first, making `task.py counts` the single home, landed and is pinned at
`tests/test_tasktool.py::test_counts_is_the_one_home_for_a_live_figure`. The second was
`count_guard.py`, a walker that mechanically refuses a restated count in prose. It never
graduated: `git ls-files | grep -c count_guard` returns 0, and the implementation was
deleted with `.scratch/tasktool/` on 2026-09-07.

There is today no mechanical guard against this repo's most-recurring defect class. No
tracked check overlaps: `handoff_lint.py::check_frozen_banners` checks banner PRESENCE and
never reads the body for figures; `task.py::check_min_parsed` polices the number itself,
never restatements of it elsewhere.

The design is recorded in the archive doc section 6 and is the part worth keeping: six
prose patterns; an escape vocabulary (a fenced block is evidence not a claim, a module
constant is the number's HOME, a FROZEN banner earns exemption only with BOTH a date and a
pointer at the live home); a declared list plus a complementary "every file beside it is
listed or a failure" check, so one half catches a deleted record and the other an unscanned
new one; and a baseline that a scan may never regenerate, because a guard that rewrites its
own expectations cannot fail.

## Traps

- This is a PORT WITH A REDESIGN, not a lift-and-shift, and the estimate should say so. The
  scratch data is worthless here: `frozen-exempt.json`'s records all named scratch files
  and hashed a 99-file corpus, `DELIVERABLES` was a flat top-level scan (wrong shape for
  `docs/` subdirectories), and the exemption predicate keyed on `[dated:]` plus a `counts`
  pointer where the tracked convention is the FROZEN / LIVING / ACTIVE-PLAN banner.
- A naive lift goes red on dozens of legitimate lines -- session-log entries and fenced
  transcripts -- and a check that is red on arrival is a check someone deletes.
- Best home is a new check inside `scripts/handoff_lint.py`, riding the existing `CHECKS`
  tuple and the existing gate. A standalone script nobody's gate runs is the dead check the
  original file itself warned about.
- Recording an exemption is an assertion, not a list edit. Keep `--record-frozen` a
  separate verb a scan can never call.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 6 -- the full design, since the tool is gone
- [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md) -- mandatory before adding the check
- `scripts/handoff_lint.py` -- the `CHECKS` tuple and the existing scope lists

## Log

### 2026-09-07b

PLAN AGREED 2026-09-07b (user), not started. Batch 4 -- do this LAST of the TK57-TK65 set,
after TK59 lands check 14.

DO NOT PORT count_guard.py AS DESIGNED. The archived design (six prose patterns, a declared
DELIVERABLES list, a frozen-exempt baseline) was built for a 99-file flat scratch corpus and
goes red on dozens of legitimate lines here -- session-log entries and fenced transcripts are
full of counts that are evidence, not claims. Red on arrival is how a check gets deleted.

SCOPE IT DOWN to the figures that have actually rotted in this repo:
  * patterns: N checks, N open tasks/rows, N tests. Three, not six. Grow the list only when
    a real rot is found, and say in the commit which one motivated the new pattern.
  * scan: CLAUDE.md, HANDOFF.md, docs/README.md, docs/*.md (non-history), tasks/.
  * skip: fenced blocks, docs/history/, formal/history/, tasks/closed/, and any line
    carrying a date stamp. Frozen and closed files are as-of-then by definition
    (CLAUDE.md, "Status lines inside docs/history/ ... are FROZEN as-of-then").

HOME: a new check appended to handoff_lint.py::CHECKS. Not a standalone script -- the
original file warned about exactly that, and a script nobody gates is a dead check. Note
handoff_lint already rides verify.sh 4f, so it is gated on arrival.

KEEP these two rules from the archived design, they are the load-bearing part:
  * recording an exemption is an ASSERTION, via a separate verb a scan can never call.
  * no baseline regeneration, ever. A guard that rewrites its own expectations cannot fail.

SABOTAGE: write "12 checks" into HANDOFF.md, watch it go red, restore. Control: the clean
tree must be green in the same run.

SCOPE NOTE, measured 2026-09-07b: this session removed two restated counts by hand (TK60
deleted R6 parent census; TK61 reworded 13 R6-N citations). Re-measure the live corpus
before sizing -- the S/M estimate on this row predates both.
