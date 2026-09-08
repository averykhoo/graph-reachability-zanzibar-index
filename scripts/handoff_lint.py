#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""handoff_lint.py -- mechanical guards on the two handoff notes and the ledgers.

Run it before committing any edit to them (it is step 0 of the Rhythm, docs/README.md
section 7; until the 2026-09-06 cutover the Rhythm lived in HANDOFF.md itself)::

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

The tenth check, added 2026-08-20 with ``HS-2`` (the ``docs/spec-deviations.md`` split),
same protocol, literal output::

    doc links     FAIL: HANDOFF.md:63 links to 'docs/latent-gap.md', which does not exist
                        (resolved to docs/latent-gap.md).

Nothing in this repo resolved a doc-to-doc markdown link before it -- ``verify.sh`` step 4d
resolves ``file::symbol`` anchors in ``formal/CORRESPONDENCE.md`` and nothing else -- so a
rename or a split rotted every inbound pointer at full green. See ``check_doc_links``'
docstring for the two controls and for the 32 false reds its first version produced.

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

**CORRECTION, 2026-08-24c (board row ``TK46``): the ``P99`` sabotage above was NOT
sufficient, and this record over-claimed for eight days.** ``P99`` is a shape ``_ROW_ID``
parses correctly, so it certified the COMPARISON and could not see that the EXTRACTOR was
blind: ``R6-99`` matched ``R6``, a real id, and an invented sub-item citation reported
clean across all nineteen ``R6-N`` ids. Both halves are now pinned as tests rather than as
a docstring claim -- ``tests/test_handoff_lint_row_ids.py``, which asserts on the extracted
TOKENS and not only on the verdict, and whose module docstring carries the literal output.
The transferable rule is filed as ``docs/sabotage-procedure.md`` section "A check that
PARSES before it compares has two halves". Read it before certifying any check here --
every check below extracts something (ids, links, entry keys, table cells) before it
judges anything, so every one of them has the same two halves and the same easy mistake
available.

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

``check_restated_counts`` (added 2026-09-08, task ``TK58``) breaks the pattern above and
should be read as the better model: its sabotage, its five escapes' measured
contributions, and a ten-mutation sweep of its own test module all live in
``tests/test_handoff_lint_count_guard.py``, where they RUN. Everything above this
paragraph is a transcript that nothing re-executes -- accurate on its date, and unable to
notice the day it stops being true.
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
#                    absolute number". LOWERED to 60 on 2026-09-06 (the Phase B-prime
#                    cutover, user go): the row table, item blocks, standing traps,
#                    "Where things live" and the Rhythm all left the file -- the tree is
#                    the authority and the file is a one-hop note (title, pointers, the
#                    banner `board` prints, still-owed, next-session). 60 is the spec's
#                    figure (docs/tree-sole-authority-spec-2026-08-29.md), not landed+10%:
#                    the point of a one-hop note is that it CANNOT grow a table back.
#   formal/HANDOFF.md was 1005 lines with a 1105 ceiling that the script itself called
#                    "not a guard". HS-3 (the deep half) landed 2026-08-16: 1010 -> 471,
#                    so the ceiling drops to 520 as the same landed+10% rule prescribes.
MAX_LINES = {
    'HANDOFF.md': 60,
    'formal/HANDOFF.md': 520,
}

BOARD_FILES = ('HANDOFF.md', 'formal/HANDOFF.md')
ROOT_BOARD = 'HANDOFF.md'

# The file-per-task tree, the sole authority on open work since the 2026-09-06 cutover
# (on trial as the board's replacement from 2026-08-23). Named here rather than reached
# for inline because two checks read it, and because its ABSENCE is a legitimate state
# this script must keep working in -- a temp root in a test (see ``_tree_ids``).
TASKS_DIR = 'tasks'
# Non-task markdown inside tasks/. Duplicated from ``scripts/task.py::NON_TASK_MD`` rather
# than imported: this script imports nothing from the tool it is meant to cross-check, for
# the same reason ``tests/oracle.py`` imports nothing from the backends -- one bug must not
# be able to corrupt both sides. Duplication of a two-element tuple is the cheap half of
# that trade, and the disagreement it could cause is a spurious extra id, not a missed one.
TASKS_NON_TASK_MD = ('BANNER.md', 'README.md')

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
#
# formal/HANDOFF.md: 9 -> 6 on 2026-08-17 (row ``HS-4``). The retirement pass moved the
# 2026-08-09 and 2026-08-08 dated blocks to history, and three of the nine offenders went
# with them (they were lines 227/229/234 of the 2026-08-09 block). Re-measured at 6, which
# is the ratchet's rule -- leaving it at 9 would have bought three free offenders for the
# next session, i.e. re-created exactly the slack the original sabotage caught.
MAX_BOLDCAPS = {
    'HANDOFF.md': 0,
    'formal/HANDOFF.md': 6,
}

# The two ledgers, and the heading forms they use. Both keys are YYYY-MM-DD[letter], which
# sorts correctly under PLAIN STRING comparison: the letterless form is a prefix of every
# lettered same-day form, so "2026-08-16" < "2026-08-16b" < "2026-08-16c". No date parsing.
ROOT_LEDGER = 'docs/history/session-log.md'
FORMAL_LEDGER = 'formal/history/PROOF_STATUS.md'

