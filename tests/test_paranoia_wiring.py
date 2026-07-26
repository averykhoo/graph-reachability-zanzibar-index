"""ZT-P1-3: the I1-I13 invariant layer is reachable from production wiring.

Before this, ``install_paranoia`` had exactly two callers -- both tests -- so every
runtime corruption detector was dark in any real deployment, including the I6
dead-node-id clause that catches the ZT-P0-1 residue-GC authorization escalation
(pinned in ``tests/test_reg14_residue_gc_elision.py``).

``ConnectedStore`` now takes ``paranoia=`` and honours ``ZANZIBAR_PARANOIA``:

  ``off``      DEFAULT -- no listeners (the historical behaviour, bit-for-bit).
  ``residue``  the cheap tier: I6 residue hygiene, pre-commit only,
               O(residue rows + referenced ids). Fail-closed on the write path.
  ``full``     the whole checker + the delta-scoped BFS verifier, pre/post-commit.
               O(store) per commit; prerelease/test tier.

The default is OFF on measured evidence, not by fiat. Interleaved A/B (alternating
arms, min-of-3, boolean fixture, per-write commits through the real
``ConnectedStore`` sync path, 2026-07-26):

  162 writes:  off  3.896s | residue  4.063s (+4.3%) | full  8.743s (+124%)
  478 writes:  off 14.641s | residue 15.480s (+5.7%) | full 58.928s (+303%)

So the cheap tier is ~50x cheaper than the full one but still ~5% of the write path
AND growing with store size (its scan is O(residue rows)) -- worth switching on
deliberately, not worth imposing silently. If anyone widens the cheap tier's clause
set, RE-MEASURE with the same interleaved method and update these numbers and
``ConnectedStore.DEFAULT_PARANOIA``.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import ConnectedStore, TupleLogV1
from index_v4.invariants import (InvariantViolation, PARANOIA_ENV_VAR,
                                 install_paranoia, normalize_paranoia_level,
                                 resolve_paranoia_level)
from index_v4.models import NodeV4, ResidueV1

STORE = 'cs'


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture(autouse=True)
def _no_ambient_env(monkeypatch):
    """The env var is process-wide; never let the developer's shell decide a result."""
    monkeypatch.delenv(PARANOIA_ENV_VAR, raising=False)


def _open(session, load_fga_schema, **kw):
    cs = ConnectedStore(session, STORE, schema=load_fga_schema('boolean_wildcards.fga'), **kw)
    # a small, residue-bearing state: a wildcard grant (stars), an exclusion (neg),
    # and an ordinary derived edge.
    cs.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    cs.add_tuple('...', 'user', 'alice', 'blocked', 'doc', 'd1')
    cs.add_tuple('...', 'user', 'bob', 'editor', 'doc', 'd2')
    return cs


def _residue(session):
    row = session.exec(select(ResidueV1).where(ResidueV1.store_id == STORE)).first()
    assert row is not None, 'fixture must leave a residue row to tamper with'
    return row


def _dead_id(session):
    """An id no node holds (and none can: node ids are positive autoincrement)."""
    live = {n.id for n in session.exec(
        select(NodeV4).where(NodeV4.store_id == STORE)).all()}
    return max(live) + 10_000


def _log_len(session):
    return len(session.exec(select(TupleLogV1)
                            .where(TupleLogV1.store_id == STORE)).all())


# --------------------------------------------------------------------------- #
# (a) disabled behaves as today
# --------------------------------------------------------------------------- #

def test_paranoia_off_installs_nothing_and_does_not_check(session, load_fga_schema):
    cs = _open(session, load_fga_schema, paranoia=False)
    assert cs.paranoia == 'off'
    assert cs.paranoia_guard is None
    assert session.info.get('paranoia_guards', {}) == {}

    # The corruption the default tier catches sails straight through: this is the
    # pre-ZT-P1-3 production behaviour, pinned so "off" can never silently become
    # "on" (or vice versa) without this test moving.
    row = _residue(session)
    row.upos = json.dumps([_dead_id(session)])
    session.add(row)
    cs.add_tuple('...', 'user', 'carol', 'editor', 'doc', 'd3')
    assert cs.check('...', 'user', 'carol', 'editor', 'doc', 'd3') is True
    assert json.loads(_residue(session).upos) != [], 'the tampering must have committed'


