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
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
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

### 2026-10-07c

Promoted LATER -> NEXT by the owner (2026-10-07c, in chat), on the recommendation of the 2026-10-07 cross-repo context audit (docs/context-audit-2026-10-07.md item 5): a 2026-10-05 Still-owed bullet had already been re-stamped instead of acted on. HS-5 and TK86 stay at LATER (owner chose only TK97).

### 2026-10-12b

Re-ranked 2026-10-12b (user approved the order in chat): TK118 NOW, then TK79, then TK102 (NEXT); TK97 and TK44 down to LATER (process tooling / coverage research with no known bug); TK134+TK135 stay LATER, user says no rush to release 0.0.4. Why TK118 first: it is the only row about a fail-OPEN, and it bears on what we tell production users about residue today.

### 2026-10-13

LANDED 2026-10-13 (batch lane L4a): `scripts/handoff_lint.py::check_still_owed_fresh`, APPENDED at `CHECKS[12]`. NUMBERING DECISION: it is NOT "check 15". That number belongs to `task.py`'s numbered series, while `handoff_lint.py::CHECKS` is unnumbered and cited by NAME. The CHECKS comment and the docstring both say so. RULE: every top-level bullet of `## Still owed` in HANDOFF.md carries a session key (`YYYY-MM-DD[letter]`, matched anywhere on the bullet including its indented continuation lines). Its OLDEST key must be >= the second-newest root-ledger key (`STILL_OWED_SESSIONS = 2`: the writing session and the next one, which must consume it). DECISIONS (REASONED): (1) The bound is in LEDGER ENTRIES, not days. A day count would redden over a quiet weekend and let a bullet survive a five-session day; the ledger is the clock the rule is about. Keys compare as strings, which is the ledger's own order (`2026-10-12` < `2026-10-12b`). (2) RE-STAMPING DOES NOT RESET AGE: min() of all keys on the bullet, so `(2026-10-05, re-stamped 2026-10-06)` counts as 2026-10-05. Accepted side effect: a bullet that cites an older entry reads as old; the remedy (file a row) is the right one anyway. (3) A missing `## Still owed` section is RED, so deleting it is not a way to pass. A keyless bullet is RED. A bare `- Nothing` is allowed (docs/README.md sec 7 prescribes "Nothing"). Fenced lines are skipped, and a fenced `## ` line does not end the section. TESTS: `tests/test_handoff_lint_still_owed.py` (11 tests), plus `tests/test_handoff_lint_b_prime.py::test_the_two_checks_are_in_the_list_and_nothing_was_inserted`, which now pins `names[12]` and `len == 13`. SABOTAGE (first-hand, 2026-10-13, on a temp-dir COPY after a clean baseline of `96 passed`; every anchor asserted to occur exactly once): S1 no-key skipped -> FAILED test_a_bullet_with_no_key_is_red + test_prose_and_fences_in_the_section_are_not_bullets. S2 `max(stamps)` -> FAILED test_restamping_does_not_reset_age + test_a_wrapped_bullet_is_read_whole. S3 bound +1 -> FAILED test_a_bullet_two_entries_old_is_red. S4 missing section returns clean -> FAILED test_a_missing_section_is_red. S5 continuation arm removed -> FAILED test_a_wrapped_bullet_is_read_whole. S6 removed from CHECKS -> FAILED test_the_check_is_appended + b_prime's positional pin. The literal lines are in the module docstring. LIVE (READ 2026-10-13): `python scripts/handoff_lint.py` -> `FAIL: HANDOFF.md:21: a ## Still owed bullet is stamped 2026-10-05, older than 2026-10-12b`. That is the TK107-leftover bullet the batch disposes of elsewhere (records stage 2026-10-13 deleted it after lane L5 confirmed all three named docs handled). Probe with that bullet removed: all 13 checks clean. docs/README.md sec 7 step 2 now states the rule.
