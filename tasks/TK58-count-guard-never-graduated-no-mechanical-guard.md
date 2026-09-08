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
moved: 2026-09-08
updated: 2026-09-08
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

### 2026-09-08

CENSUS 2026-09-08, before any code. The check as specified on this row is RED ON
ARRIVAL: the three agreed patterns fire on 87 lines in the agreed scan scope. Numbers
are a subagent sweep; the items marked VERIFIED were re-checked first-hand.

SCOPE ACTUALLY SCANNED: `CLAUDE.md`, `HANDOFF.md`, 12 x `docs/*.md` (top level, incl.
`docs/README.md`), 72 x `tasks/*.md`. Fence-aware. The per-line date-stamp skip dropped
18 lines, the fence rule 1.

BREAKDOWN of the 87: 7 true live claims, ~65 evidence, 15 pattern false positives.

THE SHAPE IS FAVOURABLE. 61 of the 80 non-claims collapse under ONE file-level
exemption. Zero hits in `HANDOFF.md`, `docs/README.md`, `docs/latent-gaps.md`,
`docs/perf-next-round.md`, `docs/tasktool-spec.md`, `tasks/README.md`, and 70 of 72 open
task files. Residue to adjudicate by hand: roughly 26 lines.

AMENDMENT 1, and it invalidates part of the agreed plan. THE PER-LINE DATE-STAMP SKIP
DOES NOT WORK. `docs/spec-deviations.md` contributes 35 hits, every one a pytest summary
inside a dated entry -- but the date sits on the `## <date>` HEADING, not on the body
line, so a per-line rule sees none of it. The exemption predicate must key on the FILE's
liveness banner (`docs/README.md`'s LIVING / FROZEN / ACTIVE-PLAN vocabulary), not on the
line. `spec-deviations.md`'s own banner says it is append-only and every entry true as of
its date key -- that is the machine-readable fact to key on. Same mechanism covers the
three FROZEN 2026-09-06d tasktool docs (15 hits) and `docs/perf-round6-audit-2026-08.md`.

AMENDMENT 2: pattern (b) needs a word boundary. It currently matches "6 row" inside the
identifier `R6-6` (`docs/perf-round6-audit-2026-08.md:40`, twice) and "00 row" inside
`1.00 row/edge` (`R6-16:3`). Other false positives are DB/closure rows (`14,868 rows`,
`100,000 rows`, `one row per id`) and narrative "two checks" / "one test" meaning a
specific pair, not a census.

AMENDMENT 3, SELF-REFERENTIAL TRAP: this row's own SABOTAGE bullet (TK58 line 89)
instructs writing a restated check-count literal into `HANDOFF.md`, and that instruction
contains the literal. The check fires on its own design spec. Same shape as the
minted-id pin that caught the 2026-09-07b write-up twice. Plan for it -- describe the
token rather than quoting it, or accept the row is exempt-by-banner -- do not weaken the
pattern to dodge it.

THE 7 TRUE LIVE CLAIMS, and TWO OF THEM ARE ALREADY WRONG TODAY:
  * VERIFIED WRONG -- `docs/gate-runbook.md:285` says three checks run inside the `lean`
    phase. `formal/verify.sh` echoes `[4a/7]` through `[4g/7]`: seven. TK57 added 4g and
    renumbered 4a-4f last session; this line was not updated.
  * VERIFIED WRONG -- `docs/gate-runbook.md:365` states a check count for
    `scripts/handoff_lint.py`. The `CHECKS` tuple at `handoff_lint.py:890-904` has ELEVEN
    entries; `check_session_receipt` was appended 2026-09-06c and the prose was not
    updated. Rot introduced by the very session that added the eleventh check.
  * `docs/gate-runbook.md:81` -- a skip-budget figure restated in prose; true today
    against `verify.sh:505`.
  * `docs/gate-runbook.md:197` and `:201` -- a per-file test count, restated TWICE in the
    same bullet, and unverifiable statically (the file has one parametrized `def test_`).
    That duplication is the ZT-P3-5 shape exactly.
  * `CLAUDE.md:16` -- restates `task.py:609 LIST_LIMIT`. True today. Borderline: a UI cap,
    not a corpus census.
  * `TK62:19` -- a live census of open `R6-N` rows; rots the moment one closes.

A third wrong figure, outside this row's scan scope but the same defect:
`docs/tasktool-spec.md:397` restates the `task.py` lint check count, and it goes wrong
the moment TK59 appends check 14.

HOME CONFIRMED 2026-09-08, first-hand: no existing check overlaps.
`handoff_lint.py::check_frozen_banners` tests banner PRESENCE and never reads the body;
`check_bold_caps` counts formatting, not numerals; `check_ledger_row_ids` resolves ids,
not counts. The module docstring at `handoff_lint.py:17` names this exact motivation and
nothing implements it. Appending to `CHECKS` rides `verify.sh` 4f, so it is gated on
arrival with no `verify.sh` edit.

ORDERING NOTE: still do this AFTER TK59, and there is now a concrete reason beyond the
one already on this row. Landing check 14 makes `docs/tasktool-spec.md:397` wrong; TK59
fixes that line as part of its own doc update, so this check does not inherit it.