def test_paranoia_off_is_the_pre_existing_write_behaviour(session, load_fga_schema):
    """Ordinary writes/reads/rejections are identical with the layer disabled."""
    cs = _open(session, load_fga_schema, paranoia='off')
    assert cs.check('...', 'user', 'bob', 'viewer', 'doc', 'd2') is True
    assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False
    with pytest.raises(ValueError):
        cs.remove_tuple('...', 'user', 'nobody', 'editor', 'doc', 'd9')


# --------------------------------------------------------------------------- #
# (b) enabled detects injected corruption and FAILS CLOSED
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('level', ['residue', 'full', True])
def test_paranoia_aborts_the_write_on_a_dangling_residue_id(session, load_fga_schema, level):
    """The ZT-P0-1 corruption class (a residue vouching for a node id that no longer
    exists -- SQLite then recycles that rowid onto an unrelated principal). Injected
    by tampering with state directly, exactly as the seeded-corruption tests in
    ``test_invariants_derived.py`` do."""
    cs = _open(session, load_fga_schema, paranoia=level)
    before_log = _log_len(session)

    row = _residue(session)
    row.upos = json.dumps([_dead_id(session)])
    session.add(row)

    with pytest.raises(InvariantViolation) as exc:
        cs.add_tuple('...', 'user', 'carol', 'editor', 'doc', 'd3')

    msg = str(exc.value)
    assert 'I6' in msg and 'dead node id' in msg, msg          # the violated clause
    assert f'store={STORE!r}' in msg, msg                      # ... and which store
    assert 'pre-commit' in msg, msg                            # ... and which phase

    # Fail-closed: the commit never happened, so BOTH halves rolled back -- the
    # tuple is absent, the log did not grow, and the tampering itself is gone.
    assert _log_len(session) == before_log
    assert cs.check('...', 'user', 'carol', 'editor', 'doc', 'd3') is False
    assert json.loads(_residue(session).upos) == []
    # ... and the store is still usable afterwards (the evaluator self-healed).
    cs.add_tuple('...', 'user', 'carol', 'editor', 'doc', 'd3')
    assert cs.check('...', 'user', 'carol', 'editor', 'doc', 'd3') is True


def test_residue_tier_catches_dangling_neg_ids_too(session, load_fga_schema):
    cs = _open(session, load_fga_schema, paranoia='residue')
    row = _residue(session)
    row.neg = json.dumps([_dead_id(session)])
    session.add(row)
    with pytest.raises(InvariantViolation, match='I6.*dead node id'):
        cs.add_tuple('...', 'user', 'dave', 'editor', 'doc', 'd4')


def test_tier_boundary_is_what_it_says_it_is(session, load_fga_schema):
    """Honesty pin for the tier table: an I13 refcount corruption is O(store) to see,
    so the CHEAP tier does not catch it and the FULL tier does. If someone widens the
    cheap tier they must move this test -- and re-measure."""
    cheap = _open(session, load_fga_schema, paranoia='residue')
    node = session.exec(select(NodeV4).where(NodeV4.store_id == STORE)).first()
    node.reference_count += 7
    session.add(node)
    cheap.add_tuple('...', 'user', 'erin', 'editor', 'doc', 'd5')   # commits happily

    engine2 = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine2)
    with Session(engine2) as s2:
        full = _open(s2, load_fga_schema, paranoia='full')
        n2 = s2.exec(select(NodeV4).where(NodeV4.store_id == STORE)).first()
        n2.reference_count += 7
        s2.add(n2)
        with pytest.raises(InvariantViolation, match='I13'):
            full.add_tuple('...', 'user', 'erin', 'editor', 'doc', 'd5')


# --------------------------------------------------------------------------- #
# (c) configuration: env var, and the explicit argument beating it
# --------------------------------------------------------------------------- #

def test_default_level_when_nothing_is_configured(session, load_fga_schema):
    """The default is OFF -- an unconfigured store behaves exactly as it did before
    ZT-P1-3 (no listeners, no per-commit cost, ``benchmarks/stmt_bench.py``'s
    statement counts unchanged). Changing this default means re-running the
    interleaved A/B in this module's docstring, so the constant is pinned here."""
    cs = ConnectedStore(session, STORE, schema=load_fga_schema('boolean_wildcards.fga'))
    assert cs.paranoia == ConnectedStore.DEFAULT_PARANOIA == 'off'
    assert cs.paranoia_guard is None
    assert session.info.get('paranoia_guards', {}) == {}


