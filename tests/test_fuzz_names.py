"""
Boundary / adversarial entity-name tests for both backends.

Entity names are passed as structured arguments and stored as bound SQL parameters
(never string-interpolated) and interned as tuple elements (never re-parsed), so DSL
delimiters, unicode, and injection-style strings must round-trip losslessly and never
collide, confuse the parser, or reach the database as SQL. The only reserved name is the
wildcard sentinel ``'*'``, which cannot be a concrete entity.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine, ALL_SETOPS
from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index

SCHEMA = '''
type user
type doc
  relations
    define viewer: [user]
'''

# DSL delimiters, unicode/emoji, whitespace, quotes, and an injection payload.
WEIRD_NAMES = [
    'alice#member', 'user:bob', 'carol@example.com', 'a, b', 'x or y', 'p but not q',
    'main.py', 'shared-docs', 'a/b/c', '  spaced  ', 'tab\tsep', 'new\nline',
    'quote"d', "apos'x", 'C:\\win\\path', '日本語', '😀emoji🚀', 'null\x00byte',
    "rob'); DROP TABLE node_v4; --", "1 OR 1=1", '{"json":true}', '',
]


def _set_backend():
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.bind)
    return session, SetEngine(session, 'f', SCHEMA)


def _graph_backend():
    rs = parse_openfga_schema(SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info, store_id='f')
    return session, widx


@pytest.mark.parametrize('backend', ['set', 'graph'])
@pytest.mark.parametrize('name', WEIRD_NAMES, ids=lambda s: repr(s)[:24])
def test_weird_name_round_trips_and_isolates(backend, name):
    session, be = _set_backend() if backend == 'set' else _graph_backend()
    try:
        be.add_tuple('...', 'user', name, 'viewer', 'doc', 'd')
        session.commit()
        # exact round-trip
        assert be.check('...', 'user', name, 'viewer', 'doc', 'd') is True
        # no collision with a near-neighbour name or a different object
        assert be.check('...', 'user', name + 'x', 'viewer', 'doc', 'd') is False
        assert be.check('...', 'user', name, 'viewer', 'doc', 'other') is False
        # the injection payload did not execute: the store still works afterwards
        be.add_tuple('...', 'user', 'sentinel', 'viewer', 'doc', 'd2')
        session.commit()
        assert be.check('...', 'user', 'sentinel', 'viewer', 'doc', 'd2') is True
    finally:
        session.close()


@pytest.mark.parametrize('backend', ['set', 'graph'])
def test_star_is_reserved_as_concrete_name(backend):
    # viewer is [user] (no user:* declared), so a literal '*' subject is not a valid
    # concrete entity in either backend.
    session, be = _set_backend() if backend == 'set' else _graph_backend()
    try:
        with pytest.raises(ValueError):
            be.add_tuple('...', 'user', '*', 'viewer', 'doc', 'd')
    finally:
        session.close()


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_many_distinct_weird_names_do_not_collide(ops):
    # Interning many delimiter-laden names keeps them all distinct (surrogate keys are
    # structured tuples, so delimiters can't merge two identities).
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.bind)
    se = SetEngine(session, 'm', SCHEMA, ops=ops)
    names = [n for n in WEIRD_NAMES if n != '']
    for i, n in enumerate(names):
        se.add_tuple('...', 'user', n, 'viewer', 'doc', f'd{i}')
    session.commit()
    # each name resolves only to its own doc
    for i, n in enumerate(names):
        assert se.check('...', 'user', n, 'viewer', 'doc', f'd{i}') is True
        assert se.check('...', 'user', n, 'viewer', 'doc', f'd{(i + 1) % len(names)}') is False
    assert len(se.interner.id_of) == 2 * len(names)     # every name a distinct surrogate
    session.close()