# --- Doc-to-doc links (check_doc_links, added 2026-08-20 with board row ``HS-2``) --------
# The set of LIVING roots whose links a cold session actually follows. Deliberately a short
# explicit list rather than a glob over docs/: a glob would sweep in frozen archives, whose
# links are PROVENANCE and may legitimately point at a path that no longer exists (see
# docs/README.md section 2), and a check that demands a fix its own convention forbids is a
# check that gets commented out -- the same reasoning that scoped HEADLINE_LEDGERS.
LINKED_DOCS = (
    'HANDOFF.md',
    'formal/HANDOFF.md',
    'CLAUDE.md',
    'README.md',
    'docs/README.md',
    'docs/spec-deviations.md',
    'docs/latent-gaps.md',
    'docs/architecture/overview.md',
)

# Floor on links PARSED, not on links broken. Without it a regex that stops matching -- a
# link-syntax change, a rename of every file in LINKED_DOCS -- turns this check into a
# green no-op forever. This is an INSTRUMENT control, not a coverage ratchet, so unlike
# MAX_BOLDCAPS it is deliberately loose: it answers "is this check looking at anything at
# all", and the same idiom with the same slack is check_ledger_row_ids' ``len(known) < 5``
# against ~30 real ids. Measured 220 at landing (2026-08-20); 100 survives retiring a doc
# from LINKED_DOCS and still catches a parser that has gone blind.
MIN_DOC_LINKS = 100

_MD_LINK = re.compile(r'\]\(([^)\s]+\.md)(?:#[^)\s]*)?\)')
_MD_MENTION = re.compile(r'`([A-Za-z0-9_.\-/]+\.md)`')

# An inline code-span mention is resolved against the REPO ROOT, so it is only checked when
# it is unambiguously repo-root-anchored: it must start with one of these. Everything else
# is skipped ON PURPOSE, and the exclusions are not laziness --
#   * a bare `spec-deviations.md` inside docs/architecture/ could mean either directory;
#   * a `../HANDOFF.md` is relative to the CITING file, and it is usually the label of a
#     markdown link whose target _MD_LINK already resolved correctly. Resolving labels
#     against the root produced 32 false reds on a clean tree the first time this check
#     ran, which is the other way an unbelievable check dies: not silence, but noise.
# Guessing a base directory would trade real coverage for false positives; this check is
# aimed at renames of a PATH.
MENTION_ROOTS = ('docs/', 'formal/', 'tests/', 'scripts/', 'benchmarks/',
                 'index_v4/', 'setengine/', 'connectedstore/', 'legacy/')
_ROOT_ENTRY = re.compile(r'^## (\d{4}-\d\d-\d\d[a-z]?) ')
_FORMAL_ENTRY = re.compile(r'^## Session (\d{4}-\d\d-\d\d[a-z]?)\b')
_ROWS_LINE = re.compile(r'^rows:\s*(.+)$')

# Id shapes, ORDERED: the compound form must be tried before the bare one.
#   ZT-P5   R6-19   AW-1   P3   B2   R6
# The inherited pattern was ``[A-Z]{1,3}-?\d+|ZT-[A-Z0-9-]+`` and it had a live hole
# (board row ``TK46``, fixed 2026-08-24c): on ``R6-19`` it matched ``R6`` and stopped at the
# word boundary before the hyphen, so a ledger citing the INVENTED ``R6-99`` resolved to the
# real parent ``R6`` and PASSED. Every ``R6-N`` sub-item sat in that blind spot -- at the
# time, nineteen of them. Widening the extractor alone is NOT the fix and was observed
# false-redding a real id; see ``check_ledger_row_ids`` for the other half.
_ROW_ID = re.compile(r'\b(ZT-[A-Z0-9]+(?:-[A-Z0-9]+)*|[A-Z]{1,3}\d+(?:-\d+)?|[A-Z]{1,3}-\d+)\b')


def _tree_ids():
    """Every id the task tree knows -- open, closed, and retired -- or None if no tree.

    None and an EMPTY SET are different answers and the caller treats them differently:
    None means "this repo has no task tree", which is the state before the trial and a
    perfectly good one; an empty set means the tree is there and the harvester read
    nothing out of it, which is the blind-parser failure and gets a non-vacuity floor.

    Ids come from the FRONTMATTER, not the filename. ``scripts/task.py`` is emphatic that
    the id is the address and the filename is cosmetic -- it resolves by glob and then
    falls back to a full frontmatter scan for exactly this reason -- so harvesting names
    off disk would disagree with the tool the first time anyone renamed a file, and
    disagree in the direction that invents ids.
    """
    root = os.path.join(REPO, TASKS_DIR)
    if not os.path.isdir(root):
        return None
    out = set()
    for d, top in ((root, True), (os.path.join(root, 'closed'), False)):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith('.md') or (top and name in TASKS_NON_TASK_MD):
                continue
            with io.open(os.path.join(d, name), encoding='utf-8') as fh:
                for ln in fh.read().split('\n')[:20]:
                    if ln.startswith('id:'):
                        out.add(ln[3:].strip())
                        break
    retired = os.path.join(root, 'retired-ids.txt')
    if os.path.exists(retired):
        with io.open(retired, encoding='utf-8') as fh:
            for ln in fh:
                ln = ln.strip()
                if ln and not ln.startswith('#'):
                    out.add(ln)
    out.discard('')
    return out


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