@pytest.mark.parametrize('raw,expected', [
    ('full', 'full'), ('FULL', 'full'), (' residue ', 'residue'), ('off', 'off'),
    ('1', 'full'), ('true', 'full'), ('0', 'off'), ('no', 'off'),
])
def test_env_var_selects_the_level(session, load_fga_schema, monkeypatch, raw, expected):
    monkeypatch.setenv(PARANOIA_ENV_VAR, raw)
    cs = ConnectedStore(session, STORE, schema=load_fga_schema('boolean_wildcards.fga'))
    assert cs.paranoia == expected
    assert (cs.paranoia_guard is None) == (expected == 'off')


@pytest.mark.parametrize('level', ['residue', 'full'])
def test_env_var_actually_wires_the_checker(session, load_fga_schema, monkeypatch, level):
    """Not just the label: an env-enabled store really does abort a corrupt write.
    This is the operator's whole story -- set one variable, get the detector."""
    monkeypatch.setenv(PARANOIA_ENV_VAR, level)
    cs = _open(session, load_fga_schema)
    row = _residue(session)
    row.upos = json.dumps([_dead_id(session)])
    session.add(row)
    with pytest.raises(InvariantViolation, match='I6'):
        cs.add_tuple('...', 'user', 'carol', 'editor', 'doc', 'd3')


@pytest.mark.parametrize('arg,env,expected', [
    ('full', 'off', 'full'),
    (False, 'full', 'off'),
    ('off', 'residue', 'off'),
    (True, 'off', 'full'),
])
def test_explicit_argument_beats_the_env_var(session, load_fga_schema, monkeypatch,
                                             arg, env, expected):
    monkeypatch.setenv(PARANOIA_ENV_VAR, env)
    cs = ConnectedStore(session, STORE, paranoia=arg,
                        schema=load_fga_schema('boolean_wildcards.fga'))
    assert cs.paranoia == expected


def test_empty_env_var_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv(PARANOIA_ENV_VAR, '   ')
    assert resolve_paranoia_level(default='residue') == 'residue'


@pytest.mark.parametrize('bad', ['paranoid', 'I6', 'on-ish', 2, None])
def test_a_typod_level_is_loud(bad):
    """A misspelled security switch must never quietly resolve to 'off'."""
    with pytest.raises(ValueError):
        normalize_paranoia_level(bad)


def test_bad_env_var_is_loud(session, load_fga_schema, monkeypatch):
    monkeypatch.setenv(PARANOIA_ENV_VAR, 'yes-please')
    with pytest.raises(ValueError, match='paranoia'):
        ConnectedStore(session, STORE, schema=load_fga_schema('boolean_wildcards.fga'))


# --------------------------------------------------------------------------- #
# existing wiring must not double-install
# --------------------------------------------------------------------------- #

def test_reinstall_upgrades_in_place_instead_of_stacking(session, load_fga_schema):
    """``tests/wildcard_helpers`` and ``tests/test_connectedstore`` install paranoia
    themselves, on sessions a ConnectedStore may already have wired."""
    cs = _open(session, load_fga_schema, paranoia='residue')
    guard = install_paranoia(session, STORE, cs.widx.schema_info)      # level='full'
    assert guard is cs.paranoia_guard, 'a second guard would double-check every commit'
    assert guard.level == 'full', 'a stronger re-install must win'

    install_paranoia(session, STORE, cs.widx.schema_info, level='off')
    assert guard.level == 'full', 'a re-install must never silently DOWNGRADE'

    listeners = session.info['paranoia_guards']
    assert list(listeners) == [STORE]

    # and the upgraded level is live: an I13 corruption (full-tier only) now bites.
    node = session.exec(select(NodeV4).where(NodeV4.store_id == STORE)).first()
    node.reference_count += 3
    session.add(node)
    with pytest.raises(InvariantViolation, match='I13'):
        cs.add_tuple('...', 'user', 'frank', 'editor', 'doc', 'd6')


def test_off_store_can_still_be_wired_by_a_later_install(session, load_fga_schema):
    cs = _open(session, load_fga_schema, paranoia='off')
    assert cs.paranoia_guard is None
    guard = install_paranoia(session, STORE, cs.widx.schema_info, level='residue')
    assert guard is not None and guard.level == 'residue'
    row = _residue(session)
    row.upos = json.dumps([_dead_id(session)])
    session.add(row)
    with pytest.raises(InvariantViolation, match='I6'):
        cs.add_tuple('...', 'user', 'grace', 'editor', 'doc', 'd7')


if __name__ == '__main__':          # pragma: no cover
    pytest.main([__file__, '-q'])
