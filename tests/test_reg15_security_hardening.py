"""reg15 — the zero-trust review's security-hardening pins (2026-07-26).

Three independent findings, one file, because each is a one-line defect with a
one-line fix and the value is entirely in the regression pin:

* **ZT-P1-1** — ``_IDENTIFIER_RE`` was anchored with ``$``, which in Python also
  matches immediately BEFORE a trailing newline. So ``'alice\\n'`` validated, and
  because the newline is not consumed by the ``{1,256}`` repeat, so did
  257-character names ending in one — a control character reaching persisted
  identity strings and an off-by-one against the documented bound, both in direct
  contradiction of ``zanzibar_utils_v1``'s stated contract. Fixed with ``\\Z`` +
  ``re.fullmatch``.
* **ZT-P1-2** — sixteen load-bearing safety checks in ``index_v4/core.py`` (plus one
  in ``processor.py``) were bare ``assert`` statements, which ``python -O`` REMOVES.
  Three of them are the only guard on their path: the batch/bridge cycle detector
  (whose bypass yields unbounded path counts, hence permanent phantom reachability,
  hence a stale ALLOW), the two refcount-underflow guards, and the ``remove_node``
  dangling-edge post-condition. Converted to explicit raises.
* **ZT-P1-7** — ``_lock_store`` / ``_lock_source`` memoized on
  ``Session.get_transaction()``, which returns the ROOT transaction even inside
  ``begin_nested()``. A caller taking the lock inside a savepoint and rolling that
  savepoint back (PostgreSQL releases locks acquired inside it) would then match the
  memo and take NO lock. Keyed on ``(root, nested)`` now.

The ``-O`` pins are the point of this file: a test that only exercises the default
interpreter cannot distinguish an ``assert`` from a ``raise``, which is exactly how
these survived.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from index_v4.core import ReachabilityIndex
from index_v4.invariants import InvariantViolation
from index_v4.models import StoreV4
from zanzibar_utils_v1 import is_valid_identifier, validate_write_identifiers

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _fresh_index(store_id: str = 't'):
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(StoreV4(id=store_id))
    session.commit()
    return session, ReachabilityIndex(session, store_id)


# --------------------------------------------------------------------------- #
# ZT-P1-1 — identifier anchoring
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('value', [
    'alice\n',              # the original bypass: `$` matches before a trailing \n
    'a' * 256 + '\n',       # ...which also smuggled a 257th character past {1,256}
    'alice\r',
    'alice\r\n',
    '\n',
    'alice\nbob',           # embedded, not trailing -- was already rejected; stays so
])
def test_reg15_identifier_rejects_control_characters(value):
    """A name carrying any newline is not a valid identifier. The trailing-newline
    cases are the regression: they were ACCEPTED before the `\\Z` fix."""
    assert is_valid_identifier(value) is False


@pytest.mark.parametrize('value', [
    'alice',
    'a' * 256,              # the legitimate upper bound MUST still be accepted
    'a',
    'a.b/c@d+e=f-g_h',      # every charset member
])
def test_reg15_identifier_still_accepts_legitimate_names(value):
    """The fix must not tighten the documented 1-256 charset bound."""
    assert is_valid_identifier(value) is True


def test_reg15_identifier_length_bound_is_exactly_256():
    """Off-by-one pin: 256 in, 257 out, and 257-with-a-newline out (the bypass)."""
    assert is_valid_identifier('a' * 256) is True
    assert is_valid_identifier('a' * 257) is False
    assert is_valid_identifier('a' * 256 + '\n') is False


def test_reg15_write_validation_rejects_trailing_newline_end_to_end():
    """The bypass mattered because it reached the WRITE path, not just the predicate."""
    with pytest.raises(ValueError):
        validate_write_identifiers('...', 'user', 'alice\n', 'viewer', 'doc', 'd1')
    with pytest.raises(ValueError):
        validate_write_identifiers('...', 'user', 'alice', 'viewer', 'doc', 'd1\n')
    # control: the same write without the newline is fine
    validate_write_identifiers('...', 'user', 'alice', 'viewer', 'doc', 'd1')


# --------------------------------------------------------------------------- #
# ZT-P1-2 — safety checks must survive `python -O`
# --------------------------------------------------------------------------- #

_GUARDED_MODULES = ['index_v4/core.py', 'index_v4/processor.py']


@pytest.mark.parametrize('rel', _GUARDED_MODULES)
def test_reg15_no_bare_assert_statements_in_guarded_modules(rel):
    """Structural pin, and the durable one: parse the module and assert it contains
    NO ``assert`` statement at all.

    This is what stops the defect class from coming back. A reviewer adding an
    ``assert`` to express a store invariant in these two modules is writing a check
    that silently disappears in any ``-O`` deployment; if an invariant belongs here it
    must be a raise. (Test modules are free to use ``assert`` -- only these two
    production modules are pinned.)
    """
    tree = ast.parse((REPO_ROOT / rel).read_text(encoding='utf-8'))
    offenders = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    assert offenders == [], (
        f'{rel} contains bare assert statement(s) at line(s) {offenders}; these vanish '
        f'under `python -O`. Express store invariants as `raise InvariantViolation(...)`'
    )


def _run_under_O(body: str) -> subprocess.CompletedProcess:
    """Execute a snippet in a subprocess with assertions DISABLED (`-O`)."""
    script = textwrap.dedent(body)
    return subprocess.run([PY, '-O', '-c', script], cwd=str(REPO_ROOT),
                          capture_output=True, text=True, timeout=180)


def test_reg15_assertions_really_are_disabled_under_O():
    """Control for the two tests below: prove `-O` actually strips asserts here, so a
    green result cannot be a false negative from the flag being ignored."""
    proc = _run_under_O("""
        try:
            assert False, 'should have been stripped'
            print('STRIPPED')
        except AssertionError:
            print('STILL_ACTIVE')
    """)
    assert proc.returncode == 0, proc.stderr
    assert 'STRIPPED' in proc.stdout, proc.stdout


def test_reg15_direct_edge_delta_guard_survives_O():
    """A converted guard (`count in {-1, 1}`) still fires with assertions disabled."""
    proc = _run_under_O("""
        from sqlmodel import Session, SQLModel, create_engine
        from index_v4.core import ReachabilityIndex
        from index_v4.invariants import InvariantViolation
        from index_v4.models import StoreV4

        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        s = Session(engine)
        s.add(StoreV4(id='t')); s.commit()
        idx = ReachabilityIndex(s, 't')
        try:
            idx._add_direct_edge_unsafe_impl(1, 2, 7)   # 7 is neither -1 nor +1
            print('NO_RAISE')
        except InvariantViolation:
            print('RAISED')
    """)
    assert proc.returncode == 0, proc.stderr
    assert 'RAISED' in proc.stdout, (
        f'the direct-edge delta guard did not fire under -O\n'
        f'stdout={proc.stdout}\nstderr={proc.stderr}')


def test_reg15_self_edge_cycle_guard_survives_O():
    """The self-edge rejection (the blind-audit C3 precedent) under `-O`. If this
    regressed, the node-DELETION shortcut would run on a self-referential edge."""
    proc = _run_under_O("""
        from sqlmodel import Session, SQLModel, create_engine
        from index_v4.core import ReachabilityIndex
        from index_v4.models import StoreV4

        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        s = Session(engine)
        s.add(StoreV4(id='t')); s.commit()
        idx = ReachabilityIndex(s, 't')
        try:
            idx._add_edge_locked(5, 5)
            print('NO_RAISE')
        except ValueError:
            print('RAISED')
    """)
    assert proc.returncode == 0, proc.stderr
    assert 'RAISED' in proc.stdout, (
        f'the self-edge guard did not fire under -O\n'
        f'stdout={proc.stdout}\nstderr={proc.stderr}')


def test_reg15_invariant_violation_is_still_assertionerror():
    """`InvariantViolation` subclasses `AssertionError`, so converting these asserts to
    raises is backward-compatible with any caller/test catching `AssertionError`.
    Pinned because that compatibility is why the conversion was safe to do wholesale."""
    assert issubclass(InvariantViolation, AssertionError)


# --------------------------------------------------------------------------- #
# ZT-P1-7 — the savepoint lock-memo hole
# --------------------------------------------------------------------------- #

def test_reg15_lock_memo_invalidated_by_savepoint_rollback():
    """Taking the lock inside `begin_nested()` and rolling the savepoint back must NOT
    leave a memo that suppresses the next real lock acquisition.

    On SQLite `with_for_update()` renders to nothing, so this asserts on the memo state
    rather than on observable lock behaviour -- the memo IS the bug: whatever the dialect
    does, a stale memo means `_lock_store` returns without issuing its SELECT.
    """
    session, idx = _fresh_index()

    nested = session.begin_nested()
    idx._lock_store()
    memo_in_savepoint = idx._locked_txn
    assert memo_in_savepoint is not None
    # the memo must record the NESTED transaction, not just the root
    assert memo_in_savepoint[1] is not None, (
        'memo did not capture the nested transaction; keyed on the root alone')

    nested.rollback()

    # after the savepoint is gone the memo must no longer match, so the next call
    # re-issues the lock SELECT instead of short-circuiting
    key_now = (session.get_transaction(), session.get_nested_transaction())
    assert key_now != memo_in_savepoint, (
        'the memo still matches after savepoint rollback -- _lock_store would '
        'short-circuit and take no lock (ZT-P1-7)')

    idx._lock_store()
    assert idx._locked_txn == (session.get_transaction(),
                               session.get_nested_transaction())
    assert idx._locked_txn != memo_in_savepoint
    session.close()


def test_reg15_lock_memo_still_short_circuits_within_one_transaction():
    """The P12a optimization must survive the fix: repeated calls inside ONE
    transaction (no savepoint) still short-circuit on the memo."""
    session, idx = _fresh_index()
    idx._lock_store()
    first = idx._locked_txn
    idx._lock_store()
    assert idx._locked_txn is first, 'memo stopped short-circuiting; P12a regressed'
    session.close()


def test_reg15_source_lock_memo_keys_on_nested_transaction_too():
    """`TupleSource._lock_source` must carry the same fix -- the HA write path takes it
    BEFORE the graph store lock, so a suppressed source lock breaks admission
    validation against current committed state."""
    import inspect

    from connectedstore import source as source_mod

    src = inspect.getsource(source_mod.TupleSource._lock_source)
    assert 'get_nested_transaction' in src, (
        '_lock_source still keys its memo on the root transaction alone (ZT-P1-7)')
