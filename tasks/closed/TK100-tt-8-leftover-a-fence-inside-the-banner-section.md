---
id: TK100
title: TT-8 leftover: a fence inside the banner section is unpinned behaviour
brief: observed in TT-8, never pinned; extract_banner is SHARED by check_banner and op_board
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

`TT-8` left one behaviour OBSERVED but UNPINNED: a fence (a fenced code block) placed
*inside* the `## Banner` section now counts as banner content, so such a corpus fails the
line cap rather than truncating.

This came out of the `TT-8` work on `task.py::extract_banner` (2026-09-10), whose sabotage
record is the reason the fence handling exists at all: a fenced `## Banner` is a code line,
so a note whose only `## Banner` is a worked EXAMPLE now fails `check_banner` instead of
linting clean while `board` printed the example. That fix is landed and pinned. What is NOT
pinned is the adjacent behaviour above -- it was observed during the same session and never
got a test.

An unpinned observed behaviour is one refactor away from silently changing, and
`extract_banner` is SHARED by `task.py::check_banner` and `task.py::op_board` -- which is
exactly what made the original `TT-8` defect dangerous: both consumers agreed on the wrong
text.

Carried in `HANDOFF.md`'s `## Still owed` until the 2026-09-22 disposition filed it here.

## Traps

- (!) **`TT-8`'s own lesson applies to its leftovers**: 7 of 12 weakenings left everything
  green because the clause guarded one fence SHAPE, not the fence GRAMMAR. Pin the grammar,
  and sweep the module with mutations -- one sabotage certifies one test
  (`docs/sabotage-procedure.md`).
- (!) **Decide whether failing the cap is the RIGHT behaviour before pinning it.** A pin
  freezes whatever is there; if truncating is actually correct, this row is a bug fix, not a
  test-addition. Say which on the row before writing the test.

## Read first

- `scripts/task.py::extract_banner` -- the function, its docstring, and the literal sabotage
  output recorded there.
- `scripts/task.py::check_banner` -- check 12, the consumer that shares `extract_banner`
  with `op_board`, and its "FENCES AND SECOND BANNERS (`TT-8`, 2026-09-10)" paragraph.
- [`../docs/sabotage-procedure.md`](../docs/sabotage-procedure.md) sec "Sweep the TEST
  MODULE with mutations" -- `TT-8` is one of the named cases.

## Log

### 2026-10-13

DONE 2026-10-13 (lane L4b). DECISION, made before pinning as the row's trap requires: (1) a CLOSED ``` fence inside the `## Banner` section is banner CONTENT. Its delimiters and lines count toward BANNER_MAX_LINES, and a `## ` line inside it does not end the section (CommonMark). This is correct, not a bug: the cap bounds what `board` PRINTS, `board` prints those lines, and truncating would hide text the author wrote. So that half is a PIN of existing behaviour. (2) An UNCLOSED fence opened inside the section is now REFUSED by `scripts/task.py::extract_banner`, so `board` exits rc 2 and lint check 12 fails, naming the file and the line that opens the fence. Truncating is not safe, because which `## ` line the author meant as a heading is a guess. That is the same reason two banners refuse. No new check number: it is check 12's existing Refused path. A `> ```` line (the banner is a blockquote) is not a fence to `_FENCE_RE`. That is harmless: in CommonMark the end of the blockquote closes it, and `> ## x` is not a heading. Pinned as control G. PRE-FIX PROBE (READ, 2026-10-13): `extract_banner` on an unclosed fence inside the banner -> `['2026-10-13 -- head', '```', 'example', '## Still owed', '- x', '## Next session', 'y']`, and lint was clean under the cap. LANDED: `scripts/task.py::extract_banner` now tracks `fence_at` and refuses when `fence is not None and start < fence_at < stop`; the docstring has a new paragraph `A FENCE INSIDE THE SECTION (TK100)`. The pin is `tests/test_tasktool.py::test_lint_check_12_a_fence_inside_the_banner_section` plus the helper `fenced_note`. Clauses: A, a closed fence is accepted and printed in full; B, fenced lines count toward the cap (BANNER_MAX_LINES+1 -> red); C, an unclosed fence refuses in lint and board; D, the same with a closed fence above the banner; E, control: an unclosed fence AFTER the section is not refused; F, an unclosed fence ABOVE the section hides the heading and stays red as `has no ## Banner heading`; G, control: a blockquoted fence. MUTATION SWEEP (READ, 2026-10-13; the test was run via `against()` on mutated copies of task.py). Literal first failure per mutant: CONTROL GREEN | N0 HEAD task.py RED `C: an unclosed fence swallowed the rest of the note into the banner and lint was clean` | N1 refusal deleted RED C | N2 refuse any unclosed fence RED `E: an unclosed fence AFTER the banner was refused` | N3 fence_at = first opener RED D | N4 fence delimiters dropped RED `B: fenced banner lines did not count toward the cap` | N5 section stops at a fenced `## ` RED `A: board dropped the fenced lines of the banner` | N6 drop the `start <` bound GREEN, which is EQUIVALENT (REASONED: a fence still open at EOF that opened above the section has swallowed the `## Banner` heading, so `banners` is empty and None is returned first; see clause F) | N7 check_banner swallows the Refused RED C. Clauses A and B also held on HEAD task.py (probe: clause B's note -> 15 lines), so they pin existing behaviour. TESTS: `pytest tests/test_tasktool.py -q` -> 1 failed, 103 passed. The one failure is `test_shipped_config_is_measured_not_an_example`, on a minted-shape placeholder id another lane added in a `scripts/handoff_lint.py` comment (for TK98); the records stage reworded it 2026-10-13. `task.py lint` on the live tree -> `task lint: clean (13 checks, 253 task file(s) parsed), 28 warning(s)`; `task.py board` rc 0 and prints the real 2026-10-12c banner. Next action: none.
