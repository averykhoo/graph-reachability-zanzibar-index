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
moved: 2026-09-08
updated: 2026-09-08
closed: 2026-09-08
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

### 2026-09-08

CENSUS 2026-09-08, before any code. Check 14 as specified is RED ON ARRIVAL. Numbers
below are a subagent sweep; the four marked VERIFIED were re-checked first-hand against
the tree by the session, per the delegation rule that a report is evidence, not a finding.

CORPUS: 67 `tasks/*.md` at depth 1, minus `tasks/README.md` (no frontmatter) = 66 open
tasks. 62 have a `## Read first` section; FOUR DO NOT (`P22`, `P23`, `P24`, `TK54` jump
`## Traps` -> `## Log`). 194 bullet entries plus 18 pointers on WRAPPED CONTINUATION
LINES (`P6`, `R6`, `TK53`) -- a bullet-only parser misses those 18 silently, which is a
fail-by-passing hazard in the check itself.

`-- derived` is NOT on disk (emitted at render time, `task.py:2285`). The on-disk
section terminator is the next `## ` heading only.

25 HARD DEAD POINTERS across 24 of the 66 open tasks:
  * VERIFIED: 22 open tasks cite `migrate.py::check_formal_pointer` in the formal-item
    boilerplate. `git ls-files | grep -c 'migrate.*\.py'` returns 0 -- the file went with
    `.scratch/tasktool/` on 2026-09-07. `R6-1:38` records the deletion; TK61 reworded
    that ONE line and the 22 copies were never swept. This is the check's own best
    motivating case: it would have caught the deletion the day it happened.
  * bare basenames, real path elsewhere: `test_conformance_enum.py` (P16:28, really
    `formal/conformance/`), `verify.sh` (TK38:33, really `formal/`), `Cascade.lean`
    (P6:73, really `formal/lean/ZanzibarProofs/GraphIndex/`, and it carries a LINE RANGE
    `:190-191`, not the `path:123` form this row planned a stripper for),
    `UsStarWrite.lean` (P6:76, same dir, and on a continuation line).

TWO FALSE GREENS under a path-only rule. VERIFIED: `TK39:29` and `TK43:29` write
`[README.md](README.md)` and cite `:399`, `:142`, `:150`. From `tasks/` that resolves to
`tasks/README.md`, which is 86 lines. They mean the ROOT `README.md`, 660 lines. Both
counts measured 2026-09-08. A path-only check calls both green.

`file::symbol`: 55 occurrences, 30 fully resolve, ZERO symbol-level misses among files
that exist. All 25 failures are file-level (22 migrate.py, 1 UsStarWrite.lean, 2 with an
empty file part). So the symbol half of the check is cheap and already clean.

THE `../` FORK, which this row did not decide. VERIFIED tree-wide over `tasks/*.md`:
130 markdown links written bare vs 11 written with `../`. (The Read-first-scoped count
is 105 vs 8 -- same direction, narrower window.) As rendered markdown from `tasks/` the
bare ones are 404s. But ZERO pointers are dead under BOTH roots.

DECISION TAKEN 2026-09-08: resolve against EITHER root, pass if either resolves.
Reason: `handoff_lint.py::check_doc_links` resolves relative to the citing file
"because that is how a reader's click resolves it", but a `## Read first` pointer's
consumer is `task.py show` in a terminal, not a renderer. Either-root aims the check at
genuine deaths instead of at 130 cosmetic links. COST, recorded so it is not discovered
later: either-root permits the two README false greens above. They get fixed by hand,
not by the check.

FIVE RULES STILL OWED, each a real corpus shape:
  1. 4 tasks with no `## Read first` section -- skip or fail?
  2. 5 prose entries with no path (`AW-1:27`, `HS-5:30`, `SD-2:27`, `SD-3:27`,
     `TK28:39`). Two are literally "(the board row carried no pointer)" migration
     placeholders -- argues for skip.
  3. 17 `python task.py show <id>` entries are CLI commands, not paths. `HS-5:29` uses
     the correct `python scripts/task.py show TK49`, so the corpus is inconsistent.
  4. `::symbol` elision shorthand meaning "same file as the previous entry" (`P6:76`,
     `TK50:35`).
  5. continuation lines (see above).

MECHANICS CONFIRMED 2026-09-08, all first-hand:
  * `task.py::split_body` + `section_slug` already extract the section (`show --section
    read-first` uses them). The extractor is free.
  * Position 14 is reserved by the comment at `task.py:2876`. Append only.
  * `handoff_lint.py::check_doc_links` is the model but NOT reusable: `_MD_MENTION`
    (`handoff_lint.py:260`) matches `.md` only, and `LINKED_DOCS` is a fixed 8-file
    tuple. A read-first citing a `.py` is resolvable by nothing today, even in principle.
  * Gated on arrival with no `verify.sh` edit -- 4g already runs `task.py lint`
    (`verify.sh:946`).
  * ZERO-HEADROOM PIN WILL BITE: `tests/test_tasktool.py:3685` asserts
    `len(fixture) == 22` exactly. A new `test_sabotage_check_read_first` needs a
    deliberate bump to 23 plus the module docstring.
  * INSTRUMENT CONTROL REQUIRED: `check_doc_links`' own record says a link checker that
    matches nothing passes forever, which is why `MIN_DOC_LINKS` exists. Check 14 needs
    the equivalent floor or its sabotage proves nothing.

