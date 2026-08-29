"""Gated correctness pin for ``scripts/task.py`` -- the task-tree CLI.

PROVENANCE. This file is a port of ``.scratch/tasktool/test_task.py`` (2800 lines, 41
cases, a stdlib-only self-runner with a ``--sabotage`` mode), rescued into the tracked,
gated tree on 2026-08-29 as item A1 of ``docs/tree-sole-authority-spec-2026-08-29.md``.
The scratch original lived under ``.scratch/``, which this repo treats as already-lost
evidence (``CLAUDE.md``, "anything recorded ONLY there is already lost"): the tool's
entire correctness argument -- including a 22-case sabotage record whose reds were never
reproducible by anyone who did not have that directory -- was one ``rm`` from gone.

WHAT WAS RESCUED, AND THE RECORD IT CARRIES
-------------------------------------------
``.scratch/tasktool/sabotage-log.txt`` (the machine-written transcript, 2026-08-21) and
``.scratch/tasktool/PROOF4.md`` section 9.6 recorded three passes:

  * ``22/22 sabotages produced an attributable red.`` -- 21 table-driven lint sabotages
    plus the inline blind-parser case, each run as: baseline lint GREEN -> narrowest
    plausible weakening -> lint red AND a failure line naming the sabotaged subject ->
    rebuild -> green again.
  * ``4/4`` write-path sabotages -- cases whose subject is not an exit code (a WARNING
    going silent, a ``moved`` stamp being laundered, a flag that is parsed and ignored,
    a validator that returns None for everything). Each patches a COPY of the tool and
    re-runs the test that claims to guard the rule; a test that still passes against the
    broken copy guards nothing.
  * ``LIVE-CORPUS PASS: 4/4 produced an attributable red.`` -- the same shapes against a
    copy of the real corpus, because a sabotage record is evidence ABOUT A CORPUS and
    two of the fixture's claims had already turned out false of the live tree.

All 30 of those are now individual permanent pytest cases below (``docs/sabotage-
procedure.md``'s durability ranking: a permanent test outranks a floor outranks a
docstring). Each carries its expected-red regex and the literal 2026-08-21 observation in
its own docstring. Nothing here is a skip, an xfail or a mark: ``formal/verify.sh``
asserts zero skipped / xfailed / xpassed / deselected, so every case runs every time.

THE ONE CASE THAT COULD NOT BECOME A TEST
-----------------------------------------
``test_migrate_schema14_refusal_is_a_message_not_a_traceback`` drove
``.scratch/tasktool/migrate_schema14.py``, a one-off schema migration script that was
never tracked and does not exist in this tree. Its subject is gone, so the case is
retired here rather than ported, and its literal red output is transcribed instead
(sabotage ``sync_sabotage.py`` S14 -- the ``Refused`` handler bypassed, which is the
state the script shipped in)::

    assert 'Traceback' not in text, 'a Refused surfaced as a traceback:\\n%s' % text
    AssertionError: a Refused surfaced as a traceback:

    rc=1
    Traceback (most recent call last):
      File "<t>\\_sab14.py", line 217, in <module>
        sys.exit(main())
      File "<t>\\_sab14.py", line 138, in main
        return migrate(args)
      File "<t>\\_sab14.py", line 158, in migrate
        where = TM.find_board(store, args.board)
      File "<t>\\task.py", line 2964, in find_board
        raise Refused('--board %s does not exist. sync READS its source; it never '
                      'creates one.' % rel(explicit))
    task.Refused: --board <t>/testtmp/mig14sab/nope.md does not exist. sync READS its
    source; it never creates one.

The ``rc=1`` is the load-bearing half: an uncaught exception also exits 1, which in this
repo's vocabulary means "lint found violations", not "refused". The traceback cost the
message AND the exit code. The equivalent property is still pinned for ``task.py``
itself by ``test_unknown_id_is_a_refusal_not_a_traceback``.

WHY SUBPROCESS AND NOT import+call
----------------------------------
Two contracts under test are only observable across a process boundary: the EXIT CODE
(0 fine / 1 lint violations / 2 refused) and the CONSOLE ENCODING. An in-process test
captures ``sys.stdout`` as a ``str`` and would report green on a board full of U+26A0 --
this repo's house failure mode, an assurance step that fails by PASSING.
``test_board_ascii_under_cp1252`` re-runs ``board`` with ``PYTHONIOENCODING=ascii``
(strict), where one non-ASCII byte is a hard error and a nonzero exit; ``run()``
therefore pops ``PYTHONIOENCODING`` out of the inherited environment so that the test
controls it rather than the harness. The parser's byte-identity contract is checked BOTH
ways: in-process over ``parse_file``/``render_file``, and through the CLI via a
same-session ``touch`` that must leave the file byte-for-byte unchanged.

WHAT THE PORT CHANGED (and why), beyond paths
---------------------------------------------
* Temp trees come from pytest's ``tmp_path_factory`` (session-scoped, autouse) instead of
  ``.scratch/tasktool/testtmp``. Nothing is written inside ``.scratch/`` or the repo.
* ``LIVE_TREE`` was the gitignored ``sandbox-migrated``; it is now the repo's tracked
  ``tasks/``, always reached through ``shutil.copytree`` into tmp. The original is never
  mutated. A MISSING live corpus FAILS (it never skips) -- the scratch original is
  emphatic that a control which silently skips is the house failure mode.
* The tool changed on 2026-08-29 (spec A2/A3): ``brief`` is a 15th frontmatter field,
  ``ack`` REFUSES a non-board task, ``new`` takes ``--id``/``--brief``, ``set``'s flag
  forms are traps, ``tasks/BANNER.md`` is required by ``board`` and by new lint check 12,
  and ``LINT_CHECKS`` is 12 long. Every corpus builder here writes a ``BANNER.md``, the
  ``11 checks`` assertions were re-measured to ``12``, and the ``ack`` cases moved onto
  board-sourced fixtures. Per-case notes are in the cases themselves.
"""

import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..'))
REAL_TASK_PY = os.path.join(REPO_ROOT, 'scripts', 'task.py')

# The tool under test. Kept as a module GLOBAL rather than a constant because the
# write-path sabotages below repoint it at a patched copy (``against()``), which is the
# only way to ask "does this test still pass against a deliberately broken tool?".
TASK_PY = REAL_TASK_PY

# The live corpus. `tasks/` sits at the repo root beside `HANDOFF.md`; `--dir` takes the
# directory that CONTAINS `tasks/`, so the live tree root is the repo root itself.
LIVE_TREE = REPO_ROOT

TMP = None                       # set by the autouse session fixture below

WARN = u'⚠'                 # the repo's trap badge; must never reach stdout raw
ARROW = u'→'
KEY = '2026-08-21'               # every test pins --session, so nothing depends on today

# Written into every fixture tree. `board` REFUSES without it and lint check 12 fails
# without it, so a corpus builder that omits it produces a tree no read op will render.
# The first line must carry a session key (check_banner uses SESSION_KEY_IN_TEXT, an
# unanchored \b...\b search, so ordinary prose around the date is fine).
BANNER_TEXT = (
    '%s -- fixture banner, written by tests/test_tasktool.py.\n'
    '\n'
    'State of play: this is a throwaway corpus. Nothing here outlives the test.\n'
) % KEY


@pytest.fixture(scope='session', autouse=True)
def _tasktool_tmp_root(tmp_path_factory):
    """Point the module-global TMP at a pytest-managed directory.

    Session-scoped and autouse so that the ported zero-argument ``test_*`` functions keep
    working unchanged -- they build their trees through ``fresh()``, which reads TMP.
    """
    global TMP
    TMP = str(tmp_path_factory.mktemp('tasktool'))
    yield
    TMP = None


@pytest.fixture(autouse=True)
def _task_py_is_restored():
    """Guarantee the tool pointer is the REAL tool at the start and end of every test.

    ``against()`` already restores it in a ``finally``, but a global that a test can leave
    dangling would make every LATER test in the session silently run against a sabotaged
    copy -- a failure that presents as an unrelated test going red, or worse, as a green
    run against a broken tool.
    """
    global TASK_PY
    TASK_PY = REAL_TASK_PY
    yield
    TASK_PY = REAL_TASK_PY


# --- module import (for the unit-level parser contract) --------------------------------

def load_module(path, name='taskmod'):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TM = load_module(REAL_TASK_PY)


# --- process driver --------------------------------------------------------------------

def run(root, *argv, **kw):
    """Run task.py against ``root``. Returns (rc, stdout_bytes, stderr_text)."""
    cmd = [sys.executable, TASK_PY, '--dir', root] + list(argv)
    env = dict(os.environ)
    # The harness must not decide the child's console encoding: test_board_ascii_under_
    # cp1252 sets it deliberately, and an inherited value would make that test assert
    # about the environment it inherited rather than about the tool.
    env.pop('PYTHONIOENCODING', None)
    env.update(kw.get('env') or {})
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE, env=env)
    data = kw.get('stdin')
    out, err = proc.communicate(data.encode('utf-8') if data else None)
    return proc.returncode, out, err.decode('utf-8', 'replace')


def out_text(raw):
    return raw.decode('ascii', 'replace')


def out_lines(raw):
    """stdout as a list of lines with the CRLF the Windows console emits normalised away.

    Assertions on EXACT line content (the board's `brief` placement, the size ceiling)
    need this: a trailing ``\\r`` makes every `==` comparison false on Windows and true on
    Linux, which is a test that passes on the machine that did not run it.
    """
    return out_text(raw).replace('\r\n', '\n').replace('\r', '\n').split('\n')


def rj(root, *argv):
    rc, out, err = run(root, *(list(argv) + ['--json']))
    return rc, json.loads(out.decode('utf-8')), err


def lint_text(root, task_py=None):
    """Exit code + combined output of a lint run.

    ``task_py`` defaults to the module global rather than to a captured default argument:
    a default bound at def time would have silently ignored ``against()``'s repointing,
    which is the one thing the write-path sabotages depend on.
    """
    cmd = [sys.executable, task_py or TASK_PY, '--dir', root, 'lint']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, (out + err).decode('utf-8', 'replace')


def first_match(text, pattern):
    for line in text.split('\n'):
        if re.search(pattern, line):
            return line.strip()
    return None


# --- tree fixtures ---------------------------------------------------------------------

# `min_tasks_parsed` is the FIXTURE's floor and it carries ZERO headroom too: good_tree()
# is exactly seven files, so the floor is seven. It was 5 against 7 -- the same defect as
# the shipped 5-against-99, in miniature, and a fixture that models the bug is a fixture
# that cannot detect it. Tests only ever ADD files (`new`) or MOVE them (`close`), so a
# floor at the tree's size never reddens on correct use.
CONFIG = {
    'id_prefix': 'T',
    'labels': ['formal', 'perf', 'docs', 'infra'],
    'budgets': {'NOW': 1, 'NEXT': 3},
    'min_tasks_parsed': 7,
    'stale_days': 14,
}


def write(path, text):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


def read(path):
    with io.open(path, 'rb') as fh:
        return fh.read()


def fresh(name, config=None, banner=BANNER_TEXT):
    """A tasks/ tree with only config + registry + banner. Wiped on every call."""
    assert TMP is not None, 'the session tmp fixture did not run'
    root = os.path.join(TMP, name)
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(os.path.join(root, 'tasks'))
    cfg = dict(CONFIG)
    cfg.update(config or {})
    write(os.path.join(root, 'tasks', 'config.json'),
          json.dumps(cfg, indent=2) + '\n')
    write(os.path.join(root, 'tasks', 'retired-ids.txt'), '')
    if banner is not None:
        write(os.path.join(root, 'tasks', 'BANNER.md'), banner)
    return root


def canon(tid, title, brief='', pri='LATER', size='M', deps=(), related=(), parent='',
          labels=(), source='hand', source_hash='', created=KEY, moved=KEY,
          updated=None, closed='', body='Summary line.\n\n## Log\n'):
    """Render a task file exactly as task.py's canonical writer would.

    `updated` defaults to `moved`, not to KEY: that is what the schema-13 migration
    wrote for a corpus whose every recorded write predated the moved/updated split, and
    a fixture whose default disagrees with the live corpus tests a tree that does not
    exist. `source` defaults to `hand` for the same reason `new` does -- the fixture's
    tasks were typed, not synced.

    `brief` (the 15th field, added 2026-08-29) defaults to EMPTY, which is legal and is
    what `new` writes; it is threaded through here rather than left to render_file's
    ``fm.get`` default so that a test can set one.
    """
    fm = {'id': tid, 'title': title, 'brief': brief, 'pri': pri, 'size': size,
          'deps': list(deps), 'related': list(related), 'parent': parent,
          'labels': list(labels), 'source': source, 'source_hash': source_hash,
          'created': created, 'moved': moved,
          'updated': moved if updated is None else updated, 'closed': closed}
    return TM.render_file(fm, body)


def place(root, tid, slug, closed_dir=False, **kw):
    sub = os.path.join('tasks', 'closed') if closed_dir else 'tasks'
    path = os.path.join(root, sub, '%s-%s.md' % (tid, slug))
    write(path, canon(tid, **kw))
    return path


def good_tree(name):
    """A SEVEN-task tree that lints clean: 1 NOW, 2 NEXT, 2 LATER (one of them a parent),
    HOLD, SOMEDAY. Seven files, and CONFIG's floor is seven -- zero headroom, so a
    sabotage that loses even one file to the scanner is red.

    BANNER.md is NOT one of the seven: it is excluded by exact name at the top level from
    both scanners (``NON_TASK_MD``), which ``test_non_task_md_is_skipped_only_at_the_top``
    pins rather than assumes.
    """
    root = fresh(name)
    os.makedirs(os.path.join(root, 'tasks', 'closed'))
    place(root, 'T1', 'the-now-row', title='the NOW row', pri='NOW', size='L',
          labels=['infra'])
    place(root, 'T2', 'next-alpha', title='next alpha', pri='NEXT', size='M')
    place(root, 'T3', 'next-beta', title='next beta', pri='NEXT', size='S',
          deps=['T2'])
    place(root, 'T4', 'later-gamma', title='later gamma', pri='LATER', size='?',
          parent='T6', labels=['docs'])
    place(root, 'T5', 'held-delta', title='held delta', pri='HOLD', size='M')
    place(root, 'T6', 'the-group', title='the group', pri='LATER', size='L')
    place(root, 'T7', 'someday-eps', title='someday epsilon', pri='SOMEDAY', size='S')
    return root


SYNC_BOARD = u"""# HANDOFF -- a fixture board

## Board

| id | item (%s pointer) | pri | size | deps | moved |
|---|---|---|---|---|---|
| `T1` | the NOW row %s [pointer](docs/README.md) | **NOW** | L | %s | 2026-08-21 |
| `T2` | next alpha | **NEXT** | M | %s | 2026-08-21 |
| `T3` | next beta | **NEXT** | S | `T2` | 2026-08-21 |
| `T4` | later gamma | LATER | ? | %s | 2026-08-21 |
| `T6` | the group | LATER | L | %s | 2026-08-21 |

Closed ids stay retired: `T0`.

## Item blocks -- `NOW` and `NEXT` only

### `T1` -- the NOW row

The summary paragraph as the BOARD states it.

**Read first:** the pointer list.

## Standing traps

Nothing here.
""" % (ARROW, ARROW, u'—', u'—', u'—', u'—')


def sync_tree(name, board=SYNC_BOARD):
    """`good_tree` plus a board above it, with T1..T4/T6 marked `source: board`.

    T5 and T7 stay `hand`: a corpus with no hand-filed tasks cannot show that the quiet
    bucket is quiet, and the whole point of the `source` field is that the two are
    distinguished per task rather than per tree. Since 2026-08-29 it is also the only
    fixture on which `ack` runs at all -- `ack` refuses a `source: hand` task outright.
    """
    root = good_tree(name)
    for tid, slug in (('T1', 'the-now-row'), ('T2', 'next-alpha'), ('T3', 'next-beta'),
                      ('T4', 'later-gamma'), ('T6', 'the-group')):
        p = os.path.join(root, 'tasks', '%s-%s.md' % (tid, slug))
        write(p, read(p).decode('utf-8').replace('source: hand', 'source: board'))
    write(os.path.join(root, 'HANDOFF.md'), board)
    write(os.path.join(root, 'tasks', 'retired-ids.txt'), 'T0\n')
    return root


def seed_hashes(root):
    """The one-off `migrate_schema14.py` step, in miniature: reconcile, then ack.

    Written as a helper rather than baked into `sync_tree` because "a corpus that has
    never been reconciled" is itself a state worth testing, and the fixture would hide it.
    """
    rc, out, err = run(root, 'sync', '--json')
    for item in json.loads(out.decode('utf-8'))['body']:
        rc2, _, err2 = run(root, 'ack', item['id'], '-m', 'seeded', '--session', KEY)
        assert rc2 == 0, err2
    return rc


def live_copy(name):
    """A throwaway copy of the LIVE `tasks/` corpus. The original is never touched."""
    src = os.path.join(LIVE_TREE, 'tasks')
    assert os.path.isdir(src), (
        'the live corpus %s is missing. This is NOT a skip: a control that silently '
        'skips is this repo\'s house failure mode, and a live-corpus sabotage against no '
        'corpus proves nothing.' % src)
    root = os.path.join(TMP, name)
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    shutil.copytree(src, os.path.join(root, 'tasks'))
    return root


def pick(root, closed_dir, preferred):
    """The subject file: ``preferred`` if it is still there, else the first row.

    Hardcoding an id would make the record rot the day that task is renamed or closed --
    the same rot this whole tool exists to delete.
    """
    d = os.path.join(root, 'tasks', 'closed') if closed_dir else os.path.join(root, 'tasks')
    names = sorted(n for n in os.listdir(d)
                   if n.endswith('.md') and n not in TM.NON_TASK_MD)
    for n in names:
        if n.startswith(preferred + '-'):
            return os.path.join(d, n)
    return os.path.join(d, names[0])


def patched_tool(name, old, new):
    """Write a copy of task.py with one substitution applied; assert it applied."""
    src = io.open(REAL_TASK_PY, encoding='utf-8').read()
    out = src.replace(old, new, 1)
    assert out != src, 'sabotage patch did not apply: %r' % old[:60]
    path = os.path.join(TMP, name)
    write(path, out)
    return path


def against(tool_path, case_fn):
    """Run a test case with TASK_PY pointing at a sabotaged copy. Returns the message."""
    global TASK_PY
    saved = TASK_PY
    TASK_PY = tool_path
    try:
        case_fn()
        return None
    except AssertionError as exc:
        return str(exc).split('\n')[0][:300]
    finally:
        TASK_PY = saved


# The `@case` registry is retained from the scratch original so that the ported bodies are
# a diff of paths and expectations rather than a rewrite. It is inert under pytest --
# collection is by name -- and exists only as provenance.
CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# --- the ported cases ------------------------------------------------------------------

@case
def test_roundtrip_is_byte_identical():
    """The parser's core contract: parse then render an untouched file and get the
    SAME BYTES. A YAML library fails this by reordering keys and coercing
    2026-08-21 into a date; the hand-written subset exists to buy exactly this."""
    root = fresh('rt')
    body = (u'Summary with the warn badge %s inline.\n\n'
            u'## Traps\n\n'
            u'%s a trap paragraph.\n\n'
            u'## Read first\n\n'
            u'- `index_v4/core.py::ReachabilityIndex`\n\n'
            u'## Log\n\n'
            u'### 2026-08-21\n\n'
            u'first entry\n') % (WARN, WARN)
    path = os.path.join(root, 'tasks', 'T1-round.md')
    text = canon('T1', 'round trip: with a colon in the title', pri='NOW',
                 brief='a brief that must survive the round trip untouched',
                 deps=['T2', 'T3'], labels=['formal', 'docs'], body=body)
    write(path, text)
    before = read(path)

    pairs, parsed_body = TM.parse_file(text, path)
    fm = dict(pairs)
    assert TM.render_file(fm, parsed_body) == text, 'unit round-trip differs'

    # ... and through the CLI: a same-session `touch` must be a no-op on disk.
    place(root, 'T2', 'two', title='two')
    place(root, 'T3', 'three', title='three')
    rc, out, err = run(root, 'touch', 'T1', '--session', KEY)
    assert rc == 0, (rc, err)
    assert read(path) == before, 'same-session touch was not byte-stable'


@case
def test_new_allocates_by_scanning_and_skips_retired():
    """Ids come from a SCAN of open + closed + retired-ids.txt, never a counter.
    The registry line is the whole point: an id that ever existed can never be
    minted again, so an inbound citation can never be re-pointed at new work."""
    root = fresh('alloc')
    rc, out, err = run(root, 'new', 'first', '--session', KEY)
    assert rc == 0 and out_text(out).startswith('T1 '), (rc, out_text(out), err)

    # A retired id far above the live max must push allocation past it.
    write(os.path.join(root, 'tasks', 'retired-ids.txt'),
          '# ids are never reused\nT9\nP3\nZT-P0-1\n')
    rc, out, err = run(root, 'new', 'second', '--session', KEY)
    assert rc == 0, err
    assert out_text(out).split()[0] == 'T10', out_text(out)

    # A CLOSED file also participates in the scan.
    place(root, 'T30', 'archived', closed_dir=True, title='archived',
          closed=KEY)
    rc, out, err = run(root, 'new', 'third', '--session', KEY)
    assert out_text(out).split()[0] == 'T31', out_text(out)

    # Non-prefix legacy ids are addresses, not allocation input.
    ids = set()
    rc, data, err = rj(root, 'list', '--all')
    for row in data:
        ids.add(row['id'])
    assert 'T9' not in ids and 'P3' not in ids, ids


