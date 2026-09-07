---
id: TK60
title: no parent-census lint check; R6's census sentence is hand-maintained prose
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
moved: 2026-09-07b
updated: 2026-09-07b
closed: 2026-09-07b
---

`notes.md` "Still open" item 1 named a parent-census lint check as the durable fix for a
known weakness: the `R6` parent's census sentence and its children's trap count are
hand-maintained PROSE with nothing recomputing them. The check has now been deferred
through three renumbering opportunities -- slot 11 went to `check_parent_depth`, slot 12 to
`check_banner`, slot 13 to `check_board_sync` (retired at the cutover, number never
reused).

The mitigation that was used instead -- correct the prose by hand -- has already been
needed once: the `R6` title moved from "11 to land" to "10 to land" when `R6-6` closed. The
failure mode is exactly the one the check would have caught, and the record that predicted
it lived only in the deleted `.scratch/tasktool/`.

A census check recomputes, from the children on disk, what the parent's title and body
assert about them, and fails when the two disagree.

## Traps

- The next check appended is number 14; 13 is retired and never reused
  (`scripts/task.py::LINT_CHECKS`).
- Do not restate the check count anywhere in prose while doing this -- that is the defect
  class this whole family of work exists to stop.
- The parent's census sentence is generated text in origin. Recomputing it at lint time is
  the fix; rewriting it by hand again is not.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 5
- `scripts/task.py` -- `LINT_CHECKS` and `check_parent_depth` as the nearest shape

## Log

### 2026-09-07b

LANDED, and NOT as proposed. No parent-census lint check was built. The census was DELETED
instead, which is the cheaper and more durable fix: R6 title no longer carries a count
clause, and the body paragraph that asserted "10 LATER, 3 HOLD, 6 closed" is replaced by the
query that derives it (`task.py list --parent R6 --limit 0 --all`). Nothing to recompute
means nothing to drift, and no check 14 slot spent.

Two things found while doing it, both recorded in the row:
  * the migrate.py::r6_census attribution was dead (deleted with .scratch/tasktool/), so the
    "generated, not typed" claim was false on its face -- the TK61 defect, in a second place.
  * R6 now has 37 children, not 19: TK17-TK32 and TK47/TK48 are parented there too. The old
    census silently meant "R6-N children only" and had a caveat bolted on to say so. A
    census check would have had to encode that scope rule; the query plus one warning
    sentence does it without a mechanism.

Judgements that are NOT derivable -- which candidates were declined and on what number --
were left in place. Only the counts went.

Check 14 remains unspent and is claimed by TK59 (read-first resolver).
