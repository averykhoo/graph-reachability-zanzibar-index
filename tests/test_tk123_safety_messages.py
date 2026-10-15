"""TK123 items 9-13, 17, 18 (2026-10-15): keyword-only ids, one predicate spelling,
clean sessions, validated tokens, ``StoreNotFound``, a stall that names its row, and
admission / schema-mismatch messages that say what is wrong.

Plan and decisions: ``docs/tk123-api-review-2026-10-14.md`` § S2 item 9 and § S3.

SABOTAGES (2026-10-15, ``.scratch/tk123/sab918.py``: one anchor replaced, count asserted
== 1, this module run with ``-k``, file restored and sha256-checked). Literal lines::

    S10 Store._write's _require_clean_session call -> pass
        rc=1 | 1 failed, 2 passed, 34 deselected | Failed: DID NOT RAISE ValueError
    S11 token_diagnosis store check -> `if False:`
        rc=1 | 1 failed, 36 deselected | AssertionError: Regex pattern did not match.
             Expected regex: "Token 3 was returned by a write to store 'b', not 'a'"
    S12 Store.__init__'s except-arm session.rollback() deleted
        rc=1 | 1 failed, 36 deselected | sqlite3.OperationalError: database is locked
    S13 advance_index's _attach_failing_row call -> pass
        rc=1 | 1 failed, 36 deselected | AttributeError: 'PathCountExceeded' object has
             no attribute 'failing_log_row'
    S17 no_restriction_reason -> always ''
        rc=1 | 4 failed, 33 deselected | assert False (endswith "type 'dok' is not
             declared in the schema; did you mean 'doc'?")
    S18 first_schema_difference compares raw expressions (no _canonical_expr)
        rc=1 | 1 failed, 36 deselected | SchemaMismatch: explicit schema for store 'st'
             disagrees with its persisted schema, first at doc#viewer
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

import zanzibar
from zanzibar.schema import AdmissionRejected, parse_openfga_schema
from zanzibar.schema.syntax import first_schema_difference
from zanzibar.schema import parse_schema_ast
from zanzibar.setengine import SetEngine
from zanzibar.setengine.models import RelationTuple
from zanzibar.store import (SchemaMismatch, StaleRead, Store, StoreNotFound,
                            TablesNotCreated, TupleSource, build_index, rebuild_index)
from zanzibar.store.models import TupleLog

SCHEMA = '''model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define owner: [user]
    define viewer: [user, group#member] or owner
    define can_read: viewer
'''


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk123.db").as_posix()}',
                        connect_args={'timeout': 0.2})
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def store(engine):
    with Session(engine) as s:
        yield Store(s, 'st', schema=SCHEMA)


# --------------------------------------------------------------------------- item 9

@pytest.mark.parametrize('fn', [build_index, rebuild_index])
def test_index_store_id_is_keyword_only(fn, engine):
    with Session(engine) as s:
        with pytest.raises(TypeError, match='positional'):
            fn(s, 'src', 'idx')


@pytest.mark.parametrize('value, level', [(0, 'off'), (1, 'full'), (True, 'full'),
                                          (False, 'off'), ('fixpoint', 'fixpoint')])
def test_paranoia_accepts_the_documented_values(value, level):
    from zanzibar.graphindex.invariants import normalize_paranoia_level
    assert normalize_paranoia_level(value) == level


@pytest.mark.parametrize('value', [2, -1, 1.0, 'loud'])
def test_paranoia_refuses_anything_else(value):
    from zanzibar.graphindex.invariants import normalize_paranoia_level
    with pytest.raises(ValueError, match='paranoia'):
        normalize_paranoia_level(value)


def test_store_paranoia_docstring_names_every_level():
    doc = Store.__init__.__doc__
    for level in ("'off'", "'residue'", "'full'", "'fixpoint'"):
        assert level in doc, level


_SIX = ('user', 'alice', 'owner', 'doc', 'd1')


def test_ellipsis_predicate_is_refused_on_store_entries(store):
    with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
        store.add_tuple(..., *_SIX)
    store.add_tuple('...', *_SIX)
    with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
        store.remove_tuple(..., *_SIX)
    with pytest.raises(TypeError, match=r"string '\.\.\.'"):
        store.check(..., *_SIX)
    with pytest.raises(TypeError, match=r"string '\.\.\.'"):
        store.lookup(..., 'user', 'alice')
    assert store.check('...', *_SIX) is True


def test_ellipsis_predicate_is_refused_on_tuplesource_and_setengine(engine):
    with Session(engine) as s:
        Store(s, 'st', schema=SCHEMA)
        src = TupleSource(s, 'st')
        with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
            src.add(..., *_SIX)
        with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
            src.remove(..., *_SIX)
        with pytest.raises(TypeError, match=r"string '\.\.\.'"):
            src.check(..., *_SIX)
        s.rollback()
        se = SetEngine(s, 'free', SCHEMA)
        with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
            se.add_tuple(..., *_SIX)
        with pytest.raises(AdmissionRejected, match=r"string '\.\.\.'"):
            se.remove_tuple(..., *_SIX)
        with pytest.raises(TypeError, match=r"string '\.\.\.'"):
            se.check(..., *_SIX)
        with pytest.raises(TypeError, match=r"string '\.\.\.'"):
            se.lookup(..., 'user', 'alice')
        # None-on-read leniency is unchanged (the TK125 pin): it reads as bare
        assert se.check(None, *_SIX) is False


def test_setengine_reads_the_schema_of_a_store(engine):
    with Session(engine) as s:
        Store(s, 'st', schema=SCHEMA).add_tuple('user:alice', 'owner', 'doc:d1')
        se = SetEngine(s, 'st')
        assert se.check('...', 'user', 'alice', 'can_read', 'doc', 'd1') is True
        with pytest.raises(TypeError, match=r"needs schema=.*Store\(session, 'nope'"):
            SetEngine(s, 'nope')


# --------------------------------------------------------------------------- item 10

@pytest.mark.parametrize('surface', ['open', 'write', 'refresh'])
def test_a_dirty_session_is_refused_and_its_pending_row_survives(engine, surface):
    with Session(engine) as s:
        if surface != 'open':
            st = Store(s, 'st', schema=SCHEMA)
        pending = RelationTuple(store_id='other', subject_predicate='...',
                                subject_type='user', subject_name='p', relation='r',
                                object_type='t', object_name='n')
        s.add(pending)
        with pytest.raises(ValueError, match='pending changes'):
            if surface == 'open':
                Store(s, 'st', schema=SCHEMA)
            elif surface == 'write':
                st.add_tuple('user:alice', 'owner', 'doc:d1')
            else:
                st.refresh()
        assert pending in s.new          # neither committed nor discarded
        s.rollback()
    with Session(engine) as s:
        assert s.exec(select(RelationTuple).where(RelationTuple.store_id == 'other')).all() == []


# --------------------------------------------------------------------------- item 11

@pytest.mark.parametrize('bad, exc', [(True, TypeError), ('3', TypeError),
                                      (1.0, TypeError), (-1, ValueError)])
def test_at_least_is_validated(store, bad, exc):
    for call in (lambda: store.check('user:alice', 'owner', 'doc:d1', at_least=bad),
                 lambda: store.lookup('user:alice', at_least=bad),
                 lambda: store.lookup_reverse('owner', 'doc:d1', at_least=bad),
                 lambda: store.source.check('user:alice', 'owner', 'doc:d1',
                                            at_least=bad)):
        with pytest.raises(exc, match='at_least'):
            call()


def test_a_foreign_token_names_the_store_that_issued_it(engine):
    with Session(engine) as s:
        a = Store(s, 'a', schema=SCHEMA)
        a.add_tuple('user:alice', 'owner', 'doc:d1')
    with Session(engine) as s:
        b = Store(s, 'b', schema=SCHEMA)
        b.add_tuple('user:bob', 'owner', 'doc:d1')
        token_b = b.add_tuple('user:carol', 'owner', 'doc:d1')
    with Session(engine) as s:
        a = Store(s, 'a', schema=SCHEMA)
        with pytest.raises(StaleRead, match=f"Token {token_b} was returned by a write to "
                                            f"store 'b', not 'a'"):
            a.check('user:alice', 'owner', 'doc:d1', at_least=token_b)


def test_a_future_token_is_not_called_never_issued(store):
    token = store.add_tuple('user:alice', 'owner', 'doc:d1')
    with pytest.raises(StaleRead, match=r"past the newest log id this session can see "
                                        rf"\({token}\): it was not issued yet, or it was "
                                        r"committed after"):
        store.check('user:alice', 'owner', 'doc:d1', at_least=token + 10)
    with pytest.raises(zanzibar.LookupNotFresh, match='past the newest log id'):
        store.lookup('user:alice', at_least=token + 10)


# --------------------------------------------------------------------------- item 12

def test_store_not_found_is_a_keyerror_with_a_hint(engine):
    with Session(engine) as s:
        with pytest.raises(StoreNotFound) as ei:
            Store(s, 'nope')
    e = ei.value
    assert isinstance(e, KeyError) and isinstance(e, zanzibar.ZanzibarError)
    assert e.store_id == 'nope'
    # its own __str__: not KeyError's repr-quoted message
    assert str(e).startswith("store 'nope' has no persisted schema")
    assert "Store(session, 'nope', schema=...)" in str(e)


def test_store_not_found_releases_the_write_lock(engine):
    s1 = Session(engine)
    try:
        with pytest.raises(StoreNotFound):
            Store(s1, 'nope')
        # s1 is still open: had it kept its write lock, this write would be locked out
        with Session(engine) as s2:
            Store(s2, 'other', schema=SCHEMA).add_tuple('user:alice', 'owner', 'doc:d1')
    finally:
        s1.close()


def test_tuplesource_not_found_rolls_back(engine):
    with Session(engine) as s:
        with pytest.raises(StoreNotFound):
            TupleSource(s, 'nope')
        assert not s.in_transaction()


# --------------------------------------------------------------------------- item 13

STALL_SCHEMA = '''model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
'''


def test_a_stall_names_the_failing_log_row_and_its_tuple(engine, monkeypatch):
    import zanzibar.graphindex.core as core
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 3)
    with Session(engine) as s:
        st = Store(s, 'st', schema=STALL_SCHEMA, sync=False)
        st.add_tuple('user:u', 'member', 'group:L0')
        # two diamond layers: 4 paths from u to L2, over the (patched) bound of 3
        for i in range(2):
            for mid in ('A', 'B'):
                st.add_tuple(f'group:L{i}#member', 'member', f'group:{mid}{i}')
                last = st.add_tuple(f'group:{mid}{i}#member', 'member', f'group:L{i + 1}')
        with pytest.raises(core.PathCountExceeded) as ei:
            st.catch_up(batch=1)
        msg = str(ei.value)
        assert 'distinct derivation paths' in msg
        assert 'user:u' in msg and 'group:L2#member' in msg      # rendered, not row ids
        assert ei.value.failing_log_row == (last, 'ADD group:B1#member member group:L2')
        assert any(f'log row {last}' in n for n in ei.value.__notes__)
        assert st.stall_error.startswith(
            f'applied through {last - 1}; failing row {last} '
            f'(ADD group:B1#member member group:L2): PathCountExceeded')


# --------------------------------------------------------------------------- item 17

@pytest.mark.parametrize('tup, reason', [
    (('...', 'user', 'alice', 'viewer', 'dok', 'd1'),
     "type 'dok' is not declared in the schema; did you mean 'doc'?"),
    (('...', 'user', 'alice', 'viewr', 'doc', 'd1'),
     "type 'doc' declares no relation 'viewr'; did you mean 'viewer'?"),
    (('...', 'user', 'alice', 'can_read', 'doc', 'd1'),
     'doc#can_read has no direct type restriction (it is computed from other relations), '
     'so tuples cannot be written to it'),
    (('...', 'group', 'g', 'owner', 'doc', 'd1'), 'it admits only user'),
])
def test_admission_refusal_explains_itself(engine, tup, reason):
    with Session(engine) as s:
        se = SetEngine(s, 'free', SCHEMA)
        with pytest.raises(AdmissionRejected, match='matches no declared type restriction') as e_set:
            se._validate(tup[0], *tup[1:], pairs=[])
        rs = parse_openfga_schema(SCHEMA)
        from zanzibar.schema import Entity, RelationalTriple
        triple = RelationalTriple(Entity(tup[1], tup[2]), tup[3], Entity(tup[4], tup[5]),
                                  Ellipsis)
        with pytest.raises(AdmissionRejected, match='matches no declared type restriction') as e_graph:
            list(rs.apply(triple))
    # one helper, so both backends give the same reason
    assert str(e_set.value).endswith(reason)
    assert str(e_graph.value).endswith(reason)


def test_a_type_name_string_in_a_name_field_gets_a_split_hint(store):
    with pytest.raises(AdmissionRejected, match=r"invalid object_type 'doc:d1'.*looks like "
                                                r"'type:name'"):
        store.add_tuple('...', 'user', 'alice', 'owner', 'doc:d1', 'x')


# --------------------------------------------------------------------------- item 18

def test_reordered_restrictions_reopen(engine):
    with Session(engine) as s:
        Store(s, 'st', schema=SCHEMA)
    reordered = SCHEMA.replace('[user, group#member] or owner', '[group#member, user] or owner')
    assert reordered != SCHEMA
    with Session(engine) as s:
        Store(s, 'st', schema=reordered)
        SetEngine(s, 'st', reordered)


def test_a_schema_mismatch_names_the_relation(engine):
    with Session(engine) as s:
        Store(s, 'st', schema=SCHEMA)
    changed = SCHEMA.replace('define owner: [user]', 'define owner: [user, group#member]')
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch, match='disagrees with its persisted schema, '
                                                 'first at doc#owner'):
            Store(s, 'st', schema=changed)
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch, match='first at doc#owner'):
            SetEngine(s, 'st', changed)
    added = SCHEMA + '    define blocked: [user]\n'
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch, match=r'first at doc#blocked \(declared only in '
                                                 r'the schema passed here\)'):
            Store(s, 'st', schema=added)


def test_first_schema_difference_is_order_insensitive_only_for_restrictions():
    a = parse_schema_ast(SCHEMA)
    assert first_schema_difference(a, parse_schema_ast(
        SCHEMA.replace('[user, group#member] or owner', '[group#member, user] or owner'))) is None
    # union operand order is still a difference (not decided; the AST keeps it)
    assert first_schema_difference(a, parse_schema_ast(
        SCHEMA.replace('[user, group#member] or owner', 'owner or [user, group#member]'))
    ) == 'doc#viewer'


def test_missing_create_all_is_named(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "empty.db").as_posix()}')
    try:
        with Session(eng) as s:
            with pytest.raises(TablesNotCreated, match=r'SQLModel\.metadata\.create_all') as ei:
                Store(s, 'st', schema=SCHEMA)
            assert 'zanzibar_store' in ei.value.missing
            assert not s.in_transaction()
    finally:
        eng.dispose()
