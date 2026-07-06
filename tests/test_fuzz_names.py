"""
Boundary / adversarial entity-name tests for both backends.

Identifiers (types, names, relations) are now constrained to a strict, delimiter-free
charset (``[A-Za-z0-9_./@+=-]``, 1-256 chars; names may also be the wildcard ``'*'``).
Valid identifiers -- including ones bearing the *allowed* punctuation -- must round-trip
losslessly and never collide. Everything else (DSL delimiters, whitespace, quotes,
unicode, control bytes, injection payloads, empty) must be rejected cleanly with a
ValueError, never silently stored or executed as SQL.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine, ALL_SETOPS
from zanzibar_utils_v1 import parse_openfga_schema, is_valid_identifier
from tests.wildcard_helpers import make_wildcard_index

SCHEMA = '''
type user
type doc
  relations
    define viewer: [user]
'''

# In-charset identifiers, including the allowed punctuation (. _ - / @ + =).
VALID_NAMES = [
    'alice', 'main.py', 'shared-docs', 'a/b/c', 'carol@example.com',
    'a+b', 'x=y', 'A_B-C.d/e@f+g=h', 'x' * 256,
]

# Out-of-charset: DSL delimiters, whitespace/keywords, quotes, unicode, control, injection.
INVALID_NAMES = [
    'alice#member', 'user:bob', 'a, b', 'x or y', 'p but not q', 'has space',
    'tab\tsep', 'new\nline', 'quote"d', "apos'x", 'C:\\win\\path', '日本語',
    '😀emoji🚀', 'null\x00byte', "rob'); DROP TABLE node_v4; --", '{"json":true}',
    '', 'x' * 257,
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
@pytest.mark.parametrize('name', VALID_NAMES, ids=lambda s: repr(s[:16]))
def test_valid_name_round_trips_and_isolates(backend, name):
    session, be = _set_backend() if backend == 'set' else _graph_backend()
    try:
        be.add_tuple('...', 'user', name, 'viewer', 'doc', 'd')
        session.commit()
        assert be.check('...', 'user', name, 'viewer', 'doc', 'd') is True
        assert be.check('...', 'user', name, 'viewer', 'doc', 'other') is False
    finally:
        session.close()


@pytest.mark.parametrize('backend', ['set', 'graph'])
@pytest.mark.parametrize('name', INVALID_NAMES, ids=lambda s: repr(s[:16]))
def test_invalid_name_rejected(backend, name):
    session, be = _set_backend() if backend == 'set' else _graph_backend()
    try:
        with pytest.raises(ValueError):
            be.add_tuple('...', 'user', name, 'viewer', 'doc', 'd')
        # the write was rejected up-front: the store is untouched and still usable
        be.add_tuple('...', 'user', 'sentinel', 'viewer', 'doc', 'd2')
        session.commit()
        assert be.check('...', 'user', 'sentinel', 'viewer', 'doc', 'd2') is True
    finally:
        session.close()


@pytest.mark.parametrize('backend', ['set', 'graph'])
def test_reserved_and_bad_types_relations_rejected(backend):
    session, be = _set_backend() if backend == 'set' else _graph_backend()
    try:
        # '*' is reserved: not a valid concrete name here ([user], no user:* declared)
        with pytest.raises(ValueError):
            be.add_tuple('...', 'user', '*', 'viewer', 'doc', 'd')
        # out-of-charset type / relation are rejected too
        with pytest.raises(ValueError):
            be.add_tuple('...', 'us er', 'alice', 'viewer', 'doc', 'd')
        with pytest.raises(ValueError):
            be.add_tuple('...', 'user', 'alice', 'view#er', 'doc', 'd')
    finally:
        session.close()


def test_identifier_predicate():
    assert is_valid_identifier('main.py')
    assert is_valid_identifier('service-account')
    assert is_valid_identifier('_all_attrs')
    assert not is_valid_identifier('a:b')
    assert not is_valid_identifier('a b')
    assert not is_valid_identifier('')
    assert not is_valid_identifier('*')          # bare validator: '*' is not a plain id
    assert not is_valid_identifier('x' * 257)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_valid_names_do_not_collide(ops):
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.bind)
    se = SetEngine(session, 'm', SCHEMA, ops=ops)
    for i, n in enumerate(VALID_NAMES):
        se.add_tuple('...', 'user', n, 'viewer', 'doc', f'd{i}')
    session.commit()
    for i, n in enumerate(VALID_NAMES):
        assert se.check('...', 'user', n, 'viewer', 'doc', f'd{i}') is True
        assert se.check('...', 'user', n, 'viewer', 'doc', f'd{(i + 1) % len(VALID_NAMES)}') is False
    assert len(se.interner.id_of) == 2 * len(VALID_NAMES)
    session.close()
