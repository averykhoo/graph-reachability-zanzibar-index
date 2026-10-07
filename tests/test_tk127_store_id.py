"""TK127 follow-up -- a store id must be a non-empty ``str``, refused at construction.

FOUND by the TK127 review of TK125 (2026-10-08, ``.scratch/tk127-2026-10-08/
tmp-small-fixes/probe_storeid.py``, gitignored -- this docstring is the tracked record).
TK125 made every tuple field of a write a ``str``; the store id, which is a write field of
every persisted row, was never validated. Re-run first-hand on the TK125 tree::

    None RAISED sqlalchemy.exc.IntegrityError (sqlite3.IntegrityError) NOT NULL constraint
         failed: zanzibar_schema_record.store_id
    int OK True
    empty OK True
    bytes OK True
    space OK True

i.e. ``ConnectedStore(s, None, schema=S)`` leaked the same raw ``IntegrityError`` class as
trial finding B3, and ``5`` / ``b'x'`` / ``''`` / ``' '`` bootstrapped a store and served
writes under an id no caller could have meant.

DECISION (2026-10-08): ``zanzibar.schema.errors.validate_store_id`` refuses anything but a
``str`` with a non-whitespace character, raising ``AdmissionRejected`` (``invalid store_id
...``, the TK125 message form) BEFORE any statement touches the database. It is called by
every constructor that takes a store id and can persist under it -- ``ConnectedStore``,
``TupleSource``, ``SetEngine``, ``ReachabilityIndex`` -- and by ``save_schema``, the one
function that inserts the ``SchemaRecord``. The identifier CHARSET is deliberately NOT
applied: a store id is the caller's key (``tenant:acme``, a UUID), never a tuple field, and
narrowing it would break stores that work today (the accept controls below pin that).

PRE-FIX (TK125 tree, before ``validate_store_id`` existed), literal summary
(``pytest tests/test_tk127_store_id.py -q -rf --tb=line``)::

    61 failed, 4 passed, 9 warnings in 4.89s
    44 x  Failed: DID NOT RAISE AdmissionRejected   (reachability / setengine / save_schema /
          cs-* for int, float, bool, bytes, '', ' ', tab-newline; build_index)
     6 x  sqlalchemy.exc.ProgrammingError: (sqlite3.ProgrammingError) Error binding
          parameter 1: type 'tuple' is not supported
     3 x  sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint
          failed: zanzibar_schema_record.store_id
     8 x  KeyError: 'store None has no persisted schema' (TupleSource; likewise 'store 5 ...',
          "store b'x' ...", "store '' ...", one per bad value except the tuple)

(the 4 passes are the ``GOOD`` accept controls.)

SABOTAGE on the fixed tree (``.scratch/tk127-2026-10-08/fix-tk127-sab-storeid.py``, anchor
asserted, sha256-restored), literal summary lines::

    A  validate_store_id allows blanks (isinstance only)   20 failed, 45 passed in 6.34s
       (every '', ' ', tab-newline case on all six entry points, + build_index[space|tab-newline])
    B  ReachabilityIndex's call dropped                      9 failed, 56 passed in 6.90s
    C  save_schema's call dropped                           10 failed, 55 passed in 6.90s
       (the nine save_schema cases + build_index[tuple])
    D  ConnectedStore's own call dropped                     2 failed, 63 passed in 7.15s
       (cs-sync/async-tuple: the open-time lock probe binds the id before anything else;
        every other value is still caught one layer down -- the layers are deliberate)

Fixed tree: ``65 passed in 7.46s``.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar.connectedstore import (
    ConnectedStore, SchemaRecord, TupleLog, TupleSource, build_index, save_schema,
)
from zanzibar.graphindex import ReachabilityIndex, Store
from zanzibar.schema import AdmissionRejected
from zanzibar.setengine import RelationTuple, SetEngine

SCHEMA = 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n'

BAD = {
    'None': None,
    'int': 5,
    'float': 1.5,
    'bool': True,
    'bytes': b'x',
    'empty': '',
    'space': ' ',
    'tab-newline': '\t\n',
    'tuple': ('x',),
}

#: Accepted on purpose: a store id is NOT held to the identifier charset.
GOOD = ['x', 'tenant:acme', 'store with spaces', '6f1c2a9e-0b7d-4c1e-9f3a-2d5b8e7c4a10']


def _engine(tmp_path):
    engine = create_engine(f'sqlite:///{(tmp_path / "sid.db").as_posix()}')
    SQLModel.metadata.create_all(engine)
    return engine


def _nothing_persisted(engine) -> None:
    with Session(engine) as s:
        for model in (SchemaRecord, TupleLog, RelationTuple, Store):
            assert s.exec(select(model)).all() == [], model.__name__


ENTRY = {
    'cs-sync': lambda s, sid: ConnectedStore(s, sid, schema=SCHEMA),
    'cs-async': lambda s, sid: ConnectedStore(s, sid, schema=SCHEMA, sync=False),
    'tuplesource': lambda s, sid: TupleSource(s, sid),
    'setengine': lambda s, sid: SetEngine(s, sid, SCHEMA),
    'reachability': lambda s, sid: ReachabilityIndex(s, sid),
    'save_schema': lambda s, sid: save_schema(s, sid, SCHEMA),
}


@pytest.mark.parametrize('label', sorted(BAD))
@pytest.mark.parametrize('entry', sorted(ENTRY))
def test_bad_store_id_is_refused_before_any_state(tmp_path, entry, label):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        with pytest.raises(AdmissionRejected, match=r'invalid store_id'):
            ENTRY[entry](s, BAD[label])
        s.commit()  # commit, not rollback: whatever the refusal left behind would land
        _nothing_persisted(engine)
        # the same session is usable afterwards, under a real id
        cs = ConnectedStore(s, 'ok', schema=SCHEMA)
        cs.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True


@pytest.mark.parametrize('label', sorted(k for k, v in BAD.items() if v))
def test_build_index_refuses_a_bad_index_store_id(tmp_path, label):
    """``build_index`` reaches ``ReachabilityIndex`` / ``save_schema`` with the index id.
    Falsy values are excluded: ``index_store_id or source_store_id`` documents them as
    "index in place", which is a legitimate call."""
    engine = _engine(tmp_path)
    with Session(engine) as s:
        ConnectedStore(s, 'src', schema=SCHEMA, sync=False).add_tuple(
            '...', 'user', 'alice', 'viewer', 'doc', 'd1')
        s.commit()
    with Session(engine) as s:
        with pytest.raises(AdmissionRejected, match=r'invalid store_id'):
            build_index(s, 'src', index_store_id=BAD[label])
        s.rollback()
    with Session(engine) as s:
        assert [r.store_id for r in s.exec(select(SchemaRecord)).all()] == ['src']


@pytest.mark.parametrize('sid', GOOD)
def test_any_non_blank_str_store_id_still_works(tmp_path, sid):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        cs = ConnectedStore(s, sid, schema=SCHEMA)
        cs.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        s.commit()
    with Session(engine) as s:
        cs = ConnectedStore(s, sid)
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
        assert cs.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False
