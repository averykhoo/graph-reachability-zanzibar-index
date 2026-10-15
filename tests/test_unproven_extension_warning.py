"""`UnprovenExtensionWarning`: a schema that uses a wildcard extension beyond OpenFGA says so.

User decision 2026-09-26 (task `ASK-2`): the three extensions -- wildcard usersets
`[T:*#p]`, star tuplesets (a `from`-tupleset admitting `[T:*]`), and object wildcards
(`object_wildcard_shapes`) -- are KEPT, but they sit outside the headline equivalence
theorems' premise (`FullScope.lean::W4Fragment` fields `wsBare` / `bareStar` /
`ttuStarFree`), so anyone using them must be told agreement rests on tests, not proof.

The warning is raised in `src/zanzibar/schema/compiler.py::derive_schema_info`, the one step every
construction path shares (`parse_openfga_schema`, `SetEngine.__init__`,
`zanzibar.store.schema_io`). `pytest.ini` IGNORES it suite-wide so the hundreds of
wildcard fixtures do not flood the warnings summary; `pytest.warns` / `catch_warnings`
below install their own filter, so these pins are not blinded by that ignore.

Sabotage (2026-09-26): with the `_warn_unproven_extensions(...)` call deleted from
`derive_schema_info`, the six warning tests go red (observed 2026-09-26: `6 failed, 2 passed`;
`test_openfga_surface_is_silent[graph|set-engine]` stayed green, as they must).
"""
import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.setengine import SetEngine
from zanzibar.schema import UnprovenExtensionWarning, parse_openfga_schema

PLAIN = """model
  schema 1.1
type user
type folder
  relations
    define viewer: [user, user:*]
type doc
  relations
    define parent: [folder]
    define viewer: [user, user:*] or viewer from parent
"""

USERSET_STAR = """model
  schema 1.1
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, group:*#member]
"""

STAR_TUPLESET = """model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
"""

OBJ_WILD = frozenset({('doc', 'viewer')})

CASES = [
    pytest.param(USERSET_STAR, frozenset(), r'wildcard usersets \[group:\*#member\]',
                 id='userset-star'),
    pytest.param(STAR_TUPLESET, frozenset(), r'star tuplesets doc#parent', id='star-tupleset'),
    pytest.param(PLAIN, OBJ_WILD, r'object wildcards doc:\*#viewer', id='object-wildcard'),
]


def _set_engine(schema, owc):
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.get_bind())
    return SetEngine(session, 's', schema, object_wildcard_shapes=owc)


@pytest.mark.parametrize('schema,owc,feature', CASES)
def test_graph_compile_warns(schema, owc, feature):
    with pytest.warns(UnprovenExtensionWarning, match=feature):
        parse_openfga_schema(schema, object_wildcard_shapes=owc)


@pytest.mark.parametrize('schema,owc,feature', CASES[:2])
def test_set_engine_warns(schema, owc, feature):
    with pytest.warns(UnprovenExtensionWarning, match=feature):
        _set_engine(schema, owc)


def test_message_says_not_proven():
    with pytest.warns(UnprovenExtensionWarning, match=r'not covered by the formal equivalence proofs'):
        parse_openfga_schema(USERSET_STAR)


@pytest.mark.parametrize('build', [
    pytest.param(lambda: parse_openfga_schema(PLAIN), id='graph'),
    pytest.param(lambda: _set_engine(PLAIN, frozenset()), id='set-engine'),
])
def test_openfga_surface_is_silent(build):
    """A bare `[user:*]` is standard OpenFGA public access, and a plain `from` over a
    concrete tupleset is too: neither may warn, or the warning becomes noise people
    learn to ignore."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        build()
    assert [w for w in caught if issubclass(w.category, UnprovenExtensionWarning)] == []


# --------------------------------------------------------------------------- #
# TK123 item 15: ONE warning per Store, attributed to the caller's own line.
# --------------------------------------------------------------------------- #

def _caught_unproven(build):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        build()
    return [w for w in caught if issubclass(w.category, UnprovenExtensionWarning)]


@pytest.mark.parametrize('sync', [True, False], ids=['sync', 'async'])
def test_exactly_one_warning_per_store_at_the_callers_line(sync):
    """Bootstrapping a ``Store`` and reopening it each raise the warning exactly ONCE, and
    the warning's source file is THIS file (the line that constructed the ``Store``), not a
    library line. ``SetEngine`` adopts the ``RuleSet`` the store already compiled instead of
    deriving (and warning) again.

    Sabotage (2026-10-15), each observed red, then restored:
    - ``setengine/engine.py::SetEngine.__init__`` reverted to an unconditional
      ``derive_schema_info(...)``: ``assert 2 == 1``, ``2 failed, 1 passed`` (bootstrap and
      reopen both warned twice, the 0.0.5 behaviour; the direct-entry test stays green).
    - ``schema/compiler.py::_warn_unproven_extensions`` reverted to ``stacklevel=3``:
      ``assert '...compiler.py' == '...on_warning.py'``, ``3 failed`` (the warning
      pointed at a library line instead of this file).
    """
    from zanzibar import Store
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.get_bind())
    boot = _caught_unproven(lambda: Store(session, 's', schema=USERSET_STAR, sync=sync))
    session.commit()
    reopen = _caught_unproven(lambda: Store(session, 's', sync=sync))
    for ws in (boot, reopen):
        assert len(ws) == 1, [str(w.message) for w in ws]
        assert ws[0].filename == __file__, ws[0].filename


def test_direct_entry_points_point_at_the_caller():
    """``parse_openfga_schema`` and a standalone ``SetEngine`` also attribute the warning to
    the calling file (a fixed ``stacklevel`` only fits one call depth)."""
    for build in (lambda: parse_openfga_schema(USERSET_STAR),
                  lambda: _set_engine(USERSET_STAR, frozenset())):
        ws = _caught_unproven(build)
        assert len(ws) == 1
        assert ws[0].filename == __file__, ws[0].filename


def test_message_carries_no_repo_internal_references():
    """The wheel ships no ``formal/`` directory and no task tracker: the message names
    neither (TK123 item 14), and says how to silence it."""
    msg = str(_caught_unproven(lambda: parse_openfga_schema(USERSET_STAR))[0].message)
    for leak in ('formal/', 'W4Fragment', 'ASK-', 'TK1', 'See task'):
        assert leak not in msg, (leak, msg)
    assert "filterwarnings('ignore', category=zanzibar.UnprovenExtensionWarning)" in msg
