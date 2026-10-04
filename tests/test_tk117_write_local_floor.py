"""TK117 (c) -- the ParityEngine grid always asks the queries at the object the last op wrote.

Property guarded
----------------
``tests/parity.py::ParityEngine._grid`` appends ``ParityEngine._write_local_floor`` AFTER
its ``grid_cap`` sample. The floor is rng-free and holds the op's own tuple plus every grid
subject x every target relation on the written object. So a backend that is wrong about the
written object is caught on EVERY seed, whatever the cap throws away. This applies to adds
and removes alike. Below the cap the floor adds nothing, except at an object-wildcard write,
whose ``*`` object the pool never lists.

Why: above the cap, Layer A was a bare ``rng.sample`` with no floor. A lie confined to the
last write's own check therefore escaped with probability about ``(N - cap) / N``. Pre-fix
evidence, literal output (P10 re-run, verifier 2, 2026-09-28, recorded in
``docs/p10-scope-audit-2026-09-27.md`` sec 5 H7 witness 9; the store is ``_AUDITOR`` below)::

    M0 no-lie cap=600: GREEN  graph_present=True leaf_families=0
    final pool=1056 final compared=600 ever compared=931 never=125
    never-compared TRUE: ('...', 'user', 'hank', 'maintainer', 'repo', 'docs')
    planted lie cap=600: GREEN
    planted lie cap=10**9: RED: check parity broken after add ('...', 'user', 'hank', ...
    lie on the last write's own check escapes at cap=600 on 8/20 seeds   (independent store: 15/20)

Every test that claims the floor CATCHES something has a control that stubs the floor
out and shows the same lie ESCAPING. Without that control a green would not show the
floor did anything.

LIMIT (stated, not tested): effects that land on OTHER objects stay sampled. That covers a
TTU child of the written object, and an object that names the written userset. Parts (a)
and (b) of TK117 are still open. Map: ``docs/tk117-write-local-floor-2026-10-04.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity import ParityEngine

_GITHUB = (Path(__file__).parent / 'fga_schemas' / 'github.fga').read_text(encoding='utf-8')

#: The P10 verifier-2 store, verbatim. 14 writes; the last one is the witness.
_AUDITOR = [
    ('...', 'user', 'alice', 'owner', 'organization', 'acme'),
    ('...', 'user', 'bob', 'member', 'organization', 'acme'),
    ('member', 'organization', 'acme', 'repo_reader', 'organization', 'acme'),
    ('...', 'user', 'carol', 'repo_writer', 'organization', 'acme'),
    ('...', 'user', 'dave', 'member', 'team', 'core'),
    ('member', 'team', 'core', 'member', 'team', 'infra'),
    ('...', 'user', 'erin', 'member', 'team', 'infra'),
    ('...', 'organization', 'acme', 'owner', 'repo', 'api'),
    ('...', 'organization', 'acme', 'owner', 'repo', 'web'),
    ('member', 'team', 'core', 'writer', 'repo', 'api'),
    ('member', 'team', 'infra', 'triager', 'repo', 'web'),
    ('...', 'user', 'frank', 'admin', 'repo', 'cli'),
    ('...', 'user', 'gina', 'owner', 'organization', 'globex'),
    ('...', 'user', 'hank', 'maintainer', 'repo', 'docs'),
]
_HANK = _AUDITOR[-1]

#: The verifier's independent store, cut at its 15th write, which writes a USERSET
#: (``team:t2#member``) onto ``repo:r6``. ``user:u3`` reaches r6 only through that userset.
_USERSET = [
    ('...', 'user', 'u1', 'owner', 'organization', 'o1'),
    ('...', 'user', 'u2', 'repo_admin', 'organization', 'o1'),
    ('member', 'organization', 'o1', 'repo_writer', 'organization', 'o1'),
    ('...', 'organization', 'o1', 'owner', 'repo', 'r1'),
    ('...', 'organization', 'o1', 'owner', 'repo', 'r2'),
    ('...', 'user', 'u3', 'member', 'team', 't1'),
    ('...', 'user', 'u4', 'member', 'team', 't2'),
    ('member', 'team', 't1', 'member', 'team', 't2'),
    ('member', 'team', 't2', 'reader', 'repo', 'r3'),
    ('...', 'user', 'u5', 'triager', 'repo', 'r3'),
    ('...', 'user', 'u6', 'owner', 'organization', 'o2'),
    ('...', 'organization', 'o2', 'owner', 'repo', 'r4'),
    ('...', 'user', 'u7', 'maintainer', 'repo', 'r5'),
    ('...', 'user', 'u8', 'member', 'organization', 'o2'),
    ('member', 'team', 't2', 'admin', 'repo', 'r6'),
]
_U3_R6 = ('...', 'user', 'u3', 'maintainer', 'repo', 'r6')

#: The floor is rng-free, so the seed count buys nothing for the floor itself; it only
#: has to let the no-floor CONTROLS escape. A cap well under the 1056-query pool makes
#: escapes likely and each op cheap. At the P10 cap of 600 with 20 seeds this module
#: took 371 s (2026-10-04); the property does not depend on the cap's value.
_SEEDS = range(5)
_CAP = 100


def _plant_lie(pe: ParityEngine, lie: tuple) -> None:
    """The graph side answers the NEGATION of the truth on exactly one query."""
    assert pe.graph is not None, 'witness needs the graph backend in the matrix'
    orig = pe.graph.check
    pe.graph.check = lambda q, _o=orig: (not _o(q)) if tuple(q) == lie else _o(q)


def _run(writes, *, seed, lie=None, lie_after_writes=False, removes=(), cap=_CAP):
    """Return 'GREEN', or the parity failure message. Any other AssertionError (an
    accept/reject disagreement, an I12 hit) is NOT a parity verdict and propagates."""
    pe = ParityEngine(_GITHUB, paranoia=False, grid_cap=cap, seed=seed)
    try:
        if lie is not None and not lie_after_writes:
            _plant_lie(pe, lie)
        for w in writes:
            assert pe.add_tuple(*w), f'write refused: {w}'
        if lie is not None and lie_after_writes:
            _plant_lie(pe, lie)
        for r in removes:
            assert pe.remove_tuple(*r), f'remove refused: {r}'
        return 'GREEN'
    except AssertionError as e:
        if 'check parity broken' not in str(e):
            raise
        return str(e)
    finally:
        pe.close()


@pytest.fixture
def no_floor(monkeypatch):
    """The instrument control: the floor stubbed out, i.e. the pre-TK117 grid."""
    monkeypatch.setattr(ParityEngine, '_write_local_floor',
                        staticmethod(lambda last, subjects, targets, have: []))


def test_the_store_is_capped_and_the_lie_is_a_real_divergence():
    """Preconditions, or every test below proves nothing: the store's final pool really
    exceeds the cap, the lie target is oracle-TRUE, and with no lie the run is GREEN."""
    pe = ParityEngine(_GITHUB, paranoia=False, grid_cap=10**9)
    try:
        for w in _AUDITOR:
            pe.add_tuple(*w)
        assert len(pe._grid()) > _CAP
        assert pe.check(*_HANK) is True
    finally:
        pe.close()
    assert _run(_AUDITOR, seed=0) == 'GREEN'


def test_a_lie_on_the_last_writes_own_check_is_caught_on_every_seed():
    """Sabotage (permanent, see the control below): the same lie, floor stubbed out,
    escapes on some seed. At cap 600 pre-fix it escaped on 8 of 20 (P10, above)."""
    for seed in _SEEDS:
        verdict = _run(_AUDITOR, seed=seed, lie=_HANK)
        assert f'after add {_HANK}' in verdict and f'q={_HANK}' in verdict, (seed, verdict)


def test_control_without_the_floor_that_lie_escapes(no_floor):
    escaped = [s for s in _SEEDS if _run(_AUDITOR, seed=s, lie=_HANK) == 'GREEN']
    assert escaped, 'the witness no longer discriminates: no seed lets the lie escape'


def test_a_userset_write_floors_its_expanded_members_at_the_written_object():
    """``team:t2#member admin repo:r6`` is the write; ``user:u3`` is a member only via
    team t1 nested in t2, so the lie is not on the op's own tuple. The floor asks every
    grid subject at repo:r6, which includes u3."""
    for seed in _SEEDS:
        verdict = _run(_USERSET, seed=seed, lie=_U3_R6)
        assert f'after add {_USERSET[-1]}' in verdict and f'q={_U3_R6}' in verdict, \
            (seed, verdict)


def test_control_without_the_floor_the_userset_lie_escapes(no_floor):
    escaped = [s for s in _SEEDS if _run(_USERSET, seed=s, lie=_U3_R6) == 'GREEN']
    assert escaped, 'the witness no longer discriminates: no seed lets the lie escape'


def test_a_remove_is_floored_too():
    """The lie is planted AFTER the adds (so the adds' floors cannot see it). It claims
    hank still holds the access that removing the tuple took away."""
    for seed in _SEEDS:
        verdict = _run(_AUDITOR, seed=seed, lie=_HANK, lie_after_writes=True,
                       removes=[_HANK])
        assert f'after remove {_HANK}' in verdict and f'q={_HANK}' in verdict, \
            (seed, verdict)


def test_control_without_the_floor_the_remove_lie_escapes(no_floor):
    escaped = [s for s in _SEEDS
               if _run(_AUDITOR, seed=s, lie=_HANK, lie_after_writes=True,
                       removes=[_HANK]) == 'GREEN']
    assert escaped, 'the witness no longer discriminates: no seed lets the lie escape'


def test_below_the_cap_the_floor_adds_nothing():
    """The uncapped grid is byte-identical with and without the floor, after every op of
    the store. Uncapped means no rng draw, so the two calls see the same state."""
    pe = ParityEngine(_GITHUB, paranoia=False, grid_cap=10**9)
    try:
        for w in _AUDITOR:
            pe.add_tuple(*w)
            assert pe._grid(w) == pe._grid(), w
        pe.remove_tuple(*_HANK)
        assert pe._grid(_HANK) == pe._grid()
    finally:
        pe.close()


# --- the one place the floor asks what the pool never lists: an object-* write --------

_OWC_SCHEMA = ('model\n  schema 1.1\ntype user\ntype folder\n  relations\n'
               '    define viewer: [user]\n'
               'type doc\n  relations\n    define parent: [folder]\n'
               '    define viewer: viewer from parent\n')
_OWC_SHAPES = frozenset({('doc', 'parent')})
_OWC_WRITES = [('...', 'user', 'a', 'viewer', 'folder', 'f1'),
               ('...', 'folder', 'f1', 'parent', 'doc', '*')]
_A_VIEWS_DOC_STAR = ('...', 'user', 'a', 'viewer', 'doc', '*')


def _owc_run():
    pe = ParityEngine(_OWC_SCHEMA, object_wildcard_shapes=_OWC_SHAPES, paranoia=False)
    try:
        _plant_lie(pe, _A_VIEWS_DOC_STAR)
        for w in _OWC_WRITES:
            assert pe.add_tuple(*w), w
        return 'GREEN'
    except AssertionError as e:
        if 'check parity broken' not in str(e):
            raise
        return str(e)
    finally:
        pe.close()


def test_an_object_wildcard_write_is_asked_at_its_star_object():
    """This is TK117 witness 5, at the object a write NAMED. The store is far below the cap,
    so the sample plays no part. Before TK117, no object-``*`` query was ever asked. Part
    (a), an object-``*`` query for every object-wildcard shape, is still open."""
    pe = ParityEngine(_OWC_SCHEMA, object_wildcard_shapes=_OWC_SHAPES, paranoia=False)
    try:
        for w in _OWC_WRITES:
            pe.add_tuple(*w)
        assert pe.check(*_A_VIEWS_DOC_STAR) is True
        assert len(pe._grid()) < pe.grid_cap
    finally:
        pe.close()
    verdict = _owc_run()
    assert f'after add {_OWC_WRITES[-1]}' in verdict and f'q={_A_VIEWS_DOC_STAR}' in verdict, \
        verdict


def test_control_without_the_floor_the_object_wildcard_lie_escapes(no_floor):
    assert _owc_run() == 'GREEN'
