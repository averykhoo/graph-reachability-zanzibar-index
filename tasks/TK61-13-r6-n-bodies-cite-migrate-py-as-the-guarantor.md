---
id: TK61
title: 13 R6-N bodies cite migrate.py as the guarantor of a count; it no longer exists
brief:
pri: LATER
size: S
deps: []
related: [TT-1]
parent:
labels: [docs]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07
updated: 2026-09-07
closed:
---

Thirteen open `R6-N` task bodies carry the sentence "the five round-wide traps (counted
from that section at generation time, not restated: `migrate.py` refuses to build if the
bullet count moves)".

The COUNT is still correct -- `docs/perf-round6-audit-2026-08.md`'s "Traps the numbers do
not carry" still has exactly five top-level bullets. The GUARANTOR is not: `migrate.py`
lived in `.scratch/tasktool/`, was neutralised on 2026-09-07 and deleted with the
directory. The sentence now claims an enforcement that cannot run.

This is precisely what `notes.md` "Still open" item 5 predicted, materialising in the
citation rather than in the figure: a trap that cites a mechanism which no longer exists is
weaker than one that admits the number is hand-maintained, because a reader who checks the
citation finds nothing and a reader who does not is falsely reassured.

Two honest resolutions: build the check (see the census item, same shape), or reword the
thirteen bodies to state that the count is hand-maintained and dated. The repo's standing
rule -- a trap must cite a symbol that EXISTS -- makes the current state the one option
that is not available.

## Traps

- Do not "fix" this by deleting the parenthetical and leaving a bare "five". That converts
  a broken citation into an unattributed restated count, which is worse.
- Whatever is written must survive the audit doc being corrected. The count is only right
  relative to that file.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 6
- [`CLAUDE.md`](../CLAUDE.md) -- "a trap must cite a symbol that EXISTS"

## Log