@case
def test_comment_touch_and_log_append():
    """`comment` is the workhorse -- cheap dated appends are what fix "completed but
    never marked". Two comments in one session must land under ONE heading."""
    root = good_tree('log')
    rc, out, err = run(root, 'comment', 'T2', '-m', 'first note', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'comment', 'T2', '-m', 'second note', '--session', KEY)
    assert rc == 0, err
    text = read(os.path.join(root, 'tasks', 'T2-next-alpha.md')).decode('utf-8')
    assert text.count('### %s' % KEY) == 1, 'duplicate session heading:\n' + text
    assert text.index('first note') < text.index('second note'), 'log not append-only'

    # A different session key gets its own heading, newest LAST. A LETTERED same-day key,
    # not a tomorrow: a future key is refused outright (see session_key), so a fixture
    # that reaches for one is a fixture that will start failing on a date it did not
    # choose.
    rc, out, err = run(root, 'comment', 'T2', '-m', 'later note',
                       '--session', KEY + 'b')
    assert rc == 0, err
    text = read(os.path.join(root, 'tasks', 'T2-next-alpha.md')).decode('utf-8')
    assert text.index('### %s\n' % KEY) < text.index('### %sb' % KEY)

    # -m - reads stdin (multi-line evidence).
    rc, out, err = run(root, 'comment', 'T3', '-m', '-', '--session', KEY,
                       stdin='line one\nline two\n')
    assert rc == 0, err
    text = read(os.path.join(root, 'tasks', 'T3-next-beta.md')).decode('utf-8')
    assert 'line one\nline two' in text, text

    # touch bumps `moved` and nothing else.
    rc, data, err = rj(root, 'show', 'T5')
    before = data
    rc, out, err = run(root, 'touch', 'T5', '--session', KEY + 'c')
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T5')
    assert data['moved'] == KEY + 'c'
    for k in ('title', 'brief', 'pri', 'size', 'deps', 'labels', 'created', 'closed',
              'body'):
        assert data[k] == before[k], k


@case
def test_close_moves_stamps_and_reports():
    """close: message REQUIRED, file MOVES, `closed` stamped, and the two derived
    facts a human never remembers get PRINTED -- what this unblocked, and whether
    the parent group is now empty."""
    root = good_tree('close')

    # -m is required by argparse: omitting it is exit 2, not a silent close.
    rc, out, err = run(root, 'close', 'T2')
    assert rc == 2, (rc, out_text(out), err)
    assert os.path.exists(os.path.join(root, 'tasks', 'T2-next-alpha.md'))

    rc, out, err = run(root, 'close', 'T2', '-m', 'landed in abc1234',
                       '--session', KEY)
    assert rc == 0, err
    text = out_text(out)
    assert not os.path.exists(os.path.join(root, 'tasks', 'T2-next-alpha.md'))
    moved_to = os.path.join(root, 'tasks', 'closed', 'T2-next-alpha.md')
    assert os.path.exists(moved_to), text
    body = read(moved_to).decode('utf-8')
    assert 'closed: %s' % KEY in body, body
    assert 'landed in abc1234' in body
    # T3 depended on T2 alone, so closing T2 made it ready -- and says so.
    assert 'now ready' in text and 'T3' in text, text

    # The parent sweep: T4's parent is T6 and T4 is its only child.
    rc, out, err = run(root, 'close', 'T4', '-m', 'done', '--session', KEY)
    assert rc == 0, err
    assert 'ZERO open children' in out_text(out), out_text(out)

    # Closing a parent that still has open children is refused (lint 7 would fire).
    place(root, 'T8', 'kid', title='kid', parent='T6')
    rc, out, err = run(root, 'close', 'T6', '-m', 'group done', '--session', KEY)
    assert rc == 2 and 'T8' in err, (rc, err)


@case
def test_reopen_inverts_close():
    root = good_tree('reopen')
    run(root, 'close', 'T3', '-m', 'closed by mistake', '--session', KEY)
    rc, out, err = run(root, 'reopen', 'T3')
    assert rc == 2, 'reopen without -m must be refused'
    rc, out, err = run(root, 'reopen', 'T3', '-m', 'was not actually done',
                       '--session', KEY + 'b')
    assert rc == 0, err
    path = os.path.join(root, 'tasks', 'T3-next-beta.md')
    assert os.path.exists(path)
    text = read(path).decode('utf-8')
    assert '\nclosed:\n' in text, text
    assert 'was not actually done' in text
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # Reopening into a full budget is refused, naming the offending rows.
    run(root, 'close', 'T1', '-m', 'shipped', '--session', KEY)
    run(root, 'promote', 'T2', 'NOW', '--session', KEY)
    rc, out, err = run(root, 'reopen', 'T1', '-m', 'not shipped', '--session', KEY)
    assert rc == 2 and 'NOW would have 2 rows' in err, err


