---
id: TT-8
title: extract_banner is not code-fence-aware: a fenced ## Banner fools board and lint 12 alike
brief: audit finding 2026-09-06d, deferred from the cutover commit; fix + sabotage clause in the check-12 test
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-06d
moved: 2026-09-10
updated: 2026-09-10
closed: 2026-09-10
---

`task.py::extract_banner` finds the `## Banner` section of `HANDOFF.md` by scanning for lines that equal `BANNER_HEADING`, with no awareness of fenced code blocks. A `## Banner` line inside a ``` fence anywhere in the note (a doc example, say) would either be taken as the section or would end the real one early, and `board` and lint check 12 share the extractor so both would agree on the wrong text. Found by the 2026-09-06d cutover audit (adversarial lens), confirmed, deferred because the note is 39 lines and hand-written and the cutover commit had to stay one revertable change.

Fix shape: skip lines between fence markers when scanning for `## ` headings, and refuse (not warn) on a second `## Banner`. Pin it the house way: sabotage a copy of the note with a fenced `## Banner` and watch check 12 go red BEFORE believing the fix (`docs/sabotage-procedure.md`).

## Read first

- `scripts/task.py::extract_banner`, `banner_lines`, `check_banner`
- `tests/test_tasktool.py::test_lint_check_12_catches_the_three_banner_failures` (add the clause there)

## Log

### 2026-09-10

LANDED 2026-09-10. `task.py::extract_banner` is fence-aware, and two `## Banner` headings now REFUSE instead of silently picking one.

Implementation: a `_FENCE_RE` tracks ``` / ~~~ blocks (indent-tolerant, info-string aware, close-marker length-aware), headings inside a fence are skipped, and the section is sliced from a harvested heading list rather than a break-on-first-`##` scan. `board` exits 2 on a double banner; `check_banner` catches the refusal and fails so the rest of lint still runs, and the message names the FILE and both line numbers.

SABOTAGE, run BEFORE the fix, against the `git show HEAD:scripts/task.py` extractor, on a temp copy of the live corpus (the real HANDOFF.md was never touched):
    --- mode=onlyfenced act=check12
    --- check 12 failures: 0
      extract_banner -> ['2026-01-01a -- EXAMPLE ONLY, this is documentation of the banner shape', '```']
i.e. check 12 did NOT go red for a banner that existed only inside a fence -- the bug reproducing. Same run, `mode=twice`: 0 failures for two real `## Banner` headings.

After the fix, same harness:
    --- mode=onlyfenced act=check12
      FAIL: <TMP>/HANDOFF.md has no `## Banner` heading...
    --- check 12 failures: 1
    --- mode=twice act=check12
      FAIL: <TMP>/HANDOFF.md has 2 `## Banner` headings (lines 14, 31), and there is no safe way to pick one...
Each of the three new clauses was certified STANDALONE against the pre-fix tool (clause 5 fires first and would otherwise mask 6 and 7): all three RED pre-fix, GREEN post-fix.

MUTATION SWEEP -- the standing rule from 2026-09-08b ("a sabotage certifies ONE test; sweep the whole MODULE"), and it earned its place. Twelve narrow weakenings; SEVEN left every test GREEN: tracking only ``` and not ~~~, requiring a column-0 fence, a naive toggle, an `==` close-marker length test, letting an info-string line close a fence, dropping the file name from the refusal, and tracking only the FIRST fence in the file. The gap was uniform and worth recording: the original clause wrote ONE fence shape, so the fence GRAMMAR was unguarded, not the fence. Five new clauses (8-12) plus a filename assertion close all seven; re-sweeping the seven now gives "1 failed, 95 passed" each, every one naming `test_lint_check_12_catches_the_three_banner_failures`. The twelve mutations and their verdicts are recorded in that test's docstring, in the tracked tree -- not in `.scratch/`.

Also updated `docs/tasktool-spec.md`, whose `extract_banner` bullet described the pre-fix contract.

Suite: 96 passed. Not pinned by a clause, and left as an observation on purpose: a fence INSIDE the banner section now counts as banner content, so such a corpus fails the 14-line cap rather than truncating silently. Correct behaviour, but observed rather than designed.
