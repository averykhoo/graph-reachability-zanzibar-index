---
id: TK86
title: the HANDOFF trap-badge budget counts one glyph and (!) evades it
brief: handoff_lint counts only the WARN glyph; a trap written (!) is free, and the banner already does it
pri: LATER
size: S
deps: []
related: [TK77]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-19d
moved: 2026-09-19d
updated: 2026-09-19d
closed:
---

`scripts/handoff_lint.py::check_warn_budget` counts one glyph and one glyph only --
`WARN = u'⚠'` (`:209`, budget checked at `:477-486`). A trap written with the ASCII
`(!)` instead is invisible to it, and `HANDOFF.md` already does this in several places:
the 2026-09-19c banner headline carried five `(!)` markers, the "Known live correctness
bugs" line carries one, and the 2026-09-19d headline written this session carries four.
So the trap budget -- which exists to force the DEFINED move (demote to a scope doc, or
promote to `CLAUDE.md`) -- can be satisfied by changing a character.

MEASURED 2026-09-19d: adding a 2026-09-19d banner line with one `⚠` took the count
from 10 to 11 and the lint went RED; the SAME line with `(!)` in that position is green
with no other change. That session took the defined move anyway (promoted the red-gate
snapshot trap into `CLAUDE.md`), but nothing made it.

This is the house failure mode in its usual shape: an assurance step that fails by
PASSING. A session with no room left will reach for `(!)`, the lint will say `clean`, and
the budget will have measured nothing.

⚠ Do NOT "fix" this by simply adding `(!)` to the counted set. Two reasons, both worth
checking before writing the patch:

* `(!)` is not unambiguously a trap badge. `python scripts/task.py board` RENDERS `⚠`
  as `(!)` on the way out (compare the board output against the raw `HANDOFF.md` line),
  so the two glyphs are already conflated at the read surface, and prose that happens to
  contain `(!)` would start costing budget.
* Widening the count without re-measuring the live corpus will turn the banner red at
  once (it would be ~15+ today, budget 10) -- which means the widening has to come with a
  decision about what leaves the banner, not just a one-line lint edit. That is the same
  shape as `GC-1`'s recorded reason for why widening is not free.

The cheap honest first step is a WARN rather than a FAIL: report how many `(!)`-style
markers the banner carries beside the counted total, so the evasion is at least visible.

## Log

### 2026-09-19d

(!) SECOND HALF OF THE SAME HOLE, found while filing this row on 2026-09-19d: the counter
has NO ESCAPE FOR QUOTING THE GLYPH. Writing a banner pointer that merely NAMES the badge
-- inside backticks, as a quoted character -- spends budget and turned the lint RED
(literally: `11 trap badges, budget 10`, on a line whose only new occurrence was inside a
backticked span). The pointer had to be written as `U+26A0` to stay green.

So the two guards in this file disagree about escaping. The figure guard has FOUR escapes
(a fenced block, a backticked/quoted span, a `YYYY-MM-DD` key on the line, a file whose
banner declares its body provenance -- see the banner's own trap). The badge counter has
none, and counts inside code spans. A check you cannot document inside the file it guards
is pushing every author toward the ASCII form -- which is the evasion at the top of this
row, so the two halves feed each other.

Whatever the fix is, it needs a sabotage that a `(!)`-written trap actually goes RED, and
a control that a QUOTED glyph does not. Both directions, or it will fail by passing again.
