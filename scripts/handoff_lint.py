#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""handoff_lint.py -- mechanical guards on the two board files and the ledgers.

Run it before committing any board edit (it is step 0 of HANDOFF.md's Rhythm)::

    python scripts/handoff_lint.py

Exit 0 = clean, exit 1 = at least one violation, exit 2 = a file it needs is missing.

WHY THIS EXISTS
---------------
The 2026-08-16 handoff redesign replaced a 986-line accreted status file with a compact
board. Every capacity in that design -- one ``NOW`` row, at most three ``NEXT`` rows, a
bounded trap budget, a line ceiling -- was prose, and this repo's own record shows what
happens to a capacity nobody checks: ``HANDOFF.md`` restated gate counts in prose three
separate times after a rule forbade it (``ZT-P3-5``), and ``formal/HANDOFF.md`` still
claimed "~250 lines top to bottom" at 1005 lines. An unenforced size claim rots exactly
like an unenforced count. So this ships WITH the migration rather than after it: the
habit-forming window is the first weeks, and a guard that first fires on the fifth
accretion layer has taught everyone that layers are the convention.

THE HONEST LIMIT OF EVERY CHECK HERE
------------------------------------
None of this verifies that the board is TRUE, useful, or current. It cannot tell you that
a ``NOW`` row is the right ``NOW``, that a pointer resolves to something a session can
act on, or that a ``moved`` date is not a lie. It converts *silently violated* into
*loudly must-look*, and nothing more. In particular ``check_frozen_banners`` proves a
banner exists, never that the document under it is actually frozen.

NOT WIRED INTO ``verify.sh`` YET -- that is board row ``HS-1``, which also adds the
checks deliberately left out here (bold-caps outside trap lines, ``moved``-vs-ledger
cross-validation, newest-session-log >= newest-PROOF_STATUS). Until then Rhythm step 0
runs it by hand.

SABOTAGE RECORD (per docs/sabotage-procedure.md -- every check below was broken on
purpose and watched go red before it was believed, 2026-08-16). The literal observed
output, one narrowest-plausible weakening per check::

    ceiling       FAIL: HANDOFF.md is 230 lines, ceiling 220.
    NOW count     FAIL: HANDOFF.md: found 2 NOW rows (lines [39, 43]), must be exactly 1.
    NEXT cap      FAIL: HANDOFF.md: found 4 NEXT rows (lines [40,41,42,43]), cap is 3.
    star glyph    FAIL: HANDOFF.md: 1 line(s) still use the retired star glyph ([139]).
    trap budget   FAIL: HANDOFF.md: 12 trap badges, budget 10.
    headline cap  FAIL: docs/history/session-log.md:28: entry headline is 238 chars, cap 120.

Two things that make the above evidence rather than decoration:

* **The instrument was controlled too.** Each sabotage was checked against the baseline
  first. Five of the six markers were ABSENT from a clean run, so the red is attributable
  to the sabotage. The sixth -- the star glyph -- was already present at baseline (from
  ``formal/HANDOFF.md``), so that case only counts because the new failure line names
  ``HANDOFF.md`` specifically: a check that had merely re-reported the old file would have
  proved nothing.
* **``check_frozen_banners`` was caught failing-by-passing and fixed.** Its first version
  tested ``'LIVING' in head`` as a plain substring, which every frozen archive satisfied
  via the prose "provenance, not a **living** document" -- so it reported clean on exactly
  the files it existed to police, hiding six real violations. The match is now anchored to
  the bold declaration form (``_DECLARATION`` / ``_FROZEN_DECL``).

The harness that produced this is deliberately not committed: it rewrites tracked files in
place and restores them, which is fine to run by hand and a hazard to leave lying around.
Re-derive it from this list if you change a check.
"""

import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Ceilings -------------------------------------------------------------------------
# Provenance: set at LANDED SIZE + ~10% on 2026-08-16, per the redesign's section 11
# decision ("a max must exist, but its VALUE is not pre-committed"). Raising either is a
# deliberate act: say why in the commit message, not in a drive-by edit.
#   HANDOFF.md       landed at 200 lines (from 986) -> 220
#   formal/HANDOFF.md was 1005 lines and is NOT restructured yet; its deep half is board
#                    row HS-3. LOWER THIS to that file's new landed size + 10% when HS-3
#                    closes -- a ceiling far above the file is not a guard.
MAX_LINES = {
    'HANDOFF.md': 220,
    'formal/HANDOFF.md': 1105,
}

BOARD_FILES = ('HANDOFF.md', 'formal/HANDOFF.md')
ROOT_BOARD = 'HANDOFF.md'

NEXT_MAX = 3          # redesign section 4: NEXT is capped so the ranking argument happens
                      # once, at write time, instead of every session re-deriving it.
WARN_BUDGET = 10      # redesign section 4: traps rank only while they are scarce.
HEADLINE_MAX = 120    # a ledger headline is copied verbatim into the board banner.

# The headline cap applies to the ROOT ledger only, because the justification is "the
# headline is copied verbatim into the board banner" and only this ledger's headlines are.
# Scoping it to formal/history/PROOF_STATUS.md too was tried on 2026-08-16 and reverted:
# it fired 60 times on an APPEND-ONLY file whose entries may never be retro-edited, i.e.
# it demanded a fix that its own convention forbids. A check that cannot be satisfied is
# a check that gets commented out.
HEADLINE_LEDGERS = ('docs/history/session-log.md',)
HISTORY_DIRS = ('docs/history', 'formal/history')

# How far into a file the liveness declaration may sit. 5 was the design's number; 10 is
# what the tree actually needs -- a doc legitimately opens with a title, a blank, and a
# one-line status paragraph before its banner. Still above the fold either way.
LIVENESS_WINDOW = 10

# The declaration must be a BOLD KEYWORD, not merely the word somewhere in the prose.
# Caught 2026-08-16 by sabotage: a plain substring test for "LIVING" silently exempted
# every file whose banner read "provenance, not a living document" -- i.e. the check
# passed on exactly the frozen archives it was written to police, and reported clean.
# That is this project's house failure mode (an assurance step that fails by PASSING),
# so the match is anchored to the declaration form docs/README.md section 3 prescribes.
_DECLARATION = re.compile(r'\*\*(LIVING|ACTIVE-PLAN)\b')
_FROZEN_DECL = re.compile(r'\*\*FROZEN\b')

WARN = u'⚠'      # the trap badge
STAR = u'★'      # retired from the board files


def _read(rel):
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        return None
    with io.open(path, encoding='utf-8') as fh:
        return fh.read().split('\n')


def _table_rows(lines):
    """Yield (cells, lineno) for every markdown table row that has a pri-like shape."""
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s.startswith('|') or not s.endswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) >= 6:
            yield cells, i


def _pri_values(lines):
    """The pri column of the board table, normalised. Located by HEADER NAME, not index:
    an index would silently read the wrong column the day a column is inserted."""
    pri_at = None
    out = []
    for cells, lineno in _table_rows(lines):
        low = [c.lower() for c in cells]
        if 'pri' in low and 'id' in low:
            pri_at = low.index('pri')
            continue
        if pri_at is None or pri_at >= len(cells):
            continue
        val = cells[pri_at].replace('*', '').replace('`', '').strip().upper()
        if val in ('NOW', 'NEXT', 'LATER', 'HOLD', 'SOMEDAY'):
            out.append((val, lineno))
    return out


def check_ceilings(fail):
    for rel, cap in sorted(MAX_LINES.items()):
        lines = _read(rel)
        if lines is None:
            fail('MISSING: %s (a ceiling on a file that does not exist guards nothing)' % rel)
            continue
        n = len([l for l in lines if True])
        if lines and lines[-1] == '':
            n -= 1
        if n > cap:
            fail('%s is %d lines, ceiling %d. Do not raise the ceiling to fit the file: '
                 'move content to its home per docs/README.md section 1, or raise it '
                 'deliberately and say why in the commit.' % (rel, n, cap))


def check_priority_capacities(fail):
    lines = _read(ROOT_BOARD)
    if lines is None:
        return
    pris = _pri_values(lines)
    if not pris:
        fail('%s: found no board rows with a recognised pri value. The parser looks for a '
             'markdown table with "id" and "pri" header cells -- if the board was '
             'restructured, fix this check rather than deleting it.' % ROOT_BOARD)
        return
    now = [ln for v, ln in pris if v == 'NOW']
    nxt = [ln for v, ln in pris if v == 'NEXT']
    if len(now) != 1:
        fail('%s: found %d NOW rows (lines %s), must be exactly 1. NOW is what an '
             'unassigned session picks up; two of them is no ranking at all.'
             % (ROOT_BOARD, len(now), now or '-'))
    if len(nxt) > NEXT_MAX:
        fail('%s: found %d NEXT rows (lines %s), cap is %d. Demote one to LATER -- the cap '
             'is the mechanism that forces the ranking argument.'
             % (ROOT_BOARD, len(nxt), nxt, NEXT_MAX))


def check_no_stars(fail):
    for rel in BOARD_FILES:
        lines = _read(rel)
        if lines is None:
            continue
        hits = [i for i, ln in enumerate(lines, 1) if STAR in ln]
        if hits:
            fail('%s: %d line(s) still use the retired star glyph (lines %s). Priority is '
                 'a word in the pri column; a glyph anyone can add for free ranks nothing.'
                 % (rel, len(hits), hits[:8]))


def check_warn_budget(fail):
    lines = _read(ROOT_BOARD)
    if lines is None:
        return
    n = sum(ln.count(WARN) for ln in lines)
    if n > WARN_BUDGET:
        fail('%s: %d trap badges, budget %d. Overflow is a DEFINED move, not a judgement '
             'call: demote the trap to its item\'s scope-doc "Traps" section and leave the '
             'pointer -- or, if it is durable and repo-wide, put it in CLAUDE.md.'
             % (ROOT_BOARD, n, WARN_BUDGET))


def check_frozen_banners(fail):
    """Every file under a history dir declares its liveness in its first 5 lines.

    The exemption is STRUCTURAL -- a file is exempt if it declares LIVING or ACTIVE-PLAN
    up top -- deliberately NOT a hand-maintained filename list. That pattern has already
    failed twice in this tree; a list beside a glob goes stale the first time someone adds
    a file and does not think to update it.
    """
    for d in HISTORY_DIRS:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if not name.endswith('.md'):
                continue
            rel = '%s/%s' % (d, name)
            lines = _read(rel) or []
            head = '\n'.join(lines[:LIVENESS_WINDOW])
            if _DECLARATION.search(head):
                continue
            if not _FROZEN_DECL.search(head):
                fail('%s: no FROZEN / LIVING / ACTIVE-PLAN declaration in its first %d '
                     'lines. A reader cannot tell whether its status lines are still '
                     'true. See docs/README.md sections 2-3 for the banner text.'
                     % (rel, LIVENESS_WINDOW))


def check_ledger_headlines(fail):
    for rel in HEADLINE_LEDGERS:
        lines = _read(rel)
        if lines is None:
            continue
        for i, ln in enumerate(lines, 1):
            if not ln.startswith('## '):
                continue
            if len(ln) > HEADLINE_MAX:
                fail('%s:%d: entry headline is %d chars, cap %d. It is copied verbatim '
                     'into the board banner, which is one line.'
                     % (rel, i, len(ln), HEADLINE_MAX))


CHECKS = (
    check_ceilings,
    check_priority_capacities,
    check_no_stars,
    check_warn_budget,
    check_frozen_banners,
    check_ledger_headlines,
)


def main():
    failures = []
    for check in CHECKS:
        check(failures.append)
    if failures:
        sys.stderr.write('handoff_lint: %d violation(s)\n\n' % len(failures))
        for f in failures:
            sys.stderr.write('  FAIL: %s\n\n' % f)
        return 1
    sys.stdout.write('handoff_lint: clean (%d checks)\n' % len(CHECKS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
