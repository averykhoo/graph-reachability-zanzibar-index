"""`UnprovenExtensionWarning`: a schema that uses a wildcard extension beyond OpenFGA says so.

User decision 2026-09-26 (task `ASK-2`): the three extensions -- wildcard usersets
`[T:*#p]`, star tuplesets (a `from`-tupleset admitting `[T:*]`), and object wildcards
(`object_wildcard_shapes`) -- are KEPT, but they sit outside the headline equivalence
theorems' premise (`FullScope.lean::W4Fragment` fields `wsBare` / `bareStar` /
`ttuStarFree`), so anyone using them must be told agreement rests on tests, not proof.

The warning is raised in `zanzibar_utils_v1.py::derive_schema_info`, the one step every
construction path shares (`parse_openfga_schema`, `SetEngine.__init__`,
`connectedstore.schema_io`). `pytest.ini` IGNORES it suite-wide so the hundreds of
wildcard fixtures do not flood the warnings summary; `pytest.warns` / `catch_warnings`
below install their own filter, so these pins are not blinded by that ignore.

Sabotage (2026-09-26): with the `_warn_unproven_extensions(...)` call deleted from
`derive_schema_info`, the six warning tests go red (observed 2026-09-26: `6 failed, 2 passed`;
`test_openfga_surface_is_silent[graph|set-engine]` stayed green, as they must).
"""
import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine
from zanzibar_utils_v1 import UnprovenExtensionWarning, parse_openfga_schema

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
