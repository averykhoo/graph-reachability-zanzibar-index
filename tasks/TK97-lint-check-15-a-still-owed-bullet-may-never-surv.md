---
id: TK97
title: lint check 15: a Still-owed bullet may never survive two sessions
brief: Still owed has no checker; 0 of 5 live bullets were skipped-Rhythm actions, oldest 15 days
pri: LATER
size: M
deps: []
related: [TK96]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-09-22
updated: 2026-09-22
closed:
---

`HANDOFF.md`'s `## Still owed` section has NO checker and has accreted a backlog. Censused
first-hand 2026-09-22: 5 bullets, `HANDOFF.md:30-50` -- **20 lines, one third of the
60-line note** -- and **0 of 5** were what the section is specified to hold.

The spec is narrow and explicit. `docs/tree-sole-authority-spec-2026-08-29.md:95-102`
defines the one-hop note as three sections, of which (2) is *"**Still owed** -- the verbatim
skipped Rhythm actions"*, and adds *"No table, no item blocks"*. The disposition found:

| line | bullet | verdict |
|---|---|---|
| `:32` | ledger receipt vocabulary has no "entered via `show`" token | self-says "Unfiled"; dates itself `2026-09-07b` (15 days) |
| `:36` | a percentage has no mechanical guard | self-says "FILED as `GC-1`" -- `GC-1` exists at `pri: LATER`, so this is a SECOND COPY |
| `:39` | `MIN_TESTS_ALL` ratcheted by hand | self-says "Unfiled" |
| `:44` | `TT-8` left one behaviour observed but unpinned | a finding, not a skipped step |
| `:46` | `P6` stage 2 | an ITEM BLOCK, which the spec bans by name -- and half of it is STALE (see below) |

**Why it drifted: it is the one permitted section with no checker.** `check_ceilings` counts
lines only; `check_banner` (`task.py` check 12) covers the Banner; grep of `scripts/` for
the string `Still owed` returns NOTHING. The Banner, which has even a weak checker (first
line must carry a date and a session key -- its own docstring calls the rule "deliberately
weak"), is rewritten every session in practice. Observed live on 2026-09-21/22: two
consecutive sessions rewrote the banner and left all five Still-owed bullets BYTE-IDENTICAL.

**The rule, and why "cleared every session" is the wrong shape.** The user's original intent
(confirmed 2026-09-22) was that the note be ephemeral. It IS the stated design -- "Rewritten
every session, never appended" (spec `:97`), "`HANDOFF.md` is rewritten whole every session"
(`docs/README.md` sec 6) -- so it was never too restrictive, only unenforced. But Banner and
Still owed have DIFFERENT lifecycles: the Banner is REPLACE (session N overwrites N-1,
nothing is lost because it is state-of-play), while Still owed is CONSUME (session N writes
it FOR N+1, which executes and deletes it -- a work queue of depth one). A literal "clear it
every session" would delete the baton, which is probably why it was written as the softer
"rewritten every session" and why nobody could enforce it.

**The checkable form -- lint check 15:**

> Every `## Still owed` bullet carries a session key, and that key is the current or the
> immediately-previous entry in `docs/history/session-log.md`. Older -> it survived a
> handoff -> it is backlog, not a baton -> file it as a task row.

Against the 2026-09-22 file all five bullets go red: `:32` carries `2026-09-07b`, `:46`
carries `2026-09-15b`, and `:36` / `:39` / `:44` carry no key at all. It would have fired on
day one of the drift. The incentive is the point: "I ran out of context" stays cheap and
honest (write the bullet, stamp your key), while "I will park this here forever" becomes
expensive, because the only way to keep it is to file a row.

## Traps

- (!) **`task.py:3282` reserves the number**: check 13 retired at the cutover and its number
  is never reused, so *"The next check appended here is number 15."* This check is 15, and
  it is APPENDED, never inserted -- the checks are cited BY NUMBER in this file, in the
  spec, in `tasks/config.json`'s `_provenance` and in the sabotage records.
- (!) **This check lives in `handoff_lint.py`, not `task.py`.** Its subject is the note, and
  `handoff_lint.py` deliberately imports nothing from `task.py` (same independence argument
  as `tests/oracle.py` vs the backends). Numbering: `task.py`'s checks are the numbered
  series; `handoff_lint.py::CHECKS` is unnumbered by its own comment. Decide which series
  "check 15" means BEFORE writing it down anywhere, or the citation is ambiguous forever.
- (!) **Sabotage it** (`docs/sabotage-procedure.md`): a bullet stamped with a 3-session-old
  key must go RED, and a bullet with NO key must go red too -- the no-key case is the one 3
  of 5 live bullets are in, and a check that only inspects keys it can parse would pass them
  all. Sweep the module with mutations; one sabotage certifies one test.
- (!) **Do not "fix" the current file by stamping today's key onto the old bullets.** That
  is the fail-by-passing move. The 2026-09-22 session DISPOSED of all five (three filed as
  rows, one deleted as a `GC-1` duplicate, one deleted as duplicate-plus-stale); the check
  is what stops them coming back.

## Read first

- [`../docs/tree-sole-authority-spec-2026-08-29.md`](../docs/tree-sole-authority-spec-2026-08-29.md)
  sec (ii), `:95-102` -- FROZEN. The three permitted sections and the "no item blocks" line.
- [`../docs/README.md`](../docs/README.md) sec 6 "Boards replace; ledgers accrete" -- the
  replace-vs-accrete split this check enforces the missing third case of (consume).
- [`../docs/README.md`](../docs/README.md) sec 4 -- *"Signals rank only if they are
  bounded"*. Two channels have now drifted for exactly the reason that heading gives: this
  section, and the compass badge (see the `ASK-*` row).
- `scripts/handoff_lint.py::check_ceilings` / `::check_session_receipt` -- the neighbours,
  and the receipt check is the model for reading the newest ledger entry.
- `scripts/task.py::check_banner` -- read its docstring on why a deliberately WEAK
  anti-staleness rule is still worth having.

## Log
