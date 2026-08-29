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
moved: 2026-07-29
updated: 2026-08-21
closed:
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

No row on HANDOFF.md, and that is correct: ZT-P5 is covered by the retired line's WILDCARD -- "and the whole ZT-* zero-trust series". A literal line-by-line harvest (the one handoff_lint.py::check_ledger_ids runs, and the one task.py's parse_board mirrors so the two cannot disagree) yields that as the single token ZT-*, not as ZT-P5, which is why RETIRED-BUT-OPEN never fired on it and why it presented as an orphan instead. The disposition ledger is docs/history/handoff-status-2026-07.md. Nothing to file, nothing to close: the row is gone because the series was retired wholesale.
