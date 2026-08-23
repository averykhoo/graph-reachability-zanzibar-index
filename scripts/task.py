#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""task.py -- a file-per-task tracker whose board is a QUERY, never a file.

Run it from anywhere inside a tree that contains ``tasks/config.json``::

    python task.py board                  # the ~25-line session-start view
    python task.py list --pri NEXT
    python task.py show P3
    python task.py ready
    python task.py lint                   # exit 1 on any violation
    python task.py counts                 # measure the corpus (see NO RESTATED COUNTS)

Exit codes: 0 = fine, 1 = lint found violations, 2 = the operation was REFUSED
(bad arguments, unknown id, budget violation, dependency cycle) or a file it
needs is missing. A refusal always names the offending rows and says what to
pass instead; a tool that only says "no" trains people to work around it.

WHY THIS EXISTS
---------------
This repo tracks work in ``HANDOFF.md``, which is simultaneously the *database*
and the *session-start read*. That coupling caps the database at whatever a cold
session can afford to read -- today a hard 260-line ceiling enforced by
``scripts/handoff_lint.py::check_ceilings``. The observable consequences are all
in the repo's own record: items dropped "for space", completed work still marked
open because nobody wanted to spend board lines on a disposition, and task groups
that never migrated to an archive.

The fix is to decouple the two:

