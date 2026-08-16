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

WIRED INTO ``verify.sh`` as lean-phase step **4f** (board row ``HS-1``, 2026-08-16). It
rides ``lean`` rather than being an eleventh phase, for the reason 4d/4e do: pure Python,
no Lean toolchain, sub-second. Consequence, the same one 4e already carries -- **a
HANDOFF-only edit now needs ``lean`` green before push.** Rhythm step 0 still runs it by
hand while iterating; the gate is what makes it non-optional.

Of the three checks the redesign deferred to ``HS-1``, two landed here
(``check_bold_caps``, ``check_ledger_ordering``) plus ``check_ledger_row_ids``. The
fourth, full ``moved``-vs-ledger cross-validation, was **attempted and rejected** -- see
``check_ledger_row_ids``' docstring for the measurement that killed it.

SABOTAGE RECORD (per docs/sabotage-procedure.md -- every check below was broken on
purpose and watched go red before it was believed, 2026-08-16). The literal observed
output, one narrowest-plausible weakening per check::

    ceiling       FAIL: HANDOFF.md is 230 lines, ceiling 220.
    NOW count     FAIL: HANDOFF.md: found 2 NOW rows (lines [39, 43]), must be exactly 1.
    NEXT cap      FAIL: HANDOFF.md: found 4 NEXT rows (lines [40,41,42,43]), cap is 3.
    star glyph    FAIL: HANDOFF.md: 1 line(s) still use the retired star glyph ([139]).
    trap budget   FAIL: HANDOFF.md: 12 trap badges, budget 10.
    headline cap  FAIL: docs/history/session-log.md:28: entry headline is 238 chars, cap 120.

The three checks added 2026-08-16 with ``HS-1``, same protocol, literal output::

    bold caps     FAIL: formal/HANDOFF.md: 9 line(s) with bold ALL-CAPS outside a trap
                        paragraph, budget 8 (lines [29, 132, 143, 203, 205, 210, 354, 376]).
    bold caps     FAIL: HANDOFF.md: 1 line(s) ... budget 0 (lines [213]).   [one line appended]
    ledger order  FAIL: formal/history/PROOF_STATUS.md newest entry is 2026-09-01, but
                        docs/history/session-log.md only reaches 2026-08-16c.
    rows: ids     FAIL: docs/history/session-log.md:2 cites board id 'P99', which is on
                        neither the board nor its retired-ids line.

**The bold-caps sabotage failed first, and that is the point of running it.** The budgets
were initially set to 1 and 18, above the true post-restructure counts of 1 and 9. Lowering
the budget by one left the check SILENT -- it was slack, and guarded nothing. A budget above
the measured value is the same defect as a floor with headroom (cf. ``MIN_CONF_ALL`` /
``MIN_TESTS_ALL``, which carry zero by design). Both are now exact.

Two controls were run for the checks whose exemptions could have made them vacuous:

* ``check_bold_caps``' trap-paragraph exemption was tested by stripping every badge from
  ``formal/HANDOFF.md`` in memory: offenders went 9 -> 28. So the exemption exempts
  something real rather than everything.
