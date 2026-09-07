#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Count every non-ASCII code point in the task corpus and flag the UNMAPPED ones.

``task.py``'s ``ASCII_FOLD`` is the difference between a ``show`` that reads and a ``show``
that prints ``Read \\u00a711.10 before touching the cone`` -- honest (it escapes rather
than drops) and useless in the one surface a session actually consumes, and un-greppable
once pasted. The table is only right RELATIVE TO A CORPUS, so it is measured rather than
guessed: run this after any bulk import and map whatever comes back UNMAPPED with a real
ASCII equivalent, or decide deliberately that an escape is the honest rendering.

``scripts/task.py`` carries that standing instruction in the comment above ``ASCII_FOLD``;
this file is what it means by "re-run it".

PORT NOTE (2026-09-07). Ported out of ``.scratch/tasktool/measure_glyphs.py`` in the pass
that deleted that gitignored directory. Two things changed and nothing else: the default
tree is the repo's tracked ``tasks/`` rather than the scratch ``sandbox-migrated/``, and
``ASCII_FOLD`` is loaded from the sibling ``scripts/task.py`` rather than a scratch copy.
The measurement it originally produced is recorded in
``docs/history/tasktool-scratch-archive-2026-09-07.md``; the numbers below are not
restated here, deliberately -- run it.

Exit code is 1 when anything is UNMAPPED, so this can be used as a check and not only as
a report. It is NOT in the gate: the tracked pin is
``tests/test_tasktool.py::test_banner_is_ascii``, which makes an unmapped glyph fatal for
the BANNER only, because making every unmapped glyph fatal would redden 153 task files.
Widening that pin is a deliberate, separate decision.

Usage: ``python scripts/measure_glyphs.py [tree]`` (default: the repo's ``tasks/``).
Output is ASCII.
"""

import collections
import importlib.util
import io
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_task_module():
    """Load the sibling ``task.py`` by path, for ``ASCII_FOLD``.

    By path rather than by import so this works regardless of cwd and without
    ``scripts/`` being a package.
    """
    spec = importlib.util.spec_from_file_location('taskmod',
                                                  os.path.join(HERE, 'task.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    tasks = argv[0] if argv else os.path.join(ROOT, 'tasks')
    if not os.path.isdir(tasks):
        sys.stderr.write('no such tree: %s\n' % tasks)
        return 2
    fold = load_task_module().ASCII_FOLD
    counts = collections.Counter()
    files = collections.defaultdict(set)
    scanned = 0
    for d in (tasks, os.path.join(tasks, 'closed')):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith('.md'):
                continue
            scanned += 1
            with io.open(os.path.join(d, name), encoding='utf-8') as fh:
                for ch in fh.read():
                    if ord(ch) >= 128:
                        counts[ch] += 1
                        files[ch].add(name)
    print('scanned %d task file(s) under %s' % (scanned, tasks))
    # Instrument control. A scan that reached nothing prints a table of zero rows and
    # exits 0, which reads exactly like "no unmapped glyphs" -- the fail-by-passing shape
    # this repo is built around. Say so instead.
    if not scanned:
        print('NOTHING WAS SCANNED -- this measurement is not evidence about anything.')
        return 1
    unmapped = 0
    print('')
    print('%-9s %-7s %-6s %-8s %s' % ('codepoint', 'count', 'files', 'mapped', 'name'))
    for ch, n in counts.most_common():
        ok = ch in fold
        if not ok:
            unmapped += 1
        print('%-9s %-7d %-6d %-8s %s'
              % ('U+%04X' % ord(ch), n, len(files[ch]),
                 ('-> %r' % fold[ch]) if ok else 'UNMAPPED',
                 unicodedata.name(ch, '?')))
    print('')
    print('%d distinct non-ASCII code point(s), %d UNMAPPED' % (len(counts), unmapped))
    return 1 if unmapped else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
