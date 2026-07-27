"""reg16 (zero-trust ZT-P1-8e): the I5 bypass window is THREAD-scoped, not shared.

``WildcardIndex.processor_writes`` is the ENTIRE derived-relation-exclusivity (I5)
bypass: while it is True, a write onto a derived-public family is permitted, because
the delta processor is understood to be the one writing. It used to be a plain
instance attribute, so two threads sharing one ``WildcardIndex`` shared ONE window --
the processor's cascade on thread A silently authorised a USER write on thread B to
land directly on a derived family. That is not a DB error that a caller retries; it
is authorization state (a derived grant nobody derived) that survives commit, and it
is the one flag in this repo where violating the documented "one Session per thread"
rule corrupts answers rather than raising.

The window (and its downstream mirror ``ReachabilityIndex._writing_derived``, which
decides whether the direct edge row is stamped ``derived``) is now backed by
``threading.local``, so it belongs to the thread that opened it and every other
thread reads the closed default. The failure is loud: the foreign thread hits the
ordinary I5 ``ValueError``, which the repo deliberately does NOT classify as
``AdmissionRejected`` (it means a write path bypassed ``RuleSet.apply``).

These tests assert on the flag/guard layer rather than on two concurrent ``add_tuple``
calls, deliberately: the guard IS the window, and a real cross-thread write against a
shared in-memory SQLite session would fail for connection-affinity reasons that have
nothing to do with I5 -- which would make a green test prove nothing.
"""

import threading

import pytest

from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index

SCHEMA = '''
    type user
    type doc
      relations
        define banned: [user]
        define viewer: [user] but not banned
'''

# (object type, derived-public relation) -- the family only the processor may write.
DERIVED = ('doc', 'viewer')


@pytest.fixture
def widx():
    rs = parse_openfga_schema(SCHEMA, enable_boolean=True)
    session, w = make_wildcard_index(rs.schema_info)
    assert DERIVED in w.schema_info.derived_families, 'fixture must target a derived family'
    yield w
    session.close()


def _observe(w) -> dict:
    """Every read site of the window, from the calling thread.

    ``_assert_derived_exclusivity`` is the gate (raise = user writes refused);
    ``_derived_write_ctx`` is the stamp (True = the edge row is marked ``derived``);
    ``idx._writing_derived`` is the mirror the row writer actually consults.
    """
    o_type, rel = DERIVED
    try:
        w._assert_derived_exclusivity(rel, o_type)
        refused = False
    except ValueError:
        refused = True
    return {'flag': w.processor_writes,
            'refused': refused,
            'stamp': w._derived_write_ctx(rel, o_type)}


def test_window_opened_on_one_thread_does_not_authorise_another(widx):
    """THE BUG: thread A holds the processor window open; thread B must still be
    refused. Pre-fix thread B saw the shared True and its user write was admitted."""
    opened = threading.Event()
    release = threading.Event()
    seen: dict[str, dict] = {}
    checks = 0

    def processor_thread():
        widx.processor_writes = True
        try:
            seen['inside_owner'] = _observe(widx)
            opened.set()
            assert release.wait(10), 'observer thread never reported'
        finally:
            widx.processor_writes = False
        seen['after_owner'] = _observe(widx)

    def observer_thread():
        assert opened.wait(10), 'processor thread never opened the window'
        seen['foreign'] = _observe(widx)
        release.set()

    a = threading.Thread(target=processor_thread)
    b = threading.Thread(target=observer_thread)
    a.start(); b.start()
    a.join(10); b.join(10)
    assert not a.is_alive() and not b.is_alive(), 'threads deadlocked'

    # Anti-vacuity: all three observations must have happened, and each is a real
    # three-way read (flag + gate + stamp), so 9 distinct facts are pinned below.
    assert set(seen) == {'inside_owner', 'foreign', 'after_owner'}
    for phase, obs in seen.items():
        checks += len(obs)
        assert set(obs) == {'flag', 'refused', 'stamp'}, phase
    assert checks == 9

    # The owner thread has the window: flag on, user-write gate open, edges stamped.
    assert seen['inside_owner'] == {'flag': True, 'refused': False, 'stamp': True}
    # The FOREIGN thread, at the same instant, must see a CLOSED window on all three.
    assert seen['foreign'] == {'flag': False, 'refused': True, 'stamp': False}
    # ...and the owner closes it normally afterwards (no leak into the next write).
    assert seen['after_owner'] == {'flag': False, 'refused': True, 'stamp': False}


def test_window_is_not_inherited_by_a_thread_started_inside_it(widx):
    """A thread SPAWNED while the window is open must not inherit it either --
    ``threading.local`` state is per-thread, never copied from the parent."""
    inner: list[dict] = []
    widx.processor_writes = True
    try:
        t = threading.Thread(target=lambda: inner.append(_observe(widx)))
        t.start(); t.join(10)
        assert not t.is_alive()
        # the parent still holds its own window while the child observed
        assert widx.processor_writes is True
    finally:
        widx.processor_writes = False
    assert len(inner) == 1, 'child thread never observed (vacuous)'
    assert inner[0] == {'flag': False, 'refused': True, 'stamp': False}


def test_single_thread_behaviour_is_unchanged(widx):
    """The property must be a drop-in for the old attribute on ONE thread: open,
    write is admitted and stamped; closed, it is refused. (Every existing caller --
    ``DeltaProcessor._write_derived`` and three test modules -- is single-threaded,
    so this is the no-regression half of the fix.)"""
    transitions = 0
    for want in (False, True, False, True, False):
        widx.processor_writes = want
        transitions += 1
        obs = _observe(widx)
        assert obs == {'flag': want, 'refused': not want, 'stamp': want}, want
    assert transitions == 5


def test_foreign_thread_refusal_names_the_routing_fix(widx):
    """The loud failure must stay diagnosable: the I5 ValueError names the relation
    and the routing contract, and is NOT an AdmissionRejected (a bypassed write path
    is a wiring bug, not an inadmissible tuple -- see ``_assert_derived_exclusivity``)."""
    from zanzibar_utils_v1 import AdmissionRejected

    caught: list[BaseException] = []

    def observer():
        try:
            widx._assert_derived_exclusivity(DERIVED[1], DERIVED[0])
        except ValueError as e:                     # pragma: no branch - must raise
            caught.append(e)

    widx.processor_writes = True
    try:
        t = threading.Thread(target=observer)
        t.start(); t.join(10)
    finally:
        widx.processor_writes = False
    assert len(caught) == 1, 'foreign-thread write was NOT refused'
    assert not isinstance(caught[0], AdmissionRejected)
    assert 'processor-maintained' in str(caught[0])
    assert 'RuleSet.apply' in str(caught[0])