* ``check_ledger_row_ids`` was re-run with a REAL id (``P15``) in the same position the
  bogus ``P99`` occupied; it stayed silent. Without that control the check could have been
  firing on the line's shape rather than on the id.

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
#   HANDOFF.md       landed at 200 lines (from 986) -> 220. RAISED to 260 on 2026-08-16
#                    (user-approved) when the post-migration audit added five board rows
#                    for the FINAL_REVIEW section-4 items the board's completeness charter
#                    claimed to cover and did not: the file went to 211, leaving nine lines
#                    of headroom, which is a tripwire on the next edit rather than on the
#                    next accretion LAYER. 260 restores roughly a dozen rows or two item
#                    blocks of room. It is deliberately not the ~2000 that was floated: at
#                    ten times the file the check would not fire until the board had
#                    re-accreted the entire 986-line disease and doubled it, i.e. it would
#                    stop being a guard at all, and section 11's decision was explicitly
#                    that the point is "firing on the first appended layer, not the
#                    absolute number".
#   formal/HANDOFF.md was 1005 lines with a 1105 ceiling that the script itself called
#                    "not a guard". HS-3 (the deep half) landed 2026-08-16: 1010 -> 471,
#                    so the ceiling drops to 520 as the same landed+10% rule prescribes.
MAX_LINES = {
    'HANDOFF.md': 260,
    'formal/HANDOFF.md': 520,
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

# --- Bold ALL-CAPS budgets (docs/README.md section 4: bold caps live only in trap lines) --
# These are RATCHETS, not allowances: set at the EXACT measured residue on 2026-08-16, so
# any new offending line fails immediately. Lower them when you clean a line; never raise
# one to fit a file. The root board is at a hard 0 -- its single offender was cleaned in
# the same commit. formal/HANDOFF.md keeps 9 as declared debt, following the repo's
# existing idiom for that (MAX_TESTS_XFAILED), which puts the debt in code that runs
# rather than in a doc nobody reads.
#
# ⚠ These were first set to 1 and 18 -- ABOVE the true counts -- and the sabotage caught
# it: lowering the budget by one left the check SILENT, i.e. it was slack and guarded
# nothing. A budget above the measured value is the same defect as a floor with headroom.
MAX_BOLDCAPS = {
    'HANDOFF.md': 0,
    'formal/HANDOFF.md': 9,
}

# The two ledgers, and the heading forms they use. Both keys are YYYY-MM-DD[letter], which
# sorts correctly under PLAIN STRING comparison: the letterless form is a prefix of every
# lettered same-day form, so "2026-08-16" < "2026-08-16b" < "2026-08-16c". No date parsing.
ROOT_LEDGER = 'docs/history/session-log.md'
FORMAL_LEDGER = 'formal/history/PROOF_STATUS.md'
_ROOT_ENTRY = re.compile(r'^## (\d{4}-\d\d-\d\d[a-z]?) ')
_FORMAL_ENTRY = re.compile(r'^## Session (\d{4}-\d\d-\d\d[a-z]?)\b')
_ROWS_LINE = re.compile(r'^rows:\s*(.+)$')
_ROW_ID = re.compile(r'\b([A-Z]{1,3}-?\d+|ZT-[A-Z0-9-]+)\b')


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


_BOLD_SPAN = re.compile(r'\*\*(.+?)\*\*', re.S)
_CODE_SPAN = re.compile(r'`[^`]*`')
_CAPS_WORD = re.compile(r'\b[A-Z]{2,}\b')


def _boldcaps_lines(lines, pri_linenos):
    """Line numbers carrying bold ALL-CAPS that docs/README.md section 4 does not allow.

    Three exemptions, each structural rather than a hand-kept list:

    * **Paragraph-scoped trap exemption.** The rule is written "inside a ⚠ line", but a
      trap is a PARAGRAPH and prose gets hard-wrapped, so a per-physical-line test would
      flag the second line of a trap and effectively ban line-wrapping. A line is exempt
      when any line in its blank-line-delimited block carries the badge.
    * **The pri column.** ``**NOW**`` / ``**NEXT**`` in the board table IS the sanctioned
      vocabulary of section 4, bolded exactly because it ranks. Located via the same
      header-name lookup the capacity check uses, never by column index.
    * **Code spans.** Caps inside backticks are identifiers (``ZT-*``, ``NO-BLOCK``),
      not shouting. Stripped before matching.
    """
    # blank-line-delimited blocks -> exempt whole block if any line has the badge
    exempt = set()
    start = 0
    for i in range(len(lines) + 1):
        if i == len(lines) or not lines[i].strip():
            if any(WARN in l for l in lines[start:i]):
                exempt.update(range(start + 1, i + 1))
            start = i + 1
    out = []
    for i, ln in enumerate(lines, 1):
        if i in exempt or i in pri_linenos:
            continue
        stripped = _CODE_SPAN.sub('', ln)
        if any(_CAPS_WORD.search(s) for s in _BOLD_SPAN.findall(stripped)):
            out.append(i)
    return out


def check_bold_caps(fail):
    for rel, budget in sorted(MAX_BOLDCAPS.items()):
        lines = _read(rel)
        if lines is None:
            continue
        pri_linenos = {ln for _, ln in _pri_values(lines)} if rel == ROOT_BOARD else set()
        hits = _boldcaps_lines(lines, pri_linenos)
        if len(hits) > budget:
            fail('%s: %d line(s) with bold ALL-CAPS outside a trap paragraph, budget %d '
                 '(lines %s). docs/README.md section 4 confines bold caps to ⚠ lines so '
                 'that emphasis still ranks. The budget is a RATCHET: clean a line and '
                 'lower it, never raise it to fit.'
                 % (rel, len(hits), budget, hits[:8]))


def _entry_keys(rel, pattern):
    lines = _read(rel)
    if lines is None:
        return None
    return [m.group(1) for m in (pattern.match(l) for l in lines) if m]


def check_ledger_ordering(fail):
    """The root ledger must not lag the formal one.

    House rule: one ROOT entry every session, and a formal-heavy session writes its detail
    to PROOF_STATUS and points at it from the root. So a PROOF_STATUS entry newer than
    anything in the root ledger means a session wrote formal detail and skipped the root
    entry -- which silently breaks the board's `moved` column, whose whole meaning is that
    every session leaves a dated trace.
    """
    root = _entry_keys(ROOT_LEDGER, _ROOT_ENTRY)
    formal = _entry_keys(FORMAL_LEDGER, _FORMAL_ENTRY)
    for rel, keys in ((ROOT_LEDGER, root), (FORMAL_LEDGER, formal)):
        if keys is None:
            fail('MISSING: %s' % rel)
            return
        if not keys:
            fail('%s: no entry headings matched. If the heading format changed, fix this '
                 'check rather than deleting it -- it is the only thing asserting that a '
                 'formal session also wrote a root ledger entry.' % rel)
            return
    if max(formal) > max(root):
        fail('%s newest entry is %s, but %s only reaches %s. Every session writes ONE root '
             'ledger entry, formal-heavy ones included (they put the detail in '
             'PROOF_STATUS and point at it). Append the missing root entry.'
             % (FORMAL_LEDGER, max(formal), ROOT_LEDGER, max(root)))


def check_ledger_row_ids(fail):
    """Every board id named in a ledger `rows:` line must be a real id.

    Deliberately NOT the reverse check (every moved row must appear in some `rows:` line):
    that was tried on 2026-08-16 and rejected. The `2026-08-16c` entry covers ~20 rows with
    the prose clause "every open item re-keyed onto the new board" rather than an id list,
    so the reverse direction false-fails most of the board on the very commit that created
    the ledger. This direction catches typos and invented ids and cannot false-fail.
    """
    board = _read(ROOT_BOARD)
    lines = _read(ROOT_LEDGER)
    if board is None or lines is None:
        return
    known = set()
    for cells, _ in _table_rows(board):
        known.add(cells[0].replace('`', '').strip())
    for ln in board:
        if 'Closed ids stay retired' in ln or 'survives as the historical grouping' in ln:
            known.update(m.group(1) for m in _ROW_ID.finditer(ln.replace('`', ' ')))
    known.discard('')
    if len(known) < 5:
        fail('%s: parsed only %d board ids; the id parser is broken, so this check would '
             'pass by comparing against nothing. Fix it.' % (ROOT_BOARD, len(known)))
        return
    for i, ln in enumerate(lines, 1):
        m = _ROWS_LINE.match(ln.strip())
        if not m:
            continue
        for cited in _ROW_ID.finditer(m.group(1)):
            if cited.group(1) not in known:
                fail('%s:%d cites board id %r, which is on neither the board nor its '
                     'retired-ids line. Ids are never reused, so a citation that resolves '
                     'to nothing is a typo or an invented id.'
                     % (ROOT_LEDGER, i, cited.group(1)))


CHECKS = (
    check_ceilings,
    check_priority_capacities,
    check_no_stars,
    check_warn_budget,
    check_frozen_banners,
    check_ledger_headlines,
    check_bold_caps,
    check_ledger_ordering,
    check_ledger_row_ids,
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
