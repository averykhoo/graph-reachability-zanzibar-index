"""Smoke test for an INSTALLED ``zanzibar-index``: the release install trial runs it.

Usage, from OUTSIDE the checkout, with the trial env's interpreter:

    <env>/python.exe installed_smoke.py --version 0.0.3

It imports only ``zanzibar`` and ``sqlmodel``, so it exercises whatever pip
installed, never this checkout (it refuses to run against a ``src/`` tree unless
``--allow-checkout`` is passed, which is for developing the script itself). It
takes seconds: no fuzzing, no hypothesis, no pytest. It is a smoke test of
the published wheel, not a substitute for the gate.

What it covers:

1. the PyPI README quickstart, verbatim in substance;
2. a seeded batch of writes and removes on a schema using nested groups, a TTU
   chain, ``and``, ``but not``, a ``[user:*]`` wildcard and the per-type
   ``viewer from parent`` idiom (TK126), then again on TK126's "second form"
   (a TTU arm inside ``but not``, which crashed 0.0.2), with the graph index
   (``Store``), two standalone set engines (both ``SetOps``) and an
   async store all agreeing on every cell of a full check grid; then
   hand-written expectations, lookups and the watermark;
3. reopening a store from disk (schema read back, same answers);
4. the async schedule: token reads before and after ``catch_up``;
5. several instances on ONE store in one SQLite file (TK181): two ``Store``
   instances (one writes, the other catches up; ``lag()`` agrees without
   ``refresh()``, TK172), then a second OS process (``sys.executable``) that
   writes, with and without catching up, while the parent's ``lag()`` / ``check``
   follow; and TK175's self-parent ``doc:d1 parent doc:d1``, sync and async;
6. bad input: the 0.0.2 trial bugs (TK124 empty schema, TK125 ``None``
   predicate), bad identifiers, undeclared relations, a schema
   mismatch on reopen, ``sync=None`` / ``ops="pysets"`` (TK176), and the
   ``ZANZIBAR_MAX_CLOSURE_FANOUT`` cap.

Exit status 0 means every check passed. Any failure prints ``FAIL`` lines and
exits 1.
"""

import argparse
import os
import random
import shutil
import sys
import tempfile
import time
import warnings
from pathlib import Path

FAILURES: list[str] = []
PASSES = 0


def ok(cond: bool, what: str) -> None:
    global PASSES
    if cond:
        PASSES += 1
    else:
        FAILURES.append(what)
        print(f'FAIL  {what}')


def raises(exc_names: tuple[str, ...], fn, what: str):
    """``fn()`` must raise an exception whose class name (or a base's) is in
    ``exc_names``. Matched by name so the script needs no private imports."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001 -- classify below
        names = {c.__name__ for c in type(e).__mro__}
        ok(bool(names & set(exc_names)),
           f'{what}: expected {exc_names}, got {type(e).__name__}: {str(e)[:200]}')
        return e
    ok(False, f'{what}: expected {exc_names}, nothing was raised')
    return None


def section(title: str) -> None:
    print(f'-- {title}')


# ---------------------------------------------------------------------------
# Schema for the differential section. Every type has its own `viewer` (the
# OpenFGA idiom the 0.0.2 graph index refused, TK126), and doc.viewer reaches
# folder.viewer through `viewer from parent`.
# ---------------------------------------------------------------------------
SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, user:*, group#member]
type folder
  relations
    define parent: [folder]
    define owner: [user, group#member]
    define viewer: [user, group#member] or owner or viewer from parent
type doc
  relations
    define parent: [folder]
    define banned: [user, group#member]
    define editor: [user, group#member]
    define approved: [user]
    define reader: [user, group#member] or editor or viewer from parent
    define viewer: reader but not banned
    define publisher: editor and approved
"""