* the DATABASE is ``tasks/*.md``, one file per task, unbounded, nothing ever
  dropped and nothing ever deleted;
* the SESSION VIEW is the *output* of ``task.py board`` -- about 25 lines,
  printed and never committed, at constant context cost no matter how large the
  backlog grows.

A committed ``BOARD.md`` would re-create the disease within a month, so there
isn't one. The board is a query, always. Same reasoning as the repo's rule that
live gate counts live in exactly one machine-checked place: a second copy of a
fact is a copy that rots.

THE HONEST LIMITS OF THIS THING
-------------------------------
* It does not know whether a task is TRUE, useful, current, or correctly ranked.
  ``lint`` converts *silently violated* into *loudly must-look* and nothing more.
  It cannot tell you that the ``NOW`` row is the right ``NOW``, that a pointer in
  ``## Read first`` resolves to something actionable, or that a ``moved`` key is
  not simply a lie typed by a session that did no work.
* Staleness is a heuristic on ``moved``, i.e. on a field the tool itself stamps.
  Any write op refreshes it, so ``touch`` can launder a stale item indefinitely.
  That is a known and accepted hole: the field is a prompt, not evidence.
* Writes are not transactional. ``promote --demote`` renders and validates both
  files before writing either, which closes the realistic failure (a refusal
  landing half a swap) but not a crash between the two ``write()`` calls. There
  is no lock: two concurrent runs can both allocate the same id. Single-session
  tooling, deliberately.
* ``lint`` reads only the ``tasks/`` tree. It has no idea what the main repo's
  documents say, so it cannot catch a task that contradicts ``HANDOFF.md``.

WHAT IS DELIBERATELY ABSENT, each one a headstone in the distributed
bug-tracker graveyard: ``edit`` (that is your editor), ``search`` (that is
grep), assignees, due dates, time tracking, kanban rendering, a web UI, an MCP
server. "Wontfix" is a ``close`` with the reason in the required message.

WHY THE FRONTMATTER PARSER IS HAND-WRITTEN (and must stay that way)
------------------------------------------------------------------
A real YAML library reorders keys, rewrites quote styles, and coerces
``2026-08-20`` into a ``datetime.date`` -- which then round-trips back as
``2026-08-20 00:00:00`` and, worse, cannot represent the session-key form
``2026-08-20b`` at all. The result is diff churn on every write and format drift
across sessions. Thirty lines of hand-parsing over a deliberately constrained
subset (section 3.2 of SPEC.md) buys byte-stable round-trips and zero
dependencies, and the files stay valid YAML for any other reader that wants
them. Do not "upgrade" this to PyYAML.

The THIRTEEN keys are ALWAYS present, in a fixed order, with ``[]`` for an empty
list and a bare ``key:`` for an empty scalar. Always-present plus fixed-order is
what makes the parser trivial and the diffs readable; an optional key means every
reader needs a default and the defaults drift apart.

Ten of those keys until 2026-08-21, when ``updated``, ``source`` and ``related``
were added and every existing file was rewritten in place by
``migrate_schema13.py`` (bodies byte-identical, verified per file, both
directions). The three exist for reasons the ten could not cover:

* ``updated`` bumps on EVERY write while ``moved`` bumps only on PROGRESS, so an
  automated housekeeping pass cannot launder a neglected row into a fresh-looking
  one. See PROGRESS_OPS below for the per-op rule, which is mechanical: the op --
  or the calling tool's ``--mechanical`` -- decides, never a judgement about
  whether an edit felt substantial.
* ``source`` records where the task came from (``board`` / ``hand`` / a
  repo-relative path), set once at ``new`` and immutable after. It REPLACES the
  ``sync-state.json`` SYNC-SPEC.md section 3 used to propose: provenance inside
  the file travels with it through the archive move and cannot desync from the
  corpus, and there is no second state file to go missing and silently degrade
  every task to "hand-filed, expected".
* ``related`` is an unordered, NON-SEMANTIC navigation list. Deliberately untyped
  -- no supersedes / duplicate-of / see-also -- because ``deps`` and ``parent``
  earn their complexity by being READ BY QUERIES (``ready``, the archive sweep),
  while a typed relation carries no query semantics and does create a decision
  point where a model picks the wrong type invisibly. Prose in the body says it
  better and is already there.

NO RESTATED COUNTS, AND NO EXAMPLE VALUES IN A SHIPPED CONFIG
------------------------------------------------------------
Two rules, one cause, both learned here the expensive way.

This docstring used to state a task-file count, and it was wrong about the live tree
within days [dated: 2026-08-21]. That is
``ZT-P3-5`` -- the repo's own name for a restated figure going stale -- recurring
inside the tool built to cure it, so the number is gone rather than corrected:
``task.py counts`` measures the corpus, and it is the ONE place any surface should
get that figure from. Where a count appears below it is quoted OBSERVED OUTPUT
from a command the test suite re-runs, which is a different kind of claim.

And ``tasks/config.json`` shipped with three values copied verbatim out of
SPEC.md section 6's EXAMPLE block: ``id_prefix: "T"`` (whose first minted id,
``T1``, is already the set-engine correctness theorem -- 162 first-party
occurrences), ``min_tasks_parsed: 5`` [dated: 2026-08-21] (a control with most of
the corpus as headroom -- see ``check_min_parsed``, and run ``task.py counts``
for the live figure), and ``stale_days: 14`` (no
derivation anywhere). An example is a shape, not a value. So: every tuned knob
carries its provenance in the config's ``_provenance`` block -- JSON has no
comments and keys starting with ``_`` are ignored by the loader -- saying how the
number was MEASURED and what would make it wrong; the two knobs with no honest
default (``id_prefix``, ``min_tasks_parsed``) have none, and are a refusal and a
lint violation respectively rather than a silent guess. ``measure_prefix.py`` and
``measure_stale.py`` re-derive the measurements.

THE ONE DELIBERATE REDUNDANCY is ``closed``: the FOLDER answers *whether* a task
is closed, the FIELD answers *when*. ``check_closed_field`` asserts they agree.
Everywhere else one fact has exactly one home -- which is why there is no
``status`` field, no H1 duplicating the frontmatter title, and no ``blocks``
field. The reverse of ``deps`` is DERIVED (see ``op_show``); a hand-maintained
inverse edge is precisely the rot machine this design exists to delete.

SABOTAGE RECORD (per docs/sabotage-procedure.md)
------------------------------------------------
RUN 2026-08-21c. Reproduce with ``python test_task.py --sabotage``; the full log,
including the per-case baseline lines, is written to ``sabotage-log.txt``. Every
line quoted below is regenerated by that command, so a figure inside one is
OBSERVED OUTPUT rather than a restated fact -- and the only place this file quotes
a live corpus size from is ``task.py counts``, which measures it.

Method, per the procedure: each of the ten checks had the property it guards
broken by the narrowest *plausible* weakening -- the edit a real session makes by
hand between two runs of the tool -- and the failure had to both go red AND name
the sabotaged subject, so the red is attributable to that check rather than to
collateral damage. Every case is bracketed by an instrument control: the same tree
lints clean immediately before the sabotage and again after the restore.

TWO CORPORA, because a record is evidence about a corpus and this tool ships
against a tree fourteen times the size of its fixture:

* ``<t>/`` elides ``.../testtmp/sab/``, the seven-file FIXTURE, baseline
  ``task lint: clean (10 checks, 7 task file(s) parsed)``;
* ``<m>/`` elides ``.../testtmp/live/``, a throwaway COPY of the live migrated
  tree, baseline ``task lint: clean (10 checks, 99 task file(s) parsed)``. The
  original is never edited, and a MISSING live corpus fails the run instead of
  skipping it.

Nothing else is edited in either.

    check_parses         delete the empty ``parent:`` line from T2 while
                         hand-tidying the frontmatter
      FAIL: <t>/tasks/T2-next-alpha.md: missing keys ['parent'], unknown keys -
      (all fourteen keys are always present -- see SPEC.md section 3.1). Fix the
      frontmatter by hand -- the fourteen keys are fixed and always present (SPEC.md
      section 3.1).

    check_ids_unique     archive T5 by COPYING it into closed/ rather than moving
      FAIL: id 'T5' is used by BOTH <t>/tasks/T5-held-delta.md and
      <t>/tasks/closed/T5-held-delta.md. Ids are addresses and are never reused;
      give one of them a fresh id from `task.py new`.

    check_filenames      hand-rename T3-next-beta.md -> T3next-beta.md (a slug
                         typo that drops the id separator)
      FAIL: <t>/tasks/T3next-beta.md does not start with 'T3-'. The filename is
      cosmetic, but a filename that disagrees with the id makes `ls` lie; rename
      the file (the id stays put).

    check_enums          moved: 2026-08-21 -> 2026-8-21 (a hand-typed date that
                         loses its zero padding -- still obviously a date to a
                         human, and unsortable to string comparison)
      FAIL: <t>/tasks/T4-later-gamma.md: moved is '2026-8-21', not a session key
      (YYYY-MM-DD with an optional single lowercase letter).

    check_enums          the RELAXATION pair, sabotaged from BOTH SIDES, on the
      (a) open row       FIXTURE and again on the LIVE corpus. Added 2026-08-21b
                         when the check was relaxed to accept an empty pri/size
                         under ``closed/``; RE-DONE 2026-08-21c because the first
                         version was the one case in this record that could not be
                         reproduced -- it cited a copy at ``audit/sb-pri`` (no such
                         directory), a baseline of 83 files (the tree is bigger),
                         and ``--sabotage`` did not run it. Both sides now run in
                         ``--sabotage`` as ``check_enums(open)``/``(closed)`` on the
                         fixture and as ``enums(open,live)``/``(closed,live)`` on a
                         COPY of the live tree, so this text cannot rot again
                         without a red. (a) blank BOTH fields on an OPEN row -- the
                         closed/ exemption must not leak out:
      FAIL: <m>/tasks/P10-re-run-the-scope-audit-hand-curated.md: pri '' is not one
      of ['NOW', 'NEXT', 'LATER', 'HOLD', 'SOMEDAY'] (it may be empty only under
      closed/).
      FAIL: <m>/tasks/P10-re-run-the-scope-audit-hand-curated.md: size '' is not one
      of ['S', 'M', 'L', '?'] (use "?" when unsized, or empty under closed/).
    check_enums          (b) a NON-empty but bogus ``pri: URGENT`` on a CLOSED
      (b) closed row     record -- "optional" must not degrade into "unchecked".
                         The row is closed THROUGH the tool first, so the only hand
                         edit is the bogus value and the red is attributable to it:
      FAIL: <m>/tasks/closed/B1-w3cjobvalid-enumjob2d-star-freeness-hole-closed.md:
      pri 'URGENT' is not one of ['NOW', 'NEXT', 'LATER', 'HOLD', 'SOMEDAY'].
      (both cases exit 1 against the live baseline printed above; the copy lints
      clean again the moment it is rebuilt, which the pass asserts.)

    check_pri_budget     hand-edit a second row to ``pri: NOW``, which is exactly
                         what someone does after `promote` refuses them
      FAIL: found 2 open NOW row(s) (T1, T4), must be exactly 1. NOW is the one
      row an unassigned session picks up: with none it has no answer, with more
      than one it has no ranking. Set the count with `task.py promote <id> NOW
      --demote <id2> <pri2>`.

    check_pri_budget     fill NEXT to the cap legally THROUGH the tool (green at
      (NEXT cap)         3), then hand-edit a fourth row to ``pri: NEXT``
      FAIL: found 4 open NEXT row(s) ['T2', 'T3', 'T4', 'T5'], cap is 3. Demote
      one to LATER -- the cap is the mechanism that forces the ranking argument
      to happen once, at write time.

    check_deps           a dep id typo: T2 -> T20
      FAIL: <t>/tasks/T3-next-beta.md: dep 'T20' resolves to no task (open or
      closed). If it is retired, drop it with `task.py dep rm T3 T20`; a dep that
      resolves to nothing blocks forever.

    check_deps (cycle)   hand-add ``deps: [T3]`` to T2, closing the T2<->T3 loop
                         that `dep add` refuses
      FAIL: <t>/tasks/T2-next-alpha.md: dependency cycle T2 -> T3 -> T2. Nothing
      in the cycle can ever be ready.

    check_parents        archive parent T6 into closed/ while child T4 is still
                         open (the sloppy end of an archive sweep)
      FAIL: <t>/tasks/closed/T6-the-group.md is CLOSED but still has open
      children ['T4']. Either reopen it or close the children -- a closed parent
      is what tells the next session the group is done.

    check_closed_field   ``mv`` a finished task into closed/ without stamping the
                         ``closed`` field
      FAIL: <t>/tasks/closed/T7-someday-eps.md is under closed/ but its `closed`
      field is empty. Re-close it with `task.py close T7 -m ...` so the date is
      recorded.

    check_labels         a label case slip: infra -> Infra
      FAIL: <t>/tasks/T1-the-now-row.md: label 'Infra' is not in the declared
      vocabulary ['formal', 'perf', 'docs', 'infra']. Add it to tasks/config.json
      deliberately, or use an existing one.

    check_min_parsed     the corpus shrinks below the declared floor (7 -> 4)
      FAIL: parsed only 4 task file(s), floor min_tasks_parsed=7. Either the
      tasks directory is nearly empty or the parser has gone blind -- and a lint
      that parses nothing passes forever. Fix the parser rather than lowering the
      floor.

    check_min_parsed     THE FLOOR ON THE LIVE CORPUS, and the case that found the
      (live, rm closed/) worst defect in this record. ``rm -rf tasks/closed``
                         deletes 57 of 99 files -- the MAJORITY of the corpus.
                         BEFORE the fix, with ``min_tasks_parsed`` at SPEC.md
                         section 6's EXAMPLE value of 5 (i.e. 94 files of
                         headroom), the observed result was:
      task lint: clean (10 checks, 42 task file(s) parsed)   [exit 0]
                         The check whose entire purpose is noticing a blind
                         parser did not notice losing the majority of the corpus.
                         With the floor set to the measured 99 with ZERO headroom
                         (the way verify.sh sets MIN_CONF_ALL / MIN_TESTS_ALL):
      FAIL: parsed only 42 task file(s), floor min_tasks_parsed=99. Either the
      tasks directory is nearly empty or the parser has gone blind -- and a lint
      that parses nothing passes forever. Fix the parser rather than lowering the
      floor.

    check_min_parsed     THE INSTRUMENT'S OWN CONTROL, and the one that matters:
      (blind parser)     a BLIND PARSER. ``Store.md_paths`` is patched (in a copy
                         of this file, so the original is never edited) to stop
                         scanning ``closed/`` -- the plausible "lint only cares
                         about open tasks" refactor. Run on BOTH corpora. The
                         other checks all stay GREEN on the half they can
                         still see; check 10 fires TWICE, and the second line is
                         why the fix is not just a bigger number -- the floor says
                         the corpus shrank, the recount says WHICH half went dark
                         and is true at every future corpus size:
      FAIL: parsed only 42 task file(s), floor min_tasks_parsed=99. Either the
      tasks directory is nearly empty or the parser has gone blind -- and a lint
      that parses nothing passes forever. Fix the parser rather than lowering the
      floor.
      FAIL: the scan offered 0 closed task file(s) but <m>/tasks/closed holds 57
      *.md on disk. The scanner is not seeing the corpus (this is the control, not
      a data problem): fix `Store.md_paths` rather than the count.
                         Exactly two violations, both from check 10, asserted by
                         the pass -- a third would mean the red is not attributable.

THE WRITE-OP HALF, added 2026-08-21 after an adversarial audit found four ways to
reach a lint-red tree through a successful write. That is the tool sabotaging its
own gate, so the checks that close them get the same treatment as the lint checks
-- except that here the SUBJECT is a refusal, so the sabotage is to REVERT the
refusal and confirm the pin goes red. Each fix was reverted in a patched copy of
this file (the original is never edited) and the whole suite re-run; each revert
produced exactly ONE red, its own regression test, which is what makes the red
attributable rather than merely present::

    stamp_and_render's created guard  revert -> RED (attributable)
    check_parent_open                 revert -> RED (attributable)
    validate_record (via need_writable) revert -> RED (attributable)
    _ghost's id/title arguments       revert -> RED (attributable)
    check_pri_budget's zero-NOW text  revert -> RED (attributable)
    append_log's log_end/tail slicing revert -> RED (attributable)

Added 2026-08-21d, found on the COLD-SESSION DEMO rather than by an audit -- the
first write op a fresh session runs was refused outright (see ``resolve_key``).
Two weakenings, because the obvious one is not the dangerous one::

    resolve_key -> identity (reuse never fires)   -> RED (attributable)
      AssertionError: refused a derived key on a same-day lettered row:
      task comment: REFUSED
    reuse moved LATE, into stamp_and_render only  -> RED (attributable)
      AssertionError: T1 logged under 2026-08-21

The second is the subtle one and it is why the promotion happens at the op's load
point: promoting inside ``stamp_and_render`` still wrote the right ``moved``, so
the tree stayed lint-clean, while the Log heading and the printed confirmation
kept the un-promoted key. One write, three opinions about which session it was --
green on the gate, wrong in the record a human reads.

The durable form is the TEN ``test_regression_*`` cases in ``test_task.py``, not
this paragraph: a permanent test outranks a docstring in the repo's own
durability ranking, and each of those docstrings carries the literal pre-fix
output it pins. Seven of the ten pin the seven reverts listed above; the other
three (``empty_message``, ``title_stays_on_one_line``, ``bracketed_title``) pin
bugs found the same way. This paragraph said "six ``test_regression_*`` cases" and
meant the six reverts -- a count of the wrong set, in the one sentence whose job
is to tell you where the real evidence lives.

A GREEN SABOTAGE, recorded because the procedure says a green sabotage is a
finding: the FIRST version of the ``check_pri_budget`` probe bumped one row to
NEXT on a tree that already had two, reaching THREE -- which is the cap, not over
it -- and came back ``task lint: clean (10 checks, 7 task file(s) parsed)``. The
check was fine; the PROBE never drove the property it named. It now fills the
budget legally through the tool, asserts the tree is still green at exactly the
cap, and only then makes the illegal edit. Same shape as the repo's own S2
correction in ``docs/sabotage-procedure.md``: the first green was the instrument,
not the subject.

RUN 2026-08-21d -- THE SCHEMA-13 ADDITIONS (``updated`` / ``source`` /
``related``, check 11, and the ack-class write path). Same protocol, same two
corpora, regenerated by the same command; the fixture baseline is now
``task lint: clean (11 checks, 7 task file(s) parsed)``. SIX new lint clauses
were sabotaged through the DATA:

    check_enums(updated) ``updated: 2026-08-21`` -> ``2026-8-21``, a hand-typed
                         date losing its zero padding. Sabotaged separately from
                         ``moved`` because the plausible weakening is a refactor
                         that keeps a loop over two fields and forgets the third:
      FAIL: <t>/tasks/T4-later-gamma.md: updated is '2026-8-21', not a session
      key (YYYY-MM-DD with an optional single lowercase letter). One of the
      stamps was typed by hand; fix the wrong one.

    check_enums(order)   hand-set ``moved`` AHEAD of ``updated`` -- the one stamp
                         state the write path CANNOT produce, and therefore the
                         one that can only arrive silently:
      FAIL: <t>/tasks/T2-next-alpha.md: updated 2026-08-21 sorts before moved
      2026-08-21c, which the write path cannot produce: every op that bumps
      `moved` bumps `updated` too (SPEC.md section 3.1). One of the stamps was
      typed by hand; fix the wrong one.

    check_enums(source)  blank ``source`` -- an added-but-unfilled key, which is
                         what a careless in-place migration leaves behind, and
                         which "the key is present" would have accepted:
      FAIL: <t>/tasks/T5-held-delta.md: source is empty. Every task records where
      it came from: ['board', 'hand'], or a repo-relative path like
      docs/perf-round6-audit-2026-08.md. It is set once at `new` and never
      changes.

    check_enums(source   ``source: hand`` -> ``Board``: the near-miss of a fixed
    typo)                value, same shape as the label-vocabulary slip. sync
                         keys its whole CORPUS-ONLY behaviour off this field, so
                         a value that reads right to a human and matches nothing
                         mechanically is the expensive failure:
      FAIL: <t>/tasks/T6-the-group.md: source 'Board' is neither ['board',
      'hand'] nor a path. A bare word that is not one of the two fixed values is
      almost always a typo for one of them (board/Board/handoff), and a
      vocabulary that admits typos answers no query.

    check_deps(related)  related id typo ``T5`` -> ``T50``:
      FAIL: <t>/tasks/T5-held-delta.md: related id 'T50' resolves to no task
      (open or closed). `related` is navigation: a link that goes nowhere costs
      the reader the lookup before it tells them anything.

    check_deps(related   a task related to ITSELF, which is what a copy-pasted
    self)                ``set related`` line produces:
      FAIL: <t>/tasks/T5-held-delta.md: related lists T5 itself. Remove it with
      `task.py set T5 related "..."` -- a self-link renders as a pointer to the
      page you are already on.

AND FOUR WHOSE SUBJECT HAS NO EXIT CODE TO REDDEN, which is exactly why they are
the ones most likely to ship broken. Check 11 WARNS (its OUTPUT is the artifact,
and a weakening makes it go silent while everything stays green), and the
``moved``/``updated`` split is a write-path rule that produces a perfectly valid
file either way -- no lint clause can see that a ``moved`` was bumped by
something that should not have bumped it. So the subject is the TEST: each case
patches a copy of this file with the narrowest plausible weakening and re-runs
the case that claims to guard the rule. A case that still PASSES against a
deliberately broken tool was never checking anything.

    check_parent_depth   ``MAX_PARENT_DEPTH`` 2 -> 99: "the warning is noisy,
                         raise the threshold". Lint is green before AND after --
                         the whole signal is the WARN line, and it vanishes:
      observed: task lint: clean (11 checks, 8 task file(s) parsed)
      (the three-level tree T8 -> T4 -> T6 produced NO warning, and
      test_parent_depth_warns_and_stays_green went red on its absence)

    ack-does-not-move-   ``op_ack`` calls the PROGRESS path
    moved                (``stamp_and_render(.., True)``) -- the edit a refactor
                         makes on noticing that two call sites differ by one
                         constant. This is THE property the second stamp exists
                         for:
      observed: ack moved `moved` 2026-08-21b -> 2026-08-21c: an acknowledgement
      just laundered a stale row into a fresh one

    --mechanical-is-     ``progress()`` hard-wired to ``True``: the flag is still
    honoured             accepted, still parsed, still documented, and does
                         nothing. The failure mode where a knob exists and is
                         ignored:
      observed: set --mechanical moved `moved` 2026-08-21b -> 2026-08-21d

    source-validation    ``source_problem()`` returns None for everything -- a
                         lenient validator, which is how every lenient validator
                         arrives:
      observed: ("--source 'Board' was accepted", 'T11
      <t>/tasks/T11-bad-source-board.md')

A note on what the ack cases do NOT prove: ``--mechanical`` is honoured when it
is PASSED, and nothing can verify that an automation passed it honestly. An
automation that omits it launders ``moved`` exactly as if the flag did not exist.
What the flag buys is that an honest tool has a way to be honest, and that
``ack`` -- the op with no other purpose -- cannot be anything else.

WHAT THIS RECORD DOES NOT COVER. All but one of the checks were sabotaged by
editing the DATA; only ``check_min_parsed`` was sabotaged by degrading the TOOL.
So the record shows each check fires on a bad tree, and it shows check 10 notices
a half-blind scan -- it does NOT show that the others would survive a subtler
parser defect that keeps the COUNT intact (say, a ``parse_value`` change that
silently empties ``labels``). If you touch the parser, sabotage the parser.
(The 2026-08-21d additions below are the exception: four of them sabotage the
TOOL, because their subjects have no exit code to redden.)

Nor does it cover a scanner fooled TWICE OVER: ``disk_md_count`` is deliberately
independent of ``Store.md_paths``, so the recount catches one blinded scanner --
but an edit that blinds both would pass, and no floor can catch a corpus that was
never written. And the checks reach exactly as far as ``tasks/``: nothing here
resolves a ``## Read first`` pointer, so a task whose entire navigation list is
dead still lints clean.
"""

import argparse
import datetime
import glob
import hashlib
import io
import json
import os
import re
import sys


# --- The fourteen fields --------------------------------------------------------------
# Fixed order, always all present. SPEC.md section 3.1. Changing this order is a
# tree-wide rewrite, not a drive-by edit: every existing file becomes non-canonical the
# moment the order changes, and the next write to each one produces a spurious diff.
#
# WIDENED 10 -> 13 on 2026-08-21 (`updated`, `source`, `related`; migrate_schema13.py did
# the in-place rewrite of all 149 files). The order groups by KIND rather than by date of
# addition, because the order is what a reader scans: the two edge lists (`deps`,
# `related`) sit together, the two birth facts (`source`, `created`) sit together, and the
# three stamps (`moved`, `updated`, `closed`) sit together at the end. Appending the new
# keys after `closed` would have been a smaller diff and a worse file.
#
# WIDENED 13 -> 14 on 2026-08-21d (`source_hash`; migrate_schema14.py, same in-place
# discipline). It sits IMMEDIATELY AFTER `source` and deliberately not among the stamps:
# it is a fact ABOUT the provenance -- "the source block looked like this when we last
# reconciled" -- so `source: board` / `source_hash: 39fbc1...` reads as one two-line
# statement, while parking it next to `moved`/`updated` would invite the reader to expect
# a session key there. See SOURCE_HASH below for why the digest lives in the task file at
# all, and SYNC-SPEC.md section 3.
FIELDS = ('id', 'title', 'pri', 'size', 'deps', 'related', 'parent',
          'labels', 'source', 'source_hash', 'created', 'moved', 'updated', 'closed')
LIST_FIELDS = ('deps', 'related', 'labels')

# `source` is where the task CAME FROM, set once at `new` and immutable after (SPEC.md
# section 3.1). Two fixed words plus the repo-relative path form; it replaces the
# `sync-state.json` SYNC-SPEC.md section 3 used to propose, so that provenance travels
# inside the file -- through the `closed/` move, through a rename -- instead of living in
# a second state file that can desync, go missing, or silently degrade to "everything
# looks hand-filed".
SOURCE_FIXED = ('board', 'hand')
# Deliberately NOT checked for existence on disk. This corpus lives under .scratch/ while
# its sources live in a READ-ONLY repo, and a source document that is later renamed or
# archived would turn the whole gate red for a fact that is still TRUE (the task did come
# from it). Shape is mechanical; existence is not this tool's business.
SOURCE_PATH = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_./+-]*$')

# `source_hash` is the digest of this task's SOURCE BLOCK as of the last reconciliation:
# empty when nothing has ever reconciled the task, otherwise SOURCE_HASH_LEN hex chars.
#
# WHY A DIGEST AND NOT A COMPARISON (SYNC-SPEC.md section 2, `BODY`). Comparing the
# source's prose against the task's prose reports drift FOREVER: the two legitimately
# diverge the instant a session rewrites a body, which is the normal and desired thing to
# do, so that check can never go green and a check that can never go green is as dead as
# one that never fires. What is worth reporting is that the SOURCE MOVED since anyone
# last looked -- source against ITSELF over time -- and a digest is the whole of what that
# question needs.
#
# WHY IT LIVES IN THE TASK FILE. Same argument that killed `sync-state.json` (SYNC-SPEC.md
# section 3), applied one level down: a sidecar keyed by id desyncs, goes missing, and
# when missing degrades every task to "never reconciled" -- a check that fails by passing.
# In the frontmatter it travels through the `closed/` move and through any rename, and it
# cannot disagree with the task because it IS the task.
#
# WHY IT IS NOT A SECOND SOURCE OF TRUTH. It is compared for EQUALITY and nothing else.
# It is not inverted, not decoded, not read by `board`/`list`/`ready`/`show`, and no
# decision anywhere else in this file consults it. It cannot answer any question except
# "did the source block change since the last `ack`/`sync --create-new`", and the old
# TEXT is deliberately NOT kept: the home of "what did HANDOFF.md say last week" is git,
# not a cache in this tool.
#
# 12 hex chars = 48 bits, and the reason it is truncated at all is that a human reads this
# line in every task file; the reason 48 bits is enough is that the only failure available
# is a missed report on a collision between two revisions of ONE board block, against a
# corpus of a few hundred tasks.
SOURCE_HASH_LEN = 12
SOURCE_HASH_RE = re.compile(r'^[0-9a-f]{%d}$' % SOURCE_HASH_LEN)

# THE ONE NON-DIGEST VALUE `source_hash` may hold (added 2026-08-21e, PROOF4.md section 6
# bug B). It means: "acknowledged -- this task's source names no row for it, and that is
# expected". Written by exactly one path, `ack` on a task whose row is absent, which is an
# OBSERVATION the tool made itself and not a claim a human can type (there is still no
# `--source-hash` flag).
#
# WHY IT EXISTS. `sync --check` was red forever: `B2` and `ZT-P5` are open, `source:
# board`, and have no row -- both TRUE findings that only a human `close` can clear, and
# neither is going to be closed, because both are correct as they stand. So every run of
# SYNC-SPEC.md section 4's loop exited 1, today and indefinitely, and a cheap model had no
# printed way to tell weeks-old standing drift from something that changed since the last
# run. That is the identical defect this design already fixed for `UNREADABLE-SOURCE`,
# using this exact sentence -- "a permanently red check is a dead check" -- and then did
# not apply to `CORPUS-ONLY (open)`.
#
# WHY A SENTINEL IN THE EXISTING FIELD, and not a new field or an ack-list file. A new
# state file is the `sync-state.json` this design already deleted twice over (section 3);
# a new field is a fifteenth key on 150 files plus a third migration. The sentinel needs
# no migration at all: `''` already means "never reconciled", so the field already has a
# non-digest value and already carries exactly this kind of fact.
#
# WHY IT CANNOT HIDE A NEW PROBLEM, which is the property that makes it admissible rather
# than a mute button. It is compared for EQUALITY, like every other value of this field,
# and the situation it acknowledges is "there is no row". The moment a row APPEARS the
# task stops being bucketed CORPUS-ONLY at all and goes down the normal path, where the
# stored sentinel is compared against the row's real digest -- and no digest is ever equal
# to it, because it is not hex. So the acknowledgement goes quiet for exactly the
# situation it was given, and speaks up the instant that situation changes. Proven, not
# asserted: `test_ack_covers_corpus_only_and_cannot_hide_a_new_problem`.
SOURCE_HASH_NO_ROW = 'acked-no-row'

PRI_VALUES = ('NOW', 'NEXT', 'LATER', 'HOLD', 'SOMEDAY')
SIZE_VALUES = ('S', 'M', 'L', '?')

# `list`'s default row cap. The table is sorted NOW-first, so a cap keeps the rows that
# answer "what now?" and drops the tail nobody reads: at 91 open tasks the uncapped table
# is 94 lines, which is most of a board-sized read for a view whose whole purpose was to
# be cheaper than one. BRAIN-DUMP.md predicted this exact failure and prescribed this
# exact fix ("a default filter rather than un-filing anything").
#
# TRUNCATION IS ALWAYS ANNOUNCED. A view that silently shows 20 of 91 is the fail-by-
# passing shape this project is built around -- the reader believes they have seen the
# backlog. The footer therefore names both numbers and the flag that widens it, and
# `--limit 0` restores the old behaviour exactly.
#
# THE DEFAULT DOES NOT APPLY TO `--json`, only an EXPLICIT --limit does. A machine surface
# that drops rows by default breaks its consumers silently, which is the same defect one
# layer down; a caller who asks for a cap gets it on both surfaces.
LIST_LIMIT = 20

# THE `moved` / `updated` SPLIT, which is the reason both fields exist.
#
# `updated` bumps on EVERY write. `moved` bumps only when a session made PROGRESS. The
# distinction is load-bearing: a cheap-model housekeeping pass that acknowledges the
# sync agent's work, or applies a mechanical field fix, must NOT be able to launder a
# stale item into looking fresh. An old `moved` on a NOW row means NEGLECT, and that
# signal has to survive automation -- `board`'s staleness warning reads `moved` for
# exactly that reason, and reading `updated` there would make the warning unfireable the
# moment anything automated runs on a schedule.
#
# The rule is PER-OP and mechanical; nothing here consults judgement about whether an
# edit "felt like progress":
#   both  -- new, touch, promote, dep add/rm, close, reopen, comment, set
#   updated only -- ack, and any write carrying --mechanical (the flag a housekeeping
#                   TOOL passes on every call it makes; see PROGRESS_OPS below)
PROGRESS_OPS = ('new', 'set', 'promote', 'dep', 'comment', 'touch', 'close', 'reopen')
ACK_OPS = ('ack',)

# HOLD and SOMEDAY are excluded from `ready` BY DEFINITION, not as a filter someone can
# turn off: a HOLD item with satisfied deps is still held, and offering it as ready is how
# a hold quietly stops meaning anything.
READY_PRIS = ('NOW', 'NEXT', 'LATER')

# Session key = YYYY-MM-DD with an optional single lowercase suffix, matching the repo's
# session-ledger heading keys (docs/history/session-log.md). PLAIN STRING comparison sorts
# these correctly because the letterless form is a prefix of every lettered same-day form:
# "2026-08-16" < "2026-08-16b" < "2026-08-16c". Nothing here ever parses one as a date --
# that is what makes the letter suffix representable at all.
SESSION_KEY = re.compile(r'^\d{4}-\d\d-\d\d[a-z]?$')

# Id VALIDATION is permissive and id ALLOCATION is strict, and the asymmetry is load
# bearing (SPEC.md section 6). Legacy ids (P3, HS-5, R6, ZT-P0-1, B1, AW-1, LT-1, DW-1,
# SD-1, GS-1) must keep working verbatim as addresses forever, because ids are never
# reused and an inbound citation that stops resolving is worse than an ugly id. But a
# NEWLY minted id has to be mechanically derivable, so allocation only ever mints
# <id_prefix><integer>.
ID_OK = re.compile(r'^[A-Za-z0-9][A-Za-z0-9-]*$')

# NOTE the absence of `min_tasks_parsed`. It is the ONE knob with no honest default: it
# is a MEASUREMENT of a particular corpus, and any number invented here would be a floor
# with headroom in every tree that forgot to set one -- which is the exact defect that
# shipped (SPEC.md section 6's EXAMPLE value 5 was copied into a config guarding 99
# files, so deleting 57 of them still linted clean). `check_min_parsed` therefore treats
# a missing floor as a VIOLATION and tells you to run `task.py counts`, which prints the
# measured value to paste. Keys beginning with `_` (e.g. `_provenance`) are documentation
# for humans: JSON has no comments, and a tuned number without its provenance is how the
# next reader learns to copy it again.
#
# `id_prefix` has no default for the same reason: a prefix is only correct RELATIVE to a
# repo's existing namespaces, and the default that shipped ("T", again SPEC.md's example)
# mints `T1` -- already the name of the set-engine correctness theorem, 162 first-party
# occurrences. `next_id` refuses rather than guess.
CONFIG_DEFAULTS = {
    'labels': [],
    'budgets': {'NOW': 1, 'NEXT': 3},
    'stale_days': 14,
}

# Body skeleton for `new`. The three prose sections are REPLACE-ON-TOUCH -- a session that
# works the item rewrites them and this script never edits them -- while `## Log` is
# append-only and this script is its only writer. Keeping the two kinds of section
# physically separate is what lets a human edit the file freely without fighting the tool.
BODY_SKELETON = (
    'TODO: one paragraph -- what this item is and why it matters.\n'
    '\n'
    '## Traps\n'
    '\n'
    '## Read first\n'
    '\n'
    '## Log\n'
)

LOG_HEADING = '## Log'

# Console stdout on this Windows host is cp1252, so PRINTED output is ASCII-only while
# file CONTENT stays UTF-8 (task bodies legitimately carry the repo's warn badge). This
# maps the handful of glyphs the repo's docs actually use and backslash-escapes the rest,
# rather than dropping characters: a silently dropped glyph in a `show` is a lie about the
# file's contents, and this tool's whole job is to be a faithful view of the files.
#
# The table is MEASURED, not guessed: `measure_glyphs.py` counts every non-ASCII code
# point in the live corpus and prints which are unmapped. Re-run it after any bulk
# import. The five added on 2026-08-21 were all unmapped and all landed on the rows a
# session reads FIRST -- the section sign alone occurs 77 times across 32 of the 99
# files, and rendered P3's own trap as "Read §11.10 before touching the cone":
# honest, unreadable, and un-greppable once pasted.
ASCII_FOLD = {
    u'⚠': '(!)',    # warn badge, the trap glyph
    u'★': '(*)',    # retired star glyph
    u'→': '->',
    u'←': '<-',
    u'↔': '<->',    # x1, in P4's title (leaf-probe <-> directLeaf bridge)
    u'—': '--',
    u'–': '-',
    u'‘': "'",
    u'’': "'",
    u'“': '"',
    u'”': '"',
    u'…': '...',
    u' ': ' ',
    u'·': '*',
    u'•': '*',
    u'§': 'sec ',   # x77 in 32 files -- spec/section citations, the commonest of all
    u'×': 'x',      # x15 in 6 files -- measured speedup factors ("2.54x")
    u'−': '-',      # x2, U+2212 MINUS SIGN, which is NOT the ASCII hyphen ("-60.7%")
    u'σ': 'sigma',  # x2, P3's rewrite-closure chain (sigma0-side)
    u'🧭': '(nav)',  # x1, P3's "machine-checked, needs a human call" badge
}


class Refused(Exception):
    """A write op that declined to run. Carries the message shown to the caller.

    Mechanical refusal beats a doc warning: the next person will not read the doc.
    """


class ParseError(Exception):
    """A task file that is not in the constrained subset. Always names the file."""


# --- Output ---------------------------------------------------------------------------

def ascii_safe(text):
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in ASCII_FOLD:
            out.append(ASCII_FOLD[ch])
        else:
            out.append('\\u%04x' % ord(ch))
    return ''.join(out)


def prog():
    """How THIS run was invoked, for printing back as a runnable next command.

    The board and several refusals name the follow-up command, and they used to hardcode
    ``task.py``. Once the script lands at ``scripts/task.py`` -- which is where the
    graduated stub puts it -- every one of those strings is a copy-paste that fails:

        $ python task.py show P3
        can't open file '...gate-sim/task.py': [Errno 2] No such file or directory

    Observed on 2026-08-21d in ``gate-sim`` while running the cold-session demo, i.e. by
    the one path the whole tool exists to serve. A printed command must be the command
    the reader can actually run, so it is derived from ``sys.argv[0]`` and never typed.
    Falls back to the bare name when argv[0] is empty (``-c``, an embedding host).
    """
    raw = sys.argv[0] or 'task.py'
    return os.path.basename(raw) if os.path.dirname(raw) in ('', '.') else \
        raw.replace(os.sep, '/')


def emit(text=''):
    sys.stdout.write(ascii_safe(text) + '\n')


def emit_err(text):
    sys.stderr.write(ascii_safe(text) + '\n')


def emit_json(obj):
    # sort_keys so a --json consumer diffing two runs sees content changes only. NO
    # ascii_safe here: json.dumps defaults to ensure_ascii=True, so the result is already
    # pure ASCII: json.dumps({'a': u'§'}) is the 15-byte str '{"a": "\\u00a7"}'.
    # The ascii_safe() wrapper this used to carry could not fire on any input, and a
    # dead call reads to the next person as a live guarantee.
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + '\n')


# --- File IO --------------------------------------------------------------------------
# Always explicit encoding and newline='' on both sides. The platform default would make
# these files byte-unstable across machines, and byte-stability is the entire argument for
# hand-writing the frontmatter rather than importing YAML.

def read_text(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as fh:
        return fh.read().replace('\r\n', '\n')


def write_text(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


# --- The frontmatter subset (SPEC.md section 3.2) --------------------------------------

def parse_file(text, path='<memory>'):
    """Split a task file into (pairs, body).

    ``pairs`` is an ordered list of (key, value) exactly as written -- duplicates and
    unknown keys included, because ``lint`` has to be able to REPORT them. Callers that
    want a validated task use ``Task.load``.
    """
    lines = text.split('\n')
    if not lines or lines[0] != '---':
        raise ParseError('%s: no opening "---" on line 1' % path)
    close = None
    for i in range(1, len(lines)):
        if lines[i] == '---':
            close = i
            break
    if close is None:
        raise ParseError('%s: opening "---" is never closed' % path)

    pairs = []
    for n in range(1, close):
        raw = lines[n]
        if not raw.strip():
            raise ParseError('%s:%d: blank line inside frontmatter' % (path, n + 1))
        cut = raw.find(': ')
        if cut >= 0:
            key, value = raw[:cut], raw[cut + 2:]
        elif raw.endswith(':'):
            key, value = raw[:-1], ''
        else:
            raise ParseError('%s:%d: not "key: value" -- %r' % (path, n + 1, raw))
        if key != key.strip():
            raise ParseError('%s:%d: key %r has surrounding whitespace' % (path, n + 1, key))
        pairs.append((key, parse_value(value, key in LIST_FIELDS)))

    body_lines = lines[close + 1:]
    # The canonical form has exactly one blank line between the closing "---" and the
    # body; strip it on read and re-add it on write so a round-trip is byte-identical.
    if body_lines and body_lines[0] == '':
        body_lines = body_lines[1:]
    return pairs, '\n'.join(body_lines)


def parse_value(value, is_list):
    """A flow list, or a plain string. Nothing is ever coerced to int or date.

    Which one it is comes from the KEY, not from the shape of the value. The schema
    is fixed and tiny (``LIST_FIELDS``), so the key already knows -- and sniffing the
    brackets instead is a live corruption bug: ``task.py new "[wip]"`` wrote a
    ``title: [wip]`` that read back as the LIST ``['wip']``, and every subsequent op
    on the whole tree died with ``'title' must be a plain scalar, not a list``
    (observed 2026-08-21). A scalar field now round-trips any bracketed text
    verbatim. A list field whose value is NOT bracketed still returns a string, so
    ``load_task``'s "must be a flow list" error keeps firing on a hand-typed
    ``deps: T4``.
    """
    v = value.strip()
    if is_list and v.startswith('[') and v.endswith(']'):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [p.strip() for p in inner.split(',') if p.strip()]
    return v


def render_file(fm, body):
    """The canonical writer. Thirteen keys, fixed order, [] for empty lists, bare `key:`
    for empty scalars, one blank line before the body, one trailing newline."""
    out = ['---']
    for key in FIELDS:
        value = fm.get(key, [] if key in LIST_FIELDS else '')
        if key in LIST_FIELDS:
            out.append('%s: [%s]' % (key, ', '.join(value)))
        elif value:
            out.append('%s: %s' % (key, value))
        else:
            out.append('%s:' % key)
    out.append('---')
    out.append('')
    text = '\n'.join(out) + '\n'
    body = body.rstrip('\n')
    if body:
        text += body + '\n'
    return text


# --- Task -----------------------------------------------------------------------------

class Task(object):

    def __init__(self, path, fm, body, is_closed):
        self.path = path
        self.fm = fm
        self.body = body
        self.is_closed = is_closed

    @property
    def id(self):
        return self.fm.get('id', '')

    @property
    def title(self):
        return self.fm.get('title', '')

    @property
    def pri(self):
        return self.fm.get('pri', '')

    @property
    def size(self):
        return self.fm.get('size', '')

    @property
    def deps(self):
        return list(self.fm.get('deps', []))

    @property
    def labels(self):
        return list(self.fm.get('labels', []))

    @property
    def parent(self):
        return self.fm.get('parent', '')

    @property
    def related(self):
        return list(self.fm.get('related', []))

    @property
    def source(self):
        return self.fm.get('source', '')

    @property
    def source_hash(self):
        return self.fm.get('source_hash', '')

    @property
    def moved(self):
        return self.fm.get('moved', '')

    @property
    def updated(self):
        return self.fm.get('updated', '')

    @property
    def created(self):
        return self.fm.get('created', '')

    @property
    def closed(self):
        return self.fm.get('closed', '')

    def render(self):
        return render_file(self.fm, self.body)

    def summary(self):
        """The first prose paragraph of the body -- the one line `board` shows."""
        out = []
        for line in self.body.split('\n'):
            if line.startswith('#'):
                break
            if not line.strip():
                if out:
                    break
                continue
            out.append(line.strip())
        return ' '.join(out)

    def as_dict(self):
        d = dict((k, self.fm.get(k, [] if k in LIST_FIELDS else '')) for k in FIELDS)
        d['is_closed'] = self.is_closed
        d['path'] = self.path.replace(os.sep, '/')
        return d


def load_task(path, is_closed):
    # rel() everywhere, so a ParseError is pasteable next to a check_* failure rather
    # than being the one message in the tool that prints Windows backslashes.
    pairs, body = parse_file(read_text(path), rel(path))
    fm = {}
    for key, value in pairs:
        if key in fm:
            raise ParseError('%s: duplicate key %r' % (rel(path), key))
        fm[key] = value
    missing = [k for k in FIELDS if k not in fm]
    unknown = [k for k in fm if k not in FIELDS]
    if missing or unknown:
        raise ParseError('%s: missing keys %s, unknown keys %s (all fourteen keys are '
                         'always present -- see SPEC.md section 3.1)'
                         % (rel(path), missing or '-', unknown or '-'))
    for k in LIST_FIELDS:
        if not isinstance(fm[k], list):
            raise ParseError('%s: %r must be a flow list like [a, b] or [] -- got %r'
                             % (rel(path), k, fm[k]))
    # There is deliberately no converse check ("a scalar field must not be a list").
    # It used to be here and it was reachable only because `parse_value` sniffed the
    # brackets; now that the KEY decides, a scalar field cannot come back as a list,
    # and a check that cannot fire is a comment that costs runtime.
    return Task(path, fm, body, is_closed)


# --- Store ----------------------------------------------------------------------------

class Store(object):
    """The tasks/ tree. Open vs closed is the FOLDER; there is no status field."""

    def __init__(self, tasks_dir):
        self.dir = tasks_dir
        self.closed_dir = os.path.join(tasks_dir, 'closed')
        self.config = dict(CONFIG_DEFAULTS)
        cfg_path = os.path.join(tasks_dir, 'config.json')
        if os.path.exists(cfg_path):
            loaded = json.loads(read_text(cfg_path))
            self.config.update(loaded)
        budgets = dict(CONFIG_DEFAULTS['budgets'])
        budgets.update(self.config.get('budgets') or {})
        self.config['budgets'] = budgets
        self._tasks = None

    # -- discovery --

    @staticmethod
    def find(start):
        """Walk up from ``start`` looking for tasks/config.json.

        Anchored on the CONFIG file rather than on a directory named ``tasks``: a bare
        directory name is something any tree may have for unrelated reasons, and picking
        up the wrong one would be a silent wrong answer rather than a loud miss.
        """
        cur = os.path.abspath(start)
        while True:
            candidate = os.path.join(cur, 'tasks', 'config.json')
            if os.path.exists(candidate):
                return Store(os.path.join(cur, 'tasks'))
            if os.path.basename(cur) == 'tasks' and \
                    os.path.exists(os.path.join(cur, 'config.json')):
                return Store(cur)
            parent = os.path.dirname(cur)
            if parent == cur:
                raise Refused('no tasks/config.json found at or above %r. Create one '
                              '(SPEC.md section 6) or pass --dir.' % start)
            cur = parent

    # -- scanning --

    def md_paths(self):
        """Every task file. Only *.md counts; config.json and retired-ids.txt are skipped
        by every scan, which is why they can live in the same directory."""
        out = []
        for d, is_closed in ((self.dir, False), (self.closed_dir, True)):
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if name.endswith('.md'):
                    out.append((os.path.join(d, name), is_closed))
        return out

    def tasks(self):
        if self._tasks is None:
            out = []
            for path, is_closed in self.md_paths():
                out.append(load_task(path, is_closed))
            self._tasks = out
        return self._tasks

    def invalidate(self):
        self._tasks = None

    def open_tasks(self):
        return [t for t in self.tasks() if not t.is_closed]

    def closed_tasks(self):
        return [t for t in self.tasks() if t.is_closed]

    def by_id(self):
        return dict((t.id, t) for t in self.tasks())

    def resolve(self, task_id):
        """Find a task by id. The ID IS THE ADDRESS; the path never is.

        Glob ``<id>-*.md`` first (the fast path, and correct for every file this tool
        wrote), then fall back to a FULL SCAN verified against the frontmatter. That
        fallback is the point: a rename, a hand-edited filename, or an archive move can
        never rot an inbound reference, because the filename is cosmetic -- it exists so
        that `ls` is readable -- and the frontmatter id is truth.
        """
        for d, is_closed in ((self.dir, False), (self.closed_dir, True)):
            for path in sorted(glob.glob(os.path.join(d, '%s-*.md' % task_id))):
                try:
                    task = load_task(path, is_closed)
                except ParseError:
                    continue
                if task.id == task_id:
                    return task
        for task in self.tasks():
            if task.id == task_id:
                return task
        return None

    def need(self, task_id):
        task = self.resolve(task_id)
        if task is None:
            raise Refused('no task with id %r (searched %s and %s, by glob then by full '
                          'frontmatter scan). Ids are never reused, so check '
                          'retired-ids.txt before assuming it is a typo.'
                          % (task_id, rel(self.dir), rel(self.closed_dir)))
        return task

    # -- retired registry --

    def retired_ids(self):
        path = os.path.join(self.dir, 'retired-ids.txt')
        if not os.path.exists(path):
            return []
        out = []
        for line in read_text(path).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                out.append(line)
        return out

    def next_id(self):
        """Allocate by SCANNING, never from a stored counter.

        A counter goes stale the first time someone hand-creates a file, restores one from
        git, or edits the counter to "fix" a conflict -- and the failure mode is a REUSED
        id, which silently merges two items' histories. The scan covers open + closed +
        the retired registry, so an id that ever existed can never be minted again.
        """
        prefix = self.config.get('id_prefix')
        if not prefix:
            raise Refused('tasks/config.json has no "id_prefix", and there is no honest '
                          'default: a prefix is only correct relative to the namespaces '
                          'already in the repo (measure with measure_prefix.py -- the '
                          'shipped value "TK" has zero `\\bTK\\d+\\b` hits in any '
                          'first-party file, where "T" had 686). Set it deliberately.')
        pattern = re.compile(r'^%s(\d+)$' % re.escape(prefix))
        best = 0
        seen = [t.id for t in self.tasks()] + self.retired_ids()
        for value in seen:
            m = pattern.match(value)
            if m:
                best = max(best, int(m.group(1)))
        return '%s%d' % (prefix, best + 1)


def rel(path):
    return path.replace(os.sep, '/')


# --- Session keys ---------------------------------------------------------------------

class SessionKey(str):
    """A session key that remembers whether a human typed it.

    A plain ``str`` everywhere it is compared, sorted or written -- the distinction
    matters at exactly one place (``stamp_and_render``'s same-day reuse), and threading a
    boolean through eight call sites to reach it would put the flag in seven functions
    that have no business knowing about it.
    """

    explicit = False

    def __new__(cls, value, explicit=False):
        self = str.__new__(cls, value)
        self.explicit = explicit
        return self


def session_key(explicit):
    """The key stamped into ``moved`` by every write op.

    ``--session KEY`` wins. Otherwise today's plain ``YYYY-MM-DD``, and DELIBERATELY no
    auto-lettering: a letter suffix means "a distinct session on the same day" in the
    repo's session ledger, and only a human knows whether that is true. Auto-incrementing
    it would invent ledger entries that do not exist.

    A FUTURE KEY IS REFUSED (added 2026-08-21, PROOF2.md section 4). Backdating was
    already blocked relationally (``resolve_key``: ``moved`` may not sort before
    ``created``), which left forward-stamping as the one remaining way to write a
    ``moved`` that no ledger entry can justify -- ``--session 2026-08-22`` was accepted
    silently, lint stayed clean, and the stale-detector (``stale_threshold``) treats the
    row as fresh for as long as the lie runs. The rule is the same one that forbids
    auto-lettering: a session key NAMES an entry in ``docs/history/session-log.md``, and
    an entry dated after today cannot exist yet. Today itself is always legal, letter
    suffixes included; every past key stays legal, because importing history is honest.
    """
    if explicit:
        if not SESSION_KEY.match(explicit):
            raise Refused('--session %r is not a session key (YYYY-MM-DD with an optional '
                          'single lowercase letter, e.g. 2026-08-20b)' % explicit)
        today = datetime.date.today().isoformat()
        if explicit[:10] > today:
            raise Refused('--session %s is in the FUTURE (today is %s). A session key '
                          'names an entry in docs/history/session-log.md, and an entry '
                          'dated after today cannot exist yet -- a forward-stamped '
                          '`moved` is a freshness claim no ledger row can back, and it '
                          'reads as fresh to every staleness check until that day '
                          'arrives. Use today (%s, or %sb for a second session on it) or '
                          'a past key.' % (explicit, today, today, today))
        return SessionKey(explicit, explicit=True)
    return SessionKey(datetime.date.today().isoformat())


def stale_threshold(stale_days):
    """The session key below which ``moved`` counts as stale.

    Date arithmetic happens HERE, once, to derive a threshold string -- the comparison
    against stored keys is still plain string comparison, so a lettered key like
    2026-08-20b never has to be parsed as a date.
    """
    day = datetime.date.today() - datetime.timedelta(days=int(stale_days))
    return day.isoformat()


# --- Graph helpers --------------------------------------------------------------------

def find_cycle(edges, start):
    """A path from ``start`` back to ``start``, or None. Depth-first, iterative.

    Used for both deps and parent. Both are checked AT WRITE TIME rather than only in
    lint, because a cycle written today is a cycle every future ``ready`` has to survive.
    """
    stack = [(start, [start])]
    seen = set()
    while stack:
        node, path = stack.pop()
        for nxt in edges.get(node, []):
            if nxt == start:
                return path + [nxt]
            if nxt in seen:
                continue
            seen.add(nxt)
            stack.append((nxt, path + [nxt]))
    return None


def dep_edges(store, override=None):
    edges = {}
    for task in store.tasks():
        edges[task.id] = task.deps
    if override:
        edges.update(override)
    return edges


def parent_edges(store, override=None):
    edges = {}
    for task in store.tasks():
        edges[task.id] = [task.parent] if task.parent else []
    if override:
        edges.update(override)
    return edges


def is_ready(task, closed_ids):
    if task.is_closed or task.pri not in READY_PRIS:
        return False
    return all(d in closed_ids for d in task.deps)


def pri_rank(pri):
    try:
        return PRI_VALUES.index(pri)
    except ValueError:
        return len(PRI_VALUES)


def sort_key(task):
    return (pri_rank(task.pri), task.id)


# --- Body / Log editing ---------------------------------------------------------------

def append_log(body, key, message):
    """Append a dated entry to ``## Log``. Newest LAST, append-only, never rewritten.

    If an entry for the same session key already exists, the text goes UNDER it rather
    than creating a second heading: two ``### 2026-08-20`` headings in one file make the
    ledger unreadable and break "newest last" as an ordering.

    SPEC.md section 3.3 says ``## Log`` is last, but a file that carries a section AFTER
    it is ordinary hand-editing and the append has to survive it. This used to work on
    the raw line list with no notion of where the Log section ENDS, which cost two
    things (both observed 2026-08-21). The same-key branch trimmed the block's trailing
    blank and then spliced the following heading straight back on, producing
    ``...\\nappended\\n## Notes`` -- one blank line eaten per append, degrading every
    time. The new-key branch was worse in a quieter way: it appended at end of BODY, so
    a second session's entry landed under ``## Notes`` instead of under ``## Log``.
    Slicing the section out by its bounds fixes both, and leaves Log-last files -- every
    file this tool writes -- byte-identical to before.
    """
    lines = body.split('\n') if body else []
    log_at = None
    for i, line in enumerate(lines):
        if line.strip() == LOG_HEADING:
            log_at = i
            break
    if log_at is None:
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            lines.append('')
        lines.append(LOG_HEADING)
        log_at = len(lines) - 1

    # Where the Log section ENDS: the next `## ` heading, or end of body. `### 2026-...`
    # does not match -- its third character is `#`, not a space -- so log ENTRIES stay
    # inside the section, which is the whole point.
    log_end = len(lines)
    for i in range(log_at + 1, len(lines)):
        if lines[i].startswith('## '):
            log_end = i
            break
    head, section, tail = lines[:log_at + 1], lines[log_at + 1:log_end], lines[log_end:]

    heading = '### %s' % key
    entry_at = None
    for i, line in enumerate(section):
        if line.strip() == heading:
            entry_at = i
            break

    if entry_at is None:
        while section and not section[-1].strip():
            section.pop()
        section.append('')
        section.append(heading)
        section.append('')
        section.extend(message.rstrip('\n').split('\n'))
    else:
        end = len(section)
        for i in range(entry_at + 1, len(section)):
            if section[i].startswith('### '):
                end = i
                break
        block = section[:end]
        while block and not block[-1].strip():
            block.pop()
        block.append('')
        block.extend(message.rstrip('\n').split('\n'))
        section = block + section[end:]

    if tail:
        # Exactly one blank line before whatever follows the Log section, every time.
        while section and not section[-1].strip():
            section.pop()
        section.append('')

    return '\n'.join(head + section + tail).rstrip('\n') + '\n'


def read_message(raw):
    """``-m -`` reads the message from stdin, for multi-line entries.

    An EMPTY message is refused in both forms. argparse only enforces that the flag
    is PRESENT, so ``close ID -m ""`` used to close the task and append a dated Log
    heading with nothing under it (observed 2026-08-21) -- a close with no outcome
    evidence, which is precisely the state this tool exists to delete, arrived at
    through the one op whose whole point is requiring evidence.
    """
    if raw != '-':
        text = raw.replace('\r\n', '\n').strip()
        if not text:
            raise Refused('-m was given an empty message. It is required outcome '
                          'evidence: say what happened, or cite where the evidence '
                          'lives (a commit, a gate run, a ledger entry).')
        return text
    data = sys.stdin.buffer.read() if hasattr(sys.stdin, 'buffer') else sys.stdin.read()
    if isinstance(data, bytes):
        data = data.decode('utf-8', 'replace')
    text = data.replace('\r\n', '\n').strip('\n')
    if not text.strip():
        raise Refused('-m - was given but stdin was empty. A close/comment with no '
                      'evidence is the thing this tool exists to stop.')
    return text


# --- Writing --------------------------------------------------------------------------

def source_problem(value):
    """Return a complaint string for a bad ``source``, or None.

    ONE implementation, called by both ``check_enums`` (lint) and ``validate_record``
    (every write op), for the same reason the pri/size clauses are mirrored: a write op
    that refuses what lint accepts -- or accepts what lint refuses -- is a second,
    undocumented schema, and whichever one you learn first teaches you the wrong rule.
    """
    if not value:
        return ('source is empty. Every task records where it came from: %s, or a '
                'repo-relative path like docs/perf-round6-audit-2026-08.md. It is set '
                'once at `new` and never changes.' % (list(SOURCE_FIXED),))
    if value in SOURCE_FIXED:
        return None
    if not SOURCE_PATH.match(value):
        return ('source %r is neither %s nor a repo-relative path (%s). A leading "/", a '
                'backslash or a space means it is not the path this repo would cite.'
                % (value, list(SOURCE_FIXED), SOURCE_PATH.pattern))
    if '..' in value.split('/'):
        return ('source %r escapes the repo with "..". Cite the path as the repo cites '
                'it, from the repo root.' % value)
    if '/' not in value and '.' not in value:
        return ('source %r is neither %s nor a path. A bare word that is not one of the '
                'two fixed values is almost always a typo for one of them (board/Board/'
                'handoff), and a vocabulary that admits typos answers no query.'
                % (value, list(SOURCE_FIXED)))
    return None


def source_hash_problem(value, source):
    """Return a complaint string for a bad ``source_hash``, or None.

    Two clauses, and the second is the interesting one. SHAPE: empty (never reconciled),
    the ``SOURCE_HASH_NO_ROW`` sentinel, or exactly ``SOURCE_HASH_LEN`` lowercase hex.
    RELATION: a task whose ``source`` is ``hand`` has no source block anywhere, so there
    is nothing a digest could be OF -- a hand-filed task carrying one is a state no write
    path can produce, which is precisely the class ``stamp_problems`` checks for and the
    class that arrives silently (a hand edit, or a tool that stamped the field without
    deciding what it meant). The sentinel is held to that SAME relation clause on purpose:
    "acknowledged: this task's source names no row for it" is not a sentence a `hand` task
    can say either, because a `hand` task has no source to be absent from.
    """
    if not value:
        return None
    if value == SOURCE_HASH_NO_ROW:
        return ('source_hash is the %r sentinel but source is `hand`: a hand-filed task '
                'has no source that could be missing a row for it. Blank the hash, or fix '
                'the provenance.' % SOURCE_HASH_NO_ROW) if source == 'hand' else None
    if not SOURCE_HASH_RE.match(value):
        return ('source_hash %r is neither %d lowercase hex chars nor the %r sentinel. It '
                'is written only by `sync --create-new` and `ack`, never by hand -- if it '
                'is wrong, blank it and re-`ack` the task.'
                % (value, SOURCE_HASH_LEN, SOURCE_HASH_NO_ROW))
    if source == 'hand':
        return ('source_hash is set but source is `hand`: a hand-filed task has no '
                'source block for the digest to be OF. Blank the hash, or fix the '
                'provenance (a hand edit plus a Log entry, per SPEC.md section 3.1).')
    return None


def stamp_problems(task):
    """Complaints about `created` / `moved` / `updated` as a SET, or [].

    The ordering clauses are the whole point. `updated` bumps on every write and `moved`
    only on progress, so `moved <= updated` is an INVARIANT of the write path, not a
    style rule: a tree where `moved` sorts after `updated` has had `moved` bumped by
    something that did not go through `stamp_and_render`, which is exactly the laundering
    the split exists to prevent -- and it is silent unless something checks it.
    """
    problems = []
    for field in ('created', 'moved', 'updated'):
        value = task.fm.get(field, '')
        if not SESSION_KEY.match(value or ''):
            problems.append('%s is %r, not a session key (YYYY-MM-DD with an optional '
                            'single lowercase letter)' % (field, value))
    ok = dict((f, SESSION_KEY.match(task.fm.get(f, '') or '') and task.fm.get(f, ''))
              for f in ('created', 'moved', 'updated'))
    # Plain string comparison; see the SESSION_KEY comment for why that is sound.
    if ok['created'] and ok['moved'] and ok['moved'] < ok['created']:
        problems.append('moved %s sorts before created %s' % (ok['moved'], ok['created']))
    if ok['created'] and ok['updated'] and ok['updated'] < ok['created']:
        problems.append('updated %s sorts before created %s'
                        % (ok['updated'], ok['created']))
    if ok['moved'] and ok['updated'] and ok['updated'] < ok['moved']:
        problems.append('updated %s sorts before moved %s, which the write path cannot '
                        'produce: every op that bumps `moved` bumps `updated` too '
                        '(SPEC.md section 3.1)' % (ok['updated'], ok['moved']))
    return problems


def validate_record(task, vocab):
    """Refuse to REWRITE a record that is ALREADY invalid, naming every bad field.

    A write op that loads garbage, bumps ``moved`` and re-emits the garbage through the
    canonical writer is the tool LAUNDERING a corrupt file. Observed 2026-08-21 on a
    record hand-edited to ``pri: URGENT!!``, ``size: XXL``, ``created: last tuesday``::

        $ python task.py touch P10
        P10 moved 2026-08-21
        rc=0

    Exit 0, all three values written straight back out, no mention of any of them. The
    renderer trusted whatever the parser handed it, so the only remaining signal was the
    next ``lint`` -- and ``lint`` is the gate this tool exists to KEEP green, not the
    place to discover damage the tool has just countersigned.

    Deliberately NOT an auto-repair, and that is the load-bearing half of this function.
    There is no correct value to invent for a ``created`` of "last tuesday"; a tool that
    guesses one destroys the only evidence of what actually happened, and does it inside
    an op the caller ran for an unrelated reason. The remedy is a hand edit plus
    ``lint``, which is why SPEC.md section 4 has no ``edit`` op ("that is your editor").

    The consequence is a deliberate lockout: with ``pri`` corrupt, ``promote`` is refused
    too, even though ``promote`` would overwrite the very field that is wrong. Accepted.
    A repair path that runs through the tool would have to decide which of the other nine
    fields it also trusts, and "the file is red, open it" is a smaller rule than that.

    Every clause here mirrors a lint check (4, 8 and 9, the per-record ones), so this can
    only ever refuse a record ``lint`` already calls red. That direction matters: a write
    op that refuses something lint accepts is a second, undocumented schema.
    """
    problems = []
    if not ID_OK.match(task.id or ''):
        problems.append('id %r does not match %s' % (task.id, ID_OK.pattern))
    # `optional` mirrors check_enums EXACTLY, including its closed/ exemption. The two
    # must not drift: if this were stricter, a write op would refuse a record lint calls
    # green, which is a second undocumented schema; if it were looser it would launder
    # the very thing it exists to catch.
    optional = task.is_closed
    if (task.pri or not optional) and task.pri not in PRI_VALUES:
        problems.append('pri %r is not one of %s%s'
                        % (task.pri, list(PRI_VALUES),
                           ' (it may be empty only under closed/)' if not task.pri else ''))
    if (task.size or not optional) and task.size not in SIZE_VALUES:
        problems.append('size %r is not one of %s%s'
                        % (task.size, list(SIZE_VALUES),
                           ', or empty under closed/' if not task.size else ''))
    problems.extend(stamp_problems(task))
    bad_source = source_problem(task.source)
    if bad_source:
        problems.append(bad_source)
    bad_hash = source_hash_problem(task.source_hash, task.source)
    if bad_hash:
        problems.append(bad_hash)
    if task.id and task.id in task.related:
        problems.append('related lists %s itself' % task.id)
    if task.closed and not SESSION_KEY.match(task.closed):
        problems.append('closed is %r, not a session key' % task.closed)
    if task.is_closed and not task.closed:
        problems.append('the file is under closed/ but `closed` is empty')
    if task.closed and not task.is_closed:
        problems.append('closed is %s but the file sits in the OPEN folder' % task.closed)
    for label in task.labels:
        if label not in vocab:
            problems.append('label %r is not in the declared vocabulary %s'
                            % (label, vocab))
    if problems:
        raise Refused('%s (%s) is ALREADY invalid, and this write would re-emit it '
                      'unchanged:\n  %s\nRun `task.py lint` for the full picture and fix '
                      'the field(s) by hand. Nothing is auto-repaired here on purpose: '
                      'there is no correct value to invent for a hand-typed one, and '
                      'guessing would erase the evidence of what happened.'
                      % (task.id, rel(task.path), '\n  '.join(problems)))


def need_writable(store, task_id):
    """``store.need`` for WRITE ops: resolve the id, then refuse an already-red record.

    Read ops deliberately do NOT go through here. ``show`` on a broken record is how you
    find out what is broken, and a viewer that refuses to display damage is useless
    exactly when it is needed.
    """
    task = store.need(task_id)
    validate_record(task, list(store.config.get('labels') or []))
    return task


def resolve_key(key, *tasks):
    """Adopt a same-day key the corpus already carries. Returns the key to write.

    THE PROBLEM. A letterless key sorts BEFORE every lettered key of the same day
    (``2026-08-21`` < ``2026-08-21b``), which is the property the whole ordering relies
    on. It also means a task stamped ``created: 2026-08-21b`` refuses every DERIVED-key
    write for the rest of that calendar day. Observed 2026-08-21d on the cold-session
    demo, on the first write op a fresh session runs::

        $ python scripts/task.py comment P3 -m "..."
        task comment: REFUSED
          --session 2026-08-21 is earlier than P3's created 2026-08-21b. [...]

    -- and nothing in ``HANDOFF-stub.md`` tells a cold session that ``--session`` even
    exists, so the tool was unusable from the one entry point it is built for. The
    migration stamps ``created`` from each row's ``moved``, and lettered board keys are
    normal, so this is the common case and not an edge.

    WHY THIS IS NOT AUTO-LETTERING. It mints no letter and invents no ledger entry: it
    adopts a key the corpus ALREADY contains, which is the rule SPEC.md section 4 states
    for the exact-match case ("if a task already carries that exact key, do NOT auto-
    letter it -- just reuse it"). The trigger is narrow -- derived key only, same calendar
    day only (``task.created`` must start with the derived key), and the adopted value is
    the max over the tasks being written so a two-file atomic op stamps ONE key.

    An EXPLICIT ``--session`` is never rewritten. Silently promoting a key a human typed
    is worse than refusing it, so that path still hits ``stamp_and_render``'s refusal.
    """
    if getattr(key, 'explicit', False):
        return key
    adopted = key
    for task in tasks:
        created = task.created or ''
        if not SESSION_KEY.match(created):
            continue
        if created[:len(key)] == key and created > key:
            adopted = max(adopted, created, task.moved or created)
    return SessionKey(adopted)


def stamp_and_render(task, key, progress=True):
    """Every write op bumps ``updated``, a PROGRESS op also bumps ``moved``, and both
    re-render canonically. One code path, so a hand-edited file gets normalised the first
    time the tool touches it.

    ``progress`` is the mechanical half of the `moved`/`updated` split (see PROGRESS_OPS
    at the top of this file). It is decided by the OP, or by the calling TOOL via
    ``--mechanical`` -- never per item, and never by asking whether the edit felt
    substantial. A housekeeping pass that could choose is a housekeeping pass that will
    eventually choose "yes", and then `moved` means nothing and the staleness warning on
    `board` can no longer fire.

    Both stamps move FORWARD only within this function, but note the asymmetry: `moved`
    is left ALONE by an ack-class write rather than being reconciled, so a tree in which
    `updated` sorts before `moved` cannot be produced here at all. ``stamp_problems``
    checks for it anyway, because the file is also hand-editable.

    The guard is the other half of ``validate_record``'s bargain: a write op must never
    MANUFACTURE a state lint rejects. ``touch P10 --session 2026-01-05`` on a task
    created 2026-08-16 used to succeed (exit 0, ``P10 moved 2026-01-05``) and turn the
    very next ``lint`` red on the file it had just written -- the tool sabotaging its own
    gate. The key's SHAPE was validated in ``session_key``; its RELATION to ``created``
    was not, and lint check 4 checks both.

    ``resolve_key`` runs BEFORE this, at each op's load point, so the same-day reuse it
    performs is reflected in the Log heading and in the printed confirmation too. Doing
    it here instead was the first attempt and it wrote ``moved: 2026-08-21b`` under a
    ``### 2026-08-21`` log heading while printing ``P3 logged under 2026-08-21`` -- one
    write, three different opinions about which session it happened in.
    """
    if SESSION_KEY.match(task.created or '') and key < task.created:
        raise Refused('--session %s is earlier than %s\'s created %s. `moved` may never '
                      'sort before `created` (lint check 4), so this write would leave '
                      'the tree red the moment it succeeded. Pass a key on or after %s, '
                      'or omit --session for today. If %s is the value that is wrong, '
                      'that is a hand edit -- `created` is immutable here.'
                      % (key, task.id, task.created, task.created, task.created))
    if progress:
        task.fm['moved'] = key
    elif SESSION_KEY.match(task.moved or '') and key < task.moved:
        # An ack-class write with an EARLIER key would stamp `updated` behind `moved`,
        # which stamp_problems (and lint check 4) reject -- the same "write op must never
        # manufacture a state lint rejects" bargain as the created guard above.
        raise Refused('--session %s is earlier than %s\'s moved %s. This is an ack-class '
                      'write: it bumps `updated` and deliberately leaves `moved` alone, '
                      'so an earlier key would leave updated < moved, which lint check 4 '
                      'rejects.' % (key, task.id, task.moved))
    task.fm['updated'] = key
    return task.render()


def slugify(title):
    """Cosmetic only: it makes `ls` readable. Generated ONCE at `new` and never updated,
    because updating it would rename the file and make every id->path cache in a shell
    history wrong for no gain. The frontmatter id is truth."""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return (slug[:48].rstrip('-') or 'task')


def check_budget(open_tasks, budgets, changing):
    """Return a list of violation strings for the POST-CHANGE open set.

    ``changing`` maps id -> new pri. Only OVER-budget is a violation: a demotion that
    leaves zero NOW is legal here (you need it to be, to swap a NOW in two steps) and
    ``check_pri_budget`` in lint is what notices the board has no NOW.
    """
    counts = {}
    rows = {}
    for task in open_tasks:
        pri = changing.get(task.id, task.pri)
        counts[pri] = counts.get(pri, 0) + 1
        rows.setdefault(pri, []).append('%s (%s)' % (task.id, task.title[:40]))
    out = []
    for pri, cap in sorted(budgets.items()):
        got = counts.get(pri, 0)
        if got > cap:
            out.append('%s would have %d rows, budget %d: %s'
                       % (pri, got, cap, '; '.join(rows.get(pri, []))))
    return out


# --- Read ops -------------------------------------------------------------------------

def op_board(store, args):
    tasks = store.tasks()
    open_tasks = store.open_tasks()
    closed_ids = set(t.id for t in tasks if t.is_closed)
    stale = stale_threshold(store.config['stale_days'])
    ready = [t for t in open_tasks if is_ready(t, closed_ids)]
    counts = {}
    for t in open_tasks:
        counts[t.pri] = counts.get(t.pri, 0) + 1
    now = [t for t in open_tasks if t.pri == 'NOW']
    nxt = sorted([t for t in open_tasks if t.pri == 'NEXT'], key=sort_key)

    if args.json:
        emit_json({
            'now': [t.as_dict() for t in now],
            'next': [t.as_dict() for t in nxt],
            'ready_count': len(ready),
            'ready': [t.id for t in ready],
            'open_counts': counts,
            'stale_before': stale,
            'stale': [t.id for t in now + nxt if t.moved and t.moved < stale],
        })
        return 0

    emit('BOARD  %d open, %d closed  (generated %s -- do NOT commit this)'
         % (len(open_tasks), len(tasks) - len(open_tasks),
            datetime.date.today().isoformat()))
    emit()
    if not now:
        emit('NOW    (none) -- pick one: task.py promote <id> NOW')
    for t in now:
        emit('NOW    %-8s %s' % (t.id, t.title))
        emit('       size %s   moved %s%s'
             % (t.size or '?', t.moved or '-',
                '   STALE (not moved since %s)' % stale
                if t.moved and t.moved < stale else ''))
        summary = t.summary()
        if summary:
            for line in wrap(summary, 70):
                emit('       %s' % line)
        # The board is a SUMMARY of a file it deliberately does not print, so it has to
        # say where the rest is. It did not, and the stub that named `show` for it is a
        # different file a cold session may not have read.
        emit('       full item (traps, read-first, log): python %s show %s'
             % (prog(), t.id))
    emit()
    if nxt:
        emit('NEXT')
        for t in nxt:
            flag = ' STALE' if t.moved and t.moved < stale else ''
            emit('  %-8s %-2s %-46s %s%s'
                 % (t.id, t.size or '?', clip(t.title, 46), t.moved or '-', flag))
    else:
        emit('NEXT   (none)')
    emit()
    emit('ready  %d open task(s) have all deps closed  (python %s ready)'
         % (len(ready), prog()))
    emit('open   %s' % '  '.join('%s %d' % (p, counts.get(p, 0)) for p in PRI_VALUES))
    for i, line in enumerate(footer_lines(prog())):
        emit('%s%s' % ('next   ' if i == 0 else '       ', line))
    return 0


# The footer is the board's exit: the verbs a session reaches for after reading it. It is a
# DECLARED LIST rather than a format string because `ready` was missing from it while the
# board printed a ready COUNT three lines above -- the reader was told the number and not
# the verb, and the only ops on the footer were the three someone happened to type. As a
# list it can be asserted against: `test_board_footer_names_every_advertised_verb` requires
# every op the board's own body advertises to appear here, and every entry to be a real
# subcommand, so a fourth silent omission fails the suite instead of shipping.
NEXT_COMMANDS = ('show <id>', 'ready', 'list --pri LATER', 'lint')


def footer_lines(prog_name, width=78):
    """`NEXT_COMMANDS` as runnable, copy-pasteable commands, wrapped to `width`.

    Wrapped rather than truncated: four commands with a resolved `prog()` overflow one
    line, and a footer that runs off the edge is how the fourth verb goes unread a second
    time. `clip`'s reasoning, applied to the line that tells you what to do next.
    """
    out, cur = [], ''
    for cmd in NEXT_COMMANDS:
        piece = 'python %s %s' % (prog_name, cmd)
        candidate = piece if not cur else '%s   |   %s' % (cur, piece)
        if cur and len(candidate) + 7 > width:
            out.append(cur)
            cur = piece
        else:
            cur = candidate
    if cur:
        out.append(cur)
    return out


def clip(text, width):
    """Truncate to ``width``, MARKING that it happened.

    Same reasoning as ``ascii_safe`` folding rather than dropping: a silently
    truncated title is a lie about the title. "port the surviving handoff_lint
    checks onto th" reads as a whole title; the "..." says to run `show`.
    """
    if len(text) <= width:
        return text
    return text[:max(0, width - 3)] + '...'


def wrap(text, width, limit=4):
    """Word-wrap to ``limit`` lines, MARKING the cut -- same rule as ``clip`` above.

    It used to ``return out[:4]`` bare, and the board cut the live NOW row mid-sentence
    at "scouted 2026-08-21b into", eating the clause that said the scouting produced an
    executable design. A silently truncated summary is a lie about the summary in exactly
    the way ``clip``'s own docstring, eleven lines up, says a truncated title is; two
    truncation policies in one file meant the reasoning was written down and then applied
    to only one of them. The "..." is the signal to run `show`, which `op_board` names.
    """
    out = []
    line = ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    if line:
        out.append(line)
    if len(out) > limit:
        out = out[:limit]
        out[-1] = clip(out[-1] + ' ...', width)
    return out


def op_list(store, args):
    closed_ids = set(t.id for t in store.tasks() if t.is_closed)
    if args.all:
        rows = list(store.tasks())
    elif args.closed:
        rows = store.closed_tasks()
    else:
        rows = store.open_tasks()
    if args.pri:
        rows = [t for t in rows if t.pri == args.pri]
    if args.label:
        rows = [t for t in rows if args.label in t.labels]
    if args.parent:
        rows = [t for t in rows if t.parent == args.parent]
    rows.sort(key=sort_key)

    # Resolve the cap. `None` means "no --limit was typed", which is the only state that
    # reads differently on the two surfaces (LIST_LIMIT): the table gets the default, the
    # machine surface stays whole. A negative N is a typo for 0 and is treated as one
    # rather than silently slicing from the end, which is what a bare `rows[:-3]` would do.
    limit = getattr(args, 'limit', None)
    if limit is None:
        limit = 0 if args.json else LIST_LIMIT
    if limit < 0:
        limit = 0
    total = len(rows)
    shown = rows[:limit] if limit else rows

    if args.json:
        emit_json([t.as_dict() for t in shown])
        return 0

    def dep_cell(task):
        # A dep that is already CLOSED is annotated, not hidden: it is dead weight on the
        # row and the annotation is the only place a reader would ever notice.
        return ','.join('%s(closed)' % d if d in closed_ids else d
                        for d in task.deps) or '-'

    if not rows:
        emit('(no matching tasks)')
        return 0
    # Widths come from the rows actually PRINTED, not from the full filtered set: sizing a
    # table to a row the reader cannot see pads every column for nothing.
    widths = [max(2, max(len(t.id) for t in shown)),
              7, 4,
              min(48, max(5, max(len(t.title) for t in shown))),
              max(4, max(len(dep_cell(t)) for t in shown))]
    fmt = '%%-%ds  %%-%ds %%-%ds %%-%ds  %%-%ds  %%s' % tuple(widths)
    emit(fmt % ('id', 'pri', 'size', 'title', 'deps', 'moved'))
    for t in shown:
        # `-` not `?` for an ABSENT pri/size: `?` is a real member of the size enum
        # ("unsized"), so printing it for an empty field would show a value the file does
        # not contain. `list` is the only view that shows closed rows, where both fields
        # are legitimately empty (see check_enums).
        emit(fmt % (t.id, t.pri or '-', t.size or '-', clip(t.title, widths[3]),
                    dep_cell(t), t.moved or '-'))
    emit()
    if len(shown) < total:
        # Both numbers and the escape hatch, on the one line a reader is guaranteed to
        # reach. "20 task(s)" alone would be a true sentence that leaves a false
        # impression, which is the whole class of defect this repo tracks.
        emit('showing %d of %d task(s)  (--limit 0 for all, --limit N for N)'
             % (len(shown), total))
    else:
        emit('%d task(s)' % total)
    return 0


def op_show(store, args):
    task = store.need(args.id)
    # The two DERIVED facts the file itself cannot carry without rotting: the reverse of
    # `deps`, and the child list. Both are computed on every read precisely so that no
    # human ever has to maintain them (SPEC.md section 3.1, "no blocks field").
    blockers = sorted([t.id for t in store.open_tasks()
                       if args.id in t.deps and t.id != args.id])
    children = sorted([t.id for t in store.tasks() if t.parent == args.id])
    open_children = sorted([t.id for t in store.open_tasks() if t.parent == args.id])
    # INCOMING `related`. The field is one-directional on disk on purpose (no reciprocity
    # rule -- a hand-maintained inverse is the rot machine this format exists without), so
    # the inverse has to be computed on read or half of every link is invisible from the
    # end that did not write it. Closed tasks included: a link to an archived item is a
    # normal thing to want to follow, and `related` is navigation, not a query input.
    related_in = sorted([t.id for t in store.tasks()
                         if args.id in t.related and t.id != args.id])

    if args.json:
        d = task.as_dict()
        d['blocks_open'] = blockers
        d['children'] = children
        d['open_children'] = open_children
        d['related_in'] = related_in
        d['body'] = task.body
        emit_json(d)
        return 0

    emit('# %s  (%s)' % (rel(task.path), 'closed' if task.is_closed else 'open'))
    emit()
    sys.stdout.write(ascii_safe(task.render()))
    emit()
    emit('-- derived (computed on read, stored nowhere) --')
    emit('blocks (open tasks listing %s in deps): %s'
         % (task.id, ', '.join(blockers) or '(none)'))
    emit('related (incoming -- tasks listing %s in THEIR related): %s'
         % (task.id, ', '.join(related_in) or '(none)'))
    emit('children: %s' % (', '.join(children) or '(none)'))
    if children:
        emit('open children: %s' % (', '.join(open_children) or '(none) -- archive sweep'))
    return 0


def op_ready(store, args):
    closed_ids = set(t.id for t in store.tasks() if t.is_closed)
    rows = sorted([t for t in store.open_tasks() if is_ready(t, closed_ids)],
                  key=sort_key)
    if args.json:
        emit_json([t.as_dict() for t in rows])
        return 0
    if not rows:
        emit('(nothing ready: every open NOW/NEXT/LATER task has an open dep)')
        return 0
    for t in rows:
        emit('%-8s %-7s %-2s %s' % (t.id, t.pri, t.size or '?', t.title))
    emit()
    emit('%d ready (HOLD and SOMEDAY are excluded by definition)' % len(rows))
    return 0


def op_counts(store, args):
    """The ONE machine-checked home for "how big is this corpus".

    Added 2026-08-21 to kill a restated count, not to add a feature: this file's own
    docstring carried "83 task file(s)" against a live tree of 99, which is `ZT-P3-5`
    recurring inside the tool built to cure it. The repo's rule is that a live figure
    lives in exactly ONE machine-checked place and every other mention DERIVES it, so
    the number is now computed on demand and no prose anywhere restates it.

    It is also the bootstrap for `min_tasks_parsed`: `floor_now` is the value to paste
    into config.json, and it is printed rather than written because a floor that a tool
    can raise by itself is a floor that re-seals every time it is breached.
    """
    disk_open, disk_closed = disk_md_count(store.dir)
    tasks = store.tasks()
    ids = set(t.id for t in tasks)
    payload = {
        'open': len([t for t in tasks if not t.is_closed]),
        'closed': len([t for t in tasks if t.is_closed]),
        'total': len(tasks),
        'disk_open': disk_open,
        'disk_closed': disk_closed,
        'disk_total': disk_open + disk_closed,
        'distinct_ids': len(ids),
        'retired': len(store.retired_ids()),
        'floor_config': store.config.get('min_tasks_parsed'),
        'floor_now': disk_open + disk_closed,
    }
    if args.json:
        emit_json(payload)
        return 0
    emit('tasks   %d parsed (%d open, %d closed), %d distinct id(s), %d retired'
         % (payload['total'], payload['open'], payload['closed'],
            payload['distinct_ids'], payload['retired']))
    emit('disk    %d *.md (%d open, %d closed)'
         % (payload['disk_total'], disk_open, disk_closed))
    cfg = payload['floor_config']
    emit('floor   min_tasks_parsed=%s in config; measured now %d%s'
         % ('(unset)' if cfg is None else cfg, payload['floor_now'],
            '' if cfg == payload['floor_now'] else
            '  <- zero-headroom value to paste (raising a floor is a deliberate edit)'))
    return 0


# --- lint -----------------------------------------------------------------------------

def check_parses(store, fail, state):
    """Check 1: every *.md parses, has all fourteen keys, no unknown key."""
    for path, is_closed in store.md_paths():
        # SEEN counts what the scanner OFFERED, parsed counts what survived. The two are
        # different questions and check 10 asks the first one: a file that fails to parse
        # is already loud (right here), while a file the scanner never mentioned is
        # silent, and silence is the failure mode the instrument control exists for.
        state['seen'][1 if is_closed else 0] += 1
        try:
            task = load_task(path, is_closed)
        except ParseError as exc:
            fail('%s. Fix the frontmatter by hand -- the fourteen keys are fixed and '
                 'always present (SPEC.md section 3.1).' % exc)
            continue
        state['tasks'].append(task)
    state['parsed'] = len(state['tasks'])


def check_ids_unique(store, fail, state):
    """Check 2: ids unique across open+closed, and never both live and retired."""
    seen = {}
    for task in state['tasks']:
        if task.id in seen:
            fail('id %r is used by BOTH %s and %s. Ids are addresses and are never '
                 'reused; give one of them a fresh id from `task.py new`.'
                 % (task.id, rel(seen[task.id].path), rel(task.path)))
        seen[task.id] = task
        if not ID_OK.match(task.id or ''):
            fail('%s: id %r is not [A-Za-z0-9][A-Za-z0-9-]* . Legacy ids are allowed to '
                 'be ugly, not arbitrary.' % (rel(task.path), task.id))
    for retired in store.retired_ids():
        if retired in seen:
            fail('id %r is in retired-ids.txt AND live at %s. A retired id must never '
                 'come back; either delete the registry line deliberately or re-id the '
                 'file.' % (retired, rel(seen[retired].path)))


def check_filenames(store, fail, state):
    """Check 3: filename is <id>-<slug>.md."""
    for task in state['tasks']:
        name = os.path.basename(task.path)
        if not name.endswith('.md') or not name.startswith('%s-' % task.id):
            fail('%s does not start with %r. The filename is cosmetic, but a filename '
                 'that disagrees with the id makes `ls` lie; rename the file (the id '
                 'stays put).' % (rel(task.path), '%s-' % task.id))


def check_enums(store, fail, state):
    """Check 4: pri/size enums, well-formed session keys, created <= moved <= updated,
    and a well-formed `source`.

    `pri` and `size` may be EMPTY on a CLOSED record, and are still mandatory on an open
    one. A rank is a claim about what a session should pick up next; a closed record is
    not competing for that, so demanding one forces a value to be invented -- and the
    migration duly invented `pri: LATER` on every archive record nobody had ever ranked,
    which made `list --closed --pri LATER` answer a question entirely with fabrications
    (count them with `task.py counts`; no number is restated here on purpose).
    An empty value is the format's own way of saying "absent" (SPEC.md section 3.1), so
    this is the enum admitting a fact rather than the enum being weakened: a NON-empty
    value is still checked against the enum in both folders, and an open row with either
    field blank is still a violation.
    """
    for task in state['tasks']:
        where = rel(task.path)
        optional = task.is_closed
        if task.pri or not optional:
            if task.pri not in PRI_VALUES:
                fail('%s: pri %r is not one of %s%s.'
                     % (where, task.pri, list(PRI_VALUES),
                        ' (it may be empty only under closed/)' if not task.pri else ''))
        if task.size or not optional:
            if task.size not in SIZE_VALUES:
                fail('%s: size %r is not one of %s (use "?" when unsized%s).'
                     % (where, task.size, list(SIZE_VALUES),
                        ', or empty under closed/' if not task.size else ''))
        for problem in stamp_problems(task):
            fail('%s: %s. One of the stamps was typed by hand; fix the wrong one.'
                 % (where, problem))
        bad_source = source_problem(task.source)
        if bad_source:
            fail('%s: %s' % (where, bad_source))
        bad_hash = source_hash_problem(task.source_hash, task.source)
        if bad_hash:
            fail('%s: %s' % (where, bad_hash))


def check_pri_budget(store, fail, state):
    """Check 5: exactly one NOW and at most three NEXT among OPEN tasks.

    Exactly-one rather than at-most-one: NOW is what an unassigned session picks up, and
    zero of them is the same non-answer as two.

    ONE message covers both sides of that "!=", because the check is one check. The old
    text was the ``> 1`` branch's ("two of them is no ranking at all") printed verbatim
    on a count of ZERO, next to a bare ``-`` where the id list goes -- a FAIL that
    described a situation the tree was not in, in the output a session pastes as
    evidence. Observed 2026-08-21::

        FAIL: found 0 open NOW row(s) -, must be exactly 1. NOW is what an unassigned
        session picks up; two of them is no ranking at all.
    """
    budgets = store.config['budgets']
    open_tasks = [t for t in state['tasks'] if not t.is_closed]
    now = [t.id for t in open_tasks if t.pri == 'NOW']
    nxt = [t.id for t in open_tasks if t.pri == 'NEXT']
    if len(now) != budgets.get('NOW', 1):
        fail('found %d open NOW row(s) (%s), must be exactly %d. NOW is the one row an '
             'unassigned session picks up: with none it has no answer, with more than '
             'one it has no ranking. Set the count with `task.py promote <id> NOW '
             '--demote <id2> <pri2>`.'
             % (len(now), ', '.join(now) if now else 'none',
                budgets.get('NOW', 1)))
    if len(nxt) > budgets.get('NEXT', 3):
        fail('found %d open NEXT row(s) %s, cap is %d. Demote one to LATER -- the cap is '
             'the mechanism that forces the ranking argument to happen once, at write '
             'time.' % (len(nxt), nxt, budgets.get('NEXT', 3)))


def check_deps(store, fail, state):
    """Check 6: every dep AND every `related` id resolves; the deps graph is acyclic.

    `related` rides in this check rather than in one of its own, and it is checked LESS
    than `deps` on purpose:

    * every id resolves -- a navigation link that goes nowhere is worse than no link,
      because the reader spends the lookup before finding out;
    * self-reference refused -- it renders as a link back to the page you are on;
    * **NO cycle check.** `related` is symmetric-ish and UNORDERED, so "acyclic" is not a
      property it could have. `A related B` plus `B related A` is the NORMAL state, and a
      cycle check would call the normal state a violation. `deps` gets one because a dep
      cycle means nothing in it can ever be ready -- a real consequence, in a real query.
      There is no query `related` could break.

    Not checked either: reciprocity. A one-way `related` is fine; making the tool enforce
    the inverse would be the hand-maintained `blocks` field this format exists without.
    """
    known = dict((t.id, t) for t in state['tasks'])
    edges = dict((t.id, t.deps) for t in state['tasks'])
    for task in state['tasks']:
        for other in task.related:
            if other == task.id:
                fail('%s: related lists %s itself. Remove it with `task.py set %s '
                     'related "..."` -- a self-link renders as a pointer to the page you '
                     'are already on.' % (rel(task.path), task.id, task.id))
            elif other not in known:
                fail('%s: related id %r resolves to no task (open or closed). `related` '
                     'is navigation: a link that goes nowhere costs the reader the lookup '
                     'before it tells them anything.' % (rel(task.path), other))
        for dep in task.deps:
            if dep not in known:
                fail('%s: dep %r resolves to no task (open or closed). If it is retired, '
                     'drop it with `task.py dep rm %s %s`; a dep that resolves to nothing '
                     'blocks forever.' % (rel(task.path), dep, task.id, dep))
        cycle = find_cycle(edges, task.id)
        if cycle:
            fail('%s: dependency cycle %s. Nothing in the cycle can ever be ready.'
                 % (rel(task.path), ' -> '.join(cycle)))


def check_parents(store, fail, state):
    """Check 7: parent resolves, the parent graph is acyclic, and no closed parent has
    open children (that last one is the archive sweep, computed instead of remembered)."""
    known = dict((t.id, t) for t in state['tasks'])
    edges = dict((t.id, [t.parent] if t.parent else []) for t in state['tasks'])
    for task in state['tasks']:
        if task.parent and task.parent not in known:
            fail('%s: parent %r resolves to no task. Clear it with `task.py set %s parent '
                 '""` or create the parent.' % (rel(task.path), task.parent, task.id))
        cycle = find_cycle(edges, task.id)
        if cycle:
            fail('%s: parent cycle %s. Containment must be a tree.'
                 % (rel(task.path), ' -> '.join(cycle)))
    for task in state['tasks']:
        if not task.is_closed:
            continue
        open_kids = sorted([t.id for t in state['tasks']
                            if t.parent == task.id and not t.is_closed])
        if open_kids:
            fail('%s is CLOSED but still has open children %s. Either reopen it or close '
                 'the children -- a closed parent is what tells the next session the '
                 'group is done.' % (rel(task.path), open_kids))


MAX_PARENT_DEPTH = 2


def check_parent_depth(store, fail, state):
    """Check 11: parent chains deeper than MAX_PARENT_DEPTH levels. **WARNS, never fails.**

    Why it exists: two levels covers every real grouping this corpus has (`R6` over its
    19 children is the deepest thing anybody has needed), and each extra level costs the
    reader on every session -- and, worse, forces a housekeeper to make a JUDGEMENT CALL
    about where a new task attaches, which is the one thing the housekeeping loop is
    supposed to be free of.

    Why it is a WARNING and not a violation, which is the load-bearing half: a third level
    is not WRONG, it is unusual. A hard fail here would mean a session that legitimately
    needs one either fights the gate or -- far more likely, and this is the failure this
    check is shaped around -- flattens the tree to get green and loses the grouping. Growth
    should be VISIBLE, not prohibited. The warning is printed on a clean run and carried in
    `--json`, and the exit code stays 0.

    ``fail`` is deliberately not called. If a future session decides depth must be fatal,
    that is a one-word edit here plus a sabotage record -- not a flag, because a warning
    that can be promoted to fatal by a flag is a warning nobody promotes.

    ONE LINE PER DISTINCT FACT, not per affected task (2026-08-21e). See the comment in
    the loop: a warning that repeats itself 37 times for one edit is a warning the reader
    learns to scroll past, which costs exactly as much as not printing it.
    """
    parent_of = dict((t.id, t.parent) for t in state['tasks'])
    groups = {}
    order = []
    for task in sorted(state['tasks'], key=lambda t: t.id):
        chain = [task.id]
        seen = set(chain)
        cur = parent_of.get(task.id, '')
        while cur and cur in parent_of and cur not in seen:
            chain.append(cur)
            seen.add(cur)
            cur = parent_of.get(cur, '')
        if len(chain) > MAX_PARENT_DEPTH:
            # ONE LINE PER DISTINCT FACT (added 2026-08-21e, PROOF4.md section 6 bug C).
            # A single re-parent of `R6` onto `TK52` emitted 37 identical WARN lines --
            # one per descendant, every one naming the same cause and the same fix -- and
            # a reader who has to work out that 37 lines are one fact is a reader who
            # stops reading the warnings. The group key is the ANCESTOR chain, so tasks
            # that are deep for the SAME reason collapse into one line and tasks that are
            # deep for different reasons stay on their own: `X -> R6 -> TK52` and
            # `Y -> R6 -> TK52` are one fact, `Z -> Q -> W` is another.
            key = tuple(chain[1:])
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append((task, chain))
    for key in order:
        members = groups[key]
        task, chain = members[0]
        extra = ''
        if len(members) > 1:
            others = [t.id for t, _ in members[1:]]
            shown = ', '.join(others[:6])
            if len(others) > 6:
                shown += ', ... (+%d more)' % (len(others) - 6)
            extra = (' SAME FACT, %d more task(s) hanging off %s at this depth: %s -- '
                     're-parenting %s fixes all %d at once.'
                     % (len(others), key[0], shown, key[0], len(members)))
        state['warnings'].append(
            '%s: parent chain is %d levels deep (%s), over the %d this corpus is '
            'shaped for. Not an error -- deep is allowed, it is just expensive to '
            'read and it makes "where does this attach?" a judgement call. Consider '
            're-parenting onto %s.%s'
            % (rel(task.path), len(chain), ' -> '.join(chain), MAX_PARENT_DEPTH,
               chain[-1], extra))


def check_closed_field(store, fail, state):
    """Check 8: `closed` is non-empty IFF the file lives under closed/.

    This is the one deliberate redundancy in the format (the folder says WHETHER, the
    field says WHEN), so it is also the one place the two can disagree.
    """
    for task in state['tasks']:
        value = task.closed
        if task.is_closed and not value:
            fail('%s is under closed/ but its `closed` field is empty. Re-close it with '
                 '`task.py close %s -m ...` so the date is recorded.'
                 % (rel(task.path), task.id))
        if not task.is_closed and value:
            fail('%s carries closed: %s but sits in the OPEN folder. The folder is the '
                 'truth about status; clear the field or move the file.'
                 % (rel(task.path), value))
        if value and not SESSION_KEY.match(value):
            fail('%s: closed is %r, not a session key.' % (rel(task.path), value))


def check_labels(store, fail, state):
    """Check 9: every label is in the config's CLOSED vocabulary.

    An open vocabulary yields formal / Formal / lean / proofs within a month and then no
    label query is trustworthy. Adding a label is a deliberate edit to config.json.
    """
    vocab = list(store.config.get('labels') or [])
    for task in state['tasks']:
        for label in task.labels:
            if label not in vocab:
                fail('%s: label %r is not in the declared vocabulary %s. Add it to '
                     'tasks/config.json deliberately, or use an existing one.'
                     % (rel(task.path), label, vocab))


def disk_md_count(tasks_dir):
    """(open, closed) *.md counts, walked INDEPENDENTLY of ``Store.md_paths``.

    Deliberately duplicated logic, which is otherwise against the house style. The whole
    value of a control is that it does not share a failure with its subject: if this
    called ``md_paths`` it would agree with a blind scanner by construction, which is the
    "counted reports without checking which theorems" defect from the repo's own axiom
    audit. Two edits are now needed to fool check 10 instead of one -- and two edits is
    no longer the narrowest plausible weakening, it is a decision.
    """
    out = []
    for d in (tasks_dir, os.path.join(tasks_dir, 'closed')):
        n = 0
        if os.path.isdir(d):
            for name in os.listdir(d):
                if name.endswith('.md') and os.path.isfile(os.path.join(d, name)):
                    n += 1
        out.append(n)
    return tuple(out)


def check_min_parsed(store, fail, state):
    """Check 10, THE INSTRUMENT CONTROL, and non-negotiable.

    A lint whose parser has gone blind passes forever, reporting clean on exactly the
    corpus it exists to police. That is this project's house failure mode, and it is the
    same defect ``scripts/handoff_lint.py::check_doc_links`` guards with ``MIN_DOC_LINKS``
    and ``check_ledger_row_ids`` guards with its ``len(known) < 5``.

    TWO independent assertions, because a floor alone is not enough:

    (a) THE FLOOR, ``min_tasks_parsed``, set to the live TOTAL with ZERO headroom, the
        way ``MIN_CONF_ALL`` / ``MIN_TESTS_ALL`` are set in ``formal/verify.sh``. It
        shipped at SPEC.md's example value of 5 against 99 files, i.e. with 94 files of
        headroom: ``rm -rf tasks/closed`` deleted 57 files -- 58% of the corpus, the
        majority -- and the run still printed ``task lint: clean (10 checks, 42 task
        file(s) parsed)``, exit 0. A floor above nothing guards nothing.

        A RAW TOTAL, not an open/closed pair, and the reason is monotonicity. Total is
        the only quantity here that cannot legitimately fall: files are never deleted and
        ``close`` is a MOVE. Open falls on every ``close`` and closed falls on every
        ``reopen``, so a zero-headroom floor on either half would go red on correct use
        of the tool -- and a check that reddens on correct use is a check that gets
        lowered. Adding tasks is free; lowering this is a deliberate, reviewed edit.

        THE VALUE IS VALIDATED, not merely read (added 2026-08-21, PROOF2.md section 2).
        It was ``int(...)``, so ``min_tasks_parsed: 0`` -- literally "a check that passes
        forever" three paragraphs up -- printed ``clean``, and so did ``-5`` and the
        string ``"99"``. One config value could switch the instrument control off with
        nothing going red; the sibling ``handoff_lint_new.py::_min_known_ids`` already
        refused all three, so the tree was saved only by the coupling this tool set out
        to remove. A non-int, a bool, or anything ``< 1`` is now a violation naming the
        config path and the value. Observed before the fix, on the live 99-file corpus::

            min_tasks_parsed=0    -> task lint: clean (10 checks, 99 ...)  TRUE rc=0
            min_tasks_parsed='99' -> task lint: clean (10 checks, 99 ...)  TRUE rc=0

        and after (``test_task.py::test_a_disabled_floor_is_refused``, plus the
        ``disabled floor`` sabotage case)::

            FAIL: <t>/tasks/config.json has min_tasks_parsed = 0; expected a positive
            integer. A value of 0 or less is not a LOWERED floor, it is a DISABLED one

        NOT a lower bound on the number itself: ``1`` is green, because a floor of 1 is a
        lowering (reviewed, provenance-carrying) and this check does not get to decide how
        big the corpus should be. It decides only that a floor EXISTS and can fire.

    (b) THE RECOUNT, which is what makes (a) survive growth. A total floor slowly
        re-accumulates headroom as tasks are filed: at 156 files a floor of 99 would once
        again let the whole ``closed/`` directory vanish unnoticed. So the count the
        scanner OFFERED is compared against an independent walk of the same two
        directories (``disk_md_count``), per directory, and any disagreement is a
        violation naming the directory. That assertion is growth-invariant: it is true of
        every corpus, at every size, forever, and it names WHICH half went dark.

    Neither half is a coverage ratchet and neither is a substitute for the other: (a)
    catches a corpus that shrank or a ``--dir`` pointed at the wrong tree, (b) catches a
    scanner that stopped looking. Never delete either, and never lower the floor to make
    a run green -- fix the scanner.
    """
    if 'min_tasks_parsed' not in store.config:
        fail('tasks/config.json declares no `min_tasks_parsed` floor, so this lint '
             'cannot tell "the corpus is intact" from "the parser went blind". There is '
             'no default worth having (a guessed floor is a floor with headroom). Run '
             '`task.py counts` and paste the measured value.')
    else:
        floor = store.config['min_tasks_parsed']
        if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
            fail('%s has min_tasks_parsed = %r; expected a positive integer. A value of '
                 '0 or less is not a LOWERED floor, it is a DISABLED one -- the exact '
                 '"check that passes forever" this control exists to prevent -- and a '
                 'non-integer (a quoted "99", null, true) is a floor whose comparison is '
                 'an accident. Run `task.py counts` and paste the measured value; '
                 'lowering it is a deliberate, reviewed edit, disabling it is not an '
                 'edit anyone gets to make silently.'
                 % (rel(os.path.join(store.dir, 'config.json')), floor))
        elif state['parsed'] < floor:
            fail('parsed only %d task file(s), floor min_tasks_parsed=%d. Either the '
                 'tasks directory is nearly empty or the parser has gone blind -- and a '
                 'lint that parses nothing passes forever. Fix the parser rather than '
                 'lowering the floor.' % (state['parsed'], floor))
    seen_open, seen_closed = state['seen']
    disk_open, disk_closed = disk_md_count(store.dir)
    for label, folder, seen, disk in (('open', rel(store.dir), seen_open, disk_open),
                                      ('closed', rel(store.closed_dir),
                                       seen_closed, disk_closed)):
        if seen != disk:
            fail('the scan offered %d %s task file(s) but %s holds %d *.md on disk. The '
                 'scanner is not seeing the corpus (this is the control, not a data '
                 'problem): fix `Store.md_paths` rather than the count.'
                 % (seen, label, folder, disk))


LINT_CHECKS = (
    check_parses,
    check_ids_unique,
    check_filenames,
    check_enums,
    check_pri_budget,
    check_deps,
    check_parents,
    check_closed_field,
    check_labels,
    check_min_parsed,
    # APPENDED, not inserted next to check_parents where it thematically belongs. The
    # checks are cited by NUMBER in this file, in SPEC.md, in the config's _provenance and
    # in the sabotage records ("lint check 7 rejects", "the same defect check 10 guards"),
    # so inserting at position 8 would silently re-point every one of those citations at a
    # different check. Position is cheap; a citation that quietly means something else is
    # the rot this corpus exists to delete.
    check_parent_depth,
)


def op_lint(store, args):
    failures = []
    state = {'tasks': [], 'parsed': 0, 'seen': [0, 0], 'warnings': []}
    for check in LINT_CHECKS:
        check(store, failures.append, state)
    warnings = state['warnings']
    if args.json:
        emit_json({'violations': failures,
                   'warnings': warnings,
                   'checks': len(LINT_CHECKS),
                   'parsed': state['parsed'],
                   'clean': not failures})
        return 1 if failures else 0
    # WARNINGS PRINT ON EVERY RUN, red or green, and never touch the exit code. A warning
    # suppressed when there are violations is a warning discovered on the second run,
    # after the thing it warned about has already been built on.
    for w in warnings:
        emit_err('  WARN: %s' % w)
    if failures:
        # One violation per LINE. `emit_err` already terminates the line, and the
        # extra '\n' this carried put a blank line between every FAIL -- which makes
        # the output unpasteable as evidence, and evidence is what a sabotage record
        # is made of.
        emit_err('task lint: %d violation(s)\n' % len(failures))
        for f in failures:
            emit_err('  FAIL: %s' % f)
        return 1
    emit('task lint: clean (%d checks, %d task file(s) parsed)%s'
         % (len(LINT_CHECKS), state['parsed'],
            '' if not warnings else ', %d warning(s)' % len(warnings)))
    return 0


# --- Write ops ------------------------------------------------------------------------

def op_new(store, args):
    key = session_key(args.session)
    title = clean_title(args.title)
    pri = args.pri or 'LATER'
    if pri not in PRI_VALUES:
        raise Refused('pri %r is not one of %s' % (pri, list(PRI_VALUES)))
    size = args.size or '?'
    if size not in SIZE_VALUES:
        raise Refused('size %r is not one of %s' % (size, list(SIZE_VALUES)))
    deps = split_list(args.deps)
    labels = split_list(args.labels)
    related = split_list(args.related)
    # `source` defaults to `hand` because the default CALLER is a human typing `new`. A
    # tool that files on someone else's behalf -- `sync --create-new`, `file_backlog.py`
    # -- passes the real provenance, and that is the whole reason the field is set here
    # and never again: provenance is a fact about the moment of creation, and a field a
    # later op could rewrite is a field that will eventually disagree with the Log.
    # `is None` and NOT `or`: an explicitly EMPTY --source is a caller who meant to pass
    # provenance and passed nothing (a shell variable that did not expand is the usual
    # way), and silently filing it as `hand` is the most damaging default available --
    # sync reads this field to decide whether a task it cannot find in any source is a
    # hand-filed backlog item (expected, silent) or a board row that vanished (reported).
    # Observed while writing the test: `new --source ''` was accepted and stored `hand`.
    source = 'hand' if args.source is None else args.source.strip()
    bad_source = source_problem(source)
    if bad_source:
        raise Refused(bad_source)
    known = store.by_id()
    for dep in deps:
        if dep not in known:
            raise Refused('dep %r resolves to no task' % dep)
    for other in related:
        if other not in known:
            raise Refused('related id %r resolves to no task' % other)
    vocab = list(store.config.get('labels') or [])
    for label in labels:
        if label not in vocab:
            raise Refused('label %r is not in the declared vocabulary %s (tasks/config.json)'
                          % (label, vocab))
    if args.parent:
        if args.parent not in known:
            raise Refused('parent %r resolves to no task' % args.parent)
        # A NEW task is always open, so the closed-parent rule applies here too --
        # otherwise `new --parent <closed-id>` is a second door into the state `set` and
        # `close` both refuse.
        check_parent_open(known[args.parent], '(the new task)', False)

    violations = check_budget(store.open_tasks() + [_ghost(pri)],
                              store.config['budgets'], {})
    if violations:
        raise Refused('creating a %s row would break the budget:\n  %s\nCreate it as '
                      'LATER and promote with --demote, so the ranking argument happens '
                      'once.' % (pri, '\n  '.join(violations)))

    # `source_hash` and `body_text` have NO command-line flags, and that is deliberate.
    # `sync --create-new` builds this Namespace itself and sets them; a human typing `new`
    # has no digest to pass (it is a fact about a reconciliation, not about the task), so
    # a flag for it could only ever be a way to claim a reconciliation that did not
    # happen -- and a claimed reconciliation is exactly the state that makes sync silent
    # forever. Same shape as `--mechanical`'s "for a tool, not a person", one step
    # further: not offered at all rather than offered and documented as off-limits.
    source_hash = (getattr(args, 'source_hash', None) or '').strip()
    bad_hash = source_hash_problem(source_hash, source)
    if bad_hash:
        raise Refused(bad_hash)

    # THE ID COMES FROM THE SOURCE WHEN THE SOURCE HAS ONE. A board row is already
    # addressed -- `P3` is `P3` in the ledger, in `formal/HANDOFF.md`, and in every
    # citation ever written -- so minting `TK52` for a row that says `TK99` would file a
    # task that answers to a name nobody uses and leave the row looking unfiled forever
    # (observed while writing sync_accept.py case B: the mint succeeded, and the very next
    # `sync --check` reported the row as NEW *and* the fresh task as CORPUS-ONLY).
    # `next_id` still owns allocation for everything a human types.
    given = (getattr(args, 'task_id', None) or '').strip()
    if given:
        if not ID_OK.match(given):
            raise Refused('id %r does not match %s' % (given, ID_OK.pattern))
        if given in known:
            raise Refused('id %r already exists' % given)
        if given in store.retired_ids():
            raise Refused('id %r is in retired-ids.txt. Ids are never reused: a source '
                          'row carrying a retired id is a board mistake, and filing it '
                          'would merge two items\' histories under one address.' % given)
    new_id = given or store.next_id()
    body = BODY_SKELETON
    if getattr(args, 'body_text', None):
        body = args.body_text
    elif args.body:
        body = read_text(args.body)
    if body is not BODY_SKELETON and LOG_HEADING not in body:
        body = body.rstrip('\n') + '\n\n' + LOG_HEADING + '\n'
    fm = {'id': new_id, 'title': title, 'pri': pri, 'size': size, 'deps': deps,
          'related': related, 'parent': args.parent or '', 'labels': labels,
          'source': source, 'source_hash': source_hash,
          'created': key, 'moved': key, 'updated': key, 'closed': ''}
    path = os.path.join(store.dir, '%s-%s.md' % (new_id, slugify(title)))
    if os.path.exists(path):
        raise Refused('%s already exists' % rel(path))
    write_text(path, render_file(fm, body))
    emit('%s  %s' % (new_id, rel(path)))
    return 0


def _ghost(pri, task_id='<new>', title='(the new task)'):
    """A stand-in open row for a budget check on a task that does not exist YET.

    The defaults describe ``new``'s case, and ``reopen`` used to inherit them: reopening
    a stored-``NOW`` row into a full board refused correctly but reported the blocked row
    as ``<new> ((the new task))`` (observed 2026-08-21), i.e. named a task the caller had
    not asked for and omitted the one they had. ``reopen`` passes the real id and title.
    """
    return Task(task_id, {'id': task_id, 'pri': pri, 'title': title}, '', False)


def check_parent_open(parent, child_id, child_is_closed):
    """Refuse an OPEN child under a CLOSED parent -- the state lint check 7 rejects.

    ``close`` already refuses to create this state without ``--force`` (it names the open
    children), but the same state could be reached from the other end: ``set P10 parent
    P1`` with ``P1`` under ``closed/`` succeeded, and the next ``lint`` reported "P1-...
    is CLOSED but still has open children ['P10']" (observed 2026-08-21). Two write ops
    disagreeing about one invariant is worse than either being wrong alone, because
    whichever one you learn first teaches you the wrong rule.

    A closed child under a closed parent is fine -- that is just an archived group.
    """
    if parent.is_closed and not child_is_closed:
        raise Refused('parent %s is CLOSED and %s is open, which is exactly the '
                      'closed-parent-with-open-children state lint check 7 rejects and '
                      '`close` refuses to create without --force. Reopen %s first '
                      '(`task.py reopen %s -m ...`), or pick an open parent.'
                      % (parent.id, child_id, parent.id, parent.id))


def split_list(raw):
    if not raw:
        return []
    return [p.strip() for p in raw.split(',') if p.strip()]


def clean_title(raw):
    """Validate a title down to something the ONE-LINE frontmatter subset can hold.

    The length cap is not the dangerous part; the newline is. ``new`` used to accept
    a pasted two-line title and write a frontmatter block whose second line is not
    ``key: value``, which does not merely corrupt that one file -- every later op
    scans the tree, so the whole store became unusable, including ``new`` itself
    (observed 2026-08-21: ``T4-line-one-line-two.md:4: not "key: value" -- 'line
    two'`` from ``show``, ``lint`` AND ``new``). A refusal at the seam is the only
    place this is cheap.
    """
    title = (raw or '').strip()
    if not title:
        raise Refused('a task needs a title')
    if '\n' in title or '\r' in title:
        raise Refused('a title must be ONE line: the frontmatter subset is one '
                      '"key: value" per line, and a newline here writes a file that '
                      'no later op -- including `new` -- can parse. Put the detail in '
                      'the body (--body FILE) or in a `comment`.')
    if len(title) > 100:
        raise Refused('title is %d chars, cap 100. The title prints in `board` and '
                      '`list`; put the detail in the body.' % len(title))
    return title


SETTABLE = ('title', 'size', 'labels', 'related', 'parent')

# `source` is absent from SETTABLE and that is the ENTIRE immutability mechanism: there is
# no op that writes it after `new`. Named here so the refusal can say WHY rather than
# printing a bare list, because "not settable" reads like an oversight and this is a
# decision -- provenance that a later op can rewrite is provenance that will eventually
# disagree with the Log entry underneath it.
IMMUTABLE = {
    'id': 'the address; a task that changes id breaks every inbound citation',
    'created': 'a measurement of when the task was filed',
    'source': 'where the task CAME FROM -- a fact about creation, fixed at `new`. If it '
              'is wrong, that is a hand edit plus a Log entry saying so, not an op',
    'moved': 'derived from the write path: it bumps when a session makes progress',
    'updated': 'derived from the write path: it bumps on every write',
    'source_hash': 'the reconciliation watermark -- what the source block hashed to when '
                   '`sync --create-new` filed this task or `ack` last acknowledged it. '
                   'Setting it by hand is claiming a reconciliation that did not happen, '
                   'which is the one thing that would make sync report nothing forever',
}


def progress(args):
    """False when ``--mechanical`` was passed: bump `updated`, leave `moved` alone.

    THE FLAG IS FOR A TOOL, NOT FOR A PERSON. `sync` will pass it on every field fix it
    applies, unconditionally, the same way it emits every command unconditionally; a human
    running `set`/`promote`/`dep` by hand IS the session doing the work and simply never
    types it. That is what keeps SPEC.md section 3.1's per-op rule mechanical: the caller
    is decided once, at the call site, not per item by a model asking itself whether this
    particular edit counts as progress.

    Nothing here can VERIFY that a tool passed it honestly, and pretending otherwise would
    be worse than saying so: an automation that omits the flag launders `moved` exactly as
    if the flag did not exist. What the flag buys is that the honest automation has a way
    to be honest, and that `ack` -- the op with no other purpose -- cannot be anything but.
    """
    return not getattr(args, 'mechanical', False)


def op_set(store, args):
    key = session_key(args.session)
    if args.field not in SETTABLE:
        why = IMMUTABLE.get(args.field)
        raise Refused('%r is not settable here. Settable: %s. %s`pri` is `promote`, '
                      '`deps` is `dep add|rm`, and `closed` is `close`/`reopen` -- each '
                      'of those has a rule that a plain assignment would skip.'
                      % (args.field, list(SETTABLE),
                         '`%s` is IMMUTABLE: %s. ' % (args.field, why) if why else
                         '`id`/`created`/`source`/`moved`/`updated` are immutable, '))
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    value = args.value
    if args.field == 'title':
        value = clean_title(value)
        task.fm['title'] = value
    elif args.field == 'size':
        if value not in SIZE_VALUES:
            raise Refused('size %r is not one of %s' % (value, list(SIZE_VALUES)))
        task.fm['size'] = value
    elif args.field == 'labels':
        labels = split_list(value)
        vocab = list(store.config.get('labels') or [])
        for label in labels:
            if label not in vocab:
                raise Refused('label %r is not in the declared vocabulary %s. The '
                              'vocabulary is closed on purpose: an open one yields '
                              'formal/Formal/lean/proofs within a month.' % (label, vocab))
        task.fm['labels'] = labels
    elif args.field == 'related':
        # Whole-list assignment, not add/rm, and NOT because add/rm would be hard. `deps`
        # earns two verbs because each edge has to pass a cycle check that depends on the
        # rest of the graph; `related` has no such rule, so one verb is the whole surface.
        related = split_list(value)
        seen = set()
        for other in related:
            if other == task.id:
                raise Refused('a task cannot be related to itself')
            if other in seen:
                raise Refused('related lists %r twice; the list is a SET, unordered and '
                              'non-semantic, so a repeat carries no extra meaning' % other)
            seen.add(other)
            if store.resolve(other) is None:
                raise Refused('related id %r resolves to no task (open or closed). Ids '
                              'are never reused, so this is a typo or an invented id.'
                              % other)
        task.fm['related'] = related
    else:
        value = value.strip()
        if value:
            if value == task.id:
                raise Refused('a task cannot be its own parent')
            target = store.resolve(value)
            if target is None:
                raise Refused('parent %r resolves to no task' % value)
            check_parent_open(target, task.id, task.is_closed)
            edges = parent_edges(store, {task.id: [value]})
            cycle = find_cycle(edges, task.id)
            if cycle:
                raise Refused('that parent would create the cycle %s' % ' -> '.join(cycle))
        task.fm['parent'] = value
    write_text(task.path, stamp_and_render(task, key, progress(args)))
    emit('%s %s = %s  (%s %s)' % (task.id, args.field, args.value or '(empty)',
                                  'moved' if progress(args) else 'updated only', key))
    return 0


def op_promote(store, args):
    key = session_key(args.session)
    if args.pri not in PRI_VALUES:
        raise Refused('pri %r is not one of %s' % (args.pri, list(PRI_VALUES)))
    task = need_writable(store, args.id)
    if task.is_closed:
        raise Refused('%s is closed; reopen it first' % task.id)
    changing = {task.id: args.pri}
    edits = [(task, args.pri)]
    if args.demote:
        other_id, other_pri = args.demote
        if other_pri not in PRI_VALUES:
            raise Refused('pri %r is not one of %s' % (other_pri, list(PRI_VALUES)))
        other = need_writable(store, other_id)
        if other.is_closed:
            raise Refused('%s is closed; it cannot be demoted' % other.id)
        if other.id == task.id:
            raise Refused('--demote names the same task as the promotion')
        changing[other.id] = other_pri
        edits.append((other, other_pri))

    key = resolve_key(key, *[edited for edited, _ in edits])

    violations = check_budget(store.open_tasks(), store.config['budgets'], changing)
    if violations:
        raise Refused('refusing: the result would break the priority budget.\n  %s\n'
                      'Pass --demote <id> <pri> to make room in the same atomic write. '
                      'The cap is the mechanism that forces the ranking argument to '
                      'happen once, at write time, instead of every session re-deriving '
                      'it.' % '\n  '.join(violations))

    # Render and validate BOTH files before writing EITHER: a refusal must never land
    # half a swap. This is not a transaction (see the docstring's honest limits) -- it
    # closes the realistic failure, not a crash between two write() calls.
    pending = []
    for edited, new_pri in edits:
        edited.fm['pri'] = new_pri
        pending.append((edited.path, stamp_and_render(edited, key, progress(args))))
    for path, text in pending:
        write_text(path, text)
    for edited, new_pri in edits:
        emit('%-8s -> %s' % (edited.id, new_pri))
    return 0


def op_dep(store, args):
    key = session_key(args.session)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    dep = args.dep
    if args.action == 'add':
        if dep == task.id:
            raise Refused('a task cannot depend on itself')
        if store.resolve(dep) is None:
            raise Refused('dep %r resolves to no task (open or closed). Ids are never '
                          'reused, so this is a typo or an invented id.' % dep)
        if dep in task.deps:
            raise Refused('%s already depends on %s' % (task.id, dep))
        edges = dep_edges(store, {task.id: task.deps + [dep]})
        cycle = find_cycle(edges, task.id)
        if cycle:
            raise Refused('that dep would create the cycle %s. Nothing in a dep cycle '
                          'can ever be ready.' % ' -> '.join(cycle))
        task.fm['deps'] = task.deps + [dep]
    else:
        if dep not in task.deps:
            raise Refused('%s does not depend on %s' % (task.id, dep))
        task.fm['deps'] = [d for d in task.deps if d != dep]
    write_text(task.path, stamp_and_render(task, key, progress(args)))
    emit('%s deps = [%s]  (%s %s)' % (task.id, ', '.join(task.deps),
                                      'moved' if progress(args) else 'updated only', key))
    return 0


def op_comment(store, args):
    key = session_key(args.session)
    message = read_message(args.message)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    task.body = append_log(task.body, key, message)
    write_text(task.path, stamp_and_render(task, key, progress(args)))
    emit('%s logged under %s%s' % (task.id, key,
                                   '' if progress(args) else ' (updated only)'))
    return 0


def op_touch(store, args):
    key = session_key(args.session)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    write_text(task.path, stamp_and_render(task, key, progress(args)))
    emit('%s %s %s' % (task.id, 'moved' if progress(args) else 'updated (moved held at '
                       '%s)' % (task.moved or '-'), key))
    return 0


def op_ack(store, args):
    """Acknowledge reported drift: bump `updated`, leave `moved` ALONE, log WHY, and
    re-stamp `source_hash` to what the source says right now.

    It cannot move the staleness needle, and that is the half it shares with every
    ack-class write: if acknowledging drift bumped `moved`, a scheduled housekeeping pass
    would keep every NOW row permanently fresh and `board`'s staleness warning would be
    unfireable -- a check that fails by passing, which is this repo's declared house
    failure mode.

    THE MESSAGE IS REQUIRED, reversing this op's original "no `-m`" rule, and the reason
    is the audit trail rather than tidiness. The interesting `ack` is the one that answers
    a `BODY` report: the board's block was rewritten, someone read both, and the task's
    prose needed no change. Without a message that judgement is destroyed -- the digest
    silently advances and the next reader sees a task that was never in drift at all. With
    it, the record reads like the Jira comment it is: the description stayed stable, and
    HERE IS WHY. A message with nothing to say costs one line; a lost reason costs the
    only evidence that the drift was looked at.

    RE-STAMPING IS NOT UNCONDITIONAL. The digest is written only for a task whose source
    this tool can actually READ (today: `source: board`). For a task sourced from a
    document sync cannot parse, the hash is left exactly as it was and the output says so
    -- claiming a reconciliation that did not happen is the single edit that would make
    `sync` silent forever, so it is not something `ack` is allowed to do as a side effect.

    THE THIRD CASE, added 2026-08-21e: `source: board` and the row is GONE. That is the
    `CORPUS-ONLY` report, and it used to leave the field untouched, which made `ack`
    a no-op for the one bucket that was red forever. It now writes the
    `SOURCE_HASH_NO_ROW` sentinel. That is not the same edit as the paragraph above
    forbids: the forbidden one CLAIMS a reconciliation against text that was never read,
    while this one records an ABSENCE this run observed directly, and the absence is
    exactly what is being acknowledged. Three ops still write this field and none of them
    takes a value from a human.
    """
    key = session_key(args.session)
    message = read_message(args.message)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    note = 'source_hash unchanged (source: %s -- sync cannot read that source)' \
           % (task.source or '(empty)')
    if task.source == 'board':
        where = find_board(store, getattr(args, 'board', None))
        board = parse_board(read_text(where), where)
        row = None
        for candidate in board['rows']:
            if candidate['id'] == task.id:
                row = candidate
                break
        if row is None:
            # An ack on a task whose row has VANISHED is a legitimate act -- it is the
            # CORPUS-ONLY report -- and until 2026-08-21e it was also a NO-OP: the hash
            # was left alone, the next `sync --check` reported the same two items, and
            # steps 1-3 of the housekeeping loop exited 1 forever (PROOF4.md section 6
            # bug B). An op that reports "acknowledged" and changes nothing observable is
            # the worst of both: the reader believes the item is handled and the gate
            # keeps saying it is not.
            #
            # So the sentinel is written. It is NOT a digest of absence and not a claim
            # that a reconciliation happened -- it says only what this run OBSERVED, that
            # the source names no row for this id, plus the fact that a human looked. The
            # reason itself is in the Log entry beside it, which is why `-m` is required.
            # If a row ever appears, the sentinel is compared against its real digest,
            # never matches (it is not hex), and the task is reported again -- see
            # SOURCE_HASH_NO_ROW for the full argument.
            note = ('source_hash %s -> %s (%s has no row on %s -- acknowledged, so `sync` '
                    'stops counting it as drift and starts counting it as acknowledged; '
                    'if a row reappears it is reported again)'
                    % (task.source_hash or '(none)', SOURCE_HASH_NO_ROW, task.id,
                       rel(where)))
            task.fm['source_hash'] = SOURCE_HASH_NO_ROW
        else:
            digest = source_digest(source_block_text(row, board['blocks']))
            note = 'source_hash %s -> %s' % (task.source_hash or '(none)', digest)
            task.fm['source_hash'] = digest
    task.body = append_log(task.body, key, message)
    write_text(task.path, stamp_and_render(task, key, False))
    emit('%s acked %s (moved held at %s -- ack never claims progress); %s'
         % (task.id, key, task.moved or '-', note))
    return 0


def op_close(store, args):
    key = session_key(args.session)
    # The message is REQUIRED, and argparse enforces it. A close with no outcome evidence
    # is exactly the "completed but nobody can tell why or whether" state this tool exists
    # to delete, and per the repo's sabotage culture an assertion with no observed output
    # attached is not evidence.
    message = read_message(args.message)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    if task.is_closed:
        raise Refused('%s is already closed (closed: %s)' % (task.id, task.closed))
    open_kids = sorted([t.id for t in store.open_tasks() if t.parent == task.id])
    if open_kids and not args.force:
        raise Refused('%s still has open children %s. Close them first, or pass --force '
                      'if the parent is genuinely done and the children have outlived it.'
                      % (task.id, open_kids))

    task.fm['closed'] = key
    task.body = append_log(task.body, key, message)
    target = os.path.join(store.closed_dir, os.path.basename(task.path))
    if not os.path.isdir(store.closed_dir):
        os.makedirs(store.closed_dir)
    if os.path.exists(target):
        raise Refused('%s already exists' % rel(target))
    write_text(target, stamp_and_render(task, key))
    os.remove(task.path)
    store.invalidate()

    emit('%s closed %s -> %s' % (task.id, key, rel(target)))
    # THE ARCHIVE SWEEP, COMPUTED INSTEAD OF REMEMBERED. Both of these are things a human
    # is supposed to notice and reliably does not: "what did this unblock" and "is that
    # group finished now". They are cheap to derive and impossible to remember.
    closed_ids = set(t.id for t in store.tasks() if t.is_closed)
    unblocked = sorted([t.id for t in store.open_tasks() if is_ready(t, closed_ids)
                        and task.id in t.deps])
    if unblocked:
        emit('now ready (this was their last open dep): %s' % ', '.join(unblocked))
    else:
        emit('now ready: (nothing -- no open task was waiting on %s alone)' % task.id)
    if task.parent:
        remaining = sorted([t.id for t in store.open_tasks() if t.parent == task.parent])
        if remaining:
            emit('parent %s still has %d open child(ren): %s'
                 % (task.parent, len(remaining), ', '.join(remaining)))
        else:
            emit('parent %s now has ZERO open children -- close it too, or archive the '
                 'group.' % task.parent)
    return 0


def op_reopen(store, args):
    key = session_key(args.session)
    message = read_message(args.message)
    task = need_writable(store, args.id)
    key = resolve_key(key, task)
    if not task.is_closed:
        raise Refused('%s is not closed' % task.id)
    violations = check_budget(store.open_tasks() + [_ghost(task.pri, task.id, task.title)],
                              store.config['budgets'], {})
    if violations:
        raise Refused('reopening %s at pri %s would break the budget:\n  %s\nDemote a row '
                      'first, or reopen it and immediately promote with --demote.'
                      % (task.id, task.pri, '\n  '.join(violations)))
    task.fm['closed'] = ''
    task.body = append_log(task.body, key, message)
    target = os.path.join(store.dir, os.path.basename(task.path))
    if os.path.exists(target):
        raise Refused('%s already exists' % rel(target))
    write_text(target, stamp_and_render(task, key))
    os.remove(task.path)
    store.invalidate()
    emit('%s reopened -> %s' % (task.id, rel(target)))
    return 0


# --- sync: reconciliation, never regeneration (SYNC-SPEC.md) --------------------------
#
# THE ONE PROPERTY THIS SECTION EXISTS TO HAVE: there is no delete path. Not a flag, not
# a --force. Grep this file for `os.remove` and `shutil` and you will find `os.remove`
# exactly twice, both in `op_close`/`op_reopen`, both the second half of a MOVE, and
# `shutil` not imported at all. `sync` writes through `op_new` and nothing else, so the
# strongest thing it can do to an existing file is nothing. A board row that vanishes is
# a REPORT, because a row can vanish from a careless edit just as easily as from a
# finished item, and a tool that turns a typo into a deletion is worse than no tool.

BOARD_FILENAME = 'HANDOFF.md'
BOARD_TABLE_HEAD = '| id | item'
BOARD_BLOCKS_HEAD = '## Item blocks'
BOARD_READ_FIRST = '**Read first:**'
# Read EXACTLY as handoff_lint.py::check_ledger_ids reads them: line by line, only lines
# carrying one of these phrases. A different harvest here would disagree with the repo's
# own linter about which ids are retired, and the board warns in place that reflowing
# those lines moves ids out of scope.
BOARD_RETIRED_MARKERS = ('Closed ids stay retired',
                         'survives as the historical grouping')
BOARD_GROUPING = re.compile(r'`([^`]+)`\s+survives as the historical grouping')
ARROW = u'→'          # the board's pointer glyph
WARN_GLYPH = u'⚠'     # the repo's trap badge; the board's own paragraph badging

# The buckets, in report order. Each name is cited in SYNC-SPEC.md section 2 and in the
# emitted output, so renaming one is a documentation edit as well as a code edit.
SYNC_BUCKETS = ('NEW', 'FIELD', 'BODY', 'CORPUS-ONLY', 'RETIRED-BUT-OPEN',
                'CLOSED-BUT-ON-BOARD')

# The fields sync reconciles, and the two it deliberately does not.
#
# `title` IS NOT HERE, and dropping it is a measured decision rather than an omission.
# SYNC-SPEC.md section 2 originally listed it. On the live board, 2026-08-21d, `pri` /
# `size` / `deps` agreed with the corpus on 26 of 26 rows and `title` agreed on 0 of 26 --
# because a board cell is markdown (bold, inline code, a `[text](link)` pointer, an arrow)
# and a task title is a folded 100-char line, so `set <id> title <cell>` is neither
# pasteable nor right. A retitled row is a PROSE change and reaches the reader through
# `BODY` instead, where a human is already required. A mechanical fix nobody can paste is
# a FIELD bucket that trains its reader to ignore the FIELD bucket.
#
# `moved` is not here either: it is the corpus's own staleness signal, written by the
# write path, and copying it from the board would let a board edit launder a stale row --
# the same laundering `--mechanical` exists to prevent, arriving through the other door.
SYNC_FIELDS = ('pri', 'size', 'deps')


def find_board(store, explicit):
    """Locate the board. Explicit path wins; otherwise walk UP from the tasks dir.

    Walking up looks for the exact name ``HANDOFF.md`` and stops at the first hit, which
    from ``.scratch/tasktool/sandbox-migrated/tasks`` is the repo's real board four levels
    up. The sandbox's own ``HANDOFF-stub.md`` is deliberately not a candidate: it is the
    ~25-line pointer the board becomes AFTER this tool graduates, not a source of rows,
    and picking it up would give sync an empty board and therefore a report claiming every
    task had lost its row -- a wrong answer that looks like a very serious right one.
    """
    if explicit:
        if not os.path.isfile(explicit):
            raise Refused('--board %s does not exist. sync READS its source; it never '
                          'creates one.' % rel(explicit))
        return explicit
    cur = os.path.abspath(store.dir)
    while True:
        candidate = os.path.join(cur, BOARD_FILENAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            raise Refused('no %s at or above %s. Pass --board <path>. sync will not '
                          'fall back to "no rows found": an empty board and a missing '
                          'board are the same input and opposite facts, and guessing '
                          'between them would report every task as orphaned.'
                          % (BOARD_FILENAME, rel(store.dir)))
        cur = parent


def parse_board(text, where='<board>'):
    """The board -> ``{'rows': [...], 'blocks': {id: text}, 'retired': [ids]}``.

    Structural, not positional, and it FAILS rather than degrades: a table whose header
    is missing, or a row with the wrong cell count, raises. That is the instrument
    control SYNC-SPEC.md section 3 asks for -- a parser that silently returns zero rows
    turns "I cannot read the board" into "the board is empty", and the second one is a
    catastrophic report delivered with total confidence.
    """
    lines = text.replace('\r\n', '\n').split('\n')
    rows, in_table, saw_table = [], False, False
    for line in lines:
        if line.startswith(BOARD_TABLE_HEAD):
            in_table, saw_table = True, True
            continue
        if in_table:
            if not line.startswith('|'):
                break
            if line.startswith('|---'):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 6:
                raise Refused('%s: board row has %d cells, expected 6 (id | item | pri | '
                              'size | deps | moved):\n  %s' % (rel(where), len(cells),
                                                               line[:160]))
            rows.append({
                'id': cells[0].strip('`').strip(),
                'cell': cells[1],
                'pri': cells[2].replace('**', '').strip(),
                'size': cells[3].replace('**', '').strip(),
                'deps': re.findall(r'`([^`]+)`', cells[4]),
                'moved': cells[5],
            })
    if not saw_table:
        raise Refused('%s: no board table (no line starting %r). If this file is a '
                      'board, its table header changed; if it is not, pass the right '
                      '--board.' % (rel(where), BOARD_TABLE_HEAD))

    blocks = {}
    if BOARD_BLOCKS_HEAD in text:
        section = text[text.index(BOARD_BLOCKS_HEAD):]
        # An item block runs to the next `### ` or to the next `## ` heading, whichever
        # comes first. Splitting on `\n### ` alone swallowed the whole tail of the file
        # into the last block, so the last NOW/NEXT item's digest changed every time an
        # UNRELATED later section did -- a false BODY report on one arbitrary task.
        for part in re.split(r'\n### ', section)[1:]:
            head, _, rest = part.partition('\n')
            m = re.match(r'`([^`]+)`', head.strip())
            if not m:
                continue
            stop = re.search(r'\n## ', rest)
            blocks[m.group(1)] = rest[:stop.start()] if stop else rest

    retired, span = [], []
    for line in lines:
        if any(marker in line for marker in BOARD_RETIRED_MARKERS):
            span.append(line)
    joined = '\n'.join(span)
    # The grouping clause names an id that is explicitly NOT retired ("`B2` survives as
    # the historical grouping of `P8` + `P9`"), and everything after it on that line is
    # the group's membership. Truncate there rather than hardcoding B2.
    m = BOARD_GROUPING.search(joined)
    if m:
        joined = joined[:m.start()]
    for tid in re.findall(r'`([^`]+)`', joined):
        if tid not in retired:
            retired.append(tid)
    return {'rows': rows, 'blocks': blocks, 'retired': retired}


def source_block_text(row, blocks):
    """The text a task's PROSE comes from: the item cell, plus the item block if any.

    The pri/size/deps/moved cells are deliberately excluded. Every one of them is a
    `FIELD` fix, and folding them in here would make one `promote` on the board fire both
    a FIELD report and a BODY report against the same task -- two reports, two buckets,
    one change, and the reader has to work out that they are the same thing.
    """
    parts = [row['cell']]
    block = blocks.get(row['id'])
    if block:
        parts.append(block)
    return normalise_source(u'\n\n'.join(parts))


def normalise_source(text):
    """Trailing-whitespace and blank-edge normalisation before hashing.

    Narrow on purpose. It absorbs exactly the edits that change no meaning and that an
    editor makes without being asked (a stripped trailing space, a reflowed blank line at
    the edge of a block). It does NOT collapse internal blank lines or fold case: those
    are real edits to the source, and a digest that shrugs at real edits is a digest that
    reports nothing.
    """
    lines = [line.rstrip() for line in text.replace('\r\n', '\n').split('\n')]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return u'\n'.join(lines)


def source_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:SOURCE_HASH_LEN]


def strip_markdown(cell):
    """A board cell -> plain text. Cosmetic, and only ever used for a TITLE."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cell)   # [text](link) -> text
    text = text.replace('**', '').replace('`', '')
    return re.sub(r'\s+', ' ', text).strip()


def split_cell(cell):
    """``(item text, pointer markdown)`` -- the board cell's two halves.

    The pointer is whatever follows the last arrow glyph. It is the first line of the
    task's `## Read first`, exactly as `migrate.py` placed it, because the pointer is the
    one thing every row below NEXT has instead of an item block.
    """
    if ARROW in cell:
        item, _, pointer = cell.rpartition(ARROW)
        return item.strip(), pointer.strip()
    return cell.strip(), ''


def board_title(row):
    """A title for a minted task: the cell's item half, folded to one clipped line.

    Lossy and known to be: see SYNC_FIELDS for why `title` is not a reconciled field.
    What this has to be is *safe* (one line, within the cap, never empty), not faithful --
    a session that works the item rewrites the title along with the body.
    """
    item, pointer = split_cell(row['cell'])
    title = strip_markdown(item) or strip_markdown(pointer) or row['id']
    if len(title) > 100:
        title = title[:97].rstrip() + '...'
    return title


def board_body(row, blocks):
    """The body for a task minted from a board row: summary / Traps / Read first / Log.

    The split rule is the board's OWN badging, not position: a paragraph badged with the
    warn glyph is a trap. `migrate.py::open_task` learned this the hard way -- `P3` has
    carried its traps both before and after its completion criterion within two sessions,
    so any positional rule is wrong every other week.
    """
    item, pointer = split_cell(row['cell'])
    summary, traps, read_first = [strip_markdown(item) or row['id']], [], []
    if pointer:
        read_first.append(u'- board pointer: %s' % pointer)
    block = blocks.get(row['id'])
    if block:
        before, marker, after = block.partition(BOARD_READ_FIRST)
        summary = []
        for para in normalise_source(before).split(u'\n\n'):
            if not para.strip():
                continue
            (traps if para.lstrip().startswith(WARN_GLYPH) else summary).append(para)
        if marker and after.strip():
            read_first.append(normalise_source(after))
    out = [u'\n\n'.join(summary).strip() or row['id'], u'', u'## Traps', u'']
    if traps:
        out += [u'\n\n'.join(traps).strip(), u'']
    out += [u'## Read first', u'']
    if read_first:
        out += [u'\n\n'.join(read_first).strip(), u'']
    out += [LOG_HEADING, u'']
    return u'\n'.join(out)



def sync_report(store, board, where):
    """Compute every bucket. READ ONLY -- this function writes nothing, ever.

    Bucketing is total and disjoint: every board row and every task lands in exactly one
    place, and the two "expected, silent" outcomes (a hand-filed task, a closed task whose
    row is gone) are COUNTED rather than dropped, so the summary line always adds up
    against `task.py counts`.
    """
    rows = board['rows']
    by_id = store.by_id()
    row_by_id = dict((r['id'], r) for r in rows)
    report = dict((k, []) for k in ('new', 'field', 'body', 'corpus_only_open',
                                    'corpus_only_acked', 'corpus_only_closed',
                                    'retired_but_open', 'closed_but_on_board', 'hand'))
    report['unreadable'] = {}
    report['board'] = rel(where)
    report['rows'] = len(rows)
    report['tasks'] = len(store.tasks())

    for row in rows:
        digest = source_digest(source_block_text(row, board['blocks']))
        task = by_id.get(row['id'])
        if task is None:
            report['new'].append({'id': row['id'], 'title': board_title(row),
                                  'pri': row['pri'], 'size': row['size'],
                                  'deps': row['deps'], 'digest': digest, 'row': row})
            continue
        if task.is_closed:
            # THE REVERSE CASE, which the spec's original section 2 had no bucket for: the
            # corpus says done, the board still ranks it. Nothing else in this repo
            # catches it -- lint sees a well-formed closed task and the board is not
            # linted against the corpus at all -- and it is the shape a stale board takes
            # once `close` is the only way out of the open set.
            report['closed_but_on_board'].append(
                {'id': task.id, 'closed': task.closed, 'pri': row['pri']})
            continue
        changes = field_changes(task, row)
        if changes:
            report['field'].append({'id': task.id, 'changes': changes})
        if task.source_hash != digest:
            report['body'].append({'id': task.id, 'stored': task.source_hash,
                                   'current': digest,
                                   'seeded': bool(task.source_hash)})

    for task in store.tasks():
        # INSTRUMENT CONTROL (SYNC-SPEC.md section 3): fail loudly rather than degrade.
        # A malformed `source` is the one input that could make sync WRONG AND QUIET --
        # an empty one reads as "not board, not a path", falls off the end of the
        # bucketing, and the task silently stops being reconciled. It is already a lint
        # violation (check 4), so the honest response here is to refuse and point at the
        # linter, not to invent a bucket for a value the schema does not admit.
        bad = source_problem(task.source)
        if bad:
            raise Refused('%s: %s\n\nRun `%s lint` first: sync will not bucket a task '
                          'whose provenance it cannot read, because the plausible guess '
                          '("hand-filed, expected") is the one that makes this tool go '
                          'quiet about it forever.' % (rel(task.path), bad, prog()))
        if task.id in row_by_id:
            continue
        if task.source == 'hand':
            report['hand'].append(task.id)          # expected, and NOT drift
        elif task.source == 'board':
            if task.is_closed:
                # R1: the normal path. A row vanishes because the item was closed, and
                # the corpus already records that. Counted, silent, exit 0.
                report['corpus_only_closed'].append(task.id)
            elif task.source_hash == SOURCE_HASH_NO_ROW:
                # ACKNOWLEDGED (SOURCE_HASH_NO_ROW): a human read this, said why in the
                # Log, and the situation has not changed since. Counted and NAMED on every
                # run -- never silent, because "expected, therefore invisible" is how a
                # bucket stops being checked -- but not drift, because a check that is red
                # forever is a check nobody reads the exit code of.
                report['corpus_only_acked'].append({'id': task.id, 'pri': task.pri})
            else:
                report['corpus_only_open'].append({'id': task.id, 'pri': task.pri,
                                                   'title': task.title})
        else:
            report['unreadable'].setdefault(task.source, []).append(task.id)

    for tid in board['retired']:
        task = by_id.get(tid)
        if task is not None and not task.is_closed:
            report['retired_but_open'].append({'id': tid, 'pri': task.pri})

    report['drift'] = (len(report['new']) + len(report['field']) + len(report['body'])
                       + len(report['corpus_only_open'])
                       + len(report['retired_but_open'])
                       + len(report['closed_but_on_board']))
    return report


def field_changes(task, row):
    """The FIELD bucket for one row: the fields that differ, each with its command."""
    out = []
    if row['pri'] and task.pri != row['pri']:
        out.append({'field': 'pri', 'from': task.pri, 'to': row['pri'],
                    'commands': ['promote %s %s --mechanical' % (task.id, row['pri'])],
                    'rank': -1 if pri_rank(row['pri']) > pri_rank(task.pri) else 1})
    if row['size'] and task.size != row['size']:
        out.append({'field': 'size', 'from': task.size, 'to': row['size'],
                    'commands': ['set %s size %s --mechanical' % (task.id, row['size'])],
                    'rank': 0})
    if sorted(task.deps) != sorted(row['deps']):
        cmds = ['dep rm %s %s --mechanical' % (task.id, d)
                for d in task.deps if d not in row['deps']]
        cmds += ['dep add %s %s --mechanical' % (task.id, d)
                 for d in row['deps'] if d not in task.deps]
        out.append({'field': 'deps', 'from': task.deps, 'to': row['deps'],
                    'commands': cmds, 'rank': 0})
    return out


def corpus_arg(store):
    """``--dir <resolved corpus root>``: the target, echoed so a pasted line cannot miss.

    Derived from the STORE and not from ``args.dir``, so it is the corpus this run
    actually reconciled rather than the string somebody typed -- ``--dir .``, a relative
    path, and a walk UP from a subdirectory all resolve to the same absolute root here.
    """
    root = os.path.dirname(os.path.abspath(store.dir)).replace(os.sep, '/')
    return '--dir "%s"' % root if ' ' in root else '--dir %s' % root


def sync_command_lines(report, store):
    """Every mechanical fix, as lines that run in the order printed -- AND IN ANY CWD.

    ORDERING IS PART OF THE CONTRACT, not cosmetics. `promote` refuses at write time if
    the result would break NOW=1 / NEXT<=3, so a board that swapped its NOW row emits two
    promotions of which the raising one is refused if it runs first. Demotions are
    therefore emitted before promotions (`rank` -1 / 0 / 1 above). This is the one place
    the emitted set is not order-free, and the alternative -- telling the reader to sort
    it out -- is exactly the "needs a judgement call to PROCEED" that SYNC-SPEC.md
    section 4 calls a design bug.

    THE TARGET IS PART OF THE CONTRACT TOO, and it was missing until 2026-08-21e
    (PROOF4.md section 6 bug A). This function took no ``store`` and built each line as
    ``'python %s %s' % (prog(), cmd)``, so `--dir` was never echoed: an operator standing
    in corpus `d2` who ran `--dir d1 sync --commands` and pasted the emitted lines
    verbatim -- which is EXACTLY what the housekeeping loop this feature exists to enable
    does -- edited `d2` and left `d1` untouched. Three rc=0 lines, plausible success text,
    no warning anywhere: the house failure mode, failing by passing, with a write attached.
    Reproduced literally in PROOF4.md section 6.

    ``prog()`` had already made this argument for ``argv[0]`` -- "a printed command must
    be the command the reader can actually run" -- and it applies with more force to the
    target than to the interpreter path, because a wrong interpreter path is an error and
    a wrong target is a silent edit to the wrong corpus. The resolved ROOT is emitted
    unconditionally, including when `--dir` was never passed, because "the cwd I happen to
    be in" is not a target a pasted line may depend on.
    """
    ranked = []
    for entry in report['field']:
        for change in entry['changes']:
            for cmd in change['commands']:
                ranked.append((change['rank'], entry['id'], change['field'], cmd))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    prefix = 'python %s %s' % (prog(), corpus_arg(store))
    return ['%s %s' % (prefix, cmd) for _, _, _, cmd in ranked]


def sync_create_new(store, report, board, args):
    """Mint a task for every NEW row. THE ONLY WRITE PATH IN `sync`, and it only adds.

    It goes through `op_new` rather than writing frontmatter itself, so a synced task gets
    the same id allocation, the same budget refusal, the same dep and label validation and
    the same canonical rendering as a typed one. A second creation path is a second
    schema, and this corpus already paid for one of those.

    A row that `op_new` refuses (an unresolvable dep, a `NOW` when the corpus already has
    one) is REPORTED and skipped, and the run still exits 1. Creating it anyway with the
    offending field blanked would file a task that agrees with nothing.
    """
    made, refused = [], []
    for item in report['new']:
        row = item['row']
        ns = argparse.Namespace(
            session=args.session, task_id=item['id'], title=item['title'],
            pri=row['pri'] or 'LATER', size=row['size'] or '?',
            deps=','.join(row['deps']), labels=None,
            parent=None, related=None, source='board', body=None,
            source_hash=item['digest'], body_text=board_body(row, board['blocks']))
        try:
            op_new(store, ns)
            made.append(item['id'])
        except Refused as exc:
            refused.append((item['id'], str(exc)))
        store.invalidate()
    return made, refused


def op_sync(store, args):
    """Reconcile the corpus against the board: report drift, create what is new, and
    never, under any flag, remove anything.

    The exit code is the drift REMAINING when the run ends, so the housekeeping loop in
    SYNC-SPEC.md section 4 can sit in a gate: `--create-new` resolves the NEW bucket and
    the run goes green if that was all there was.
    """
    where = find_board(store, args.board)
    board = parse_board(read_text(where), where)
    report = sync_report(store, board, where)

    created, refused = [], []
    if args.create_new:
        created, refused = sync_create_new(store, report, board, args)
        if created:
            report = sync_report(store, board, where)   # re-measure; do not subtract
        report['created'] = created
        report['refused'] = [{'id': i, 'why': w} for i, w in refused]
        report['drift'] += len(refused)

    if args.json:
        for entry in report['new']:
            entry.pop('row', None)
        emit_json(report)
        return 1 if report['drift'] else 0

    if args.commands:
        # STDOUT carries commands and nothing else, so `sync --commands | sh` is a real
        # thing a cheap model can do; the report goes to stderr beside it. Splitting the
        # streams is what keeps the mechanical half mechanical.
        for line in sync_command_lines(report, store):
            emit(line)
        render_sync_report(report, emit_err)
    else:
        render_sync_report(report, emit)
    return 1 if report['drift'] else 0


def render_sync_report(report, out):
    out('sync   %s  (%d row(s) vs %d task(s))'
        % (report['board'], report['rows'], report['tasks']))
    for item in report.get('created', []):
        out('  CREATED           %s' % item)
    for item in report.get('refused', []):
        out('  NEW-REFUSED       %s: %s' % (item['id'], item['why'].split('\n')[0]))
    for item in report['new']:
        out('  NEW               %s  %s/%s  %s'
            % (item['id'], item['pri'], item['size'], clip(item['title'], 44)))
    for entry in report['field']:
        for change in entry['changes']:
            out('  FIELD             %s %s: %r -> %r'
                % (entry['id'], change['field'], change['from'], change['to']))
    for item in report['body']:
        out('  BODY              %s  source block moved (%s -> %s)%s'
            % (item['id'], item['stored'] or '(never reconciled)', item['current'],
               '' if item['seeded'] else ' -- first reconciliation'))
    for item in report['corpus_only_open']:
        out('  CORPUS-ONLY       %s (source: board, still OPEN, %s) -- row is gone; '
            'close it if it is done' % (item['id'], item['pri']))
    for item in report['corpus_only_acked']:
        out('  ACKED-NO-ROW      %s (source: board, still OPEN, %s) -- no row, '
            'acknowledged; NOT drift. See its Log for why. If a row reappears the stored '
            '%r will not match its digest and %s is reported again.'
            % (item['id'], item['pri'], SOURCE_HASH_NO_ROW, item['id']))
    for item in report['retired_but_open']:
        out('  RETIRED-BUT-OPEN  %s is on the retired line and still open' % item['id'])
    for item in report['closed_but_on_board']:
        out('  CLOSED-BUT-ON-BOARD %s closed %s but still a %s row'
            % (item['id'], item['closed'], item['pri']))
    if report['body']:
        out('  BODY drift is never auto-applied. `git diff -- %s` is the old-vs-new '
            'source diff (git is where the board\'s history lives, not this tool); then '
            'rewrite the body and `%s ack <id> -m "..."`.'
            % (report['board'], prog()))
    if report['corpus_only_open'] or report['retired_but_open']:
        out('  close is NEVER automatic: a row can vanish from a careless edit as easily '
            'as from a finished item.')
    # The two silent buckets are PRINTED AS COUNTS on every run, clean or dirty. They are
    # the instrument control: "expected, therefore invisible" is how a bucket stops being
    # checked, and a run that reports nothing at all is indistinguishable from a run whose
    # scanner went blind.
    out('  quiet             %d hand-filed, %d closed-and-off-the-board'
        % (len(report['hand']), len(report['corpus_only_closed'])))
    for src in sorted(report['unreadable']):
        out('  UNREADABLE-SOURCE %d task(s) cite %s -- sync cannot read that document, '
            'so it reports the count rather than bucketing them as hand-filed. NOT drift.'
            % (len(report['unreadable'][src]), src))
    out('sync   %s' % ('CLEAN' if not report['drift']
                       else '%d drift item(s)' % report['drift']))


# --- CLI ------------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog='task.py',
        description='File-per-task tracker. The board is a query, never a file.')
    p.add_argument('--dir', default='.',
                   help='where to start looking for tasks/config.json (default: cwd)')
    # `--session` is declared TWICE ON PURPOSE: here (global, before the verb) and on
    # every write op (after the verb). `--dir` is global, so the natural transcription of
    # the HANDOFF stub's line -- `task.py --session 2026-08-21c comment P3 -m x` -- put it
    # where the tool's other flag goes and got `error: argument op: invalid choice:
    # '2026-08-21c'`, TRUE rc=2 (PROOF2.md section 4). Making a cold session learn
    # argparse's ordering to obey a documented instruction is the same class of gap COLD-1
    # was, and the cure is to accept both placements rather than to write the ordering
    # down somewhere nobody reads. The two land in different dests and `merge_session`
    # reconciles them; giving both at once with DIFFERENT values is refused, never
    # silently resolved, because there is no defensible winner.
    p.add_argument('--session', dest='global_session', default=None,
                   help='session key to stamp into `moved`; accepted before OR after the '
                        'verb (write ops only)')
    sub = p.add_subparsers(dest='op')

    def read_op(name, help_text):
        s = sub.add_parser(name, help=help_text)
        s.add_argument('--json', action='store_true',
                       help='machine-readable output on stdout')
        return s

    def write_op(name, help_text, mechanical=False):
        s = sub.add_parser(name, help=help_text)
        s.add_argument('--session', default=None,
                       help='session key to stamp (default: today)')
        if mechanical:
            # Offered on the field ops a housekeeping tool actually emits, and NOT on
            # close/reopen: those require a message and `sync` is forbidden from ever
            # auto-closing, so a --mechanical close would only ever be a human quietly
            # declining to record that they closed something.
            s.add_argument('--mechanical', action='store_true',
                           help='housekeeping write: bump `updated` only and leave '
                                '`moved` alone. For TOOLS (sync applies field fixes with '
                                'it on every call); a session doing the work never passes '
                                'it')
        return s

    read_op('board', 'the ~25-line session-start view')

    s = read_op('list', 'filterable table of tasks')
    s.add_argument('--pri', choices=list(PRI_VALUES))
    s.add_argument('--label')
    s.add_argument('--parent')
    s.add_argument('--closed', action='store_true', help='closed tasks only')
    s.add_argument('--all', action='store_true', help='open and closed')
    s.add_argument('--limit', type=int, default=None, metavar='N',
                   help='show at most N rows (default %d for the table, unlimited for '
                        '--json; 0 for all). Truncation is always announced in the '
                        'footer.' % LIST_LIMIT)

    s = read_op('show', 'print a task file plus its derived facts')
    s.add_argument('id')

    read_op('ready', 'open NOW/NEXT/LATER tasks whose deps are all closed')
    read_op('lint', 'mechanical checks; exit 1 on any violation')
    read_op('counts', 'corpus size, measured -- the value min_tasks_parsed must carry')

    s = write_op('new', 'create a task, allocating the next id by scanning')
    s.add_argument('title')
    s.add_argument('--pri', default=None)
    s.add_argument('--size', default=None)
    s.add_argument('--deps', default=None, help='comma-separated ids')
    s.add_argument('--labels', default=None, help='comma-separated labels')
    s.add_argument('--parent', default=None)
    s.add_argument('--related', default=None, help='comma-separated ids (navigation only)')
    s.add_argument('--source', default=None,
                   help='where this task came from: %s, or a repo-relative path. '
                        'Immutable after creation (default: hand)' % '/'.join(SOURCE_FIXED))
    s.add_argument('--body', default=None, help='file whose contents become the body')

    s = write_op('set', 'set title / size / labels / related / parent', mechanical=True)
    s.add_argument('id')
    s.add_argument('field')
    s.add_argument('value')

    s = write_op('promote', 'change pri, refusing a budget violation at write time',
                 mechanical=True)
    s.add_argument('id')
    s.add_argument('pri')
    s.add_argument('--demote', nargs=2, metavar=('ID2', 'PRI2'),
                   help='make room in the same atomic write')

    s = write_op('dep', 'add or remove a dependency edge', mechanical=True)
    s.add_argument('action', choices=('add', 'rm'))
    s.add_argument('id')
    s.add_argument('dep')

    s = write_op('comment', 'append a dated Log entry', mechanical=True)
    s.add_argument('id')
    s.add_argument('-m', '--message', required=True, help='message, or - to read stdin')

    s = write_op('touch', 'record progress: bump `moved` and `updated`', mechanical=True)
    s.add_argument('id')

    s = write_op('ack', 'acknowledge drift: bump `updated` only, re-stamp source_hash')
    s.add_argument('id')
    s.add_argument('-m', '--message', required=True,
                   help='why the task needed no change, or - to read stdin')
    s.add_argument('--board', default=None,
                   help='the source document (default: the nearest %s above tasks/)'
                        % BOARD_FILENAME)

    # `sync` is neither a read op nor a write op and gets its own block. `--check` is the
    # default and is accepted as an explicit flag anyway, because SYNC-SPEC.md section 4's
    # loop is meant to be pasted verbatim by a model that should not have to know which
    # of four flags is the default one.
    s = sub.add_parser('sync', help='reconcile against the board; reports, adds, NEVER '
                                    'deletes')
    s.add_argument('--session', default=None,
                   help='session key to stamp on anything --create-new mints')
    s.add_argument('--check', action='store_true',
                   help='report drift and change nothing (the default)')
    s.add_argument('--create-new', dest='create_new', action='store_true',
                   help='additionally MINT a task for every source row that has none. '
                        'The only mode that writes, and it only ever adds')
    s.add_argument('--commands', action='store_true',
                   help='emit the mechanical fixes as pasteable lines on stdout, with '
                        'the report on stderr')
    s.add_argument('--json', action='store_true', help='machine-readable report')
    s.add_argument('--board', default=None,
                   help='the source document (default: the nearest %s at or above '
                        'tasks/)' % BOARD_FILENAME)

    s = write_op('close', 'close a task; message REQUIRED')
    s.add_argument('id')
    s.add_argument('-m', '--message', required=True, help='outcome evidence, or -')
    s.add_argument('--force', action='store_true',
                   help='close even though it still has open children')

    s = write_op('reopen', 'reopen a closed task; message REQUIRED')
    s.add_argument('id')
    s.add_argument('-m', '--message', required=True, help='why, or -')

    return p


OPS = {
    'board': op_board, 'list': op_list, 'show': op_show, 'ready': op_ready,
    'lint': op_lint, 'counts': op_counts, 'new': op_new, 'set': op_set,
    'ack': op_ack,
    'sync': op_sync,
    'promote': op_promote,
    'dep': op_dep, 'comment': op_comment, 'touch': op_touch, 'close': op_close,
    'reopen': op_reopen,
}


def merge_session(args):
    """Reconcile the global ``--session`` with the per-op one. Mutates ``args``.

    Three cases, and the third is why this is a function rather than an ``or``:
    only one given (either side) -> that one; both given and EQUAL -> that value, since a
    session that types it twice has said one thing twice; both given and DIFFERENT ->
    refused. Picking a winner there would silently discard a key a human typed, which is
    the same fault as backdating: a write stamped with a session it did not happen in.

    A global ``--session`` before a READ op is also refused. Read ops have no ``session``
    dest at all, so accepting it would mean accepting a flag that does nothing -- and a
    flag that is quietly ignored is how a session comes to believe a stamp happened.
    """
    global_key = getattr(args, 'global_session', None)
    if global_key is None:
        return
    if not hasattr(args, 'session'):
        raise Refused('--session %s was given, but `%s` is a read op: it writes nothing '
                      'and stamps no `moved`, so the key would be silently ignored. Drop '
                      'the flag (or run a write op).' % (global_key, args.op))
    if args.session is not None and args.session != global_key:
        raise Refused('--session was given twice with different values (%s before the '
                      'verb, %s after it). Both placements are accepted, but there is no '
                      'defensible winner between two keys a human typed -- one of them is '
                      'a session this write did not happen in. Give it once.'
                      % (global_key, args.session))
    args.session = global_key


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.op:
        parser.print_help()
        return 2
    try:
        merge_session(args)
        store = Store.find(args.dir)
        return OPS[args.op](store, args)
    except Refused as exc:
        emit_err('task %s: REFUSED\n\n  %s\n' % (args.op, exc))
        return 2
    except ParseError as exc:
        emit_err('task %s: unparseable task file\n\n  %s\n\nRun `task.py lint` for the '
                 'full list.\n' % (args.op, exc))
        return 2


if __name__ == '__main__':
    sys.exit(main())
