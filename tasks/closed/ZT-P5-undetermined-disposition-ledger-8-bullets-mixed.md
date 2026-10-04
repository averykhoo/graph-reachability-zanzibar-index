---
id: ZT-P5
title: UNDETERMINED disposition: ledger: 8 bullets mixed - most CLOSED, bullet 6 still OPEN on live boar...
brief:
pri: HOLD
size: ?
deps: []
related: []
parent:
labels: [infra]
source: board
source_hash: acked-no-row
created: 2026-07-29
moved: 2026-10-04g
updated: 2026-10-04g
closed: 2026-10-04g
---

**Disposition UNDETERMINED at migration.** The records reached by the extract do not state whether this id is finished. What they do say: ledger: 8 bullets mixed - most CLOSED, bullet 6 still OPEN on live board, bullet 7 became B1

It is OPEN on `HOLD` because an unresolved fate is a reason to look, not a licence to bury. Resolve it by reading the sources below, then either `close -m` with the evidence or `promote` it into the real backlog.

## Traps

⚠ **Do not retire this id to clear it.** A retired id can never be re-minted, so retiring on an UNKNOWN disposition converts "we did not check" into "this can never name work again" — silently, and permanently. Closing requires a message carrying outcome evidence; that is the cheap, reversible move.

## Read first

- `docs/history/handoff-status-2026-07.md`
- `docs/history/session-log.md`

## Log

### 2026-08-21

Migrated by `migrate.py`. **The disposition was NOT determined**: the extract records it as `unknown`, and this script does not guess. The earlier pass retired it — the classifier asked only "is the disposition the string `closed`?" and sent every other answer, including "unknown", to `retired-ids.txt`. **Evidence lives at:** docs/history/handoff-status-2026-07.md; docs/history/session-log.md. **`pri: HOLD` is a record of ignorance, not a ranking**, and `created`/`moved` carry 2026-07-29, a per-family fallback taken from the reconciled ZT ledger in docs/history/handoff-status-2026-07.md, because the evidence string carries no session key.

No row on HANDOFF.md, and that is correct: ZT-P5 is covered by the retired line's WILDCARD -- "and the whole ZT-* zero-trust series". A literal line-by-line harvest (the one handoff_lint.py::check_ledger_row_ids runs, and the one task.py's parse_board mirrors so the two cannot disagree) yields that as the single token ZT-*, not as ZT-P5, which is why RETIRED-BUT-OPEN never fired on it and why it presented as an orphan instead. [Symbol cite corrected 2026-08-29d: there has never been a `check_ledger_ids`, so this trap cited a symbol that does not exist -- the same defect, in the same session, as HANDOFF.md:78. Note also that as of 2026-08-29d that check ALSO fails when a board row has no task file, which is a second reason the two harvests cannot disagree.] The disposition ledger is docs/history/handoff-status-2026-07.md. Nothing to file, nothing to close: the row is gone because the series was retired wholesale.

### 2026-10-04g

CLOSED 2026-10-04g: disposition DETERMINED -- every one of the 8 bullets is closed or carried by an open row (READ first-hand 2026-10-04g). Ledger docs/history/handoff-status-2026-07.md:67-73. Bullet 1: corrected, formal/FINAL_REVIEW.md "Priority argument CORRECTED 2026-07-29". Bullets 2 and 5: Python halves pinned (spec-deviations Target 3 / Target 2); the remaining Lean/hypothesis halves are carried by open row LT-1 (docs/latent-gaps.md, both targets "Filed by: spec-deviations ... ZT-P5"). Bullets 3, 4, 8: CLOSED in the ledger. Bullet 6 (unbenchmarked full ResidueV1 scan in _any_residue_reference): RESOLVED, index_v4/processor.py::DeltaProcessor._any_residue_reference is now "an indexed existence probe against ResidueRefV1 (it was a complete residue scan until the reverse index landed)". Bullet 7 (B1 star-freeness): formal/HANDOFF.md "B1 ... verdict: CLOSED 2026-08-16". Closed, not retired: the id may still be cited.