# The 0.0.2 trial's "second form" (TK126 variant D): a TTU arm INSIDE a `but not`.
# 0.0.2 crashed both backends on it with an internal ValueError; 0.0.3 serves it.
SCHEMA_D = SCHEMA.replace('define viewer: reader but not banned',
                          'define viewer: ([user] or viewer from parent) but not banned')
assert SCHEMA_D != SCHEMA

USERS = [f'u{i}' for i in range(6)]
GROUPS = ['g0', 'g1', 'g2']
FOLDERS = ['f0', 'f1', 'f2']
DOCS = ['d0', 'd1', 'd2', 'd3']
OBJECTS = ([('group', g) for g in GROUPS] + [('folder', f) for f in FOLDERS]
           + [('doc', d) for d in DOCS])
RELATIONS = {
    'group': ['member'],
    'folder': ['owner', 'viewer'],
    'doc': ['banned', 'editor', 'approved', 'reader', 'viewer', 'publisher'],
}


def candidate_tuples() -> list[tuple]:
    """Every well-typed tuple over the small universe, excluding the ones that
    could close a cycle (group#member -> itself; parent chains go f0 -> f1 -> f2
    only), so a random subset is always admissible."""
    out = []
    for u in USERS:
        for g in GROUPS:
            out.append(('...', 'user', u, 'member', 'group', g))
        for f in FOLDERS:
            out.append(('...', 'user', u, 'owner', 'folder', f))
            out.append(('...', 'user', u, 'viewer', 'folder', f))
        for d in DOCS:
            for r in ('banned', 'editor', 'approved', 'reader'):
                out.append(('...', 'user', u, r, 'doc', d))
    for g in GROUPS:
        out.append(('...', 'user', '*', 'member', 'group', g))
    # nested groups only "upwards" (g0 in g1, g0/g1 in g2): acyclic by construction
    for a, b in (('g0', 'g1'), ('g0', 'g2'), ('g1', 'g2')):
        out.append(('member', 'group', a, 'member', 'group', b))
    for g in GROUPS:
        for f in FOLDERS:
            out.append(('member', 'group', g, 'owner', 'folder', f))
            out.append(('member', 'group', g, 'viewer', 'folder', f))
        for d in DOCS:
            for r in ('banned', 'editor', 'reader'):
                out.append(('member', 'group', g, r, 'doc', d))
    for a, b in (('f0', 'f1'), ('f1', 'f2')):
        out.append(('...', 'folder', a, 'parent', 'folder', b))
    for d in DOCS:
        for f in FOLDERS:
            out.append(('...', 'folder', f, 'parent', 'doc', d))
    return out


def grid(store_check) -> dict[tuple, bool]:
    res = {}
    for u in USERS:
        for (ot, on) in OBJECTS:
            for rel in RELATIONS[ot]:
                res[(u, rel, ot, on)] = bool(store_check('...', 'user', u, rel, ot, on))
    return res


def diff(a: dict, b: dict, limit: int = 5) -> list[str]:
    return [f'{k}: {a[k]} vs {b[k]}' for k in a if a[k] != b[k]][:limit]


