#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Measure the observed distribution of ``moved`` ages in the live task corpus.

``stale_days`` is the only knob in ``tasks/config.json`` that is a JUDGEMENT rather than a
measured fact, so the judgement has to be made against the real distribution instead of
against an example value. Prints the age histogram for OPEN rows, for the NOW/NEXT rows
the board actually flags, and the gap structure -- the number that matters is where the
distribution has a natural break, because a threshold inside a dense region flags rows
that are merely a few days old and one past the tail flags nothing ever.

``tasks/config.json``'s ``_provenance`` carries the standing instruction "re-derive with
measure_stale.py if the cadence changes"; this file is what it means.

PORT NOTE (2026-09-07). Ported out of ``.scratch/tasktool/measure_stale.py`` in the pass
that deleted that gitignored directory. Three things changed:

* the tree is the repo's tracked ``tasks/``, not the scratch ``sandbox-migrated/tasks``;
* ``TODAY`` was the hardcoded ``datetime.date(2026, 8, 21)``. It now defaults to the
  system date and takes ``--today YYYY-MM-DD``. A hardcoded clock silently turns a
  measurement into a fixed answer -- every age would keep the value it had on the day the
  script was written, and the histogram would look plausible forever;
* the frontmatter parse is unchanged, deliberately. It reads the ``moved``/``created``
  keys directly rather than importing ``task.py``, so this measurement is INDEPENDENT of
  the tool whose config knob it informs.

The original 2026-08-21 measurement that set ``stale_days = 14`` is recorded in
``docs/history/tasktool-scratch-archive-2026-09-07.md``; today's numbers are not restated
here -- run it.

Usage: ``python scripts/measure_stale.py [--today YYYY-MM-DD] [tree]``. Output is ASCII.
"""

import argparse
import datetime
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def rows(tree):
    for d, closed in ((tree, False), (os.path.join(tree, 'closed'), True)):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith('.md'):
                continue
            with io.open(os.path.join(d, name), encoding='utf-8') as fh:
                text = fh.read()
            fm = {}
            for line in text.split('\n')[1:]:
                if line == '---':
                    break
                if ': ' in line:
                    k, v = line.split(': ', 1)
                    fm[k.strip()] = v.strip()
                elif line.endswith(':'):
                    fm[line[:-1].strip()] = ''
            fm['_closed_dir'] = closed
            yield fm


def age(key, today):
    # A session key may carry a letter suffix (`2026-08-21b`); the letter distinguishes
    # sessions within a day and carries no age information, so it is dropped.
    m = re.match(r'^(\d{4})-(\d\d)-(\d\d)[a-z]?$', key or '')
    if not m:
        return None
    d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (today - d).days


def report(label, ages):
    ages = sorted(ages)
    if not ages:
        print('%s: none' % label)
        return
    n = len(ages)
    pct = lambda p: ages[min(n - 1, int(round((p / 100.0) * (n - 1))))]
    print('%s: n=%d  min=%d  p50=%d  p75=%d  p90=%d  max=%d'
          % (label, n, ages[0], pct(50), pct(75), pct(90), ages[-1]))
    hist = {}
    for a in ages:
        hist[a] = hist.get(a, 0) + 1
    print('    ages: %s' % '  '.join('%dd x%d' % (a, hist[a]) for a in sorted(hist)))
    # The empty gaps ARE the finding: a threshold belongs in one, not inside a dense run.
    gaps = []
    uniq = sorted(hist)
    for i in range(1, len(uniq)):
        if uniq[i] - uniq[i - 1] > 1:
            gaps.append((uniq[i - 1], uniq[i]))
    print('    empty gaps: %s' % (', '.join('%d..%d' % g for g in gaps) or 'none'))


def main(argv):
    ap = argparse.ArgumentParser(
        description='Measure moved-age distribution in the task corpus, to set '
                    'stale_days against the real cadence rather than a guess.')
    ap.add_argument('tree', nargs='?', default=os.path.join(ROOT, 'tasks'),
                    help='task tree root (default: the repo tasks/)')
    ap.add_argument('--today', default=None, metavar='YYYY-MM-DD',
                    help='pin the clock, for a reproducible re-measurement')
    args = ap.parse_args(argv)

    if args.today:
        m = re.match(r'^(\d{4})-(\d\d)-(\d\d)$', args.today)
        if not m:
            sys.stderr.write('--today must be YYYY-MM-DD\n')
            return 2
        today = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        today = datetime.date.today()

    if not os.path.isdir(args.tree):
        sys.stderr.write('no such tree: %s\n' % args.tree)
        return 2

    all_rows = list(rows(args.tree))
    # Instrument control: an empty scan prints "none" for every band and exits 0, which
    # reads exactly like a healthy corpus. Say it out loud instead.
    if not all_rows:
        print('NOTHING WAS SCANNED under %s -- this is not evidence about anything.'
              % args.tree)
        return 1
    op = [r for r in all_rows if not r['_closed_dir']]
    print('corpus: %d rows (%d open, %d closed), today=%s'
          % (len(all_rows), len(op), len(all_rows) - len(op), today.isoformat()))
    report('OPEN moved-age', [a for a in (age(r.get('moved'), today) for r in op)
                              if a is not None])
    board = [r for r in op if r.get('pri') in ('NOW', 'NEXT')]
    report('NOW/NEXT moved-age', [a for a in (age(r.get('moved'), today) for r in board)
                                  if a is not None])
    report('OPEN created-age', [a for a in (age(r.get('created'), today) for r in op)
                                if a is not None])
    spans = [age(r.get('created'), today) - age(r.get('moved'), today)
             for r in op
             if age(r.get('created'), today) is not None
             and age(r.get('moved'), today) is not None]
    report('OPEN created->moved span', spans)
    print('')
    for d in (3, 5, 7, 10, 14, 21, 30):
        flagged = len([r for r in board
                       if age(r.get('moved'), today) is not None
                       and age(r.get('moved'), today) > d])
        allflag = len([r for r in op
                       if age(r.get('moved'), today) is not None
                       and age(r.get('moved'), today) > d])
        print('stale_days=%-3d would flag %d/%d NOW+NEXT rows, %d/%d open rows'
              % (d, flagged, len(board), allflag, len(op)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
