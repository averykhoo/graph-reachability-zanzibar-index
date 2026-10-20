"""Repro for TK151 claim B3: a stall recorded while nothing was pending is never
cleared by a catch_up() that applies nothing.

Part A: deterministic fault injection (one OperationalError from the store lock on an
        idle poll -- stands in for a lost connection / lock timeout).
Part B: a REAL transient failure, no patching of library code: a second SQLite
        connection holds the database write lock (e.g. a writer to ANOTHER store in the
        same file) while the worker polls an idle store.
"""
import os
import sqlite3
import tempfile
import threading
import time

from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, Session, create_engine

import zanzibar
from zanzibar import Store, IndexStalled

print('zanzibar from', zanzibar.__file__)

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""


def state(tag, s):
    print(f'  [{tag}] lag={s.lag()} applied={s.cursor.applied_log_id} '
          f'stalled_after={s.cursor.stalled_after} index_stalled={s.index_stalled}')


def probe_reads(s):
    try:
        print('  lookup ->', s.lookup('user:alice', object_type='doc', relation='viewer'))
    except IndexStalled as e:
        print('  lookup -> IndexStalled:', str(e)[:160], '...')
    print('  check(alice viewer d1) ->', s.check('user:alice', 'viewer', 'doc:d1'))


def fresh_db():
    d = tempfile.mkdtemp(prefix='b3-')
    path = os.path.join(d, 'app.db')
    engine = create_engine(f'sqlite:///{path}')
    SQLModel.metadata.create_all(engine)
    return path, engine


# ---------------------------------------------------------------- Part A
print('=== Part A: injected transient failure on an idle poll ===')
path, engine = fresh_db()
session = Session(engine)
store = Store(session, 'my-app', schema=SCHEMA, sync=False)
store.add_tuple('user:alice', 'viewer', 'doc:d1')
print('  catch_up() ->', store.catch_up())
state('caught up, idle', store)

real_lock = store.widx.idx._lock_store
calls = {'n': 0}


def flaky_lock():
    calls['n'] += 1
    if calls['n'] == 1:
        raise OperationalError('SELECT 1', {}, Exception('server closed the connection unexpectedly'))
    return real_lock()


store.widx.idx._lock_store = flaky_lock
try:
    store.catch_up()
except OperationalError as e:
    print('  catch_up() raised', type(e).__name__)
state('after failed idle poll', store)
print('  stall_error =', store.stall_error)

for i in range(3):
    print(f'  catch_up() #{i + 1} (healthy, nothing pending) ->', store.catch_up())
state('after 3 successful zero-row catch_ups', store)
probe_reads(store)

store.add_tuple('user:bob', 'viewer', 'doc:d1')
print('  write bob; catch_up() ->', store.catch_up())
state('after a write was applied', store)
probe_reads(store)
session.close()

# ---------------------------------------------------------------- Part B
print('=== Part B: real SQLite lock contention, no library code patched ===')
path, engine = fresh_db()
session = Session(engine)
store = Store(session, 'my-app', schema=SCHEMA, sync=False)
store.add_tuple('user:alice', 'viewer', 'doc:d1')
print('  catch_up() ->', store.catch_up())
state('caught up, idle', store)

release = threading.Event()
held = threading.Event()


def holder():
    c = sqlite3.connect(path, timeout=0, isolation_level=None)
    c.execute('BEGIN IMMEDIATE')         # take the database write lock, write nothing
    held.set()
    release.wait()
    c.execute('ROLLBACK')
    c.close()


t = threading.Thread(target=holder)
t.start()
held.wait()

# Release the external lock the moment catch_up gives up, so _record_stall can write.
orig_record = Store._record_stall


def record_after_release(self, exc):
    release.set()
    time.sleep(0.2)
    return orig_record(self, exc)


Store._record_stall = record_after_release   # instrumentation only: timing of release
t0 = time.time()
try:
    store.catch_up()
except Exception as e:
    print(f'  catch_up() raised {type(e).__name__} after {time.time() - t0:.1f}s:', str(e).splitlines()[0][:120])
Store._record_stall = orig_record
t.join()
state('after lock-timeout on idle poll', store)
print('  stall_error =', (store.stall_error or '')[:160])
print('  catch_up() (healthy, nothing pending) ->', store.catch_up())
state('after zero-row catch_up', store)
probe_reads(store)
store.refresh()
state('after refresh()', store)
store.add_tuple('user:carol', 'viewer', 'doc:d1')
print('  write carol; catch_up() ->', store.catch_up())
state('after a write was applied', store)
session.close()