DOC EDITS THIS PULLS IN: `docs/tasktool-spec.md:397` says "Twelve checks" and its
numbered list needs a 14th entry; `task.py:462-464`'s docstring states the gap this
check closes and must be retracted in the same commit.

LANDED 2026-09-08. Lint check 14 (`task.py::check_read_first`) resolves every
`## Read first` pointer on every OPEN task. Gated on arrival -- `verify.sh` step 4g
already runs `task.py lint`, so no `verify.sh` edit was needed.

WHAT IT FOUND, which is the case for having built it: 25 dead pointers across 24 of the
66 open tasks. 22 were the same line -- a citation of a checker deleted with
`.scratch/tasktool/` on 2026-09-07. `R6-1` recorded the deletion and `TK61` reworded ONE
of the copies; the other 21 kept sending every formal session to a file that does not
exist. Also dead: three bare basenames whose real homes are under `formal/`
(`test_conformance_enum.py`, `verify.sh`, `Cascade.lean` + `UsStarWrite.lean`).

CORPUS SWEPT FIRST, so the check landed green rather than red-on-arrival:
  * 22 formal-item boilerplate lines retracted. The replacement DESCRIBES the deleted
    checker instead of naming it -- a retraction that names a dead file leaves a dead
    pointer, which is the same conclusion 2026-09-07b reached about a minted-shape id.
    The 13 `R6-N` lines `TK61` reworded had the same defect and got the same treatment.
  * 17 `python task.py show <id>` entries rewritten to `python scripts/task.py show <id>`
    (the spelling `HS-5` already used). They now resolve as paths, so check 14 needed NO
    special rule for CLI entries -- a rule not needed beats a rule handled.
  * `TK39`/`TK43` repointed to `../README.md`. Both cited `:399` / `:142` / `:150`
    against the ROOT README while the link resolved to `tasks/README.md` (86 lines vs
    660, both measured 2026-09-08). Check 14 does NOT catch that class; it is fixed by
    hand and the limit is stated in the check's docstring rather than implied.

DECISIONS TAKEN, all recorded in `task.py::check_read_first`'s docstring:
  * EITHER ROOT (repo root or `tasks/`), against `check_doc_links`' renderer-strict rule.
    130 of the corpus's links are root-relative and 11 are `../`-relative (measured
    2026-09-08); zero were dead under both. A renderer-strict rule would fail 130 live
    pointers and teach the next session the check is noise.
  * Path only, never the line. Line ranges (`:190-191`) strip too -- the plan only
    anticipated `:190`.
  * Symbols ARE resolved. 55 occurrences, zero symbol-level misses among files that
    exist, so it was cheap; it is also the half that bites, since a renamed function
    leaves the path green.
  * Warnings, not violations, for the 4 tasks with no section and the entries that name
    no path. They print on every run: a silent skip is how a blind spot becomes permanent.
  * `source` untouched, as this row required.

SABOTAGE, four runs on the live tree plus two permanent fixture cases
(`tests/test_tasktool.py::test_sabotage_rf_path`, `::test_sabotage_rf_symbol`; counted in
their own bucket so the 2026-08-21 record still means its own 22). Literal output is in
the check's docstring. The one that matters is the fourth: an early `return []` in the
tokeniser, caught by the floor at `resolved only 0`. The first three only prove the check
notices broken DATA.

TWO FALSE REDS CAME FIRST and are recorded, because both are the obvious way to write
this and both look right. (a) The token cleaner stripped `.` from both ends and ate the
`../` off every relative link -- 22 "dead" pointers that were the checker eating its own
input. (b) Code spans were read before markdown links were removed, so the LABEL of a
link was resolved as a path and reported dead while its target resolved fine. That is the
identical false positive `handoff_lint.py::check_doc_links` records 32 of and warns about
in its own docstring -- read during this work, and reproduced anyway.

INSTRUMENT CONTROL is `min_read_first_pointers` in `tasks/config.json`, not a module
constant, because a constant sized for the live tree reddens every fixture and "make the
fixture pass" is how a floor gets deleted. 209 resolved live on 2026-09-08 (measured by
raising the floor until it fired); floor 150, headroom ON PURPOSE because the quantity is
NOT monotonic -- closing a task removes its whole section. Value is validated, not just
compared.

TWO LIMITS STATED RATHER THAN LEFT TO BE DISCOVERED:
  * The floor is skipped when the corpus offers no read-first ENTRIES at all (a tree built
    entirely by `task.py new` is exactly that). So blinding the SECTION extractor evades
    the floor. It is not silent -- every task then trips the "no section" warning -- but it
    is weaker than the tokeniser half.
  * `ZANZIBAR_TASK_POINTER_ROOT` is an escape hatch for ONE caller: a `tasks/` tree copied
    out of the repo (`tests/test_tasktool.py::live_copy`) is severed from the files its
    pointers name. Deriving that root from `__file__` was tried and is WRONG -- the
    sabotage harness runs patched COPIES of the tool out of a temp directory.

Doc edits carried in the same commit: `docs/tasktool-spec.md` section 5 gains entry 14 and
STOPS restating the check count (that sentence was wrong the moment 14 was appended --
`ZT-P3-5` inside the spec for the tool built to cure it); `task.py`'s module docstring
retracts its "nothing here resolves a Read first pointer" paragraph.

FOLLOW-ON: `TK66` wanted a resolver of this shape and should now be re-read as an
extension of check 14 rather than its own mechanism.