def _tree_open_pris():
    """``(pri, filename)`` for every OPEN task file, or None if there is no tree.

    Same harvest as ``_tree_ids`` (frontmatter, first 20 lines) and the same None-versus-
    empty distinction: None is "no tree", an empty list is a tree the harvester read
    nothing out of, and the caller must not treat the second as a satisfied budget.
    """
    root = os.path.join(REPO, TASKS_DIR)
    if not os.path.isdir(root):
        return None
    out = []
    for name in sorted(os.listdir(root)):
        if not name.endswith('.md') or name in TASKS_NON_TASK_MD:
            continue
        with io.open(os.path.join(root, name), encoding='utf-8') as fh:
            for ln in fh.read().split('\n')[:20]:
                if ln.startswith('pri:'):
                    out.append((ln[4:].strip().upper(), name))
                    break
    return out


def check_priority_capacities(fail):
    """NOW == 1 and NEXT <= NEXT_MAX -- read from the board's table while it has one,
    and from the task tree's ``pri:`` fields once it does not.

    THE TREE FALLBACK (2026-09-06c, Phase B-prime prerequisite 2). After the cutover
    ``HANDOFF.md`` is a one-hop stub with no row table, and this check's only branch for
    "no rows" was a violation -- so the cutover commit would have had to delete the
    check, and a capacity nobody checks is no capacity (``docs/README.md`` section 4).
    The fallback is NOT a second opinion while the board has rows: pre-cutover the
    board is the ranked view and ``scripts/task.py lint`` check 5 already budgets the
    tree, so running both here would double-report every disagreement. It is the
    check's home AFTER the table is gone.
    """
    lines = _read(ROOT_BOARD)
    if lines is None:
        return
    pris = _pri_values(lines)
    if pris:
        where = ROOT_BOARD
        unit = 'rows (lines %s)'
    else:
        tree = _tree_open_pris()
        if not tree:
            fail('%s: found no board rows with a recognised pri value%s. The parser '
                 'looks for a markdown table with "id" and "pri" header cells -- if the '
                 'board was restructured, fix this check rather than deleting it.'
                 % (ROOT_BOARD, ' and there is no task tree to fall back to'
                    if tree is None else ', and %s/ has no open task files' % TASKS_DIR))
            return
        pris = tree
        where = '%s/ (the board has no row table, so the tree is the ranking)' % TASKS_DIR
        unit = 'open task files (%s)'
    now = [ln for v, ln in pris if v == 'NOW']
    nxt = [ln for v, ln in pris if v == 'NEXT']
    if len(now) != 1:
        # ONE message true of BOTH sides of the "!=", because this is one check. The old
        # text was the `> 1` branch's ("two of them is no ranking at all") printed
        # verbatim on a count of ZERO -- a FAIL describing a situation the corpus was not
        # in, read by a session at the moment it is already confused. Fixed in the sibling
        # checker 2026-08-21 (`task.py::check_pri_budget`, pinned by
        # `tests/test_tasktool.py::test_regression_zero_now_message_is_true_of_zero`) and
        # ported here 2026-09-07b -- the two checkers had disagreed about the same
        # invariant for 17 days, which is worse than either being wrong alone: whichever
        # you meet first teaches you the rule. The zero case became reachable here when
        # this check gained its tree fallback at the 2026-09-06 cutover.
        fail('%s: found %d NOW %s, must be exactly 1. NOW is the one row an '
             'unassigned session picks up: with none it has no answer, with more '
             'than one it has no ranking.'
             % (where, len(now), unit % (now or '(none)')))
    if len(nxt) > NEXT_MAX:
        fail('%s: found %d NEXT %s, cap is %d. Demote one to LATER -- the cap '
             'is the mechanism that forces the ranking argument.'
             % (where, len(nxt), unit % nxt, NEXT_MAX))


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

    THE EXTRACTOR IS THE FRAGILE HALF (board row ``TK46``, fixed 2026-08-24c). Until then
    ``_ROW_ID`` truncated ``R6-99`` to ``R6``, which IS a real id, so the comparison below
    found it and reported clean -- an invented sub-item citation passed, and every ``R6-N``
    id was in that blind spot. The 2026-08-16 sabotage that certified this check used
    ``P99``, which proves the COMPARISON works and cannot see whether the regex read the id
    being compared. Both halves are now pinned in ``tests/test_handoff_lint_row_ids.py``.

    WHY ``known`` READS THE WHOLE BOARD and not just its table rows. Widening the extractor
    alone was observed false-redding ``session-log.md:388``'s ``R6-10`` -- a real, landed
    sub-item that the board names in the ``### R6`` item block and deliberately never gives
    a table row, because sub-items are not ranked. A ledger legitimately cites them. So the
    id universe is every id shape ANYWHERE in the board; an id the board never mentions is
    still the typo/invention this check exists to catch. The non-vacuity floor stays on the
    TABLE harvest specifically, which is the part that breaks if the row parser breaks --
    put it on the whole-file harvest and a broken parser would coast on prose.

    KNOWN LIMIT, unchanged by the fix and never yet triggered: the retired line ends "the
    whole ``ZT-*`` series" rather than listing them, so a ``rows:`` line citing a specific
    ``ZT-`` id would false-red. That was equally true before; the series is closed, no
    ``rows:`` line cites one, and inventing wildcard machinery for a dormant case is how a
    check grows untested surface. Fix it when a session actually needs it.

    THE TREE IS THE ID UNIVERSE, auto-detected (added 2026-08-29, spec item A4; the sole
    authority since the 2026-09-06 cutover). ``tasks/`` holds one file per task; when it
    is present, its ids are unioned into ``known`` and it carries its own non-vacuity
    floor. Auto-detected rather than flagged because the useful behaviour is the same in
    all three states this repo passed through -- board only (before the trial), both
    (the trial fortnight), tree only (now: ``HANDOFF.md`` is a one-hop note with no
    table) -- and a flag would be a second thing to remember at exactly the moment the
    first thing changed.

    AND IF A ROW TABLE EVER REAPPEARS, ITS DISAGREEMENT WITH THE TREE IS ITSELF THE
    VIOLATION. During the trial ``CLAUDE.md``'s contract said a board row and its task
    file are updated in the SAME session; a board id with no task file was that contract
    silently broken. Post-cutover the branch is kept because it costs nothing and turns
    a re-grown table into a loud one. Checked in one direction only: every board row id
    must exist in the tree. The reverse is false BY DESIGN (the tree carries hand-filed
    tasks that were never board rows, which is most of why it exists), and a check that
    fails on correct use is a check that gets deleted.
    """
    board = _read(ROOT_BOARD)
    lines = _read(ROOT_LEDGER)
    if board is None or lines is None:
        return
    row_ids = set()
    for cells, _ in _table_rows(board):
        row_ids.add(cells[0].replace('`', '').strip())
    for ln in board:
        if 'Closed ids stay retired' in ln or 'survives as the historical grouping' in ln:
            row_ids.update(m.group(1) for m in _ROW_ID.finditer(ln.replace('`', ' ')))
    row_ids.discard('')
    tree_ids = _tree_ids()
    if len(row_ids) < 5 and tree_ids is None:
        fail('%s: parsed only %d board ids; the id parser is broken, so this check would '
             'pass by comparing against nothing. Fix it.' % (ROOT_BOARD, len(row_ids)))
        return
    known = set(row_ids)
    for ln in board:
        known.update(m.group(1) for m in _ROW_ID.finditer(ln.replace('`', ' ')))
    if tree_ids is not None:
        # WHAT THIS FLOOR ACTUALLY BUYS, measured 2026-08-29d by deleting it and probing
        # three corpora rather than by reasoning about it. While BOTH trees exist it does
        # NOT provide detection: with the floor gone and the harvester blinded, the parity
        # comparison below goes loud on its own (every board row reported as having no
        # task file). What it buys today is a precise diagnosis instead of that misleading
        # one, and an early return. The "passes by comparing against nothing" failure it
        # is named for became real AT the 2026-09-06 cutover: HANDOFF.md is a one-hop
        # note, `row_ids` is empty, and the tree is the sole id universe -- so this floor
        # is now the only thing between a blind harvester and a vacuous pass. It went in
        # 2026-08-29 rather than being remembered at the cutover. Recorded here because
        # the first version of this comment claimed the detection outright and a sabotage
        # pass showed it was silent.
        if len(tree_ids) < 5:
            fail('%s: harvested only %d ids from the task tree; the harvester is broken. '
                 'While the board still carries rows this is a diagnosis rather than the '
                 'only alarm (the parity check below would also go loud); once the board '
                 'is a stub it is the only thing standing between a blind harvester and a '
                 'check that passes by comparing against nothing. Fix it -- do not delete '
                 'the tree branch.' % (TASKS_DIR, len(tree_ids)))
            return
        # Filtered through ``_ROW_ID`` before comparing, and the filter is not cosmetic:
        # ``_table_rows`` yields the header row and the ``|---|---|`` separator too, so
        # the raw harvest carries ``'id'`` and ``'---'``. Those were harmless while this
        # set only fed the non-vacuity floor -- observed the moment it fed a comparison,
        # as ``HANDOFF.md names '---', 'id', which tasks has no task file for``. Anything
        # that is not id-SHAPED is not a row id and cannot be missing from anywhere.
        missing = sorted(i for i in row_ids
                         if _ROW_ID.match(i) and _ROW_ID.match(i).group(1) == i
                         and i not in tree_ids)
        if missing:
            fail('%s names %s, which %s has no task file for. Since the 2026-09-06 '
                 'cutover the tree is the sole authority and %s carries no row table at '
                 'all; a row that names an id with no task file is a citation to nothing. '
                 'File it (`python scripts/task.py new ... --id <ID>`) or remove the row.'
                 % (ROOT_BOARD, ', '.join(repr(m) for m in missing), TASKS_DIR, ROOT_BOARD))
        known.update(tree_ids)
    for i, ln in enumerate(lines, 1):
        m = _ROWS_LINE.match(ln.strip())
        if not m:
            continue
        for cited in _ROW_ID.finditer(m.group(1)):
            if cited.group(1) not in known:
                fail('%s:%d cites board id %r, which appears nowhere in %s -- not as a row, '
                     'not on the retired-ids line, not in an item block%s. Ids are never '
                     'reused, so a citation that resolves to nothing is a typo or an '
                     'invented id.'
                     % (ROOT_LEDGER, i, cited.group(1), ROOT_BOARD,
                        '' if tree_ids is None
                        else ' -- and no task file in %s carries it either' % TASKS_DIR))


def check_doc_links(fail):
    """Every doc-to-doc `.md` pointer in a LIVING root resolves to a file on disk.

    THE HAZARD THIS CLOSES. ``verify.sh`` step 4d resolves ``file::symbol`` anchors in
    ``formal/CORRESPONDENCE.md`` -- and nothing else in this repo resolves anything. It has
    never looked at a markdown link, so until 2026-08-20 a doc could be renamed or split
    and every inbound pointer would rot silently, at full green. Board row ``HS-2`` (the
    ``docs/spec-deviations.md`` split) is exactly that commit shape, which is why the check
    ships with it rather than after it.

    Two pointer forms, deliberately different resolution rules:

    * a markdown link ``](target.md)`` resolves relative to the CITING file's directory,
      because that is how a reader's click resolves it;
    * an inline code-span mention resolves against the repo root, and only when it carries
      a ``/`` so it is unambiguously a path. A bare ``spec-deviations.md`` in
      ``docs/architecture/`` could mean either directory; guessing would produce false
      reds, and this check is aimed at RENAMES, not at prose style.

    SABOTAGE (docs/sabotage-procedure.md), 2026-08-20. The weakening broken was the
    narrowest PLAUSIBLE one -- the singular/plural typo a rename commit actually makes, not
    a deleted file: ``HANDOFF.md``'s ``LT-1`` row was repointed at ``docs/latent-gap.md``
    while the file on disk is ``docs/latent-gaps.md``. Literal observed output::

        handoff_lint: 1 violation(s)

          FAIL: HANDOFF.md:63 links to 'docs/latent-gap.md', which does not exist
          (resolved to docs/latent-gap.md). A doc-to-doc pointer is checked by NOTHING
          else in this repo -- verify.sh step 4d resolves file::symbol anchors in
          CORRESPONDENCE.md only. Fix the link or restore the file.

    Restored, and the clean run reports ``handoff_lint: clean (10 checks)``.

    THE INSTRUMENT WAS CONTROLLED TOO, which is the step this repo's record says gets
    skipped. Three controls:

    * ``MIN_DOC_LINKS`` asserts the parser found links AT ALL. A link checker that matches
      nothing passes forever -- the exact fail-by-passing shape ``check_frozen_banners``
      was caught in. Verified by raising the floor to 500 against the real tree::

          FAIL: check_doc_links parsed only 220 .md pointers across 8 file(s), floor 500.

      Restored to 100. So the check is demonstrably reading 220 pointers, not zero.
    * the baseline was checked BEFORE the sabotage: a clean tree yields zero violations
      from this check, so the red above is attributable to the typo and not to pre-existing
      rot. And the failure line names ``docs/latent-gap.md`` specifically -- a check that
      merely re-reported some other broken link would have proved nothing.
    * **the first version was too eager and its 32 false reds are why MENTION_ROOTS
      exists.** ``_MD_MENTION`` matched the code-span LABEL of every link written
      ``[`../HANDOFF.md`](../HANDOFF.md)`` and resolved it against the repo root, so a
      clean tree reported 32 violations -- every one of them a link that resolves fine
      when clicked. A check nobody can get green is as dead as a check that never fires;
      that failure mode is recorded here because the eager regex is the obvious way to
      write this and it looks right.
    """
    parsed = 0
    seen_files = 0
    for rel in LINKED_DOCS:
        lines = _read(rel)
        if lines is None:
            fail('MISSING: %s is in LINKED_DOCS but does not exist. Remove it from the '
                 'list deliberately -- a link check over a file that is gone guards '
                 'nothing.' % rel)
            continue
        seen_files += 1
        base = os.path.dirname(rel)
        for i, ln in enumerate(lines, 1):
            targets = [(m.group(1), base) for m in _MD_LINK.finditer(ln)]
            targets += [(m.group(1), '') for m in _MD_MENTION.finditer(ln)
                        if m.group(1).startswith(MENTION_ROOTS)]
            for target, anchor_dir in targets:
                if target.startswith(('http:', 'https:', 'mailto:', '/')):
                    continue
                parsed += 1
                resolved = os.path.normpath(os.path.join(anchor_dir, target))
                if not os.path.exists(os.path.join(REPO, resolved)):
                    fail("%s:%d links to %r, which does not exist (resolved to %s). A "
                         "doc-to-doc pointer is checked by NOTHING else in this repo -- "
                         "verify.sh step 4d resolves file::symbol anchors in "
                         "CORRESPONDENCE.md only. Fix the link or restore the file."
                         % (rel, i, target, resolved.replace(os.sep, '/')))
    if parsed < MIN_DOC_LINKS:
        fail('check_doc_links parsed only %d .md pointers across %d file(s), floor %d. The '
             'link parser is broken or LINKED_DOCS has been gutted, so this check would '
             'pass by resolving nothing. Fix it rather than lowering the floor.'
             % (parsed, seen_files, MIN_DOC_LINKS))


# --- Session receipt (check_session_receipt, added 2026-09-06c, Phase B-prime prereq 7) ---
# The two literal lines CLAUDE.md demands of every session-log entry (born as the trial's
# receipts, kept at the 2026-09-06 cutover): the `task lint` output, and an honest
# self-report of what was read to start work. The read vocabulary changed AT the cutover
# -- there is no HANDOFF row table to read "in full" any more, so `board + HANDOFF` /
# `HANDOFF only` gave way to `board + note` (the query, then the one-hop note). Entries
# older than the cutover keep the old words; only the newest entry is checked.
# Both regexes SEARCH the line after normalisation rather than anchoring, because the C1
# tally (docs/tasktool-trial-protocol.md section 6, 2026-09-06) found four shapes in the
# ledger and none of them wrong: a bare line, a backticked one, `lint: <backticked>`, and
# `` `python scripts/task.py lint` -> <backticked> ``. A check that rejected three of the
# four would have been commented out by the second session it bit.
READ_VOCAB = ('board only', 'board + note')
_LINT_RECEIPT = re.compile(
    r'task lint: (?:clean \(\d+ checks?, \d+ task file\(s\) parsed(?:, \d+ warning\(s\))?\)'
    r'|\d+ violation\(s\))')
_READ_RECEIPT = re.compile(r'(?:^|\W)read: (%s)(?:\W|$)'
                           % '|'.join(re.escape(v) for v in READ_VOCAB))


def _newest_entry_lines(rel, pattern):
    """The lines of the FIRST entry (the ledger is newest-first), or None if no file."""
    lines = _read(rel)
    if lines is None:
        return None
    start = None
    for i, ln in enumerate(lines):
        if pattern.match(ln):
            if start is None:
                start = i
                continue
            return lines[start:i]
    return lines[start:] if start is not None else []


def check_session_receipt(fail):
    """The newest root-ledger entry carries both receipts: a `task lint:` result line
    and a `read: <vocab>` line.

    Why it is mechanical rather than a rule in CLAUDE.md: the rule IS in CLAUDE.md, and
    the C1 tally (trial week two) found 2 of 35 entries with neither line and one with
    the lint line only. Two lines nobody checks decay into one. Post-cutover the lint
    line is the proof the tree was linted before the commit (there is no board to
    cross-check it against any more), and the read line keeps recording whether the
    query was enough or the note was needed too. Only the NEWEST entry is checked: older
    entries are history, and a check that demanded retroactive edits to an append-only
    ledger would be ignored.
    """
    entry = _newest_entry_lines(ROOT_LEDGER, _ROOT_ENTRY)
    if entry is None:
        fail('MISSING: %s' % ROOT_LEDGER)
        return
    if not entry:
        fail('%s: no `## <session-key> ` entry found, so there is nothing to check the '
             'session receipts on -- the entry regex or the ledger is broken.'
             % ROOT_LEDGER)
        return
    head = entry[0].strip()
    norm = [ln.strip().replace('`', '').replace('**', '') for ln in entry]
    if not any(_LINT_RECEIPT.search(ln) for ln in norm):
        fail('%s: the newest entry (%s) has no `task lint: clean (N checks, M task '
             'file(s) parsed)` / `task lint: N violation(s)` line. Paste the literal '
             'output of `python scripts/task.py lint` -- it is the proof the tree was '
             'linted before the commit (CLAUDE.md, the receipt rule).'
             % (ROOT_LEDGER, head[:80]))
    if not any(_READ_RECEIPT.search(ln) for ln in norm):
        fail('%s: the newest entry (%s) has no `read: %s` line. It is the honest '
             'self-report of what was actually read to start work: whether the board '
             'query was enough, or the one-hop note was needed as well.'
             % (ROOT_LEDGER, head[:80], ' | '.join(READ_VOCAB)))


# --- Restated corpus counts (check_restated_counts, added 2026-09-08, task ``TK58``) -----
# The scan scope. Two DECLARED files plus two GLOBS, which is the archived design's "a
# declared list AND a walk" split (docs/history/tasktool-scratch-archive-2026-09-07.md
# section 6): the declared half fails loudly if a file it names is deleted, the glob half
# picks up a doc nobody remembered to register. ``docs/`` is TOP LEVEL only -- the same
# scope the 2026-09-08 census measured -- because docs/history/ is provenance by its path
# and docs/specs/ + docs/architecture/ were never censused, and a scope widened without a
# census is how a check arrives red on lines nobody has read.
COUNT_DECLARED = ('CLAUDE.md', 'HANDOFF.md')
COUNT_GLOB_DIRS = ('docs', TASKS_DIR)

# Floor on files actually SCANNED, i.e. walked AND not exempt. One number guards both ways
# the walk can go quietly blind: a glob that stops matching, and an exemption predicate
# that widens until it swallows the corpus. Measured 79 walked / 75 scanned on 2026-09-08;
# 40 survives closing half the open tasks (they move to tasks/closed/, out of scope) and
# still catches either failure. Same loose-instrument-control idiom as MIN_DOC_LINKS.
MIN_COUNT_SCANNED = 40

# A number: a numeral run, or a spelled-out number from THREE upward. "one" and "two" are
# deliberately absent -- at those magnitudes the prose is narrative ("one test", "two
# checks" meaning a specific pair) far more often than it is a census, and the census
# forms this guards are bigger than two. Measured: including them added noise and no hits.
# The lookbehind keeps a number from starting mid-token: without it "6 row" matched inside
# ``R6-6`` and "00 row" inside ``1.00 row/edge`` (both observed in the 2026-09-08 census).
_COUNT_WORDS = ('three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|'
                'fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty')
_COUNT_NUM = r'(?<![\w.,\-])(?:\d[\d,]*|%s)' % _COUNT_WORDS

# THREE patterns, not the archived design's six, and the list grows only when a real rot is
# found -- the commit that adds a fourth must say which rot motivated it. Each carries the
# HOME the figure actually lives in, because "delete the number" is only actionable next to
# "and here is where to read it". The noun follows the number IMMEDIATELY: an intervening
# prose word turns a census ("6 tests") into a description of a subset ("six isinstance
# tests", "44 KB test suite"), which is not this defect. A quoted qualifier stays
# transparent because _COUNT_QUOTED blanks it to spaces, so "the eight `GS-2` tests" is
# still caught.
_COUNT_PATTERNS = (
    ('checks', re.compile(r'%s\s+checks?\b' % _COUNT_NUM, re.I),
     'the tool prints its own check count (`handoff_lint.py`, `task.py lint`)'),
    ('open tasks/rows', re.compile(
        r'%s\s+(?:open\s+(?:tasks?|rows?|items?)|task\s+files?)\b' % _COUNT_NUM, re.I),
     '`python scripts/task.py counts`'),
    ('tests', re.compile(r'%s\s+tests?\b' % _COUNT_NUM, re.I),
     "`formal/FINAL_REVIEW.md`'s generated counts block (verify.sh step 4e)"),
)

# The escape vocabulary. Every one is STRUCTURAL -- a property of the text or of the file's
# own declared contract -- so there is no baseline file to keep, and therefore nothing for a
# scan to regenerate. The archived design's sharpest point was that a guard which rewrites
# its own expectations cannot fail; the cheapest way to honour it is to have no baseline.
#
#   fence     a fenced block is EVIDENCE (a transcript, a run's output), not a claim.
#   quoted    a backticked or double-quoted number is a QUOTATION -- the wrong figure a
#             correction is repealing, or a literal a test asserts. CLAUDE.md's "★ No
#             figures here" bullet is exactly this shape and must stay writable.
#   dated     a line carrying a YYYY-MM-DD[letter] key is a stamped observation, true as
#             of that day. This is the repo's own convention for a measured number.
#   banner    the file declares its body is provenance: FROZEN, ACTIVE-PLAN, or the
#             append-only form of LIVING (docs/README.md sections 2-3).
#   log       a task file's `## Log` is append-only and dated per entry. Its FRONTMATTER,
#             summary, Traps and Read-first stay in scope -- those are present-tense.
#
# ⚠ AMENDMENT 1 of the 2026-09-08 census killed the obvious version of `dated`: a per-LINE
# date test sees nothing in docs/spec-deviations.md, whose 3511 lines carry their date on
# the `## <date>` HEADING and not on the body line. That file contributes the single
# largest block of legitimate hits in the repo, so the exemption had to key on the FILE's
# liveness banner instead. `banner` and `log` are both that fix.
_COUNT_QUOTED = re.compile(u'`[^`]*`|"[^"]*"|“[^”]*”')
_COUNT_DATED = re.compile(r'\b\d{4}-\d\d-\d\d[a-z]?\b')
_COUNT_APPEND_ONLY = re.compile(r'\*\*LIVING\b[^\n*]*append-only', re.I)


def _count_scan_files():
    """(rel, lines) for every file in scope, in a stable order."""
    out = []
    for rel in COUNT_DECLARED:
        out.append(rel)
    for d in COUNT_GLOB_DIRS:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if not name.endswith('.md'):
                continue
            if d == TASKS_DIR and name in TASKS_NON_TASK_MD:
                continue
            out.append('%s/%s' % (d, name))
    return out


def _count_exempt(lines):
    """The file-level provenance banner that exempts this file, or None."""
    head = '\n'.join(lines[:LIVENESS_WINDOW])
    if _FROZEN_DECL.search(head):
        return 'FROZEN'
    if _COUNT_APPEND_ONLY.search(head):
        return 'LIVING/append-only'
    if re.search(r'\*\*ACTIVE-PLAN\b', head):
        return 'ACTIVE-PLAN'
    return None


def check_restated_counts(fail):
    """No live doc restates a corpus count -- checks, open tasks, tests -- in prose.

    THE DEFECT. ``ZT-P3-5`` is this repo's most-recurring documentation failure: a figure
    copied out of its machine-checked home into a sentence, where nothing can ever
    re-derive it. docs/README.md section 1 already forbids it in words ("Do not restate a
    count in prose anywhere -- a quoted count is not merely stale, it is unenforced"), and
    the rule had no enforcement of any kind, which is why the count of things it has
    rotted keeps growing. A ``count_guard.py`` was designed for the gitignored
    ``.scratch/tasktool/`` corpus and never graduated; it was deleted with that directory
    on 2026-09-07 (task ``TK58``). This is the port, scoped down from six patterns to
    three and re-keyed onto the tracked tree's own liveness conventions.

    WHAT IT REFUSES is a CENSUS -- ``N checks``, ``N open tasks``, ``N tests`` -- not an
    enumeration. "two pin the pinned-snapshot path, one pins torn state" carries its own
    evidence in the same sentence and is verifiable by reading it; "Three tests in the
    shared HA modules" is a number whose home is a knob in ``formal/verify.sh``. The
    remedy is always the same one the 2026-09-08 fix used: **delete the number and point
    at its home**, never update it in place. An updated number is the same unenforced
    claim, one day younger.

    THE RETROSPECTIVE CONTROL, which is stronger than an invented sabotage and is why this
    check was believed. Two figures in ``docs/gate-runbook.md`` were found wrong BY HAND on
    2026-09-08 -- a "Three checks now run inside the `lean` phase" that seven do, and a
    handoff_lint check count that was stale the day the eleventh check landed. Both were
    fixed before this check existed. Run against the parent commit (``966f6aa``), these
    patterns report::

         81 tests   Three tests    | ... Three tests in the shared HA
        197 tests   6 tests        | ... `test_conformance_enum.py` - 6 tests,
        201 tests   6 tests        | ... interleaves those 6 tests across the **five** tiles
        285 checks  Three checks   | Three checks now run inside the `lean` phase ...
        365 checks  Ten checks     | scripts/handoff_lint.py`. Ten checks over the two board files ...
        566 tests   eight        t | ... Pinned by the eight `GS-2` tests in

    i.e. it catches BOTH lines a human had to find by reading, plus four more the same
    human walked past. That is the check firing on real, independently-confirmed rot from
    before it was written, not on a hole dug for it.

    SABOTAGE (docs/sabotage-procedure.md), 2026-09-08, the narrowest PLAUSIBLE weakening --
    a session appending one true-today sentence to the banner, which is exactly how every
    figure this check exists for was born. Literal observed output in the module docstring
    above. The instrument was controlled too: the clean tree is green in the same run, and
    the sabotage line names ``HANDOFF.md`` specifically.

    RED ON ARRIVAL WAS THE RISK AND IT WAS MEASURED FIRST. The census on ``TK58``
    (2026-09-08) found 87 raw hits under a wider pattern set; this narrowed set plus the
    escapes left **6**, every one a real restated test count, all six fixed in the landing
    commit. A check that arrives red on dozens of legitimate lines is a check someone
    deletes, so the corpus was swept before the check was wired in.

    THE MECHANISM IS PINNED BY ``tests/test_handoff_lint_count_guard.py``, not by this
    docstring: which escape suppresses what, the token each pattern extracts, and the two
    directions the walk can go blind. Read it before editing anything here -- it carries a
    ten-mutation sweep in which the obvious widening of the ``checks`` pattern broke this
    check while every test still passed, and the test that now closes that hole says so.
    """
    scanned = 0
    for rel in _count_scan_files():
        lines = _read(rel)
        if lines is None:
            fail('MISSING: %s is scanned by check_restated_counts but does not exist. '
                 'Remove it from COUNT_DECLARED deliberately -- a count guard over a file '
                 'that is gone guards nothing.' % rel)
            continue
        if _count_exempt(lines) is not None:
            continue
        scanned += 1
        is_task = rel.startswith(TASKS_DIR + '/')
        fence = False
        for i, ln in enumerate(lines, 1):
            if ln.lstrip().startswith('```'):
                fence = not fence
                continue
            if is_task and ln.startswith('## Log'):
                break
            if fence or _COUNT_DATED.search(ln):
                continue
            bare = _COUNT_QUOTED.sub(lambda m: ' ' * len(m.group(0)), ln)
            for label, pat, home in _COUNT_PATTERNS:
                m = pat.search(bare)
                if not m:
                    continue
                fail('%s:%d restates a %s count in prose (%r). A quoted count is not '
                     'merely stale, it is UNENFORCED -- docs/README.md section 1, and '
                     'ZT-P3-5 is this repo\'s most-recurring doc defect. DELETE the '
                     'number and point at its home (%s); do not update it in place. If '
                     'the line is a stamped observation, give it a YYYY-MM-DD key; if it '
                     'quotes a figure it is repealing, put the quoted text in backticks.'
                     % (rel, i, label, m.group(0).strip(), home))
    if scanned < MIN_COUNT_SCANNED:
        fail('check_restated_counts scanned only %d file(s), floor %d. Either the globs '
             'have gone blind or the banner exemption has widened until it swallows the '
             'corpus -- both make this check pass by reading nothing. Fix the walk, not '
             'the floor.' % (scanned, MIN_COUNT_SCANNED))


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
    check_doc_links,
    # Appended (2026-09-06c). The task.py lint checks are cited by number and appended for
    # that reason; these are not numbered, but the same habit costs nothing.
    check_session_receipt,
    # Appended 2026-09-08 (task ``TK58``).
    check_restated_counts,
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