def differential(label, schema, args, engine_at, Store, SetEngine,
                 RoaringSets, PySets, Session) -> None:
    """Seeded random writes/removes applied to a sync graph-index store (paranoia
    on), an async store, and two standalone set engines (both ``SetOps``); at three
    checkpoints every cell of the check grid must agree across all of them."""
    section(f'differential grid: {label} (seed {args.seed}, {args.ops} ops)')
    rng = random.Random(args.seed)
    cands = candidate_tuples()
    # one SQLite file per writer: SQLite serializes writers per file, and these
    # sessions each hold an open write transaction between commits
    with warnings.catch_warnings():
        # [user:*] is plain OpenFGA and must NOT warn; turn any warning into an error.
        warnings.simplefilter('error')
        s_sync = Session(engine_at(f'{label}-sync.db'))
        s_async = Session(engine_at(f'{label}-async.db'))
        s_set = Session(engine_at(f'{label}-set.db'))
        sync_st = Store(s_sync, 'diff-sync', schema=schema, paranoia='residue')
        async_st = Store(s_async, 'diff-async', schema=schema, sync=False)
        sets = {
            'roaring': SetEngine(s_set, 'diff-set-r', schema, ops=RoaringSets),
            'py': SetEngine(s_set, 'diff-set-p', schema, ops=PySets),
        }
    live: set[tuple] = set()
    last_tok = 0
    checkpoints = {args.ops // 3, 2 * args.ops // 3, args.ops}
    for i in range(1, args.ops + 1):
        if live and rng.random() < 0.3:
            t = rng.choice(sorted(live))
            live.discard(t)
            sync_st.remove_tuple(*t)
            last_tok = async_st.remove_tuple(*t)
            for se in sets.values():
                se.remove_tuple(*t)
        else:
            t = rng.choice([c for c in cands if c not in live])
            live.add(t)
            sync_st.add_tuple(*t)
            last_tok = async_st.add_tuple(*t)
            for se in sets.values():
                se.add_tuple(*t)
        if i not in checkpoints:
            continue
        s_set.commit()
        g_graph = grid(sync_st.check)
        failed_before = len(FAILURES)
        for name, se in sets.items():
            d = diff(g_graph, grid(se.check))
            ok(not d, f'{label} op {i}: graph index vs set engine ({name}) disagree: {d}')
        # async: a tokened read before catch_up is served by the set engine
        d = diff(g_graph, grid(lambda *a, t=last_tok: async_st.check(*a, at_least=t)))
        ok(not d, f'{label} op {i}: async tokened reads (pre-catch_up) disagree: {d}')
        async_st.catch_up()
        ok(async_st.lag() == 0, f'{label} op {i}: async lag after catch_up is {async_st.lag()}')
        d = diff(g_graph, grid(async_st.check))
        ok(not d, f'{label} op {i}: async index after catch_up disagrees: {d}')
        n_true = sum(g_graph.values())
        ok(0 < n_true < len(g_graph), f'{label} op {i}: degenerate grid ({n_true} True)')
        verdict = 'all backends agree' if len(FAILURES) == failed_before else 'MISMATCH'
        print(f'   op {i:4d}: {len(live)} live tuples, {n_true}/{len(g_graph)} '
              f'cells True, {verdict}')
    for sess in (s_sync, s_async, s_set):
        sess.close()


# ---------------------------------------------------------------------------
# Multi-instance (TK181): several Store instances, and a second OS process, on ONE
# store in ONE SQLite file -- the deployment the docs describe (writers, a catch-up
# worker, a monitoring instance), which a single-instance smoke never exercises.
# ---------------------------------------------------------------------------
MULTI_SCHEMA = 'type user\ntype doc\n  relations\n    define viewer: [user]\n'

# Run by a SECOND interpreter (sys.executable). argv: db path, mode ('write' or
# 'write+catch_up'), user. Prints the zanzibar it imported, the token and the lag.
CHILD = r'''
import sys
import zanzibar
from sqlmodel import Session, create_engine
from zanzibar.store import Store
db, mode, user = sys.argv[1:4]
eng = create_engine(f"sqlite:///{db}")
with Session(eng) as s:
    st = Store(s, "multi", sync=False)
    tok = st.add_tuple(f"user:{user}", "viewer", "doc:2")
    if mode == "write+catch_up":
        st.catch_up()
    print(zanzibar.__file__)
    print(tok, st.lag(), st.check(f"user:{user}", "viewer", "doc:2", at_least=tok))
eng.dispose()
'''


def multi_instance(engine_at, Store, Session) -> None:
    import subprocess
    section('multi-instance: two Store instances, then a second process, one SQLite file')
    eng = engine_at('multi.db')
    db = eng.url.database
    with Session(eng) as sa, Session(eng) as sb:
        a = Store(sa, 'multi', schema=MULTI_SCHEMA, sync=False)
        tok = a.add_tuple('user:a', 'viewer', 'doc:1')
        ok(a.lag() == 1, f'A wrote one row async: lag is {a.lag()}, expected 1')
        b = Store(sb, 'multi', sync=False)
        ok(b.catch_up() == 1, 'B (a second instance) catches up the row A wrote')
        # TK172: A sees B's catch_up without refresh(); 0.1.0 reported lag 1 forever
        ok(a.lag() == 0, f'TK172: A.lag() after B.catch_up() is {a.lag()}, expected 0 '
                         f'without refresh()')
        ok(a.check('user:a', 'viewer', 'doc:1') is True, 'A.check sees the write B applied')
        ok(a.check('user:a', 'viewer', 'doc:1', at_least=tok) is True,
           'A.check(at_least=token) sees the write')
        # the other way round: B writes, A catches up, B's view agrees
        tok_b = b.add_tuple('user:b', 'viewer', 'doc:1')
        ok(a.catch_up() == 1, 'A catches up the row B wrote')
        ok(b.lag() == 0, f'B.lag() after A.catch_up() is {b.lag()}, expected 0')
        ok(b.check('user:b', 'viewer', 'doc:1', at_least=tok_b) is True,
           'B.check sees its own write after A applied it')

        # a second OS process: one write it catches up itself, one it leaves for us
        def child(mode: str, user: str):
            r = subprocess.run([sys.executable, '-c', CHILD, db, mode, user],
                               capture_output=True, text=True, timeout=120)
            ok(r.returncode == 0, f'child process ({mode}) exited {r.returncode}: '
                                  f'{r.stderr.strip()[-600:]}')
            return r.stdout.split('\n')
        out = child('write+catch_up', 'c')
        ok(len(out) >= 2 and Path(out[0]).resolve() == Path(sys.modules['zanzibar'].__file__)
           .resolve(), f'child imported the same zanzibar: {out[:1]}')
        ok(len(out) >= 2 and out[1].split()[1:] == ['0', 'True'],
           f'child: lag 0 and its own write visible after its catch_up, got {out[1:2]}')
        ok(a.lag() == 0, f'parent A.lag() after the child caught up is {a.lag()}, expected 0')
        ok(a.check('user:c', 'viewer', 'doc:2') is True,
           'parent A.check sees the write the child process applied')
        out = child('write', 'd')
        ok(len(out) >= 2 and out[1].split()[1:] == ['1', 'True'],
           f'child: lag 1 and a tokened read served before catch_up, got {out[1:2]}')
        ok(a.lag() == 1, f'parent A.lag() sees the child\'s unapplied row: {a.lag()}')
        ok(b.lag() == 1, f'parent B.lag() sees the child\'s unapplied row: {b.lag()}')
        ok(a.catch_up() == 1, 'parent A catches up the row the child wrote')
        ok(a.lag() == 0 and b.lag() == 0, f'both lags 0 after that: {a.lag()}, {b.lag()}')
        ok(b.check('user:d', 'viewer', 'doc:2') is True and
           a.check('user:d', 'viewer', 'doc:2') is True,
           'A and B both see the child\'s write once A applied it')
        ok(a.check('user:z', 'viewer', 'doc:2') is False, 'a stranger still reads False')


# TK175 (docs/tk175-self-parent-node-recreate-2026-10-30.md): a self-parent under a
# boolean + TTU-of-derived schema made 0.1.0 raise a raw IntegrityError (sync) or stall
# the index (async). The valid tuple must be writable and removable.
TK175_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define r0: [user]
type doc
  relations
    define parent: [doc, folder]
    define r0: [user] and [user]
    define r1: r0 but not (r0 from parent)
    define r2: r1 from parent
"""


def self_parent(engine_at, Store, Session) -> None:
    section('TK175: self-parent doc:d1 parent doc:d1, sync and async')
    for sync in (True, False):
        mode = 'sync' if sync else 'async'
        eng = engine_at(f'tk175-{mode}.db')
        with Session(eng) as s:
            st = Store(s, 'tk175', schema=TK175_SCHEMA, sync=sync)

            def settle(st=st, sync=sync):
                if not sync:
                    st.catch_up()
            st.add_tuple('user:u2', 'r0', 'doc:d1')
            settle()   # one batch holding both tuples would never hit the bug
            ok(st.check('user:u2', 'r1', 'doc:d1') is True, f'{mode}: r1 before the self-parent')
            try:
                st.add_tuple('doc:d1', 'parent', 'doc:d1')
                settle()
                err = None
            except Exception as e:  # noqa: BLE001 -- reported as a FAIL below
                err = f'{type(e).__name__}: {str(e)[:200]}'
            ok(err is None and not st.index_stalled,
               f'{mode}: self-parent write applied ({err or st.stall_error})')
            if err is not None:
                continue
            ok(st.check('user:u2', 'r1', 'doc:d1') is False, f'{mode}: r1 False under self-parent')
            ok(st.check('user:u2', 'r2', 'doc:d1') is False, f'{mode}: r2 False under self-parent')
            st.remove_tuple('doc:d1', 'parent', 'doc:d1')
            settle()
            ok(not st.index_stalled and st.check('user:u2', 'r1', 'doc:d1') is True,
               f'{mode}: removing the self-parent restores r1')
            ok(st.check('doc:d1', 'parent', 'doc:d1') is False, f'{mode}: self-parent gone')


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--version', help='assert zanzibar.__version__ equals this')
    ap.add_argument('--allow-checkout', action='store_true',
                    help='permit importing zanzibar from a source checkout')
    ap.add_argument('--seed', type=int, default=20261008)
    ap.add_argument('--ops', type=int, default=120,
                    help='random writes in the differential section')
    args = ap.parse_args()
    t0 = time.monotonic()

    import sqlmodel
    from sqlmodel import SQLModel, Session, create_engine
    import zanzibar
    from zanzibar.store import Store
    from zanzibar.setengine import SetEngine, PySets, RoaringSets

    section('import')
    where = Path(zanzibar.__file__).resolve()
    print(f'   zanzibar {zanzibar.__version__} from {where}')
    print(f'   sqlmodel {sqlmodel.__version__}, python {sys.version.split()[0]}')
    in_site = any(p in ('site-packages', 'dist-packages') for p in where.parts)
    if not in_site and not args.allow_checkout:
        print('FAIL  zanzibar was not imported from site-packages; run from outside '
              'the checkout, or pass --allow-checkout')
        return 1
    if args.version:
        ok(zanzibar.__version__ == args.version,
           f'__version__ is {zanzibar.__version__!r}, expected {args.version!r}')

    tmp = Path(tempfile.mkdtemp(prefix='zanzibar-smoke-'))
    engines = []

    def engine_at(name: str):
        eng = create_engine(f'sqlite:///{tmp / name}')
        SQLModel.metadata.create_all(eng)
        engines.append(eng)
        return eng

    # -- 1. README quickstart ------------------------------------------------
    section('README quickstart')
    QUICK = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define banned: [user]
    define viewer: [user, group#member] but not banned
"""
    eng = engine_at('perms.db')
    with Session(eng) as s:
        st = Store(s, 'my-app', schema=QUICK)
        tok = st.add_tuple('...', 'user', 'alice', 'member', 'group', 'eng')
        ok(isinstance(tok, int), f'add_tuple returns an int log id, got {tok!r}')
        st.add_tuple('member', 'group', 'eng', 'viewer', 'doc', 'd1')
        ok(st.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True,
           'quickstart: alice views d1 via group')
        st.add_tuple('...', 'user', 'alice', 'banned', 'doc', 'd1')
        ok(st.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False,
           'quickstart: banned alice no longer views d1')
    with Session(eng) as s:
        st = Store(s, 'my-app')          # reopen: schema read back
        ok(st.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False,
           'quickstart reopen: ban persisted')
        ok(st.check('...', 'user', 'alice', 'member', 'group', 'eng') is True,
           'quickstart reopen: membership persisted')

    # -- 2. differential: graph index vs set engine vs async -----------------
    for label, schema in (('main', SCHEMA), ('tk126-second-form', SCHEMA_D)):
        differential(label, schema, args, engine_at, Store, SetEngine,
                     RoaringSets, PySets, Session)

    # hand-written expectations, independent of both backends
    section('hand-written expectations')
    eng = engine_at('hand.db')
    with Session(eng) as s:
        st = Store(s, 'hand', schema=SCHEMA)
        st.add_tuple('...', 'folder', 'f0', 'parent', 'folder', 'f1')
        st.add_tuple('...', 'folder', 'f1', 'parent', 'doc', 'd0')
        st.add_tuple('...', 'user', 'u0', 'member', 'group', 'g0')
        st.add_tuple('member', 'group', 'g0', 'member', 'group', 'g1')
        st.add_tuple('member', 'group', 'g1', 'owner', 'folder', 'f0')
        c = lambda u, r, t, o: st.check('...', 'user', u, r, t, o)  # noqa: E731
        ok(c('u0', 'viewer', 'folder', 'f0'), 'nested group owner -> folder viewer')
        ok(c('u0', 'viewer', 'folder', 'f1'), 'viewer from parent (folder -> folder)')
        ok(c('u0', 'viewer', 'doc', 'd0'), 'viewer from parent (folder -> doc), TK126 idiom')
        ok(not c('u1', 'viewer', 'doc', 'd0'), 'stranger does not view d0')
        st.add_tuple('member', 'group', 'g1', 'banned', 'doc', 'd0')
        ok(not c('u0', 'viewer', 'doc', 'd0'), 'but not: banned via nested group')
        ok(c('u0', 'reader', 'doc', 'd0'), 'reader is unaffected by the ban')
        st.remove_tuple('member', 'group', 'g1', 'banned', 'doc', 'd0')
        ok(c('u0', 'viewer', 'doc', 'd0'), 'un-ban restores access')
        st.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')
        ok(not c('u2', 'publisher', 'doc', 'd1'), 'and: editor alone is not publisher')
        st.add_tuple('...', 'user', 'u2', 'approved', 'doc', 'd1')
        ok(c('u2', 'publisher', 'doc', 'd1'), 'and: editor + approved is publisher')
        st.add_tuple('...', 'user', '*', 'member', 'group', 'g2')
        ok(c('u5', 'member', 'group', 'g2'), 'wildcard [user:*] covers any user')
        st.remove_tuple('member', 'group', 'g0', 'member', 'group', 'g1')
        ok(not c('u0', 'viewer', 'doc', 'd0'), 'removing the nested-group link revokes')
        st.add_tuple('member', 'group', 'g0', 'member', 'group', 'g1')
        lk = st.lookup('...', 'user', 'u0')
        ok(len(lk.node_ids) > 0, f'lookup for u0 returns results, got {lk!r}')
        lr = st.lookup_reverse('viewer', 'doc', 'd0')
        ok(len(lr.node_ids) > 0, f'lookup_reverse for doc:d0#viewer returns results, got {lr!r}')
        ok(st.watermark() > 0, 'watermark advances')

    # -- 3. several instances / processes on one store; TK175 -------------------
    multi_instance(engine_at, Store, Session)
    self_parent(engine_at, Store, Session)

    # -- 4. bad input --------------------------------------------------------
    section('bad input')
    # The exceptions' one public home is the top level (TK164).
    from zanzibar import AdmissionRejected, SchemaMismatch  # noqa: F401 -- public names exist
    eng = engine_at('bad.db')
    with Session(eng) as s:
        # TK124: an empty schema is refused and does NOT brick the store id
        raises(('ValueError',), lambda: Store(s, 'x', schema=''),
               'TK124: empty schema refused')
        s.rollback()
        # TK176: sync picked the mode by truthiness (None -> async), ops='pysets' failed late
        raises(('TypeError',), lambda: Store(s, 'x176', schema=QUICK, sync=None),
               'TK176: sync=None refused')
        raises(('TypeError',), lambda: Store(s, 'x176', schema=QUICK, ops='pysets'),
               'TK176: ops="pysets" refused')
        s.rollback()
        st = Store(s, 'x', schema=QUICK)
        ok(st.add_tuple('...', 'user', 'bob', 'banned', 'doc', 'd1') > 0,
           'TK124: store id usable after the refused empty schema')
        # TK125: None subject predicate is a clean refusal, store stays usable
        raises(('AdmissionRejected',),
               lambda: st.add_tuple(None, 'user', 'bob', 'viewer', 'doc', 'd1'),
               'TK125: None subject predicate refused')
        raises(('AdmissionRejected',),
               lambda: st.add_tuple('...', 'user', 'bad name!', 'viewer', 'doc', 'd1'),
               'identifier outside the charset refused')
        raises(('AdmissionRejected',),
               lambda: st.add_tuple('...', 'user', 'bob', 'nosuch', 'doc', 'd1'),
               'undeclared relation refused')
        raises(('AdmissionRejected',),
               lambda: st.add_tuple('...', 'doc', 'd9', 'viewer', 'doc', 'd1'),
               'subject type outside the restriction refused')
        ok(st.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False,
           'no phantom write after refusals')
        ok(st.check('...', 'user', 'nobody', 'viewer', 'doc', 'nothing') is False,
           'unknown subject/object reads False')
    with Session(eng) as s:
        raises(('SchemaMismatch',), lambda: Store(s, 'x', schema=SCHEMA),
               'reopen with a different schema refused')
    with Session(eng) as s:
        # TK136: the same schema with CRLF + a trailing newline is the same schema
        try:
            st = Store(s, 'x', schema=QUICK.replace('\n', '\r\n') + '\r\n')
            err = None
        except Exception as e:  # noqa: BLE001 -- reported as a FAIL below
            st, err = None, f'{type(e).__name__}: {str(e)[:200]}'
        ok(st is not None and st.check('...', 'user', 'bob', 'banned', 'doc', 'd1') is True,
           f'TK136: reopen with CRLF / trailing-newline schema accepted ({err})')
    with Session(eng) as s:
        os.environ['ZANZIBAR_MAX_CLOSURE_FANOUT'] = '3'
        try:
            st = Store(s, 'cap', schema=QUICK)
            for u in ('a', 'b', 'c', 'd'):
                st.add_tuple('...', 'user', u, 'member', 'group', 'big')
            raises(('ClosureFanoutExceeded',),
                   lambda: st.add_tuple('member', 'group', 'big', 'viewer', 'doc', 'd1'),
                   'closure fan-out cap refuses an oversized write')
            ok(st.check('...', 'user', 'a', 'viewer', 'doc', 'd1') is False,
               'refused fan-out write landed nowhere')
        finally:
            del os.environ['ZANZIBAR_MAX_CLOSURE_FANOUT']

    # close every pooled SQLite connection (the 0.0.3 trial saw "unclosed database"
    # ResourceWarnings at GC), then drop the scratch dbs unless a failure needs them
    for eng in engines:
        eng.dispose()
    took = time.monotonic() - t0
    if FAILURES:
        print(f'-- {PASSES} checks passed, {len(FAILURES)} failed, {took:.1f}s '
              f'(scratch dbs kept in {tmp})')
        return 1
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'-- {PASSES} checks passed, 0 failed, {took:.1f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