@case
def test_promote_refuses_budget_and_demote_is_atomic():
    """The budget is enforced at WRITE TIME, not merely reported by lint -- a
    mechanical refusal beats a doc warning. --demote applies both edits or
    neither."""
    root = good_tree('promote')
    rc, out, err = run(root, 'promote', 'T4', 'NOW', '--session', KEY)
    assert rc == 2, (rc, out_text(out))
    assert 'NOW would have 2 rows' in err and 'T1' in err, err
    assert '--demote' in err, 'a refusal must say what to pass instead'
    rc, data, err2 = rj(root, 'show', 'T4')
    assert data['pri'] == 'LATER', 'a refused promote still wrote the file'

    # NEXT cap: two NEXT rows already, promoting two more must break at the third.
    run(root, 'promote', 'T5', 'NEXT', '--session', KEY)
    rc, out, err = run(root, 'promote', 'T7', 'NEXT', '--session', KEY)
    assert rc == 2 and 'NEXT would have 4 rows' in err, err

    # With --demote both land.
    rc, out, err = run(root, 'promote', 'T4', 'NOW', '--demote', 'T1', 'NEXT',
                       '--session', KEY)
    assert rc != 0, 'that demote overflows NEXT and must also be refused'
    rc, out, err = run(root, 'promote', 'T4', 'NOW', '--demote', 'T1', 'LATER',
                       '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'list', '--all')
    pris = dict((r['id'], r['pri']) for r in data)
    assert pris['T4'] == 'NOW' and pris['T1'] == 'LATER', pris

    # Atomicity: a refusal must leave BOTH files untouched. Here NOW stays at 1
    # (T4 is demoted out of it) but the demotion target overflows NEXT to 4, so the
    # PAIR is illegal while the promotion alone would have been fine -- exactly the
    # shape that lands half a swap if the writes are not staged.
    paths = (os.path.join(root, 'tasks', 'T6-the-group.md'),
             os.path.join(root, 'tasks', 'T4-later-gamma.md'))
    before = tuple(read(p) for p in paths)
    rc, out, err = run(root, 'promote', 'T6', 'NOW', '--demote', 'T4', 'NEXT',
                       '--session', KEY)
    assert rc == 2, (rc, out_text(out))
    assert 'NEXT would have 4 rows' in err, err
    assert tuple(read(p) for p in paths) == before, 'a refused --demote landed half a swap'


@case
def test_dep_add_refuses_cycle_and_unknown_id():
    root = good_tree('dep')
    rc, out, err = run(root, 'dep', 'add', 'T4', 'T99', '--session', KEY)
    assert rc == 2 and 'T99' in err, err
    rc, data, err2 = rj(root, 'show', 'T4')
    assert data['deps'] == [], data['deps']

    # T3 -> T2 exists; adding T2 -> T3 closes the loop and must be refused.
    rc, out, err = run(root, 'dep', 'add', 'T2', 'T3', '--session', KEY)
    assert rc == 2 and 'cycle' in err, err
    rc, data, err2 = rj(root, 'show', 'T2')
    assert data['deps'] == [], data['deps']

    # Self-dep is the degenerate cycle.
    rc, out, err = run(root, 'dep', 'add', 'T2', 'T2', '--session', KEY)
    assert rc == 2, err

    # A legal edge lands, and rm takes it away again.
    rc, out, err = run(root, 'dep', 'add', 'T4', 'T2', '--session', KEY)
    assert rc == 0, err
    rc, data, err2 = rj(root, 'show', 'T4')
    assert data['deps'] == ['T2']
    rc, out, err = run(root, 'dep', 'rm', 'T4', 'T2', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_ready_excludes_hold_and_someday():
    """HOLD and SOMEDAY are excluded BY DEFINITION, not by a flag someone can turn
    off: a HOLD item with satisfied deps is still held."""
    root = good_tree('ready')
    rc, data, err = rj(root, 'ready')
    ids = [r['id'] for r in data]
    assert 'T5' not in ids, 'HOLD leaked into ready: %s' % ids
    assert 'T7' not in ids, 'SOMEDAY leaked into ready: %s' % ids
    assert 'T3' not in ids, 'T3 has an OPEN dep (T2) and is not ready'
    # T2 (NEXT, no deps), T4/T6 (LATER, no deps) and T1 (NOW) are the whole set.
    assert set(ids) == set(['T1', 'T2', 'T4', 'T6']), ids

    rc, out, err = run(root, 'ready')
    assert 'HOLD and SOMEDAY are excluded' in out_text(out)

    # Closing the dep makes T3 ready; HOLD/SOMEDAY still do not appear.
    run(root, 'close', 'T2', '-m', 'done', '--session', KEY)
    rc, data, err = rj(root, 'ready')
    ids = [r['id'] for r in data]
    assert 'T3' in ids and 'T5' not in ids and 'T7' not in ids, ids


@case
def test_board_ascii_under_cp1252():
    """The board must be pure ASCII even when the task body carries the warn glyph.

    This is run under PYTHONIOENCODING=ascii (errors=strict), which is STRICTER
    than the cp1252 console it models: any non-ASCII byte becomes a
    UnicodeEncodeError and a nonzero exit. Checked in-process it would pass
    trivially, which is the failure-by-passing this repo names as its house mode.

    PORT NOTE: the banner is now part of the board's output and is printed VERBATIM,
    so it is part of the ASCII surface too -- a UTF-8 banner is exactly the shape that
    would newly break a cp1252 console. The fixture banner therefore carries the warn
    badge as well, and the fold must cover it.
    """
    root = fresh('ascii', banner=(u'%s -- fixture banner with the warn badge %s.\n'
                                  % (KEY, WARN)))
    body = (u'%s The NOW row body carries the warn badge, an em dash -- '
            u'and a right arrow %s, because the repo docs do.\n\n'
            u'## Traps\n\n%s watch out.\n\n## Log\n') % (WARN, ARROW, WARN)
    write(os.path.join(root, 'tasks', 'T1-warned.md'),
          canon('T1', u'a title with %s in it' % WARN, pri='NOW',
                brief=u'a brief with %s in it' % WARN, body=body))
    place(root, 'T2', 'plain', title='plain', pri='NEXT')

    for argv in (['board'], ['show', 'T1'], ['list', '--all'], ['ready']):
        rc, out, err = run(root, *argv, env={'PYTHONIOENCODING': 'ascii'})
        assert rc == 0, ('%s exited %d\n%s' % (argv, rc, err))
        assert all(b < 128 for b in out), '%s emitted a non-ASCII byte' % argv
        assert err == '' or 'UnicodeEncodeError' not in err, err
    rc, out, err = run(root, 'board', env={'PYTHONIOENCODING': 'ascii'})
    text = out_text(out)
    assert '(!)' in text, 'the warn badge should be FOLDED, not dropped:\n' + text
    assert '\\u' not in text, 'the mapped glyphs should not need \\u escaping'
    # The file itself is untouched UTF-8 -- the fold is a view, not an edit.
    raw = read(os.path.join(root, 'tasks', 'T1-warned.md'))
    assert WARN.encode('utf-8') in raw


@case
def test_board_footer_names_every_advertised_verb():
    """The footer must name every op the board's own body points at, and only real ops.

    Filed because `ready` was missing from it while the board printed a ready COUNT three
    lines above -- the reader was told the number and not the verb (INTEGRATION.md section
    5.2). Fixing the string alone would leave the next omission to the next reader, so the
    property is asserted instead of the text: any command the board advertises in its body
    (`show <id>` under the NOW row, `ready` on the ready line) has to appear on the footer,
    and every footer entry has to be a subcommand `task.py` actually accepts.

    Sabotage, run before this was believed (fixwork/footer_sabotage.py; `<t>/` elides the
    absolute checkout path, as elsewhere in this file) -- drop 'ready' from NEXT_COMMANDS,
    which is literally the shipped defect::

        AssertionError: the board advertises `python <t>/task.py ready` in its body but
        the footer does not name 'ready'. A reader is told the number and not the verb.

    and the second half, `NEXT_COMMANDS = (... 'reddy')`::

        AssertionError: footer names 'reddy', which is not a task.py subcommand (known:
        ['board', 'close', 'comment', 'counts', 'dep', 'lint', 'list', 'new', 'promote',
        'ready', 'reopen', 'set', 'show', 'touch'])

    Baseline before and after each: `27 test(s), 0 failed`, so both reds are attributable
    to the edit. (The `known:` list in that transcript predates `ack` and `sync`; the
    assertion derives it from the live parser, so it did not need re-recording.)
    """
    root = good_tree('footer')
    rc, out, err = run(root, 'board')
    assert rc == 0, err
    text = out_text(out)
    body, footer = text.split('\nnext   ', 1)
    footer = 'next   ' + footer

    ops = set(TM.build_parser()._subparsers._group_actions[0].choices)
    for entry in TM.NEXT_COMMANDS:
        verb = entry.split()[0]
        assert verb in ops, ('footer names %r, which is not a task.py subcommand '
                             '(known: %s)' % (verb, sorted(ops)))
        assert entry in footer, 'footer lost %r:\n%s' % (entry, footer)

    # Every verb the BODY advertises must be reachable from the footer too.
    for verb in ('show', 'ready'):
        assert verb in body, 'the board body no longer advertises %r:\n%s' % (verb, body)
        assert verb in [e.split()[0] for e in TM.NEXT_COMMANDS], (
            'the board advertises `python %s %s` in its body but the footer does not '
            'name %r. A reader is told the number and not the verb.'
            % (TASK_PY, verb, verb))

    # Wrapping, not truncation. Measured against the prog name the graduated tool actually
    # carries ("scripts/task.py"), NOT against this harness's absolute path -- the harness
    # invokes task.py by its full path, so asserting on that would be asserting about the
    # length of a checkout directory.
    lines = TM.footer_lines('scripts/task.py')
    assert len(lines) > 1, 'four commands should wrap, not sit on one long line'
    for line in lines:
        assert len(line) + 7 <= 85, 'footer line is %d chars: %r' % (len(line), line)
    assert '...' not in footer, 'a truncated footer is a command that does not run'


@case
def test_lint_clean_on_a_good_tree():
    """A check nobody can get green is as dead as one that never fires
    (docs/sabotage-procedure.md, "run the check against a CLEAN tree first").

    PORT NOTE: the count was `clean (11 checks` in the scratch original. RE-MEASURED
    2026-08-29 against the live tool -- `LINT_CHECKS` gained `check_banner` (check 12),
    so the literal is now `clean (12 checks`. The length is asserted independently of
    the printed string so that a check added without updating the header, or a header
    hard-coded past the list, is red rather than merely inconsistent.
    """
    root = good_tree('clean')
    assert len(TM.LINT_CHECKS) == 12, [c.__name__ for c in TM.LINT_CHECKS]
    rc, out, err = run(root, 'lint')
    assert rc == 0, 'clean tree is not green:\n%s\n%s' % (out_text(out), err)
    assert 'clean (12 checks' in out_text(out), out_text(out)
    # TWELVE, not eleven, since 2026-08-29. A clean tree must also report NO warnings --
    # a check that warns about a tree with nothing wrong is a check the next reader
    # learns to scroll past.
    assert 'WARN' not in out_text(out) + err, (out_text(out), err)
    rc, data, err = rj(root, 'lint')
    assert data['clean'] is True and data['violations'] == [], data
    assert data['parsed'] == 7, data
    assert data['checks'] == len(TM.LINT_CHECKS), data


@case
def test_id_is_the_address_not_the_path():
    """A rename or an archive move can never rot an inbound reference."""
    root = good_tree('address')
    src = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    dst = os.path.join(root, 'tasks', 'T4-renamed-by-hand.md')
    os.rename(src, dst)
    rc, data, err = rj(root, 'show', 'T4')
    assert data['id'] == 'T4', data
    # A filename that disagrees with the id is still lint-clean here (it starts
    # with "T4-"), but one that does not is check 3's business.
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_regression_empty_message_is_refused():
    """BUG FOUND 2026-08-21. argparse enforces that -m is PRESENT, not that it says
    anything, so ``close T2 -m ""`` closed the task and appended a dated Log heading
    with nothing under it. Observed before the fix::

        T2 closed 2026-08-21 -> .../tasks/closed/T2-beta.md
        rc=0

    A close with no outcome evidence, reached through the one op whose entire point
    is requiring evidence."""
    root = good_tree('emptymsg')
    for argv in (['close', 'T2', '-m', ''], ['close', 'T2', '-m', '   '],
                 ['comment', 'T2', '-m', ''], ['reopen', 'T2', '-m', '']):
        rc, out, err = run(root, *(argv + ['--session', KEY]))
        assert rc == 2, (argv, rc, out_text(out))
        assert 'empty message' in err or 'not closed' in err, (argv, err)
    assert os.path.exists(os.path.join(root, 'tasks', 'T2-next-alpha.md'))
    rc, out, err = run(root, 'close', 'T2', '-m', '-', '--session', KEY, stdin='\n\n')
    assert rc == 2, (rc, out_text(out))


@case
def test_regression_title_stays_on_one_line():
    """BUG FOUND 2026-08-21. A pasted two-line title was written straight into the
    frontmatter, and the damage was not local: EVERY op scans the tree, so the whole
    store became unusable, ``new`` included. Observed before the fix::

        task new: unparseable task file
          ...T4-line-one-line-two.md:4: not "key: value" -- 'line two'
    """
    root = good_tree('multiline')
    rc, out, err = run(root, 'new', 'line one\nline two', '--session', KEY)
    assert rc == 2 and 'ONE line' in err, (rc, err)
    rc, out, err = run(root, 'set', 'T2', 'title', 'a\nb', '--session', KEY)
    assert rc == 2 and 'ONE line' in err, (rc, err)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err
    rc, out, err = run(root, 'new', 'x' * 101, '--session', KEY)
    assert rc == 2 and 'cap 100' in err, err


@case
def test_regression_bracketed_title_is_not_a_list():
    """BUG FOUND 2026-08-21. ``parse_value`` sniffed the BRACKETS instead of asking
    the key, so ``new "[wip]"`` wrote ``title: [wip]`` and read it back as the list
    ``['wip']``. Observed before the fix::

        task show: unparseable task file
          ...T5-wip.md: 'title' must be a plain scalar, not a list

    and the file was unreadable by every op from the moment it was created. A
    bracketed title is entirely ordinary ("[wip]", "[draft] rework the gate")."""
    root = good_tree('bracket')
    for title in ('[wip]', '[draft] rework the gate', '[a, b]', '[]'):
        rc, out, err = run(root, 'new', title, '--session', KEY)
        assert rc == 0, (title, err)
        new_id = out_text(out).split()[0]
        rc, data, err = rj(root, 'show', new_id)
        assert data['title'] == title, (title, data['title'])
        assert isinstance(data['title'], str), data['title']
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # The converse must still hold: a hand-typed non-list `deps` is a parse error.
    p = os.path.join(root, 'tasks', 'T3-next-beta.md')
    write(p, read(p).decode('utf-8').replace('deps: [T2]', 'deps: T2'))
    rc, out, err = run(root, 'lint')
    assert rc == 1 and 'must be a flow list' in (out_text(out) + err), out_text(out) + err


@case
def test_regression_session_key_cannot_backdate_moved_below_created():
    """BUG FOUND 2026-08-21 (audit T4). ``--session`` was validated for SHAPE and not
    for its RELATION to ``created``, so a write op could manufacture the exact state
    its own lint rejects -- the tool sabotaging its own gate. Observed before the fix::

        $ python task.py touch P10 --session 2026-01-05
        P10 moved 2026-01-05
        $ python task.py lint          # exit 1
        FAIL: .../P10-....md: moved 2026-01-05 is before created 2026-08-16.

    Exit 0 on the write, red on the very next lint, on the file the tool had just
    written. The property under test is the general one: NO write op may leave the
    tree lint-red."""
    root = good_tree('backdate')
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')  # created 2026-08-21
    before = read(path)
    for argv in (['touch', 'T4'], ['comment', 'T4', '-m', 'note'],
                 ['set', 'T4', 'size', 'L'], ['dep', 'add', 'T4', 'T2'],
                 ['promote', 'T4', 'LATER'], ['close', 'T4', '-m', 'done']):
        rc, out, err = run(root, *(argv + ['--session', '2026-01-05']))
        assert rc == 2, (argv, rc, out_text(out), err)
        assert 'earlier than' in err and 'created 2026-08-21' in err, (argv, err)
        assert read(path) == before, '%s wrote the file it refused' % argv[0]
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # The same key and any LATER key still work -- this refuses backdating, not the
    # flag. A lettered same-day key sorts AFTER the bare one, so it must be accepted.
    for key in (KEY, KEY + 'b', KEY + 'z'):
        rc, out, err = run(root, 'touch', 'T4', '--session', key)
        assert rc == 0, (key, err)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # THE OTHER DIRECTION, added 2026-08-21 (PROOF2.md section 4): a FUTURE key was
    # accepted silently -- `--session 2026-08-22` -> `P3 logged under 2026-08-22`, rc=0,
    # lint clean. Backdating was blocked relationally, which left forward-stamping as the
    # only remaining way to write a `moved` that no ledger entry can justify, and it reads
    # as FRESH to every staleness check until that day arrives. A session key names an
    # entry in docs/history/session-log.md; tomorrow's cannot exist yet.
    before = read(path)
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    far = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()
    for key in (tomorrow, tomorrow + 'b', far):
        rc, out, err = run(root, 'touch', 'T4', '--session', key)
        assert rc == 2, ('future key %s was accepted (rc=%d): %s'
                         % (key, rc, out_text(out)))
        assert 'in the FUTURE' in err, (key, err)
        assert read(path) == before, 'a refused future key still wrote the file'
    # ... and TODAY is not the future. The off-by-one here is the whole risk of the
    # check: a control that refuses today's own key would break every write op at once.
    rc, out, err = run(root, 'touch', 'T4', '--session',
                       datetime.date.today().isoformat() + 'z')
    assert rc == 0, ("today's own key must stay legal: %s" % err)

    # AND THE FLAG IS ACCEPTED ON BOTH SIDES OF THE VERB (same section). `--dir` is
    # global, so the natural transcription of the stub's line put `--session` before the
    # subcommand and got `error: argument op: invalid choice`, TRUE rc=2 -- a documented
    # instruction that fails when typed the obvious way.
    key = KEY + 'y'
    rc, out, err = run(root, 'touch', 'T4', '--session', key)      # after the verb
    assert rc == 0, err
    cmd = [sys.executable, TASK_PY, '--dir', root, '--session', key, 'touch', 'T4']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert proc.returncode == 0, ('--session before the verb was rejected: %s'
                                  % err.decode('utf-8', 'replace'))
    assert key in out.decode('ascii', 'replace'), out
    # Given twice with DIFFERENT values there is no defensible winner, so it is refused
    # rather than silently resolved.
    cmd = [sys.executable, TASK_PY, '--dir', root, '--session', KEY + 'y', 'touch', 'T4',
           '--session', KEY + 'x']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert proc.returncode == 2, out
    assert 'twice with different values' in err.decode('utf-8', 'replace'), err
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_regression_a_lettered_created_does_not_lock_out_the_same_day():
    """BUG FOUND 2026-08-21d, on the COLD-SESSION DEMO -- i.e. by the single path this
    whole tool exists to serve. The migration stamps `created` from each board row's
    `moved`, and lettered board keys are normal, so the NOW row landed as
    `created: 2026-08-21b`. A letterless derived key sorts BEFORE it, so every write op
    with no explicit --session was refused for the rest of that calendar day::

        $ python scripts/task.py comment P3 -m "..."
        task comment: REFUSED
          --session 2026-08-21 is earlier than P3's created 2026-08-21b. [...]

    and nothing in HANDOFF-stub.md tells a cold session that --session exists. The fix
    (`resolve_key`) ADOPTS the key the task already carries when the clash is purely the
    letter on the same day. Three things are pinned, because the first attempt got two of
    them right and the third wrong -- it promoted only inside `stamp_and_render`, so the
    file said `moved: <today>b` under a `### <today>` log heading while printing
    `logged under <today>`: one write, three opinions about which session it was.

    Uses TODAY's real date on purpose. Every other case pins --session so nothing depends
    on the clock; this one is ABOUT the derived key, so pinning it would test nothing."""
    today = datetime.date.today().isoformat()
    root = fresh('sameday')
    os.makedirs(os.path.join(root, 'tasks', 'closed'))
    place(root, 'T1', 'the-now-row', title='the NOW row', pri='NOW', size='L',
          created=today + 'b', moved=today + 'b')
    for tid, slug in (('T2', 'a'), ('T3', 'b'), ('T4', 'c'), ('T5', 'd'), ('T6', 'e'),
                      ('T7', 'f')):
        place(root, tid, slug, title='row ' + slug, created=today, moved=today)

    rc, out, err = run(root, 'comment', 'T1', '-m', 'cold-session pickup')
    assert rc == 0, 'refused a derived key on a same-day lettered row: %s' % err
    # (a) the printed confirmation, (b) the frontmatter, (c) the log heading must all
    # name the SAME session.
    assert out_text(out).strip() == 'T1 logged under %sb' % today, out_text(out)
    text = read(os.path.join(root, 'tasks', 'T1-the-now-row.md')).decode('utf-8')
    assert 'moved: %sb' % today in text, text[:400]
    assert '### %sb' % today in text, text[-400:]
    assert ('### %s' % today + chr(10)) not in text, 'wrote a bare-key heading too'
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # An EXPLICIT backdated key is still refused -- the reuse must not become a general
    # "quietly fix the key" behaviour, which would re-open the audit-T4 hole above.
    rc, out, err = run(root, 'touch', 'T1', '--session', '2026-01-05')
    assert rc == 2 and 'earlier than' in err, (rc, err)
    # And a row WITHOUT a lettered created is untouched: it still stamps the bare key.
    rc, out, err = run(root, 'touch', 'T2')
    assert rc == 0 and out_text(out).strip() == 'T2 moved %s' % today, out_text(out)


@case
def test_regression_set_parent_refuses_a_closed_parent():
    """BUG FOUND 2026-08-21 (audit T5). ``set ID parent <closed-id>`` was accepted and
    created precisely the state ``close`` refuses without ``--force``, so two write ops
    disagreed about one invariant. Observed before the fix::

        $ python task.py set P10 parent P1        # P1 is under closed/
        P10 parent = P1  (moved 2026-08-21)
        $ python task.py lint          # exit 1
        FAIL: .../P1-....md is CLOSED but still has open children ['P10']
    """
    root = good_tree('closedparent')
    run(root, 'close', 'T7', '-m', 'archived', '--session', KEY)
    path = os.path.join(root, 'tasks', 'T5-held-delta.md')
    before = read(path)

    rc, out, err = run(root, 'set', 'T5', 'parent', 'T7', '--session', KEY)
    assert rc == 2, (rc, out_text(out), err)
    assert 'is CLOSED' in err and 'T5' in err, err
    assert read(path) == before, 'a refused set still wrote the file'

    # `new --parent <closed-id>` is the same door from the other side.
    rc, out, err = run(root, 'new', 'orphan', '--parent', 'T7', '--session', KEY)
    assert rc == 2 and 'is CLOSED' in err, (rc, err)

    # A CLOSED child under a closed parent is an archived group, and stays legal.
    run(root, 'close', 'T5', '-m', 'held no longer', '--session', KEY)
    rc, out, err = run(root, 'set', 'T5', 'parent', 'T7', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_regression_write_ops_refuse_an_already_invalid_record():
    """BUG FOUND 2026-08-21 (audit T6). Write ops trusted whatever the parser handed
    them, so a hand-corrupted record was re-emitted verbatim through the canonical
    writer with an exit 0 and no mention of any bad field. Observed before the fix, on
    a file carrying ``pri: URGENT!!``, ``size: XXL``, ``created: last tuesday``::

        $ python task.py touch P10
        P10 moved 2026-08-21
        rc=0

    The tool countersigned the damage. It must refuse, name every bad field, and NOT
    auto-repair -- there is no correct value to invent for "last tuesday", and guessing
    one erases the evidence."""
    root = good_tree('invalid')
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(path, canon('T4', 'later gamma', pri='URGENT!!', size='XXL',
                      created='last tuesday', labels=['Infra']))
    before = read(path)

    for argv in (['touch', 'T4'], ['comment', 'T4', '-m', 'note'],
                 ['set', 'T4', 'size', 'L'], ['promote', 'T4', 'LATER'],
                 ['dep', 'add', 'T4', 'T2'], ['close', 'T4', '-m', 'done']):
        rc, out, err = run(root, *(argv + ['--session', KEY]))
        assert rc == 2, (argv, rc, out_text(out), err)
        assert 'ALREADY invalid' in err, (argv, err)
        for bad in ("pri 'URGENT!!'", "size 'XXL'", "created is 'last tuesday'",
                    "label 'Infra'"):
            assert bad in err, (argv, bad, err)
        assert 'lint' in err, 'the refusal must point at the gate: %s' % err
        assert read(path) == before, '%s rewrote an invalid record' % argv[0]

    # It refuses only what lint already calls red -- a write op that refuses something
    # lint accepts would be a second, undocumented schema.
    rc, out, err = run(root, 'lint')
    assert rc == 1, out_text(out) + err

    # Reads still WORK on it: a viewer that hides damage is useless exactly when needed.
    rc, out, err = run(root, 'show', 'T4')
    assert rc == 0 and 'URGENT!!' in out_text(out), (rc, out_text(out), err)

    # And a hand repair unblocks every op again -- the refusal is not a dead end.
    write(path, canon('T4', 'later gamma', pri='LATER', size='?', created=KEY,
                      labels=['infra']))
    rc, out, err = run(root, 'touch', 'T4', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_regression_reopen_names_the_row_it_refused():
    """BUG FOUND 2026-08-21 (audit T2). ``reopen``'s budget refusal reused ``new``'s
    placeholder row, so it named a task the caller had not mentioned and omitted the
    one they had. Observed before the fix::

        NOW would have 2 rows, budget 1: P3 (leg 7 4c-ii ...); <new> ((the new task))

    A caller cannot tell from that which reopen just failed."""
    root = good_tree('reopenname')
    run(root, 'close', 'T1', '-m', 'shipped', '--session', KEY)
    run(root, 'promote', 'T2', 'NOW', '--session', KEY)
    rc, out, err = run(root, 'reopen', 'T1', '-m', 'not shipped after all',
                       '--session', KEY)
    assert rc == 2, (rc, out_text(out))
    assert '<new>' not in err and '(the new task)' not in err, err
    assert 'T1 (the NOW row)' in err, err
    assert 'T2 (next alpha)' in err, 'the blocking row must be named too: %s' % err
    assert os.path.exists(os.path.join(root, 'tasks', 'closed', 'T1-the-now-row.md'))


@case
def test_regression_zero_now_message_is_true_of_zero():
    """BUG FOUND 2026-08-21 (audit T3). ``check_pri_budget`` printed the ``> 1``
    branch's explanation on a count of ZERO, beside a bare ``-`` where the id list
    goes. Observed before the fix::

        FAIL: found 0 open NOW row(s) -, must be exactly 1. NOW is what an unassigned
        session picks up; two of them is no ranking at all.

    A FAIL that describes a situation the tree is not in, in the text a session pastes
    as evidence. One check, one message, true on both sides of the ``!=``."""
    root = good_tree('nowmsg')
    run(root, 'promote', 'T1', 'LATER', '--session', KEY)
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    line = [l for l in text.split('\n') if 'open NOW row(s)' in l]
    assert len(line) == 1, text
    assert 'found 0 open NOW row(s) (none)' in line[0], line[0]
    assert 'two of them' not in line[0], line[0]

    # The same message on the other side of the !=, now naming both rows.
    run(root, 'promote', 'T1', 'NOW', '--session', KEY)
    p = os.path.join(root, 'tasks', 'T5-held-delta.md')
    write(p, read(p).decode('utf-8').replace('pri: HOLD', 'pri: NOW'))
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    line = [l for l in text.split('\n') if 'open NOW row(s)' in l]
    assert rc == 1 and len(line) == 1, text
    assert 'found 2 open NOW row(s) (T1, T5)' in line[0], line[0]


@case
def test_regression_comment_keeps_the_blank_line_before_the_next_section():
    """BUG FOUND 2026-08-21 (audit T7). ``append_log`` worked on the raw line list with
    no notion of where the Log SECTION ends. On a file with a section after ``## Log``
    the same-key branch ate the blank line before it, once per append::

        ...pointer.\\n\\nappended\\n## Notes\\n\\ntrailing section...
        ...pointer.\\n\\nappended\\n\\nsecond\\n## Notes\\n\\ntrailing section...

    and the new-key branch appended at end of BODY, i.e. under ``## Notes`` rather than
    under ``## Log``. The trailing section was never eaten; the file simply drifted out
    of canonical shape and the ledger stopped being contiguous."""
    root = good_tree('logspacing')
    body = ('Summary.\n\n## Read first\n\n- pointer.\n\n'
            '## Log\n\n### %s\n\nexisting\n\n'
            '## Notes\n\ntrailing section that must not be eaten\n' % KEY)
    place(root, 'T9', 'log-not-last', title='log is not last', body=body)
    path = os.path.join(root, 'tasks', 'T9-log-not-last.md')

    run(root, 'comment', 'T9', '-m', 'appended', '--session', KEY)
    text = read(path).decode('utf-8')
    assert 'existing\n\nappended\n\n## Notes\n' in text, repr(text)

    run(root, 'comment', 'T9', '-m', 'second', '--session', KEY)
    text = read(path).decode('utf-8')
    assert 'appended\n\nsecond\n\n## Notes\n' in text, repr(text)
    assert text.count('### %s' % KEY) == 1, repr(text)

    # A NEW session key belongs inside the Log section, before ## Notes -- not at the
    # end of the file under someone else's heading.
    run(root, 'comment', 'T9', '-m', 'third', '--session', KEY + 'b')
    text = read(path).decode('utf-8')
    assert text.index('### %sb' % KEY) < text.index('## Notes'), repr(text)
    assert 'third\n\n## Notes\n' in text, repr(text)
    assert text.endswith('trailing section that must not be eaten\n'), repr(text)
    assert '\n\n\n' not in text, 'double blank line: %r' % text
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # Instrument control: Log-LAST files (every file this tool writes) are unchanged
    # by the fix, so the byte-identity contract still holds for them.
    rc, out, err = run(root, 'comment', 'T6', '-m', 'ordinary', '--session', KEY)
    assert rc == 0, err
    text = read(os.path.join(root, 'tasks', 'T6-the-group.md')).decode('utf-8')
    assert text.endswith('## Log\n\n### %s\n\nordinary\n' % KEY), repr(text)


@case
def test_lint_prints_one_violation_per_line():
    """The lint text IS the evidence a sabotage record quotes, so it has to be
    pasteable: one FAIL per line, no interleaved blanks."""
    root = good_tree('fmt')
    sab_labels(root)
    sab_filenames(root)
    rc, out, err = run(root, 'lint')
    assert rc == 1
    fails = [l for l in err.split('\n') if l.strip().startswith('FAIL:')]
    assert len(fails) == 2, err
    body = err[err.index('FAIL:'):].rstrip('\n')
    assert '\n\n' not in body, 'blank line between violations:\n%r' % body


@case
def test_unknown_id_is_a_refusal_not_a_traceback():
    root = good_tree('unknown')
    for argv in (['show', 'T404'], ['touch', 'T404'], ['comment', 'T404', '-m', 'x'],
                 ['close', 'T404', '-m', 'x'], ['promote', 'T404', 'NOW']):
        rc, out, err = run(root, *argv)
        assert rc == 2, (argv, rc, out_text(out), err)
        assert 'Traceback' not in err, (argv, err)
        assert 'T404' in err, (argv, err)


@case
def test_counts_is_the_one_home_for_a_live_figure():
    """The `counts` op exists to DELETE a restated number, not to add a feature.

    task.py's docstring said "83 task file(s)" while the live tree held 99 -- ZT-P3-5
    recurring inside the tool built to cure it. `counts` derives the figure, and every
    other surface is expected to point at it rather than repeat it.
    """
    root = good_tree('counts')
    rc, data, err = rj(root, 'counts')
    assert rc == 0, err
    assert data['total'] == 7 and data['open'] == 7 and data['closed'] == 0, data
    assert data['disk_total'] == data['total'], data
    assert data['floor_now'] == 7, data
    assert data['floor_config'] == 7, data
    # It tracks the tree rather than a constant: close one, and open/closed move while
    # the TOTAL (the only monotone quantity, and therefore the floor's subject) does not.
    rc, out, err = run(root, 'close', 'T7', '-m', 'shipped', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'counts')
    assert (data['open'], data['closed'], data['total']) == (6, 1, 7), data
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err
    # And a corpus that GROWS never reddens the floor.
    rc, out, err = run(root, 'new', 'a brand new item', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'counts')
    assert data['total'] == 8 and data['floor_now'] == 8, data
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_the_moved_updated_split_survives_automation():
    """The whole reason there are two stamps: an ack-class write must NOT move `moved`.

    `moved` answers "when did a session last make PROGRESS", and `board` reads it to warn
    about neglected NOW/NEXT rows. If a housekeeping pass -- a cheap model acking the sync
    agent's drift report, a scheduled mechanical field fix -- could bump `moved`, then a
    neglected row would look fresh forever and the staleness warning could never fire
    again. A check that cannot fire is this repo's declared house failure mode, so the
    property is asserted here rather than described in SPEC.md and hoped for.

    PORT NOTE (2026-08-29): the scratch original ran on `good_tree`, whose tasks are all
    `source: hand`. `ack` now REFUSES a hand-filed task outright (spec A2.1), so every
    `ack` here would be an exit-2 refusal and the case would be testing the refusal rather
    than the stamp split. The fixture is therefore `sync_tree` -- the same seven tasks with
    T1..T4/T6 marked `source: board` and a board above them -- and step 6's closed-task ack
    moved from T7 (hand) to T4 (board). Nothing about the stamp property changed.

    Sabotage, run before this was believed -- `op_ack` calling the progress path
    (`stamp_and_render(task, key, True)`, the one-word edit a refactor makes when it
    notices two call sites differ only by a constant)::

        AssertionError: ack moved `moved` 2026-08-21b -> 2026-08-21c: an acknowledgement
        just laundered a stale row into a fresh one

    and the mirror, `progress()` hard-wired to True so `--mechanical` is accepted and
    ignored -- the failure mode where the flag exists and does nothing::

        AssertionError: set --mechanical moved `moved` 2026-08-21b -> 2026-08-21d

    Baseline before and after each: `32 test(s), 0 failed`. Both are now permanent cases:
    test_sabotage_wp_ack_does_not_move_moved / test_sabotage_wp_mechanical_is_honoured.
    """
    root = sync_tree('stamps')
    path = os.path.join(root, 'tasks', 'T2-next-alpha.md')

    def stamps():
        fm = dict(TM.parse_file(read(path).decode('utf-8'), path)[0])
        return fm['moved'], fm['updated']

    assert stamps() == (KEY, KEY), stamps()

    # 1. A PROGRESS op bumps BOTH. `comment` is the workhorse and it is real work.
    rc, out, err = run(root, 'comment', 'T2', '-m', 'did the thing',
                       '--session', KEY + 'b')
    assert rc == 0, err
    assert stamps() == (KEY + 'b', KEY + 'b'), stamps()

    # 2. `ack` bumps `updated` ONLY -- and says so, because a caller who cannot see the
    #    difference will assume the tool did the obvious thing.
    rc, out, err = run(root, 'ack', 'T2', '-m', 'saw the drift report; body still true',
                       '--session', KEY + 'c')
    assert rc == 0, err
    moved, updated = stamps()
    assert moved == KEY + 'b', (
        'ack moved `moved` %sb -> %s: an acknowledgement just laundered a stale row into '
        'a fresh one' % (KEY, moved))
    assert updated == KEY + 'c', stamps()
    assert 'moved held at %sb' % KEY in out_text(out), out_text(out)

    # 3. --mechanical does the same for the field ops a housekeeping TOOL emits.
    rc, out, err = run(root, 'set', 'T2', 'size', 'L', '--mechanical',
                       '--session', KEY + 'd')
    assert rc == 0, err
    moved, updated = stamps()
    assert moved == KEY + 'b', (
        'set --mechanical moved `moved` %sb -> %s' % (KEY, moved))
    assert updated == KEY + 'd', stamps()

    # 4. ... and WITHOUT the flag the same op is progress. The flag is the only
    #    difference, which is what makes the rule mechanical rather than a judgement.
    rc, out, err = run(root, 'set', 'T2', 'size', 'M', '--session', KEY + 'e')
    assert rc == 0, err
    assert stamps() == (KEY + 'e', KEY + 'e'), stamps()

    # 5. The invariant that makes the pair checkable at rest: updated >= moved, always.
    #    An ack with an EARLIER key would break it, so it is refused rather than written.
    rc, out, err = run(root, 'ack', 'T2', '-m', 'backdated', '--session', KEY + 'd')
    assert rc == 2, (rc, out_text(out), err)
    assert 'earlier than' in err and 'moved' in err, err

    # 6. A closed task can still be commented on and acked -- which is exactly why
    #    `updated` is a separate field from `closed`.
    rc, out, err = run(root, 'close', 'T4', '-m', 'done', '--session', KEY + 'b')
    assert rc == 0, err
    rc, out, err = run(root, 'comment', 'T4', '-m', 'a late note',
                       '--session', KEY + 'c')
    assert rc == 0, err
    rc, out, err = run(root, 'ack', 'T4', '-m', 'archived; nothing to add',
                       '--session', KEY + 'd')
    assert rc == 0, err
    closed_path = os.path.join(root, 'tasks', 'closed', 'T4-later-gamma.md')
    fm = dict(TM.parse_file(read(closed_path).decode('utf-8'), closed_path)[0])
    assert (fm['closed'], fm['moved'], fm['updated']) == (
        KEY + 'b', KEY + 'c', KEY + 'd'), fm
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_source_is_written_once_and_never_again():
    """`source` replaces SYNC-SPEC.md section 3's `sync-state.json`, so it has to be
    trustworthy at rest: provenance a later op can rewrite is provenance that will
    eventually disagree with the Log entry under it, and a second state file was rejected
    precisely because it can drift from the corpus.

    The immutability MECHANISM is that no op writes the field after `new` -- there is no
    flag to defeat, which is why the check below is a `set` refusal and not a `--force`.
    Sabotage: adding 'source' to SETTABLE, the one-word edit that makes the field
    mutable. Observed with it added::

        AssertionError: ('`set source` was ACCEPTED (rc 0): provenance is now editable',)
    """
    root = good_tree('prov')
    rc, out, err = run(root, 'new', 'a synced row', '--source', 'board', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T8')
    assert data['source'] == 'board', data

    # The default is `hand`, because the default caller is a human typing `new`.
    rc, out, err = run(root, 'new', 'a typed row', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T9')
    assert data['source'] == 'hand', data

    # A repo-relative path is the third form, and it is the one sync keys off.
    rc, out, err = run(root, 'new', 'an audited row', '--session', KEY,
                       '--source', 'docs/perf-round6-audit-2026-08.md')
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T10')
    assert data['source'] == 'docs/perf-round6-audit-2026-08.md', data

    # Immutable: no op writes it after creation.
    rc, out, err = run(root, 'set', 'T8', 'source', 'hand', '--session', KEY)
    assert rc == 2, ('`set source` was ACCEPTED (rc %d): provenance is now editable' % rc,)
    assert 'IMMUTABLE' in err, err
    rc, data, err = rj(root, 'show', 'T8')
    assert data['source'] == 'board', data

    # Refused at the seam, not stored and linted later: a near-miss of a fixed value is a
    # typo, and a vocabulary that admits typos answers no query.
    for bad in ('Board', 'handoff', '/etc/passwd', '../outside.md', ''):
        rc, out, err = run(root, 'new', 'bad source %r' % bad, '--source', bad,
                           '--session', KEY)
        assert rc == 2, ('--source %r was accepted' % bad, out_text(out))
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_related_is_navigation_and_deliberately_not_a_graph():
    """`related` resolves and refuses self-reference, and is NOT cycle-checked.

    The absence is the point. `A related B` + `B related A` is the NORMAL state of a
    symmetric-ish navigation link, so a cycle check would call the normal state a
    violation; `deps` earns one because a dep cycle means nothing in it can ever be
    ready, which is a real consequence in a real query. This test asserts the mutual pair
    lints CLEAN, so a later session that "fixes" the missing cycle check turns this red
    instead of quietly outlawing a supported shape.

    `show` prints the INCOMING links because the field is one-directional on disk (no
    reciprocity rule -- a hand-maintained inverse is the rot machine this format exists
    without), so without the computed reverse, half of every link is invisible from the
    end that did not write it.
    """
    root = good_tree('rel')
    rc, out, err = run(root, 'set', 'T2', 'related', 'T3,T5', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'set', 'T3', 'related', 'T2', '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'lint')
    assert rc == 0, ('the mutual pair T2<->T3 is NORMAL for a navigation link and must '
                     'lint clean:\n%s\n%s' % (out_text(out), err))

    # Incoming, computed on read. T5 never wrote anything and still knows about T2.
    rc, data, err = rj(root, 'show', 'T5')
    assert data['related'] == [] and data['related_in'] == ['T2'], data
    rc, out, err = run(root, 'show', 'T5')
    assert 'related (incoming' in out_text(out) and 'T2' in out_text(out), out_text(out)

    # Refusals: self, unknown id, duplicate.
    for value, why in (('T2', 'self'), ('T99', 'unknown id'), ('T3,T3', 'duplicate')):
        rc, out, err = run(root, 'set', 'T2', 'related', value, '--session', KEY)
        assert rc == 2, ('related %r (%s) was accepted' % (value, why), out_text(out))
    rc, data, err = rj(root, 'show', 'T2')
    assert data['related'] == ['T3', 'T5'], data


@case
def test_parent_depth_warns_and_stays_green():
    """Check 11 WARNS about a parent chain deeper than two levels, and never fails.

    Two properties, and the second is the one that is easy to lose: the warning FIRES on
    a three-level chain (a check that cannot fire is not a check), and the exit code
    stays 0 (a warning that reddens the gate is a violation wearing a softer word, and
    the predictable response to it is flattening the tree to get green -- losing the
    grouping the depth was expressing).

    PORT NOTE: the two `clean (11 checks` literals were RE-MEASURED to `12` for
    `check_banner`; the warning-count and rollup assertions are unchanged.
    """
    root = good_tree('depth')
    rc, out, err = run(root, 'lint')
    assert rc == 0 and 'WARN' not in out_text(out) + err, (out_text(out), err)

    # T4's parent is T6, so hanging T8 off T4 is three levels: T8 -> T4 -> T6.
    place(root, 'T8', 'deep-one', title='a grandchild', pri='LATER', size='S',
          parent='T4')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 0, ('depth is a WARNING, not a violation -- exit %d:\n%s' % (rc, text))
    assert 'WARN' in text and 'T8 -> T4 -> T6' in text, text
    assert 'clean (12 checks' in out_text(out), out_text(out)
    assert '1 warning(s)' in out_text(out), out_text(out)

    rc, data, err = rj(root, 'lint')
    assert data['clean'] is True and data['violations'] == [], data
    assert len(data['warnings']) == 1 and 'T8' in data['warnings'][0], data

    # ONE LINE PER DISTINCT FACT (PROOF4.md section 6 bug C). A single re-parent of `R6`
    # onto `TK52` produced 37 identical WARN lines on the live corpus -- one per
    # descendant, all naming the same cause and the same fix. A reader who has to work out
    # that 37 lines are one fact is a reader who scrolls past the warnings, so the rollup
    # is not cosmetic: it is the difference between a report that is read and one that is
    # not. Three more grandchildren here, all deep for the SAME reason, must still be ONE
    # line -- and the line must still name the whole chain and count the others.
    #
    # Sabotage (sync_sabotage.py S13), run before this was believed -- the grouping key
    # changed from the ancestor chain to the whole chain (`key = tuple(chain)`), the
    # plausible "why is the first element dropped?" tidy-up, which makes every task its
    # own group again. Literal, clipped at the first entry of the four::
    #
    #     assert len(warns) == 1, (
    #     AssertionError: 4 tasks deep for ONE reason produced 4 WARN lines; the reader
    #     has to work out they are one fact: ['  WARN: <t>/testtmp/depth/tasks/
    #     T10-deep-three.md: parent chain is 3 levels deep (T10 -> T4 -> T6), over the 2
    #     this corpus is shaped for. ...', '  WARN: ...T11-deep-four.md: ...', ...]
    for tid, slug in (('T9', 'deep-two'), ('T10', 'deep-three'), ('T11', 'deep-four')):
        place(root, tid, slug, title='another grandchild', pri='LATER', size='S',
              parent='T4')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    warns = [l for l in text.split('\n') if 'WARN' in l]
    assert rc == 0, text
    assert len(warns) == 1, (
        '4 tasks deep for ONE reason produced %d WARN lines; the reader has to work out '
        'they are one fact: %s' % (len(warns), warns))
    assert 'T10 -> T4 -> T6' in warns[0], warns[0]
    assert 'SAME FACT, 3 more task(s)' in warns[0], warns[0]
    assert 'T11' in warns[0] and 'T8' in warns[0] and 'T9' in warns[0], warns[0]
    assert '1 warning(s)' in out_text(out), out_text(out)

    # A task deep for a DIFFERENT reason is a different fact and keeps its own line.
    place(root, 'T12', 'other-branch', title='a child of T3', pri='LATER', size='S',
          parent='T3')
    place(root, 'T13', 'other-deep', title='a grandchild of T3', pri='LATER', size='S',
          parent='T12')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    warns = [l for l in text.split('\n') if 'WARN' in l]
    assert rc == 0 and len(warns) == 2, (len(warns), warns)
    assert any('T13 -> T12 -> T3' in l for l in warns), warns
    for tid in ('T9', 'T10', 'T11', 'T12', 'T13'):
        for name in os.listdir(os.path.join(root, 'tasks')):
            if name.startswith(tid + '-'):
                os.remove(os.path.join(root, 'tasks', name))

    # Two levels is the shape this corpus actually uses (R6 over its children) and must
    # stay silent, or the warning is noise from the first day.
    os.remove(os.path.join(root, 'tasks', 'T8-deep-one.md'))
    place(root, 'T8', 'flat-one', title='a child', pri='LATER', size='S', parent='T6')
    rc, out, err = run(root, 'lint')
    assert rc == 0 and 'WARN' not in out_text(out) + err, (out_text(out), err)


@case
def test_a_missing_floor_is_a_violation_not_a_default():
    """No default for `min_tasks_parsed`, because a guessed floor IS a floor with
    headroom -- SPEC.md's example value 5 shipped against 99 files and let 57 of them be
    deleted silently. A config that declares no floor must say so out loud, and `new`
    must refuse rather than invent an id prefix. Observed before this change: a config
    missing both keys linted clean and minted `T1`."""
    root = good_tree('nofloor')
    cfg = os.path.join(root, 'tasks', 'config.json')
    data = json.loads(read(cfg).decode('utf-8'))
    del data['min_tasks_parsed']
    del data['id_prefix']
    write(cfg, json.dumps(data, indent=2) + '\n')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1 and 'declares no `min_tasks_parsed` floor' in text, text
    assert 'task.py counts' in text, text
    rc, out, err = run(root, 'new', 'what does this mint', '--session', KEY)
    assert rc == 2 and 'no "id_prefix"' in err, (rc, err)


@case
def test_a_disabled_floor_is_refused_not_accepted():
    """BUG FOUND 2026-08-21 (PROOF2.md section 2). The floor's VALUE was read with
    ``int(...)`` and never validated, so the instrument control could be switched off by
    editing one config value -- which is the failure mode this whole tool exists to
    prevent, applied to the thing that is supposed to notice it.

    Observed BEFORE the fix, on the live corpus, all three TRUE rc=0::

        min_tasks_parsed=0    -> task lint: clean (10 checks, 99 task file(s) parsed)
        min_tasks_parsed=-5   -> task lint: clean (10 checks, 99 task file(s) parsed)
        min_tasks_parsed='99' -> task lint: clean (10 checks, 99 task file(s) parsed)

    ``0`` is verbatim what ``check_min_parsed``'s own docstring calls "a check that passes
    forever"; ``'99'`` was green by luck (``int('99')`` happened to compare); ``-5`` is a
    floor nothing can fall below.

    The boundary is pinned in BOTH directions on purpose. ``1`` must stay GREEN: a floor
    of 1 is a *lowering*, and lowering is a reviewed edit this check does not get to veto.
    Only a value that cannot fire at all is refused. Without the green half this test
    would pass just as well against a check that refuses every floor, which is a different
    tool.
    """
    root = good_tree('badfloor')
    cfg = os.path.join(root, 'tasks', 'config.json')

    def with_floor(value):
        data = json.loads(read(cfg).decode('utf-8'))
        data['min_tasks_parsed'] = value
        write(cfg, json.dumps(data, indent=2) + '\n')
        rc, out, err = run(root, 'lint')
        return rc, out_text(out) + err

    for value in (0, -5, '99', '7', 3.0, True, None, 'seven'):
        rc, text = with_floor(value)
        assert rc == 1, ('min_tasks_parsed=%r linted clean (rc=%d): a floor that cannot '
                         'fire is a disabled control, not a lowered one.\n%s'
                         % (value, rc, text))
        assert 'expected a positive integer' in text, (value, text)
        assert 'config.json' in text and repr(value) in text, (
            'the refusal must name the config path and the bad value: %r' % text)

    # The green half: a real, positive, LOWERED floor is still accepted, and the corpus
    # check below it still runs.
    rc, text = with_floor(1)
    assert rc == 0 and 'clean' in text, ('a floor of 1 is a lowering, not a disabling, '
                                         'and must stay green: %s' % text)
    rc, text = with_floor(7)
    assert rc == 0 and 'clean' in text, text
    rc, text = with_floor(8)
    assert rc == 1 and 'parsed only 7 task file(s)' in text, (
        'the floor must still FIRE on a real shortfall -- otherwise this test is happy '
        'with a check that only ever validates its own input: %s' % text)


@case
def test_shipped_config_is_measured_not_an_example():
    """The three knobs in the SHIPPED config are the ones that were copied out of
    SPEC.md section 6's example block and never checked against the tree they guard.

    This pins the properties, not the values: the floor equals the measured corpus (zero
    headroom), `stale_days` is longer than the longest gap between working days in the
    repo's own history, each knob carries written provenance, and the id prefix does not
    collide with a non-task name. All three were wrong on 2026-08-21 -- floor 5 against 99
    files, prefix "T" whose first minted id `T1` is the set-engine correctness theorem,
    and a bare 14 with no derivation anywhere.

    PORT NOTE -- THE PREFIX CLAUSE HAD TO CHANGE, AND THIS IS WHY. The scratch version
    asserted ZERO repo-wide occurrences of `\\bPREFIX\\d+\\b`. That was a CHOICE-TIME
    measurement and it only stayed true because the corpus it minted into lived under
    `.scratch/`, which the scan excluded. The corpus is tracked now: the prefix names 53
    live tasks, cited across `HANDOFF.md`, the ledger and the tool itself, so a zero-hit
    assertion is simply unmeasurable and would have to be deleted rather than adapted.

    What survives, and what is asserted instead, is the property the original was
    protecting -- "an address that is already a name is unresolvable by grep": every
    minted-shape token found OUTSIDE `tasks/` must RESOLVE to an id the corpus knows.
    That keeps the discriminating power (under prefix "T" the formal docs are full of
    `T1`/`T4`/`T7` that resolve to nothing) and it is measurable today. Exactly one token
    does not resolve -- `TK99`, a deliberately hypothetical id in `scripts/task.py`'s own
    comment about retired ids -- and it is pinned BY NAME with `==`, not tolerated by a
    `<=`: a second unresolvable token is red, and so is this one disappearing without the
    pin being reviewed. Zero headroom, the same contract as `MIN_TESTS_ALL`.
    """
    tasks = os.path.join(LIVE_TREE, 'tasks')
    assert os.path.isdir(tasks), (
        'the live corpus %s is missing. This is a FAILURE, never a skip.' % tasks)
    cfg = json.loads(read(os.path.join(tasks, 'config.json')).decode('utf-8'))

    on_disk = sum(TM.disk_md_count(tasks))
    assert cfg['min_tasks_parsed'] == on_disk, (
        'floor %r vs %d files on disk: zero headroom means EQUAL, and the value to paste '
        'is printed by `task.py counts`' % (cfg.get('min_tasks_parsed'), on_disk))

    prov = cfg.get('_provenance') or {}
    for knob in ('id_prefix', 'min_tasks_parsed', 'stale_days'):
        assert len(prov.get(knob, '')) > 120, (
            '%s carries no written provenance; JSON has no comments, so an unexplained '
            'tuned number is indistinguishable from a copied example' % knob)

    # Every id the corpus knows: open, closed, and the retired registry. Taken from the
    # TOOL rather than from filenames -- ids legitimately contain hyphens (`ZT-P0-1`,
    # `R6-3`), so `name.split('-')[0]` yields a prefix, not an id, and silently collapses
    # the census from 152 to 89. `list` is a read op; the live corpus is not written to.
    rc, rows, err = rj(LIVE_TREE, 'list', '--all', '--limit', '0')
    assert rc == 0, err
    known = set(row['id'] for row in rows)
    for line in read(os.path.join(tasks, 'retired-ids.txt')).decode('utf-8').split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            known.add(line)
    assert len(known) >= cfg['min_tasks_parsed'], (
        'the id census went blind: %d ids against a corpus of %d files'
        % (len(known), cfg['min_tasks_parsed']))

    # The same scan measure_prefix.py runs, minus `tasks/` (the corpus the prefix owns);
    # `\bPREFIX\d+\b` is exactly the shape `Store.next_id` mints.
    rx = re.compile(r'\b%s\d+\b' % re.escape(cfg['id_prefix']))
    unresolved, where, scanned = set(), {}, 0
    for base, dirs, names in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs
                   if d not in ('.git', '__pycache__', '.gate-runs', '.scratch',
                                '.lake', '.idea', '.pytest_cache', '.hypothesis',
                                'tasks')]
        for name in names:
            if os.path.splitext(name)[1].lower() not in ('.py', '.md', '.lean', '.txt'):
                continue
            scanned += 1
            with io.open(os.path.join(base, name), encoding='utf-8',
                         errors='replace') as fh:
                for token in rx.findall(fh.read()):
                    if token not in known:
                        unresolved.add(token)
                        where.setdefault(token, os.path.join(base, name))
    assert scanned > 100, 'the collision scan saw only %d files -- it went blind' % scanned
    assert unresolved == set(['TK99']), (
        'id_prefix %r: the set of minted-shape tokens that resolve to NO task changed. '
        'Expected exactly {TK99} (the hypothetical id in scripts/task.py\'s retired-ids '
        'comment). Got %s, first seen at %s. A new entry means the prefix now names '
        'something that is not a task -- an address that is already a name.'
        % (cfg['id_prefix'], sorted(unresolved),
           dict((t, where[t]) for t in sorted(unresolved))))

    # 6 days is the longest observed gap between two working days in docs/history; a
    # threshold at or below it flags rows because nobody worked the REPO.
    assert int(cfg['stale_days']) >= 7, cfg['stale_days']


@case
def test_sync_has_no_delete_path():
    """A board row can vanish in every mode sync has, and the task file stays on disk.

    THE property of this design (SYNC-SPEC.md section 0): a row disappears from a board
    as easily by a careless edit as by a finished item, so `sync` reports and stops. The
    assertion is on the FILESYSTEM and on the bytes, not on the absence of a flag -- a
    tool with no `--delete` flag can still call `os.remove`.

    Sabotage (sync_sabotage.py S1), run before this was believed -- `os.remove(task.path)`
    on the CORPUS-ONLY branch of `sync_report`, i.e. the tool "tidying up" an orphan.
    Literal, with `<t>/` eliding the checkout path as elsewhere in this file::

        AssertionError: sync REMOVED <t>/testtmp/sync_del/tasks/T4-later-gamma.md. There
        is no flag for this and there must be no code path for it either.

    Baseline before and after: `37 test(s), 0 failed`.
    """
    root = sync_tree('sync_del')
    seed_hashes(root)
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    before = read(path)
    board = read(os.path.join(root, 'HANDOFF.md')).decode('utf-8')
    write(os.path.join(root, 'HANDOFF.md'),
          '\n'.join(l for l in board.split('\n') if not l.startswith('| `T4` |')))

    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 1, text
    assert 'CORPUS-ONLY       T4' in text, text
    assert 'close it if it is done' in text, text
    assert 'close is NEVER automatic' in text, text

    for argv in (('sync', '--check'), ('sync', '--commands'),
                 ('sync', '--create-new', '--session', KEY), ('sync', '--json')):
        rc, out, err = run(root, *argv)
        assert os.path.isfile(path), (
            'sync REMOVED %s. There is no flag for this and there must be no code path '
            'for it either.' % path)
        runnable = [l for l in out_text(out).split('\n') if l.startswith('python ')]
        assert not [l for l in runnable if ' close ' in l], (
            '%s emitted a RUNNABLE close command; close is a human act with a required '
            'message, so it may only ever be SUGGESTED in prose' % ' '.join(argv))
    assert read(path) == before, 'sync rewrote a task it only reported on'
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_sync_body_drift_compares_the_source_against_itself():
    """BODY fires when the SOURCE moves, and never when a session rewrites a task.

    The refinement that makes the bucket usable (SYNC-SPEC.md section 2). Comparing the
    board's prose against the task's prose reports drift forever, because the two
    legitimately diverge the moment anyone works the item -- and a check that can never
    go green is as dead as one that never fires. So the trigger is the stored digest of
    the source block, and the two halves below are the two things that must be true of
    it: a task rewrite is SILENT, a source rewrite is exactly ONE report.

    Sabotage (sync_sabotage.py S2 and S3), run before this was believed. First
    `report['body'].append(...)` changed to `[].append(...)`, the narrowest weakening
    that goes quiet rather than loud::

        AssertionError: rewriting ONE block produced 0 report(s), not 1: []

    then `source_block_text` hashing the row CELL only, dropping the item block. On the
    LIVE corpus, whose seeds were written by the unweakened tool, the same edit is LOUD
    instead: `sync_accept.py` case G observed all three blocked rows (`P3`, `P6`, `R6`)
    reporting at once, `sync   5 drift item(s)`. A stored digest pins the hash FUNCTION
    as well as the source text.

    Baseline before and after each: `37 test(s), 0 failed`.
    """
    root = sync_tree('sync_body')
    seed_hashes(root)
    rc, out, err = run(root, 'sync', '--check')
    assert 'BODY' not in out_text(out), out_text(out)

    # 1. A SESSION rewrites the task body. This must produce nothing at all.
    path = os.path.join(root, 'tasks', 'T1-the-now-row.md')
    write(path, read(path).decode('utf-8').replace(
        'Summary line.', 'A completely rewritten summary a session typed.'))
    rc, out, err = run(root, 'sync', '--check')
    assert 'BODY' not in out_text(out), (
        'a session rewriting a task body produced drift:\n%s' % out_text(out))

    # 2. The BOARD rewrites T1's item block. Exactly one report, against exactly T1.
    bpath = os.path.join(root, 'HANDOFF.md')
    write(bpath, read(bpath).decode('utf-8').replace(
        'The summary paragraph as the BOARD states it.',
        'The summary paragraph, REWRITTEN on the board this session.'))
    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    reports = [l for l in text.split('\n') if l.startswith('  BODY   ')]
    assert rc == 1 and len(reports) == 1 and 'T1' in reports[0], (
        'rewriting ONE block produced %d report(s), not 1: %s' % (len(reports), reports))
    assert 'never auto-applied' in text, text

    # 3. `ack -m` closes it out: updated advances, `moved` does NOT, the reason is logged.
    fm = dict(TM.parse_file(read(path).decode('utf-8'), path)[0])
    rc, out, err = run(root, 'ack', 'T1', '-m', 'reworded on the board; the task prose '
                       'is still accurate', '--session', KEY + 'b')
    assert rc == 0, err
    after = dict(TM.parse_file(read(path).decode('utf-8'), path)[0])
    assert after['moved'] == fm['moved'], (
        'ack bumped `moved` %s -> %s: acknowledging drift is housekeeping, not progress'
        % (fm['moved'], after['moved']))
    assert after['updated'] == KEY + 'b', after
    assert after['source_hash'] != fm['source_hash'], after
    assert 'still accurate' in read(path).decode('utf-8').split('## Log')[-1], (
        'ack did not record WHY the description needed no change -- which is the only '
        'thing that distinguishes an acknowledged report from an unread one')
    rc, out, err = run(root, 'sync', '--check')
    assert 'BODY' not in out_text(out), out_text(out)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_sync_creates_with_the_rows_id_and_emits_mechanical_commands():
    """`--create-new` files the ROW's id with `source: board`; `--commands` is pasteable.

    The id half is not a detail: a board row is already an ADDRESS (`P3` is `P3` in the
    ledger, in every citation), so minting a fresh id for it files a task nobody can look
    up and leaves the row looking unfiled forever.

    Sabotage (sync_sabotage.py S4 and S5), run before this was believed. First
    `task_id=item['id']` dropped from the Namespace `sync_create_new` builds, so `op_new`
    allocates by scanning as it does for a human -- and the red lands on the RETIRED-id
    clause, because with allocation restored the retired row is filed happily under a
    minted name::

        assert 'NEW-REFUSED       T0' in text and 'retired-ids.txt' in text, text
        AssertionError: T9  <t>/testtmp/sync_new/tasks/T9-a-retired-id-someone-re-typed.md

    then `--mechanical` dropped from the emitted `set` line::

        AssertionError: a sync command without --mechanical: ['python <t>/task.py set T4
        size L']

    Baseline before and after each: `37 test(s), 0 failed`.
    """
    root = sync_tree('sync_new')
    seed_hashes(root)
    bpath = os.path.join(root, 'HANDOFF.md')
    board = read(bpath).decode('utf-8')

    # A new row, and a size change on an existing one, in the same board edit.
    board = board.replace('| `T4` | later gamma | LATER | ? |',
                          '| `T4` | later gamma | LATER | L |')
    board = board.replace('| `T6` | the group',
                          '| `T8` | a row typed straight onto the board | LATER | S '
                          '| `T2` | 2026-08-21 |\n| `T6` | the group')
    write(bpath, board)

    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 1 and 'NEW               T8' in text, text
    assert "FIELD             T4 size: '?' -> 'L'" in text, text

    # --commands: stdout is ONLY commands, so `sync --commands | sh` is a real thing.
    rc, out, err = run(root, 'sync', '--commands')
    lines = [l.rstrip() for l in out_text(out).split('\n') if l.strip()]
    assert lines and all(l.startswith('python ') for l in lines), lines
    assert all('--mechanical' in l for l in lines), (
        'a sync command without --mechanical: %s' % lines)
    assert any(l.endswith('set T4 size L --mechanical') for l in lines), lines
    # And every line names the corpus it was emitted for; see
    # test_sync_commands_name_the_corpus_they_reconcile for why that is behavioural.
    assert all(('--dir %s' % root.replace(os.sep, '/')) in l for l in lines), lines

    before = dict(TM.parse_file(read(os.path.join(root, 'tasks', 'T4-later-gamma.md'))
                                .decode('utf-8'), 'T4')[0])
    for line in lines:
        argv = line.split()[2:]
        if argv[:1] == ['--dir']:       # run() supplies its own, identical, --dir
            argv = argv[2:]
        rc, out, err = run(root, *argv + ['--session', KEY + 'b'])
        assert rc == 0, err
    after = dict(TM.parse_file(read(os.path.join(root, 'tasks', 'T4-later-gamma.md'))
                               .decode('utf-8'), 'T4')[0])
    assert after['size'] == 'L', after
    assert after['moved'] == before['moved'], (
        'applying a sync command moved `moved` %s -> %s: a housekeeping pass laundered '
        'the staleness signal' % (before['moved'], after['moved']))
    assert after['updated'] == KEY + 'b', after

    # --create-new: the row's own id, its fields, `source: board`, and a seeded digest.
    rc, out, err = run(root, 'sync', '--create-new', '--session', KEY + 'b')
    made = os.path.join(root, 'tasks', 'T8-a-row-typed-straight-onto-the-board.md')
    assert os.path.isfile(made), (
        "sync minted no task with the row's id T8; `next_id` allocated one instead, so "
        "the row is STILL reported NEW and the new task is CORPUS-ONLY.\n%s"
        % out_text(out))
    fm = dict(TM.parse_file(read(made).decode('utf-8'), made)[0])
    assert fm['source'] == 'board', fm
    assert re.match(r'^[0-9a-f]{12}$', fm['source_hash']), fm
    assert (fm['pri'], fm['size'], fm['deps']) == ('LATER', 'S', ['T2']), fm

    # A retired id on the board is REFUSED, not filed: ids are never reused.
    write(bpath, read(bpath).decode('utf-8').replace(
        '| `T6` | the group', '| `T0` | a retired id someone re-typed | LATER | S | '
        '%s | 2026-08-21 |\n| `T6` | the group' % u'—'))
    rc, out, err = run(root, 'sync', '--create-new', '--session', KEY + 'b')
    text = out_text(out)
    assert 'NEW-REFUSED       T0' in text and 'retired-ids.txt' in text, text
    assert not [n for n in os.listdir(os.path.join(root, 'tasks'))
                if n.startswith('T0-')], 'a retired id was filed'

    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


@case
def test_sync_is_silent_on_the_normal_path_and_loud_on_the_reverse():
    """R1, both directions: a closed task off the board is silent; on it, reported.

    Sabotage (sync_sabotage.py S6 and S7), run before this was believed -- the closed
    orphan bucketed as the open one (the pre-R1 spec)::

        AssertionError: closing a task and dropping its row reported drift: exit 1

    and, for the reverse half, an early `continue` on `task.is_closed` in `sync_report`::

        AssertionError: T2 is closed and still a NEXT row, and sync said nothing

    Baseline before and after each: `37 test(s), 0 failed`.
    """
    root = sync_tree('sync_r1')
    seed_hashes(root)
    rc, out, err = run(root, 'close', 'T4', '-m', 'done', '--session', KEY + 'b')
    assert rc == 0, err
    bpath = os.path.join(root, 'HANDOFF.md')
    write(bpath, '\n'.join(l for l in read(bpath).decode('utf-8').split('\n')
                           if not l.startswith('| `T4` |')))
    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 0, 'closing a task and dropping its row reported drift: exit %d\n%s' % (
        rc, text)
    assert 'T4' not in text, text
    # Silent, but COUNTED. A bucket nobody prints is a bucket nobody checks.
    assert 'closed-and-off-the-board' in text, text

    # The reverse: close T2 and LEAVE its row.
    rc, out, err = run(root, 'close', 'T2', '-m', 'done', '--session', KEY + 'b')
    assert rc == 0, err
    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 1 and 'CLOSED-BUT-ON-BOARD T2' in text, (
        'T2 is closed and still a NEXT row, and sync said nothing\n%s' % text)
    assert 'FIELD             T2' not in text, (
        'a closed task was field-reconciled against a row it should not have\n%s' % text)


@case
def test_sync_refuses_a_source_it_cannot_read_rather_than_guessing():
    """Instrument control: a malformed `source` stops sync, it does not get a bucket.

    The dangerous guess is `hand` -- "expected, not drift" -- which makes the task
    invisible to this tool forever.

    Sabotage (sync_sabotage.py S8), run before this was believed -- the guard neutered
    (`bad = None`) and the empty value folded into the hand bucket. The observed output is
    worse than the assertion asked for: not merely unreported, but a clean bill of
    health::

        assert rc == 2, (rc, out_text(out), err)
        AssertionError: (0, 'sync   <t>/testtmp/sync_prov/HANDOFF.md  (4 row(s) vs 7
        task(s))[CR][LF]  quiet             3 hand-filed, 0 closed-and-off-the-board
        [CR][LF]sync   CLEAN[CR][LF]', '')

    Read the `3 hand-filed`: the task with NO provenance at all was counted as one of
    them, and the run ended `CLEAN`.

    Baseline before and after: `37 test(s), 0 failed`.
    """
    root = sync_tree('sync_prov')
    seed_hashes(root)
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(path, read(path).decode('utf-8').replace('source: board', 'source:'))
    # AND drop its row, which is the dangerous shape: a task ON the board is reconciled
    # against its row whatever its provenance says, so the silence only bites once the
    # task is the kind sync has to CLASSIFY.
    bpath = os.path.join(root, 'HANDOFF.md')
    write(bpath, '\n'.join(l for l in read(bpath).decode('utf-8').split('\n')
                           if not l.startswith('| `T4` |')))
    rc, out, err = run(root, 'sync', '--check')
    assert rc == 2, (rc, out_text(out), err)
    assert 'REFUSED' in err and 'source is empty' in err, err
    assert 'T4-later-gamma.md' in err, err
    rc, out, err = run(root, 'lint')
    assert rc == 1 and 'source is empty' in err, err


def run_verbatim(cwd, line, *extra):
    """Run an emitted `--commands` line EXACTLY as printed, from ``cwd``.

    Deliberately does not go through ``run()``: ``run()`` injects its own ``--dir``, which
    is the one thing this must not do. The whole hazard of PROOF4.md section 6 bug A is
    that a pasted line carries no target of its own and silently inherits the cwd's.
    """
    argv = line.split() + list(extra)
    proc = subprocess.Popen([sys.executable] + argv[1:], cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out, err.decode('utf-8', 'replace')


@case
def test_sync_commands_name_the_corpus_they_reconcile():
    """An emitted line edits the corpus it was emitted FOR, from any cwd. PROOF4 bug A.

    THE BUG. `sync_command_lines` took no `store` and built each line as
    `'python %s %s' % (prog(), cmd)`, so the target was never echoed. An operator standing
    in corpus `near` who runs `--dir <far> sync --commands` and pastes the lines verbatim
    edited `near` and left `far` untouched. Three rc=0 lines, plausible success text, no
    warning anywhere: this repo's declared house failure mode, failing by PASSING, with a
    write attached.

    WHY TWO CORPORA AND NOT AN ASSERTION ON THE STRING. `assert '--dir' in line` passes
    against a line that names the WRONG directory, and it passes against a line nobody can
    run. The property is behavioural.

    Sabotage (sync_sabotage.py S9 and S10), run before this was believed. First the fix
    reverted to the exact line the bug shipped (`'python %s %s' % (prog(), cmd)`)::

        assert ('--dir %s' % far.replace(os.sep, '/')) in line, (
        AssertionError: the emitted line does not name its corpus: 'python
        <t>/task.py set T4 size L --mechanical'

    Then S10 makes the SAME edit and additionally deletes this test's own string
    assertion, controlling the instrument as well as the subject::

        assert read(os.path.join(near, 'tasks', name)) == before, (
        AssertionError: pasting sync's own output edited the corpus in the CWD instead of
        the one it was emitted for. T4-later-gamma.md under <t>\\testtmp\\sync_dir_near
        changed.

    Baseline before and after each: `40 test(s), 0 failed`.
    """
    far = sync_tree('sync_dir_far')
    near = sync_tree('sync_dir_near')
    seed_hashes(far)
    seed_hashes(near)

    # One field drift on the FAR board only. The NEAR corpus is an innocent bystander and
    # is never named on any command line in this test.
    bpath = os.path.join(far, 'HANDOFF.md')
    write(bpath, read(bpath).decode('utf-8').replace(
        '| `T4` | later gamma | LATER | ? |', '| `T4` | later gamma | LATER | L |'))

    near_before = dict((n, read(os.path.join(near, 'tasks', n)))
                       for n in sorted(os.listdir(os.path.join(near, 'tasks')))
                       if n.endswith('.md'))

    rc, out, err = run(far, 'sync', '--commands')
    lines = [l.rstrip() for l in out_text(out).split('\n') if l.strip()]
    assert lines, (out_text(out), err)
    for line in lines:
        assert ('--dir %s' % far.replace(os.sep, '/')) in line, (
            'the emitted line does not name its corpus: %r' % line)

    # Apply them VERBATIM, standing in the bystander corpus. This is the paste.
    for line in lines:
        rc, out, err = run_verbatim(near, line, '--session', KEY + 'b')
        assert rc == 0, (line, out_text(out), err)

    for name, before in near_before.items():
        assert read(os.path.join(near, 'tasks', name)) == before, (
            'pasting sync\'s own output edited the corpus in the CWD instead of the one '
            'it was emitted for. %s under %s changed.' % (name, near))

    fm = dict(TM.parse_file(read(os.path.join(far, 'tasks', 'T4-later-gamma.md'))
                            .decode('utf-8'), 'T4')[0])
    assert fm['size'] == 'L', (
        'the emitted line named a corpus but did not edit it: %s' % fm)
    assert fm['updated'] == KEY + 'b' and fm['moved'] == KEY, fm

    rc, out, err = run(far, 'sync', '--check')
    assert rc == 0 and 'FIELD' not in out_text(out), out_text(out)
    for root in (far, near):
        rc, out, err = run(root, 'lint')
        assert rc == 0, out_text(out) + err


@case
def test_ack_covers_corpus_only_and_cannot_hide_a_new_problem():
    """`ack` silences a standing CORPUS-ONLY item -- and only while it stays that item.

    THE DEFECT (PROOF4.md section 6 bug B). `sync --check` was red forever: `B2` and
    `ZT-P5` are open, `source: board`, and have no row, both TRUE findings that only a
    human `close` can clear. So steps 1-3 of the housekeeping loop exited 1 on every run,
    indefinitely, and a cheap model had no printed way to tell weeks-old standing drift
    from something that changed since the last run. A permanently red check is a dead
    check.

    THE PROPERTY THAT MAKES THE FIX ADMISSIBLE: an acknowledgement must not be able to
    hide a NEW, DIFFERENT problem. So the halves below are (1) it goes quiet, (2) the item
    is still NAMED, and (3) the moment the situation CHANGES it is reported again.

    Sabotage (sync_sabotage.py S11 and S12), run before this was believed. S11 is a
    ONE-TOKEN edit: the BODY comparison accepts the sentinel as a match for any digest
    (`if task.source_hash not in (digest, SOURCE_HASH_NO_ROW)`)::

        assert rc == 1, (
        AssertionError: acking a missing row silenced the task AFTER its row came back:
        the acknowledgement hid a new, different situation.

    S12 keeps the bucket but stops NAMING it::

        assert 'ACKED-NO-ROW      T4' in text, (
        AssertionError: the acknowledged item is not named on the report. A bucket that
        goes silent is a bucket that stops being checked.

    Baseline before and after each: `40 test(s), 0 failed`.
    """
    root = sync_tree('sync_ack_only')
    seed_hashes(root)
    bpath = os.path.join(root, 'HANDOFF.md')
    board = read(bpath).decode('utf-8')
    row = [l for l in board.split('\n') if l.startswith('| `T4` |')][0]
    write(bpath, '\n'.join(l for l in board.split('\n') if l != row))

    # 1. Standing drift, exactly as B2 / ZT-P5 present on the live board.
    rc, out, err = run(root, 'sync', '--check')
    assert rc == 1 and 'CORPUS-ONLY       T4' in out_text(out), out_text(out)

    # 2. ack it with a reason -- and the reason lands in the Log, which is the whole
    #    audit trail this buys over a flag or an ignore-list.
    rc, out, err = run(root, 'ack', 'T4', '-m', 'row retired by hand; task still true',
                       '--session', KEY + 'b')
    assert rc == 0, err
    assert 'acked-no-row' in out_text(out), out_text(out)
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    text = read(path).decode('utf-8')
    fm = dict(TM.parse_file(text, path)[0])
    assert fm['source_hash'] == TM.SOURCE_HASH_NO_ROW, fm
    assert 'row retired by hand; task still true' in text, text
    # ack is housekeeping, never progress (SPEC.md section 3.1).
    assert fm['moved'] == KEY and fm['updated'] == KEY + 'b', fm

    # 3. Green, and STILL NAMED. Silence would just move the failure from "red forever"
    #    to "quiet forever", which is the worse of the two.
    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 0, ('acking the only standing item left the check red:\n%s' % text)
    assert 'CLEAN' in text, text
    assert 'ACKED-NO-ROW      T4' in text, (
        'the acknowledged item is not named on the report. A bucket that goes silent is '
        'a bucket that stops being checked.\n%s' % text)

    # 4. THE SITUATION CHANGES: the row comes back. The acknowledgement was of an absence,
    #    so it must not survive the absence ending.
    write(bpath, '\n'.join((l + '\n' + row) if l.startswith('| `T3` |') else l
                           for l in read(bpath).decode('utf-8').split('\n')))
    rc, out, err = run(root, 'sync', '--check')
    text = out_text(out)
    assert rc == 1, (
        'acking a missing row silenced the task AFTER its row came back: the '
        'acknowledgement hid a new, different situation.\n%s' % text)
    assert 'BODY              T4' in text and TM.SOURCE_HASH_NO_ROW in text, text
    assert 'ACKED-NO-ROW' not in text, text

    # 5. And the ordinary ack still closes it, restamping the real digest.
    rc, out, err = run(root, 'ack', 'T4', '-m', 'read both; body still right',
                       '--session', KEY + 'b')
    assert rc == 0, err
    fm = dict(TM.parse_file(read(path).decode('utf-8'), path)[0])
    assert re.match(r'^[0-9a-f]{12}$', fm['source_hash']), fm
    rc, out, err = run(root, 'sync', '--check')
    assert rc == 0, out_text(out)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    # 6. A `hand` task may not carry the sentinel either: a hand-filed task has no source
    #    that could be missing a row for it, so lint calls it what it is.
    hand = os.path.join(root, 'tasks', 'T5-held-delta.md')
    write(hand, read(hand).decode('utf-8')
          .replace('source_hash:', 'source_hash: ' + TM.SOURCE_HASH_NO_ROW))
    rc, out, err = run(root, 'lint')
    assert rc == 1 and 'sentinel' in err and 'T5' in err, err


@case
def test_list_truncation_is_announced_and_json_is_not_cut():
    """`list` caps the table at LIST_LIMIT rows, and SAYS SO. The cap is the feature;
    the announcement is the assurance property, and it is the one pinned here.

    Why the announcement is the part under test: a silent `showing 20 of 91` is a true
    sentence that leaves a false impression -- the reader believes they have seen the
    backlog, and an item ranked 21st is now invisible in exactly the tool built because
    items were going invisible.

    Sabotage, run before this was believed -- the footer reverted to reporting only what
    it printed, which is the shape any future "tidy up the output" edit would produce::

        -        emit('showing %d of %d task(s)  (--limit 0 for all, --limit N for N)'
        -             % (len(shown), total))
        +        emit('%d task(s)' % len(shown))

    The suite goes red, attributably, on the total::

        FAIL  test_list_truncation_is_announced_and_json_is_not_cut
              AssertionError: the footer hides the total -- 27 rows exist, footer says:
              '20 task(s)'

    Note what the sabotaged footer is NOT: not an error, not a crash, not even a wrong
    number. `20 task(s)` is a correct count of the rows above it. That is precisely why it
    needs a test rather than a reader.

    Baseline before and after: `41 test(s), 0 failed`.
    """
    root = good_tree('listlimit')
    # 20 more LATER rows -> 27 open, comfortably past the default. Adding files is always
    # free against a `-ge` floor; only losing them is loud.
    for n in range(20):
        place(root, 'L%d' % n, 'filler-%d' % n, title='filler row %d' % n,
              pri='LATER', size='S')
    rc, out, err = run(root, 'lint')
    assert rc == 0, (rc, out_text(out), err)

    rc, out, err = run(root, 'list')
    assert rc == 0, (rc, err)
    text = out_text(out)
    body = [l for l in text.split('\n') if l.strip()]
    footer = body[-1]
    # 1. The cap is applied: header + LIST_LIMIT rows, and the NOW row survives it --
    #    truncating from the wrong end would drop the one row the view exists to show.
    rows = [l for l in body[1:-1] if l.strip()]
    assert len(rows) == TM.LIST_LIMIT, (len(rows), text)
    assert rows[0].startswith('T1 '), 'NOW row not first after truncation:\n%s' % text
    # 2. THE PROPERTY: the footer names the total, not just what it printed.
    assert '27' in footer, ('the footer hides the total -- 27 rows exist, footer says: %r'
                            % footer)
    assert str(TM.LIST_LIMIT) in footer, footer
    assert '--limit 0' in footer, 'no escape hatch offered: %r' % footer

    # 3. `--limit 0` restores the whole table, and stops advertising a truncation that
    #    did not happen.
    rc, out, err = run(root, 'list', '--limit', '0')
    assert rc == 0, (rc, err)
    text = out_text(out)
    assert '27 task(s)' in text, text
    assert 'showing' not in text, text

    # 4. The machine surface is NOT cut by the default. A JSON consumer that silently
    #    receives 20 of 27 is the same defect one layer down, and harder to notice.
    rc, out, err = run(root, 'list', '--json')
    assert rc == 0, (rc, err)
    assert len(json.loads(out_text(out))) == 27, out_text(out)
    # ... but an EXPLICIT limit is honoured on both surfaces: the default is what differs
    # between them, never the flag.
    rc, out, err = run(root, 'list', '--json', '--limit', '5')
    assert rc == 0, (rc, err)
    assert len(json.loads(out_text(out))) == 5, out_text(out)


# --- cases for the 2026-08-29 changes (spec A2 footguns, A3 board upgrades) ------------

def test_ack_refuses_a_hand_filed_task_and_names_the_remedy():
    """A7 footgun 1: `ack` on a `source: hand` task printed SUCCESS and stamped nothing.

    The only stamping branch was `if task.source == 'board':`; the hand path fell straight
    through to a success print and `return 0`. So the one op whose entire job is to record
    "I read the drift report and the task is still right" logged the word "acked", bumped
    `updated`, changed nothing a later run can read, and let the next `sync` report the
    same drift forever. It must REFUSE, nonzero, naming the remedy -- `comment`, which
    writes the same Log entry and the same `updated` bump without claiming a
    reconciliation.
    """
    root = sync_tree('ackhand')
    seed_hashes(root)

    # T5 is `source: hand` in this fixture. The refusal is exit 2, not a soft warning.
    before = read(os.path.join(root, 'tasks', 'T5-held-delta.md'))
    rc, out, err = run(root, 'ack', 'T5', '-m', 'nothing changed', '--session', KEY + 'b')
    assert rc == 2, ('ack accepted a hand-filed task (rc=%d): %s' % (rc, out_text(out)))
    assert 'REFUSED' in err, err
    assert '`source: hand`' in err, err
    assert 'task.py comment T5' in err, (
        'the refusal must name the remedy, not just the rule: %s' % err)
    assert read(os.path.join(root, 'tasks', 'T5-held-delta.md')) == before, (
        'a refused ack still wrote the file')

    # The green half, without which this test would be equally happy with an `ack` that
    # refuses everything: a board-sourced task still acks.
    rc, out, err = run(root, 'ack', 'T1', '-m', 'read it; still true',
                       '--session', KEY + 'b')
    assert rc == 0, err
    assert 'T1 acked %sb' % KEY in out_text(out), out_text(out)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_ack_since_warns_on_stderr_when_the_source_moved():
    """A7 footgun 2: "`ack` must be a session's LAST step", encoded rather than written.

    `ack` stamps what the source says AT ACK TIME. If the source moved between the drift
    report a session read and the ack it types at the end, the digest just written covers
    text nobody read -- and the next `sync` is green about it. `--since DIGEST` re-reads
    the source and announces the mismatch loudly on STDERR; the exit code is unchanged,
    because the stamp is still the honest one, it is the READING that was stale.
    """
    root = sync_tree('acksince')
    seed_hashes(root)
    path = os.path.join(root, 'tasks', 'T1-the-now-row.md')

    def digest():
        return dict(TM.parse_file(read(path).decode('utf-8'), path)[0])['source_hash']

    seeded = digest()
    assert re.match(r'^[0-9a-f]{12}$', seeded), seeded

    # 1. The matching case is SILENT. Without this half the test would pass against an
    #    `ack` that warns unconditionally, which is a warning nobody reads.
    rc, out, err = run(root, 'ack', 'T1', '-m', 'acked in the same session',
                       '--since', seeded, '--session', KEY + 'b')
    assert rc == 0, err
    assert err.strip() == '', 'an unmoved source produced a warning: %r' % err
    assert digest() == seeded, digest()

    # 2. The source moves under the session's feet.
    bpath = os.path.join(root, 'HANDOFF.md')
    write(bpath, read(bpath).decode('utf-8').replace(
        'The summary paragraph as the BOARD states it.',
        'A DIFFERENT paragraph, edited after the drift report was printed.'))
    rc, out, err = run(root, 'ack', 'T1', '-m', 'acked from a stale report',
                       '--since', seeded, '--session', KEY + 'c')
    assert rc == 0, ('the mismatch is a WARNING, not a refusal -- the stamp is still '
                     'honest: rc=%d %s' % (rc, err))
    moved_to = digest()
    assert moved_to != seeded, moved_to
    assert 'WARNING' in err, ('the mismatch must be announced: %r' % err)
    assert 'source moved since the drift report' in err, err
    assert seeded in err and moved_to in err, (
        'the warning must print BOTH digests, or the reader cannot tell what they '
        'missed: %r' % err)
    assert 'last step' in err.lower(), (
        'the warning must state the rule it is enforcing: %r' % err)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_new_id_is_explicit_and_refuses_live_malformed_or_retired():
    """A7 footgun 3: `new` had no id control, so a work row was forced into the findings
    series -- an id whose prefix says "this came from an audit" for something typed by
    hand. `--id` fixes it, and is validated at the seam rather than linted afterwards.
    """
    root = good_tree('newid')
    write(os.path.join(root, 'tasks', 'retired-ids.txt'), '# spent\nT0\nZT-P0-1\n')

    # The given id is used verbatim, and the file is named for it.
    rc, out, err = run(root, 'new', 'a work row with a chosen id', '--id', 'WORK-1',
                       '--session', KEY)
    assert rc == 0, err
    assert out_text(out).split()[0] == 'WORK-1', out_text(out)
    named = [n for n in os.listdir(os.path.join(root, 'tasks'))
             if n.startswith('WORK-1-') and n.endswith('.md')]
    assert len(named) == 1, sorted(os.listdir(os.path.join(root, 'tasks')))
    rc, data, err = rj(root, 'show', 'WORK-1')
    assert data['id'] == 'WORK-1', data

    # ... and allocation is untouched by it: the next scan-minted id still comes from the
    # prefix series, not from the hand-picked one.
    rc, out, err = run(root, 'new', 'an ordinary row', '--session', KEY)
    assert rc == 0 and out_text(out).split()[0] == 'T8', out_text(out)

    # Malformed.
    rc, out, err = run(root, 'new', 'bad', '--id', 'not an id', '--session', KEY)
    assert rc == 2 and 'does not match' in err, (rc, err)
    # Already live.
    rc, out, err = run(root, 'new', 'clash', '--id', 'T1', '--session', KEY)
    assert rc == 2 and "id 'T1' already exists" in err, (rc, err)
    # Retired: ids are never reused, and the refusal says why rather than just "no".
    rc, out, err = run(root, 'new', 'zombie', '--id', 'T0', '--session', KEY)
    assert rc == 2 and 'retired-ids.txt' in err, (rc, err)
    assert 'two items' in err and 'one address' in err, err
    assert not [n for n in os.listdir(os.path.join(root, 'tasks'))
                if n.startswith('T0-')], 'a retired id was filed'
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_set_refuses_the_flag_form_and_names_the_positional():
    """A7 footgun 6: `set --title x` was an argparse error about an unknown option.

    Every OTHER write op here takes `--flags`, so reaching for `--title` is a reasonable
    guess -- it is just not the interface. The flags are declared as `argparse.SUPPRESS`ed
    traps precisely so the tool can say what to type instead of "unrecognized arguments".
    """
    root = good_tree('setflags')
    path = os.path.join(root, 'tasks', 'T2-next-alpha.md')
    before = read(path)

    for flag, value in (('--title', 'a new title'), ('--brief', 'a new brief'),
                        ('--size', 'L'), ('--labels', 'docs'),
                        ('--related', 'T3'), ('--parent', 'T6')):
        rc, out, err = run(root, 'set', 'T2', flag, value, '--session', KEY)
        assert rc == 2, ('%s was ACCEPTED (rc=%d): %s' % (flag, rc, out_text(out)))
        assert 'takes POSITIONALS, not flags' in err, (flag, err)
        assert 'task.py set T2 %s' % flag.lstrip('-') in err, (
            'the refusal must show the positional form to type: %s' % err)
        assert read(path) == before, '%s wrote the file it refused' % flag

    # And the no-argument form prints usage rather than a traceback or a silent no-op.
    rc, out, err = run(root, 'set', 'T2', '--session', KEY)
    assert rc == 2, (rc, out_text(out))
    assert 'usage: task.py set <id> <field> <value>' in err, err
    assert "'brief'" in err, 'the usage line must list what is settable: %s' % err
    assert '`pri` is `promote`' in err, err
    assert read(path) == before

    # The green half: the positional form the refusal names actually works.
    rc, out, err = run(root, 'set', 'T2', 'size', 'L', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T2')
    assert data['size'] == 'L', data


def test_list_parent_filter_announces_its_truncation_too():
    """A7 footgun 5: EVERY truncated read path announces the truncation, `--parent`
    included.

    `--parent` is the view a session uses to ask "what is left in this group", which is
    exactly the question a silent cap answers wrongly -- and the group view is the one
    where the reader is least likely to suspect a 20-row ceiling, because they are
    thinking about a group, not about the backlog.
    """
    root = good_tree('parentlimit')
    for n in range(21):
        place(root, 'C%d' % n, 'child-%d' % n, title='child row %d' % n,
              pri='LATER', size='S', parent='T6')
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err

    rc, out, err = run(root, 'list', '--parent', 'T6')
    assert rc == 0, err
    text = out_text(out)
    footer = [l for l in text.split('\n') if l.strip()][-1]
    assert 'showing %d of 22' % TM.LIST_LIMIT in footer, (
        'the --parent view hid 2 of 22 children without saying so: %r' % footer)
    assert '--limit 0' in footer, footer

    # The escape hatch works on this path too, and stops claiming a truncation.
    rc, out, err = run(root, 'list', '--parent', 'T6', '--limit', '0')
    assert rc == 0 and '22 task(s)' in out_text(out), out_text(out)
    assert 'showing' not in out_text(out), out_text(out)

    # The machine surface is never cut by the default, on this path either.
    rc, out, err = run(root, 'list', '--parent', 'T6', '--json')
    assert rc == 0, err
    assert len(json.loads(out_text(out))) == 22, out_text(out)


def test_brief_round_trips_and_prints_under_now_and_next():
    """A3.1: `brief` is the one-line board annotation for the constraint a reader must
    not miss (the "NOT parallel-safe with `P3`" class).

    Two properties: it survives the canonical writer (it is a frontmatter field like any
    other), and it PRINTS -- under the NOW block and under each NEXT row. A field that
    round-trips but never reaches the board is a field that silently does nothing, which
    is worse than not having it: a session would write the constraint down and believe it
    had been communicated.
    """
    root = good_tree('brief')
    now_brief = 'NOT parallel-safe with T2 -- both rewrite the same closure table.'
    next_brief = 'blocked on a decision, not on code'

    rc, out, err = run(root, 'set', 'T1', 'brief', now_brief, '--session', KEY)
    assert rc == 0, err
    rc, out, err = run(root, 'set', 'T2', 'brief', next_brief, '--session', KEY)
    assert rc == 0, err

    rc, data, err = rj(root, 'show', 'T1')
    assert data['brief'] == now_brief, data
    # It is the THIRD key, right after `title` -- schema order is fixed, and a field that
    # drifts down the file is a field a hand-editor stops seeing.
    text = read(os.path.join(root, 'tasks', 'T1-the-now-row.md')).decode('utf-8')
    keys = [l.split(':')[0] for l in text.split('---')[1].strip().split('\n')]
    assert keys[:3] == ['id', 'title', 'brief'], keys

    rc, out, err = run(root, 'board')
    assert rc == 0, err
    lines = out_lines(out)
    now_at = [i for i, l in enumerate(lines) if l.startswith('NOW    T1')]
    assert len(now_at) == 1, out_text(out)
    assert lines[now_at[0] + 1] == '    !  ' + now_brief, (
        'the NOW brief is not on the line under the NOW row:\n%s' % out_text(out))
    next_at = [i for i, l in enumerate(lines) if l.startswith('  T2 ')]
    assert len(next_at) == 1, out_text(out)
    assert lines[next_at[0] + 1] == '    !      ' + next_brief, (
        'the NEXT brief is not on the line under its row:\n%s' % out_text(out))

    # An empty brief prints NOTHING rather than an empty annotation line -- otherwise the
    # board grows a blank row per unannotated item and the size budget is spent on air.
    assert [l for l in lines if l.strip() == '!'] == [], lines
    rc, data, err = rj(root, 'board')
    assert data['now'][0]['brief'] == now_brief, data['now'][0]
    assert 'banner' in data, sorted(data)

    # `show` prints it beneath the title.
    rc, out, err = run(root, 'show', 'T1')
    assert now_brief in out_text(out), out_text(out)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_brief_is_refused_over_cap_or_with_a_pipe_or_a_newline():
    """The three ways a `brief` stops being a one-line board annotation, refused at the
    SEAM by both `set` and `new` rather than stored and linted afterwards.

    `|` is in the list because every row-shaped rendering of the board is pipe-delimited,
    so a brief containing one does not merely look wrong -- it silently splits a cell.
    """
    root = good_tree('briefbad')
    path = os.path.join(root, 'tasks', 'T1-the-now-row.md')
    before = read(path)

    over = 'x' * (TM.BRIEF_MAX + 1)
    for value, needle in ((over, 'cap %d' % TM.BRIEF_MAX),
                          ('a | b', 'brief contains "|"'),
                          ('a\nb', 'more than one line')):
        rc, out, err = run(root, 'set', 'T1', 'brief', value, '--session', KEY)
        assert rc == 2, ('brief %r was accepted (rc=%d)' % (value[:30], rc))
        assert needle in err, (value[:30], err)
        assert 'bounded read' in err, (
            'the refusal must say why the cap exists: %s' % err)
        assert read(path) == before, 'a refused brief still wrote the file'

        rc, out, err = run(root, 'new', 'a row', '--brief', value, '--session', KEY)
        assert rc == 2, ('new --brief %r was accepted (rc=%d)' % (value[:30], rc))
        assert needle in err, (value[:30], err)

    # The boundary is pinned on BOTH sides: exactly BRIEF_MAX is legal, or this test
    # would be equally happy with a cap set anywhere below it.
    at_cap = 'y' * TM.BRIEF_MAX
    rc, out, err = run(root, 'set', 'T1', 'brief', at_cap, '--session', KEY)
    assert rc == 0, ('a brief of exactly %d chars must be legal: %s' % (TM.BRIEF_MAX, err))
    rc, data, err = rj(root, 'show', 'T1')
    assert data['brief'] == at_cap, len(data['brief'])
    # And clearing it is always available -- the refusals all say so.
    rc, out, err = run(root, 'set', 'T1', 'brief', '', '--session', KEY)
    assert rc == 0, err
    rc, data, err = rj(root, 'show', 'T1')
    assert data['brief'] == '', data
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_lint_check_4_catches_a_hand_edited_bad_brief():
    """The seam refusals above cover the tool's own write path; check 4 covers the hand
    edit, which is the only other way a value gets into a task file.

    A brief is edited in place far more often than it is `set`, because it is one line at
    the top of a file a session already has open. Without the lint clause the cap would be
    enforced only against the interface nobody uses for it.
    """
    root = good_tree('briefint')
    path = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    long_brief = 'z' * 131
    write(path, canon('T4', 'later gamma', brief=long_brief, pri='LATER', size='?',
                      parent='T6', labels=['docs']))
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    line = first_match(text, r'brief is 131 chars, cap 120')
    assert line is not None, text
    assert 'T4-later-gamma.md' in line, line
    assert 'set T4 brief ""' in line, (
        'the violation must name the exact repair command: %s' % line)

    # A pipe and a newline are caught at rest too. (A newline cannot be written into the
    # frontmatter at all -- the parser rejects the file first -- which is itself the
    # stronger guarantee, so only the pipe is checked here as a `brief` violation.)
    write(path, canon('T4', 'later gamma', brief='a | b', pri='LATER', size='?',
                      parent='T6', labels=['docs']))
    rc, out, err = run(root, 'lint')
    assert rc == 1 and 'brief contains "|"' in (out_text(out) + err), out_text(out) + err

    # Restore control: the same file with a legal brief is green again.
    write(path, canon('T4', 'later gamma', brief='a legal one-line brief', pri='LATER',
                      size='?', parent='T6', labels=['docs']))
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_board_refuses_a_missing_or_overlong_banner():
    """A3.2: `tasks/BANNER.md` is the single must-read thing, and `board` REFUSES without
    it.

    A missing banner is a broken session-start, not a default. The alternative -- render
    the board and omit the banner -- is the failure this repo names: a session-start that
    LOOKS complete and carries nothing, because the one part of the view that cannot be
    derived (where the last session stopped, what this one must not repeat) is exactly the
    part that silently went missing.
    """
    root = good_tree('banner')
    banner_path = os.path.join(root, 'tasks', 'BANNER.md')

    # The green baseline first: a board that never renders would pass every assertion
    # below without the check existing.
    rc, out, err = run(root, 'board')
    assert rc == 0, err
    assert BANNER_TEXT.split('\n')[0] in out_text(out), (
        'the banner is printed VERBATIM above the BOARD header:\n%s' % out_text(out))
    assert out_text(out).index(BANNER_TEXT.split('\n')[0]) < out_text(out).index('BOARD'), \
        out_text(out)

    os.remove(banner_path)
    rc, out, err = run(root, 'board')
    assert rc == 2, ('board rendered without a banner (rc=%d):\n%s' % (rc, out_text(out)))
    assert 'does not exist' in err and 'BANNER.md' in err, err
    assert 'session-start' in err, err
    # The refusal precedes ALL output, --json included: a machine consumer must not get a
    # banner-less payload either.
    rc, out, err = run(root, 'board', '--json')
    assert rc == 2 and out_text(out).strip() == '', (rc, out_text(out))

    # Over the cap. `board` states a size that is arithmetic over this cap plus the
    # NOW/NEXT budgets, so an over-long banner does not make the view longer -- it makes
    # the view's CLAIM false.
    write(banner_path, '%s -- banner\n' % KEY + '\n'.join(
        'filler line %d' % n for n in range(TM.BANNER_MAX_LINES)) + '\n')
    rc, out, err = run(root, 'board')
    assert rc == 2, ('an over-long banner rendered (rc=%d)' % rc)
    assert 'cap %d' % TM.BANNER_MAX_LINES in err, err
    assert 'is %d lines' % (TM.BANNER_MAX_LINES + 1) in err, err

    # Exactly at the cap is legal -- pinned so this test cannot be satisfied by a check
    # that refuses every banner.
    write(banner_path, '\n'.join(['%s -- banner' % KEY] +
                                 ['line %d' % n for n in range(TM.BANNER_MAX_LINES - 1)])
          + '\n')
    rc, out, err = run(root, 'board')
    assert rc == 0, ('a banner of exactly %d lines must render: %s'
                     % (TM.BANNER_MAX_LINES, err))


def test_lint_check_12_catches_the_three_banner_failures():
    """Check 12 exists even though `board` already refuses, because the two answer
    different questions.

    `board` refuses at READ time, which protects the reader who runs it. Lint is what a
    session runs BEFORE it commits, and the failure this catches is the session that
    promoted a row, wrote no banner, and left the NEXT session's first command broken. A
    refusal the tool only issues to the victim is a refusal issued too late.
    """
    root = good_tree('bannerlint')
    banner_path = os.path.join(root, 'tasks', 'BANNER.md')
    assert TM.LINT_CHECKS[-1].__name__ == 'check_banner', \
        [c.__name__ for c in TM.LINT_CHECKS]

    # 1. Missing.
    os.remove(banner_path)
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    line = first_match(text, r'BANNER\.md does not exist')
    assert line is not None, text
    assert 'board` refuses without it' in line, line

    # 2. Over the cap.
    write(banner_path, '%s -- banner\n' % KEY + '\n'.join(
        'filler line %d' % n for n in range(TM.BANNER_MAX_LINES)) + '\n')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    assert first_match(text, r'is %d lines, cap %d'
                       % (TM.BANNER_MAX_LINES + 1, TM.BANNER_MAX_LINES)) is not None, text

    # 3. A first line carrying no session key -- the anti-staleness half. Deliberately
    #    weak (a date, merely well-formed): nothing here can tell a banner rewritten this
    #    session from one whose date was edited, and a check that pretended to would be
    #    the fail-by-passing shape. What it catches is the banner that is simply OLD.
    write(banner_path, 'the state of play\n\nno date anywhere on the first line\n')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    line = first_match(text, r'carries no session key')
    assert line is not None, text
    assert 'YYYY-MM-DD' in line, line

    # Restore control.
    write(banner_path, BANNER_TEXT)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_the_banner_may_not_carry_a_glyph_the_board_cannot_render():
    """Check 12, fourth clause: no character `ascii_safe` would escape.

    FOUND BY LOOKING AT THE OUTPUT, not by a test. `ASCII_FOLD` was censused out of task
    titles and bodies, and `tasks/BANNER.md` did not exist when that census ran -- so the
    first real banner, written in the house banner style, opened the session-start view
    with a literal escape sequence::

        \\u23f0 `TK53`: 15 appends remain. Until they land, deleting `tasks/` loses ...

    The escape fallback is right for a TITLE (lossy but honest, written once by someone
    who sees the result) and wrong for the banner, which is free prose rewritten every
    session and printed at the very top of the view. A reader cannot tell noise from
    content and nothing complains -- the fail-by-passing shape, in the one file whose
    whole job is to be read first.

    So the two glyphs already in use were mapped, and the GAP was made mechanical: the
    next session that pastes an emoji is told at `lint` time instead of shipping noise.
    Deliberately scoped to the banner; making every unmapped glyph fatal would redden 153
    task files nobody is editing, and the fold exists precisely so those render.

    Observed red before `unmappable` existed -- and note this case cannot be caught by
    `test_board_ascii_under_cp1252`, which proves the output IS ascii, which an escape
    sequence also is.
    """
    root = good_tree('bannerglyph')
    banner_path = os.path.join(root, 'tasks', 'BANNER.md')

    write(banner_path, u'%s -- state of play \U0001F680 shipping\nsecond line\n' % KEY)
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, text
    line = first_match(text, r'character\(s\) `board` cannot render')
    assert line is not None, text
    assert 'U+1F680' in line, line

    # A glyph that IS mapped stays green -- this is a check on renderability, not an
    # ASCII-only rule, and banning the warn badge from the banner would be absurd.
    write(banner_path, u'%s -- state of play\n⚠ a real trap\n' % KEY)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err
    rc, out, err = run(root, 'board')
    assert rc == 0, err
    assert '(!) a real trap' in out_text(out), out_text(out)

    # Restore control.
    write(banner_path, BANNER_TEXT)
    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err


def test_non_task_md_is_skipped_only_at_the_top():
    """The exclusion is exact-name and TOP-LEVEL ONLY, and both halves are load-bearing.

    `BANNER.md` and `README.md` are markdown that lives in `tasks/` for a reader; without
    the skip they would be loaded as tasks and fail checks 1 and 3 on every run. But an
    exemption that TRAVELS WITH THE ARCHIVE MOVE is an exemption that hides a real record
    -- so nothing under `closed/` is exempt, and a `README.md` filed there is a parse
    failure rather than a quiet omission.

    The skip is duplicated on purpose: `Store.md_paths` (the scanner) and `disk_md_count`
    (check 10's independent recount) each apply it. Both are asserted here, because a skip
    applied in only one of them makes the recount disagree with the scan on every run --
    which would present as the blind-parser violation and send the next reader hunting a
    scanner bug that does not exist.
    """
    root = good_tree('nontask')
    rc, data, err = rj(root, 'counts')
    assert (data['total'], data['disk_total']) == (7, 7), data

    write(os.path.join(root, 'tasks', 'README.md'),
          '# tasks/\n\nProse for a human. Not a task, and never scanned as one.\n')
    rc, out, err = run(root, 'lint')
    assert rc == 0, ('a top-level README.md was scanned as a task:\n%s'
                     % (out_text(out) + err))
    assert 'clean (12 checks, 7 task file(s) parsed)' in out_text(out), out_text(out)
    rc, data, err = rj(root, 'counts')
    assert (data['total'], data['disk_total']) == (7, 7), (
        'README.md reached one of the two scanners: %s' % data)
    assert (data['disk_open'], data['disk_closed']) == (7, 0), data

    # BANNER.md has been present in every one of those runs -- state it, rather than let
    # it be an incidental fact of the fixture.
    assert os.path.isfile(os.path.join(root, 'tasks', 'BANNER.md'))
    assert set(TM.NON_TASK_MD) == set(['BANNER.md', 'README.md']), TM.NON_TASK_MD

    # ... and under closed/ the same filename IS scanned, and fails.
    write(os.path.join(root, 'tasks', 'closed', 'README.md'),
          '# archived prose\n\nThis is not a task file and must not be treated as one.\n')
    rc, out, err = run(root, 'lint')
    text = out_text(out) + err
    assert rc == 1, ('closed/README.md was exempted from the scan:\n%s' % text)
    assert 'closed/README.md' in text, text


def test_board_stays_under_its_size_ceiling():
    """A3.3: board size is PINNED, not aspirational.

    Four prose claims in this repo said the board was "~25 lines" -- `scripts/task.py`'s
    own docstring and `docs/tasktool-spec.md` twice among them -- and by the time the
    banner and the row briefs landed, none of them was measured against anything. A stale
    size claim is exactly the rot class this repo documents, and the answer is the one it
    prescribes: derive the number, or pin it with a test.

    THE CORPUS IS DELIBERATELY THE WORST LEGAL CASE, not a typical one. Full banner (14
    lines, the cap), the full NOW budget with a maximum-length `brief` AND a summary
    paragraph, the full NEXT budget with a maximum-length `brief` on every row. A ceiling
    measured against a small corpus is a ceiling that has never been tested.
    """
    banner = '\n'.join(['%s -- fixture banner at exactly the cap.' % KEY] +
                       ['banner line %d' % n
                        for n in range(TM.BANNER_MAX_LINES - 1)]) + '\n'
    assert len(banner.rstrip('\n').split('\n')) == TM.BANNER_MAX_LINES

    root = fresh('ceiling', banner=banner)
    os.makedirs(os.path.join(root, 'tasks', 'closed'))
    max_brief = 'b' * TM.BRIEF_MAX
    summary = ('A summary paragraph long enough to wrap to several lines at the width '
               'the board uses, because a NOW row with a one-word summary would make '
               'this ceiling trivially easy to meet and prove nothing about the view a '
               'real session reads.')
    place(root, 'T1', 'the-now-row', title='the NOW row, with a title of realistic length',
          brief=max_brief, pri='NOW', size='L', labels=['infra'],
          body='%s\n\n## Traps\n\n## Log\n' % summary)
    for n, tid in enumerate(('T2', 'T3', 'T4')):
        place(root, tid, 'next-%d' % n, title='a NEXT row with a realistic title %d' % n,
              brief=max_brief, pri='NEXT', size='M')
    place(root, 'T5', 'held', title='held', pri='HOLD', size='M', brief=max_brief)
    place(root, 'T6', 'later', title='later', pri='LATER', size='L', brief=max_brief)
    place(root, 'T7', 'someday', title='someday', pri='SOMEDAY', size='S',
          brief=max_brief)

    rc, out, err = run(root, 'lint')
    assert rc == 0, out_text(out) + err
    rc, out, err = run(root, 'board')
    assert rc == 0, err
    lines = out_lines(out)
    while lines and lines[-1] == '':
        lines.pop()

    # The instrument control. A board that printed nothing, or that dropped the banner or
    # the briefs, would satisfy a bare `<=` and pass this test while failing its point.
    assert lines[0].startswith(KEY), lines[:2]
    assert lines[TM.BANNER_MAX_LINES - 1] == 'banner line %d' % (TM.BANNER_MAX_LINES - 2), \
        lines[:TM.BANNER_MAX_LINES]
    assert sum(1 for l in lines if max_brief in l) == 4, (
        'the full-budget board should carry 4 briefs (1 NOW + 3 NEXT):\n%s'
        % out_text(out))
    assert len(lines) >= 30, ('this corpus cannot produce a board this short -- the '
                              'ceiling is being met by an empty view:\n%s' % out_text(out))

    assert len(lines) <= TM.BOARD_MAX_LINES, (
        'the full-budget board is %d lines, over the stated ceiling of %d. The number is '
        'a CLAIM the tool makes about itself (banner cap + NOW/NEXT budgets); either the '
        'view grew or the claim is stale, and a stale size claim is the rot class this '
        'pin exists to delete.\n%s' % (len(lines), TM.BOARD_MAX_LINES, out_text(out)))


def test_new_help_names_the_100_char_title_cap():
    """A7 footgun 6, second half: the cap appears where a caller meets it.

    `new` refuses a title over 100 characters and never truncates one, which is the right
    behaviour and an infuriating one to discover by hitting it -- the refusal arrives
    after the sentence has been written. The number belongs in `--help`, next to the
    positional it constrains, and it is derived from `TITLE_MAX` rather than typed so that
    raising the cap cannot leave the help text lying.
    """
    root = good_tree('newhelp')
    rc, out, err = run(root, 'new', '--help')
    assert rc == 0, err
    # argparse re-wraps help text to the terminal width, so the sentence under test is
    # split across lines at a column nobody chose. Collapse whitespace before matching:
    # asserting on the wrapped form would pin the console width, not the message.
    text = ' '.join(out_text(out).split())
    assert '%d characters' % TM.TITLE_MAX in text, text
    assert 'refused above that, never truncated' in text, text
    assert TM.TITLE_MAX == 100, TM.TITLE_MAX
    # `--id` and `--brief` are advertised too -- an option nobody can discover is an
    # option that does not exist.
    assert '--id ID' in text, text
    assert '--brief' in text and '%d chars' % TM.BRIEF_MAX in text, text


# --- the sabotage pass -----------------------------------------------------------------
# Each case below breaks the property one lint check guards -- the narrowest *plausible*
# weakening, the typo a real edit makes -- and asserts that lint goes red AND that the
# failure text NAMES the sabotaged subject. That last assertion is what makes the red
# ATTRIBUTABLE: a run that reddens because some other check fired proves nothing about
# the check under test.
#
# Instrument control, in every case: a BASELINE lint on the same tree which must be clean
# (a sabotage on a red baseline is not attributable), and a REBUILD plus a re-lint which
# must be clean again (a restore bug must not be mistakeable for a green sabotage).
#
# Check 10 (`check_min_parsed`) is itself the instrument control for the other nine, so it
# gets THREE sabotages: a corpus shrunk below the declared floor, a genuinely BLIND PARSER
# (a patched copy whose `md_paths` skips `closed/` -- the plausible "lint only cares about
# open tasks" refactor), and THE FLOOR ITSELF SET TO 0, which is the instrument's own
# instrument. The first two ask whether the tool notices broken DATA; only the third asks
# whether it notices its own control being switched off by one config value. It could not,
# until PROOF2.md section 2 found it printing `clean`.

def sab_parses(root):
    """The edit: delete the (empty) `parent:` line while hand-tidying frontmatter."""
    p = os.path.join(root, 'tasks', 'T2-next-alpha.md')
    t = read(p).decode('utf-8').replace('parent:\n', '')
    write(p, t)


def sab_ids_unique(root):
    """The edit: archive a task by COPYING it into closed/ instead of moving it."""
    src = os.path.join(root, 'tasks', 'T5-held-delta.md')
    dst = os.path.join(root, 'tasks', 'closed', 'T5-held-delta.md')
    t = read(src).decode('utf-8').replace('closed:\n', 'closed: %s\n' % KEY)
    write(dst, t)


def sab_filenames(root):
    """The edit: a slug typo on a manual rename -- the id separator is dropped."""
    os.rename(os.path.join(root, 'tasks', 'T3-next-beta.md'),
              os.path.join(root, 'tasks', 'T3next-beta.md'))


def sab_enums(root):
    """The edit: a hand-typed date loses its zero padding (2026-8-21)."""
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(p, read(p).decode('utf-8').replace('moved: 2026-08-21', 'moved: 2026-8-21'))


def sab_enums_open_blank(root):
    """The RELAXATION, side (a): blank BOTH pri and size on an OPEN row.

    check_enums exempts pri/size from the enum under ``closed/`` (a closed record is not
    competing for a rank). A relaxation is the edit most likely to fail by passing, so it
    is sabotaged from both sides: the exemption must not LEAK OUT of closed/ (this case),
    and inside closed/ "optional" must not degrade into "unchecked" (the next one).
    """
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    t = read(p).decode('utf-8').replace('pri: LATER\n', 'pri:\n')
    write(p, t.replace('size: ?\n', 'size:\n'))


def sab_enums_closed_bad(root):
    """The RELAXATION, side (b): a NON-empty but bogus pri on a CLOSED record.

    The task is closed THROUGH the tool first, so the only hand edit is the bogus value
    and the red is attributable to it rather than to the archive move.
    """
    rc, out, err = run(root, 'close', 'T7', '-m', 'shipped', '--session', KEY)
    assert rc == 0, err
    rc, mid = lint_text(root)
    assert rc == 0, 'setup is not green after a legal close:\n%s' % mid
    p = os.path.join(root, 'tasks', 'closed', 'T7-someday-eps.md')
    t = read(p).decode('utf-8')
    assert '\npri:' in t, t
    write(p, re.sub(r'(?m)^pri:.*$', 'pri: URGENT', t, count=1))


def sab_pri_budget_now(root):
    """The edit: hand-edit a second row to `pri: NOW`, skipping `promote`'s refusal."""
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(p, read(p).decode('utf-8').replace('pri: LATER', 'pri: NOW'))


def sab_pri_budget_next(root):
    """The edit: a fourth row hand-edited to `pri: NEXT`.

    INSTRUMENT CORRECTION, 2026-08-21. The first version of this probe bumped ONE row to
    NEXT on a tree that had two, reaching THREE -- which is the cap, not over it -- and
    came back ``task lint: clean``. That green was the PROBE's fault, not the check's: it
    never drove the property it named. The setup now fills the budget legally THROUGH the
    tool (and asserts the tree is still green at exactly the cap, so the later red is
    attributable to the one hand edit and not to the setup), and only then makes the
    fourth row NEXT.
    """
    rc, out, err = run(root, 'promote', 'T5', 'NEXT', '--session', KEY)
    assert rc == 0, err
    rc, mid = lint_text(root)
    assert rc == 0, 'setup is not green at exactly the cap:\n%s' % mid
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(p, read(p).decode('utf-8').replace('pri: LATER', 'pri: NEXT'))


def sab_deps(root):
    """The edit: a dep id typo -- T2 becomes T20, which blocks T3 forever."""
    p = os.path.join(root, 'tasks', 'T3-next-beta.md')
    write(p, read(p).decode('utf-8').replace('deps: [T2]', 'deps: [T20]'))


def sab_deps_cycle(root):
    """The edit: close the loop by hand, skipping `dep add`'s cycle refusal."""
    p = os.path.join(root, 'tasks', 'T2-next-alpha.md')
    write(p, read(p).decode('utf-8').replace('deps: []', 'deps: [T3]'))


def sab_parents(root):
    """The edit: archive the parent group while a child is still open."""
    src = os.path.join(root, 'tasks', 'T6-the-group.md')
    dst = os.path.join(root, 'tasks', 'closed', 'T6-the-group.md')
    write(dst, read(src).decode('utf-8').replace('closed:\n', 'closed: %s\n' % KEY))
    os.remove(src)


def sab_closed_field(root):
    """The edit: `mv` a finished task into closed/ without stamping the date."""
    src = os.path.join(root, 'tasks', 'T7-someday-eps.md')
    shutil.move(src, os.path.join(root, 'tasks', 'closed', 'T7-someday-eps.md'))


def sab_labels(root):
    """The edit: a label case slip -- infra becomes Infra."""
    p = os.path.join(root, 'tasks', 'T1-the-now-row.md')
    write(p, read(p).decode('utf-8').replace('labels: [infra]', 'labels: [Infra]'))


def sab_min_parsed_floor(root):
    """Instrument control, part 1: the corpus shrinks below the declared floor."""
    for name in ('T5-held-delta.md', 'T6-the-group.md', 'T7-someday-eps.md'):
        os.remove(os.path.join(root, 'tasks', name))
    # T4's parent T6 is gone, so keep the tree otherwise consistent.
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(p, read(p).decode('utf-8').replace('parent: T6', 'parent:'))


def sab_min_parsed_disabled(root):
    """Instrument control, part 3 -- SABOTAGING THE INSTRUMENT ITSELF.

    Every other case here breaks the DATA and asks whether the tool notices. This one
    breaks the TOOL'S CONFIGURED CONTROL and asks the same question, which is the harder
    half: `docs/sabotage-procedure.md` requires controlling your instrument as well as
    your subject. The narrowest plausible weakening is not deleting the floor (that was
    already refused) -- it is the edit a real session makes when a zero-headroom floor
    reddens on a tidy: set it to 0 "for now". Before the fix that printed `clean`.
    """
    cfg = os.path.join(root, 'tasks', 'config.json')
    data = json.loads(read(cfg).decode('utf-8'))
    data['min_tasks_parsed'] = 0
    write(cfg, json.dumps(data, indent=2) + '\n')


def sab_enums_updated(root):
    """The edit: `updated` loses its zero padding, exactly as `moved` can.

    Sabotaged separately from `moved` and not assumed to be covered by it: the two are
    validated by the same helper NOW, and the plausible weakening is a future refactor
    that keeps the loop over ('created', 'moved') and forgets to add the third field --
    which is silent, because a task whose `updated` is garbage still lints on every other
    clause.
    """
    p = os.path.join(root, 'tasks', 'T4-later-gamma.md')
    write(p, read(p).decode('utf-8').replace('updated: 2026-08-21', 'updated: 2026-8-21'))


def sab_enums_updated_before_moved(root):
    """The edit: `updated` hand-set behind `moved`.

    This is the state the write path cannot produce (every op that bumps `moved` bumps
    `updated`), which is exactly why it needs a check: it can only arrive by hand or by a
    tool that stamps one and not the other, and both are silent. The ORDER clause is the
    load-bearing part of the moved/updated pair -- without it, "updated is the last write"
    is a claim nothing tests.
    """
    p = os.path.join(root, 'tasks', 'T2-next-alpha.md')
    t = read(p).decode('utf-8').replace('moved: 2026-08-21', 'moved: 2026-08-21c')
    write(p, t)


def sab_source_blank(root):
    """The edit: blank `source` -- the value a careless in-place migration leaves behind.

    Not a bogus value: an EMPTY one, because that is what an added-but-unfilled key looks
    like, and "the key is present" is the weaker property a parser check would settle for.
    """
    p = os.path.join(root, 'tasks', 'T5-held-delta.md')
    write(p, read(p).decode('utf-8').replace('source: hand\n', 'source:\n'))


def sab_source_typo(root):
    """The edit: `board` -> `Board`, the near-miss of a fixed value.

    sync keys its whole CORPUS-ONLY behaviour off this field, so a value that reads
    correctly to a human and matches nothing mechanically is the expensive failure -- a
    `Board` task is silently "never seen in a source", i.e. treated as hand-filed and
    never reported.
    """
    p = os.path.join(root, 'tasks', 'T6-the-group.md')
    write(p, read(p).decode('utf-8').replace('source: hand', 'source: Board'))


def sab_related_dangling(root):
    """The edit: a `related` id that resolves to nothing (T5 -> T50, a digit fat-finger)."""
    p = os.path.join(root, 'tasks', 'T5-held-delta.md')
    write(p, read(p).decode('utf-8').replace('related: []', 'related: [T50]'))


def sab_related_self(root):
    """The edit: a task related to itself -- what a copy-pasted `set related` line does."""
    p = os.path.join(root, 'tasks', 'T5-held-delta.md')
    write(p, read(p).decode('utf-8').replace('related: []', 'related: [T5]'))


def sabotage(name, breaker, pattern):
    """Baseline green -> break -> attributable red -> rebuild -> green. Returns the line.

    ``pattern`` is matched per LINE, not against the whole text: a red whose matching
    substring is spread across two unrelated violations is not evidence about one check.
    """
    root = good_tree(name)
    rc0, base = lint_text(root)
    assert rc0 == 0, ('BASELINE NOT GREEN -- a sabotage on a red baseline is not '
                      'attributable:\n%s' % base)
    breaker(root)
    rc1, text = lint_text(root)
    assert rc1 != 0, ('GREEN UNDER SABOTAGE -- the check does not guard this:\n%s' % text)
    line = first_match(text, pattern)
    assert line is not None, (
        'red, but NOT ATTRIBUTABLE: no line matched %r, so this run is evidence about '
        'some other check:\n%s' % (pattern, text))
    root = good_tree(name)
    rc2, back = lint_text(root)
    assert rc2 == 0, ('RESTORE NOT GREEN -- a restore bug must not be mistakeable for a '
                      'green sabotage:\n%s' % back)
    return line


def test_sabotage_check_parses():
    """check_1: delete the empty `parent:` line from T2. Regex: `missing keys`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T2-next-alpha.md: missing keys ['parent'], unknown keys -
        (all fourteen keys are always present -- see SPEC.md section 3.1). Fix the
        frontmatter by hand -- the fourteen keys are fixed and always present.
    """
    line = sabotage('sab_parses', sab_parses, r'missing keys')
    assert 'T2-next-alpha.md' in line, line


def test_sabotage_check_ids_unique():
    """check_2: copy T5 into closed/ instead of moving it. Regex: `id 'T5' is used by BOTH`.

    2026-08-21 observed::

        FAIL: id 'T5' is used by BOTH <t>/sab/tasks/T5-held-delta.md and
        <t>/sab/tasks/closed/T5-held-delta.md. Ids are addresses and are never reused;
        give one of them a fresh id from `task.py new`.
    """
    line = sabotage('sab_ids', sab_ids_unique, r"id 'T5' is used by BOTH")
    assert 'closed' in line, line


def test_sabotage_check_filenames():
    """check_3: rename T3-next-beta.md to T3next-beta.md. Regex: `does not start with 'T3-'`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T3next-beta.md does not start with 'T3-'. The filename is
        cosmetic, but a filename that disagrees with the id makes `ls` lie; rename the
        file (the id stays put).
    """
    sabotage('sab_filenames', sab_filenames, r"does not start with 'T3-'")


def test_sabotage_check_enums_moved():
    """check_4: `moved: 2026-08-21` -> `2026-8-21`. Regex: `moved is '2026-8-21'`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T4-later-gamma.md: moved is '2026-8-21', not a session key
        (YYYY-MM-DD with an optional single lowercase letter). One of the stamps was
        typed by hand; fix the wrong one.
    """
    sabotage('sab_enums', sab_enums, r"moved is '2026-8-21'")


def test_sabotage_check_enums_open_blank():
    """check_4 relaxation (a): blank BOTH pri and size on the OPEN row T4 -- the closed/
    exemption must not leak out. Regex: `pri '' is not one of`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T4-later-gamma.md: pri '' is not one of ['NOW', 'NEXT',
        'LATER', 'HOLD', 'SOMEDAY'] (it may be empty only under closed/).
    """
    line = sabotage('sab_openblank', sab_enums_open_blank, r"pri '' is not one of")
    assert 'only under closed/' in line, line


def test_sabotage_check_enums_closed_bad():
    """check_4 relaxation (b): close T7 legally, then hand-set `pri: URGENT` on the closed
    record -- "optional" must not degrade into "unchecked". Regex: `pri 'URGENT' is not
    one of`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/closed/T7-someday-eps.md: pri 'URGENT' is not one of
        ['NOW', 'NEXT', 'LATER', 'HOLD', 'SOMEDAY'].
    """
    line = sabotage('sab_closedbad', sab_enums_closed_bad, r"pri 'URGENT' is not one of")
    assert 'closed' in line, line


def test_sabotage_check_pri_budget_now():
    """check_5: hand-edit a second row to `pri: NOW`. Regex: `found 2 open NOW`.

    2026-08-21 observed::

        FAIL: found 2 open NOW row(s) (T1, T4), must be exactly 1. NOW is the one row an
        unassigned session picks up: with none it has no answer, with more than one it
        has no ranking. Set the count with `task.py promote <id> NOW --demote <id2>
        <pri2>`.
    """
    line = sabotage('sab_now', sab_pri_budget_now, r'found 2 open NOW')
    assert 'T1' in line and 'T4' in line, line


def test_sabotage_check_pri_budget_next():
    """check_5 (NEXT): fill NEXT legally to the cap, then hand-edit a fourth row to
    `pri: NEXT`. Regex: `found 4 open NEXT`.

    2026-08-21 observed::

        FAIL: found 4 open NEXT row(s) ['T2', 'T3', 'T4', 'T5'], cap is 3. Demote one to
        LATER -- the cap is the mechanism that forces the ranking argument to happen
        once, at write time.
    """
    sabotage('sab_next', sab_pri_budget_next, r'found 4 open NEXT')


def test_sabotage_check_deps():
    """check_6: dep id typo T2 -> T20. Regex: `dep 'T20' resolves to no task`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T3-next-beta.md: dep 'T20' resolves to no task (open or
        closed). If it is retired, drop it with `task.py dep rm T3 T20`; a dep that
        resolves to nothing blocks forever.
    """
    sabotage('sab_deps', sab_deps, r"dep 'T20' resolves to no task")


def test_sabotage_check_deps_cycle():
    """check_6 (cycle): hand-add `deps: [T3]` to T2, closing the T2<->T3 loop.
    Regex: `dependency cycle`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T2-next-alpha.md: dependency cycle T2 -> T3 -> T2. Nothing in
        the cycle can ever be ready.
    """
    line = sabotage('sab_cycle', sab_deps_cycle, r'dependency cycle')
    assert 'T2 -> T3 -> T2' in line, line


def test_sabotage_check_parents():
    """check_7: archive parent T6 while child T4 is open. Regex: `still has open children`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/closed/T6-the-group.md is CLOSED but still has open children
        ['T4']. Either reopen it or close the children -- a closed parent is what tells
        the next session the group is done.
    """
    line = sabotage('sab_parents', sab_parents, r'still has open children')
    assert 'T4' in line, line


def test_sabotage_check_closed_field():
    """check_8: `mv` T7 into closed/ without stamping `closed`. Regex: ``closed` field is
    empty``.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/closed/T7-someday-eps.md is under closed/ but its `closed`
        field is empty. Re-close it with `task.py close T7 -m ...` so the date is
        recorded.
    """
    sabotage('sab_closedfield', sab_closed_field, r'`closed` field is empty')


def test_sabotage_check_labels():
    """check_9: label case slip infra -> Infra. Regex: `label 'Infra' is not in the
    declared vocabulary`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T1-the-now-row.md: label 'Infra' is not in the declared
        vocabulary ['formal', 'perf', 'docs', 'infra']. Add it to tasks/config.json
        deliberately, or use an existing one.
    """
    sabotage('sab_labels', sab_labels,
             r"label 'Infra' is not in the declared vocabulary")


def test_sabotage_check_min_parsed_floor():
    """check_10, instrument control part 1: delete three task files (corpus 7 -> 4, floor
    7). Regex: `parsed only 4 task file`.

    2026-08-21 observed::

        FAIL: parsed only 4 task file(s), floor min_tasks_parsed=7. Either the tasks
        directory is nearly empty or the parser has gone blind -- and a lint that parses
        nothing passes forever. Fix the parser rather than lowering the floor.
    """
    line = sabotage('sab_floor', sab_min_parsed_floor, r'parsed only 4 task file')
    assert 'rather than lowering the floor' in line, line


def test_sabotage_check_enums_updated():
    """check_4 (`updated`): `updated: 2026-08-21` -> `2026-8-21`.
    Regex: `updated is '2026-8-21'`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T4-later-gamma.md: updated is '2026-8-21', not a session key
        (YYYY-MM-DD with an optional single lowercase letter). One of the stamps was
        typed by hand; fix the wrong one.
    """
    sabotage('sab_updated', sab_enums_updated, r"updated is '2026-8-21'")


def test_sabotage_check_enums_stamp_order():
    """check_4 (order): hand-set `moved` AHEAD of `updated` -- the one stamp state the
    write path cannot produce. Regex: `updated 2026-08-21 sorts before moved 2026-08-21c`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T2-next-alpha.md: updated 2026-08-21 sorts before moved
        2026-08-21c, which the write path cannot produce: every op that bumps `moved`
        bumps `updated` too (SPEC.md section 3.1). One of the stamps was typed by hand;
        fix the wrong one.
    """
    sabotage('sab_order', sab_enums_updated_before_moved,
             r'updated 2026-08-21 sorts before moved 2026-08-21c')


def test_sabotage_check_enums_source_blank():
    """check_4 (`source`): blank `source` -- an added-but-unfilled key, not a bogus value.
    Regex: `source is empty`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T5-held-delta.md: source is empty. Every task records where
        it came from: ['board', 'hand'], or a repo-relative path like
        docs/perf-round6-audit-2026-08.md. It is set once at `new` and never changes.
    """
    sabotage('sab_srcblank', sab_source_blank, r'source is empty')


def test_sabotage_check_enums_source_typo():
    """check_4 (`source` typo): `source: hand` -> `Board`, the near-miss of a fixed value.
    Regex: `source 'Board' is neither`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T6-the-group.md: source 'Board' is neither ['board', 'hand']
        nor a path. A bare word that is not one of the two fixed values is almost always
        a typo for one of them (board/Board/handoff), and a vocabulary that admits typos
        answers no query.
    """
    sabotage('sab_srctypo', sab_source_typo, r"source 'Board' is neither")


def test_sabotage_check_deps_related_dangling():
    """check_6 (`related`): related id typo T5 -> T50.
    Regex: `related id 'T50' resolves to no task`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T5-held-delta.md: related id 'T50' resolves to no task (open
        or closed). `related` is navigation: a link that goes nowhere costs the reader
        the lookup before it tells them anything.
    """
    sabotage('sab_reldangle', sab_related_dangling,
             r"related id 'T50' resolves to no task")


def test_sabotage_check_deps_related_self():
    """check_6 (`related` self): a task related to ITSELF.
    Regex: `related lists T5 itself`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/T5-held-delta.md: related lists T5 itself. Remove it with
        `task.py set T5 related "..."` -- a self-link renders as a pointer to the page
        you are already on.
    """
    sabotage('sab_relself', sab_related_self, r'related lists T5 itself')


def test_sabotage_check_min_parsed_disabled():
    """check_10, instrument control part 3 -- THE INSTRUMENT'S OWN INSTRUMENT: set the
    floor itself to 0, the one-value edit that switches the control off.
    Regex: `expected a positive integer`.

    2026-08-21 observed::

        FAIL: <t>/sab/tasks/config.json has min_tasks_parsed = 0; expected a positive
        integer. A value of 0 or less is not a LOWERED floor, it is a DISABLED one -- the
        exact "check that passes forever" this control exists to prevent -- and a
        non-integer (a quoted "99", null, true) is a floor whose comparison is an
        accident. Run `task.py counts` and paste the measured value; lowering it is a
        deliberate, reviewed edit, disabling it is not an edit anyone gets to make
        silently.
    """
    line = sabotage('sab_flooroff', sab_min_parsed_disabled,
                    r'expected a positive integer')
    assert 'config.json' in line, line


def _blind_parser_copy(name):
    """A patched task.py whose `md_paths` stops scanning `closed/`.

    The plausible refactor is "lint only cares about open tasks", which silently halves
    the corpus. A patched COPY is used so the real file is never edited.
    """
    return patched_tool(
        name,
        'for d, is_closed in ((self.dir, False), (self.closed_dir, True)):\n'
        '            if not os.path.isdir(d):',
        'for d, is_closed in ((self.dir, False),):\n'
        '            if not os.path.isdir(d):')


def test_sabotage_check_min_parsed_blind_parser():
    """check_10, instrument control part 2 -- A GENUINELY BLIND PARSER: `md_paths()` stops
    scanning `closed/`. Regex: `parsed only`, plus EXACTLY TWO violations, one of them
    the independent recount.

    The claim in task.py's own sabotage record is that under a blind parser the other
    eleven checks stay green on the half they can still see, and only check 10 notices --
    with BOTH of its assertions: the floor (the corpus shrank) and the recount (WHICH
    directory the scanner stopped seeing). That is a claim about this run, so it is
    asserted here rather than stated in prose.

    2026-08-21 observed::

        FAIL: parsed only 4 task file(s), floor min_tasks_parsed=7. Either the tasks
        directory is nearly empty or the parser has gone blind -- and a lint that parses
        nothing passes forever. Fix the parser rather than lowering the floor.
        violations under the blind parser: 2 (the claim is exactly 2, both from check 10
        -- floor + recount)
    """
    root = good_tree('sab_blind')
    # Move three tasks into closed/ so the blind scanner has something to go blind ABOUT.
    for tid, slug in (('T2', 'next-alpha'), ('T3', 'next-beta'), ('T5', 'held-delta')):
        src = os.path.join(root, 'tasks', '%s-%s.md' % (tid, slug))
        dst = os.path.join(root, 'tasks', 'closed', '%s-%s.md' % (tid, slug))
        t = read(src).decode('utf-8').replace('closed:\n', 'closed: %s\n' % KEY)
        if tid == 'T3':
            t = t.replace('deps: [T2]', 'deps: []')
        write(dst, t)
        os.remove(src)
    rc0, base = lint_text(root)
    assert rc0 == 0, 'BASELINE NOT GREEN -- not attributable:\n%s' % base

    blind = _blind_parser_copy('blind_task.py')
    rc1, text = lint_text(root, blind)
    assert rc1 != 0, 'GREEN UNDER SABOTAGE -- a blind parser went unnoticed:\n%s' % text
    assert first_match(text, r'parsed only') is not None, text

    fails = [l for l in text.split('\n') if l.strip().startswith('FAIL:')]
    assert len(fails) == 2, (
        'the claim is EXACTLY 2 violations, both from check 10 (floor + recount): the '
        'other eleven checks stay green on the half they can still see. Got %d:\n%s'
        % (len(fails), text))
    assert [l for l in fails if 'scan offered' in l], (
        'the recount did not fire; only the floor did, so nothing named WHICH directory '
        'the scanner stopped seeing:\n%s' % text)

    # Restore control: the SAME tree is green again under the real tool.
    rc2, back = lint_text(root)
    assert rc2 == 0, 'RESTORE NOT GREEN:\n%s' % back


# --- the write-path pass: checks whose subject is not an exit code ----------------------
# Some of what this tool guarantees cannot be sabotaged through `lint`'s exit code, and
# that is precisely why those are the ones most likely to ship broken:
#
#   * the parent-depth check WARNS -- its output IS the artifact, and a weakening makes
#     the warning go SILENT while everything stays green;
#   * `ack` and `--mechanical` are write-path rules -- no lint clause can see that a
#     `moved` was bumped by something that should not have bumped it, because the result
#     is a perfectly valid file;
#   * a validator that returns None for everything leaves a corpus that lints clean.
#
# So the subject here is the TEST, not the tree: each case patches a copy of task.py with
# the narrowest plausible weakening, re-runs the test case that claims to guard it against
# that copy, and asserts the test FAILS. A test that still passes against a deliberately
# broken tool is a test that was never checking anything.

def writepath_sabotage(patch_name, old, new, case_fn):
    """Baseline green -> patch a copy -> the guarding TEST must fail -> restore -> green."""
    case_fn()                                     # baseline, against the real tool
    tool = patched_tool(patch_name, old, new)
    message = against(tool, case_fn)
    assert message is not None, (
        'PASSED UNDER SABOTAGE -- %s does not guard this rule. The patch (%r -> %r) '
        'applied, the tool was broken, and the test that claims to catch it was green.'
        % (case_fn.__name__, old[:60], new[:60]))
    assert TASK_PY == REAL_TASK_PY, 'against() leaked the sabotaged tool pointer'
    case_fn()                                     # restore control
    return message


def test_sabotage_wp_parent_depth_warning_can_go_silent():
    """`MAX_PARENT_DEPTH = 2` -> `99` -- "the warning is noisy, raise the threshold",
    which silences it while lint stays green either way.

    This is the shape a warning-only check dies in: nothing reddens, so nothing objects.
    The guarding test is test_parent_depth_warns_and_stays_green, and it must FAIL.

    2026-08-21 observed (the assertion message is the lint output the test was handed --
    a clean line where a WARN was expected)::

        task lint: clean (11 checks, 8 task file(s) parsed)

    RE-MEASURED 2026-08-29: the same run now reads `clean (12 checks, ...)`, check_banner
    having joined the list. The observation is the CLEAN line either way, which is the
    point -- a silenced warning is indistinguishable from a healthy tree.
    """
    message = writepath_sabotage('sab_parent_depth.py',
                                 'MAX_PARENT_DEPTH = 2', 'MAX_PARENT_DEPTH = 99',
                                 test_parent_depth_warns_and_stays_green)
    assert 'clean' in message, message


def test_sabotage_wp_ack_does_not_move_moved():
    """`op_ack` calls the PROGRESS path (`stamp_and_render(task, key, True)`) -- the
    refactor that notices two call sites differ by one constant.

    If an acknowledgement could bump `moved`, a neglected row would look fresh forever and
    the staleness warning could never fire again.

    2026-08-21 observed::

        AssertionError: ack moved `moved` 2026-08-21b -> 2026-08-21c: an acknowledgement
        just laundered a stale row into a fresh one
    """
    message = writepath_sabotage(
        'sab_ack_progress.py',
        'write_text(task.path, stamp_and_render(task, key, False))',
        'write_text(task.path, stamp_and_render(task, key, True))',
        test_the_moved_updated_split_survives_automation)
    assert 'laundered a stale row' in message, message


def test_sabotage_wp_mechanical_is_honoured():
    """`progress()` hard-wired to True -- the flag is still accepted, parsed and
    documented, and does nothing.

    The failure mode where the flag EXISTS and does nothing is worse than not having it:
    an automation passes it, believes it is behaving, and launders `moved` on every field
    fix it applies.

    2026-08-21 observed::

        AssertionError: set --mechanical moved `moved` 2026-08-21b -> 2026-08-21d
    """
    message = writepath_sabotage(
        'sab_mechanical.py',
        "return not getattr(args, 'mechanical', False)", 'return True',
        test_the_moved_updated_split_survives_automation)
    assert '--mechanical moved' in message, message


def test_sabotage_wp_source_validation_is_not_lenient():
    """`source_problem()` returns None for everything -- a lenient validator, the way
    every lenient validator arrives.

    `sync` keys its whole CORPUS-ONLY behaviour off `source`, so a value that reads
    correctly to a human and matches nothing mechanically makes the task invisible to the
    tool forever.

    2026-08-21 observed::

        ("--source 'Board' was accepted", 'T11  <t>/testtmp/prov/tasks/
        T11-bad-source-board.md\\r\\n')
    """
    message = writepath_sabotage(
        'sab_source_lenient.py',
        'def source_problem(value):\n    """Return a complaint',
        'def source_problem(value):\n    return None\n    """Return a complaint',
        test_source_is_written_once_and_never_again)
    assert 'was accepted' in message, message


# --- the LIVE-CORPUS pass ---------------------------------------------------------------
# Everything above runs against a SEVEN-file fixture. The record used to stop there, and
# two of its claims turned out to be true of the fixture and FALSE of the tree the tool
# actually guards: "only the floor notices a blind parser" (with the floor at SPEC.md's
# example value against the live tree, NOTHING noticed) and the check_enums relaxation
# pair, whose evidence cited a baseline of 83 files and a copy at `audit/sb-pri` that does
# not exist. A sabotage record is evidence ABOUT A CORPUS; run it against the corpus.
#
# The original tree is NEVER touched: every case runs on a fresh copytree under tmp.
# A missing live corpus FAILS -- see live_copy(). It is not a skip.

def live_rm_closed(root):
    """The BLOCKER-1 reproduction: delete the whole closed/ archive."""
    shutil.rmtree(os.path.join(root, 'tasks', 'closed'))


def live_open_blank(root):
    """Blank pri AND size on a live OPEN row."""
    p = pick(root, False, 'P10')
    t = read(p).decode('utf-8')
    t = re.sub(r'(?m)^pri: .*$', 'pri:', t, count=1)
    write(p, re.sub(r'(?m)^size: .*$', 'size:', t, count=1))
    return os.path.basename(p)


def live_closed_bogus(root):
    """`pri: URGENT` on a live CLOSED record."""
    p = pick(root, True, 'B1')
    t = read(p).decode('utf-8')
    write(p, re.sub(r'(?m)^pri:.*$', 'pri: URGENT', t, count=1))
    return os.path.basename(p)


def live_sabotage(name, breaker, pattern):
    """The same protocol, on a throwaway copy of the tracked `tasks/` corpus."""
    root = live_copy(name)
    try:
        rc0, base = lint_text(root)
        assert rc0 == 0, ('BASELINE NOT GREEN on the live corpus -- the sabotage is not '
                          'attributable, and the corpus itself is red:\n%s' % base)
        breaker(root)
        rc1, text = lint_text(root)
        assert rc1 != 0, ('GREEN UNDER SABOTAGE on the LIVE corpus -- the check does not '
                          'guard the tree it is supposed to guard:\n%s' % text)
        line = first_match(text, pattern)
        assert line is not None, (
            'red, but not attributable: no line matched %r:\n%s' % (pattern, text))
        return line
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_sabotage_live_min_parsed_floor():
    """`rm -rf tasks/closed` on the LIVE corpus -- the MAJORITY of the files, deleted.
    Regex: `parsed only \\d+ task file`.

    This is the run that shipped GREEN once: with `min_tasks_parsed` at SPEC.md's example
    value of 5, deleting 57 of 99 files printed `clean (10 checks, 42 task file(s)
    parsed)`, exit 0. The floor is zero-headroom now, so it cannot.

    2026-08-21 observed (baseline `clean (11 checks, 150 task file(s) parsed)`)::

        FAIL: parsed only 91 task file(s), floor min_tasks_parsed=150. Either the tasks
        directory is nearly empty or the parser has gone blind -- and a lint that parses
        nothing passes forever. Fix the parser rather than lowering the floor.

    No figures are pinned in the assertion: the counts are properties of the corpus on
    the day it runs, and a hardcoded 150 is the rot this tool exists to delete.
    """
    line = live_sabotage('live_floor', live_rm_closed, r'parsed only \d+ task file')
    assert 'floor min_tasks_parsed=' in line, line


def test_sabotage_live_enums_open_blank():
    """Blank pri AND size on a live OPEN row -- the closed/ exemption must not leak out.
    Regex: `pri '' is not one of`.

    2026-08-21 observed, subject `P10-re-run-the-scope-audit-hand-curated.md`::

        FAIL: <t>/live/tasks/P10-...md: pri '' is not one of ['NOW', 'NEXT', 'LATER',
        'HOLD', 'SOMEDAY'] (it may be empty only under closed/).
        FAIL: <t>/live/tasks/P10-...md: size '' is not one of ['S', 'M', 'L', '?']
        (use "?" when unsized, or empty under closed/).
    """
    line = live_sabotage('live_openblank', live_open_blank, r"pri '' is not one of")
    assert 'only under closed/' in line, line


def test_sabotage_live_enums_closed_bogus():
    """`pri: URGENT` on a live CLOSED record -- optional must not mean unchecked.
    Regex: `pri 'URGENT' is not one of`.

    2026-08-21 observed, subject
    `B1-w3cjobvalid-enumjob2d-star-freeness-hole-closed.md`::

        FAIL: <t>/live/tasks/closed/B1-...md: pri 'URGENT' is not one of ['NOW', 'NEXT',
        'LATER', 'HOLD', 'SOMEDAY'].
    """
    line = live_sabotage('live_closedbogus', live_closed_bogus,
                         r"pri 'URGENT' is not one of")
    assert 'closed' in line, line


def test_sabotage_live_blind_parser():
    """`md_paths()` stops scanning `closed/`, against the LIVE corpus. TWO reds required.

    This is the case that justified the whole live pass. With the floor at its example
    value the fixture said "only check 10 notices"; against the real tree NOTHING noticed.
    With the floor measured AND the independent recount in place, the blind parser must
    produce exactly two violations: the floor (the corpus shrank) and the recount (WHICH
    directory the scanner stopped seeing).

    2026-08-21 observed::

        FAIL: parsed only 91 task file(s), floor min_tasks_parsed=150. Either the tasks
        directory is nearly empty or the parser has gone blind -- and a lint that parses
        nothing passes forever. Fix the parser rather than lowering the floor.
        FAIL: the scan offered 0 closed task file(s) but <t>/live/tasks/closed holds 59
        *.md on disk. The scanner is not seeing the corpus (this is the control, not a
        data problem): fix `Store.md_paths` rather than the count.
    """
    root = live_copy('live_blind')
    try:
        rc0, base = lint_text(root)
        assert rc0 == 0, 'BASELINE NOT GREEN on the live corpus:\n%s' % base
        blind = _blind_parser_copy('blind_live.py')
        rc1, text = lint_text(root, blind)
        assert rc1 != 0, 'GREEN UNDER SABOTAGE on the LIVE corpus:\n%s' % text
        fails = [l.strip() for l in text.split('\n') if l.strip().startswith('FAIL:')]
        assert len(fails) == 2, (
            'expected exactly 2 violations (floor + recount), got %d:\n%s'
            % (len(fails), text))
        assert [l for l in fails if 'parsed only' in l], fails
        assert [l for l in fails if 'scan offered' in l], (
            'the independent recount did not fire against the live corpus, which is the '
            'exact hole the live pass was added to close:\n%s' % text)
        # Restore control.
        rc2, back = lint_text(root)
        assert rc2 == 0, 'RESTORE NOT GREEN:\n%s' % back
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_sabotage_record_is_complete():
    """The module docstring claims 22/22 + 4/4 + 4/4. This counts them.

    A transcribed record is a number in prose, and prose is what rotted in the first
    place: `.scratch/tasktool/sabotage-log.txt` said `22/22` and nothing tied that to the
    cases that produced it, so deleting one was free and invisible. Deleting one now is
    red here -- which is the whole difference between a record and a pin.
    """
    import sys as _sys
    names = [n for n in dir(_sys.modules[__name__]) if n.startswith('test_')]
    fixture = [n for n in names if n.startswith('test_sabotage_check_')]
    writepath = [n for n in names if n.startswith('test_sabotage_wp_')]
    live = [n for n in names if n.startswith('test_sabotage_live_')]
    assert len(fixture) == 22, sorted(fixture)
    assert len(writepath) == 4, sorted(writepath)
    assert len(live) == 4, sorted(live)
    # And the harness the whole file rests on is the real tool, not a leftover copy.
    assert TASK_PY == REAL_TASK_PY, TASK_PY
    assert os.path.isfile(REAL_TASK_PY), REAL_TASK_PY
