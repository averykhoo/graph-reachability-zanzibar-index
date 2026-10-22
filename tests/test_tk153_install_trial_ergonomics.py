"""TK153: the 0.0.5 install-trial ergonomics findings, pinned.

Map: ``docs/tk153-install-trial-ergonomics-2026-10-17.md`` (which finding reproduced
first-hand, and what landed). ASCII-only help text (F3) is pinned separately by
``tests/test_tk153_ascii_public_text.py``.

- **F17, one condition -> one exception type.** A store whose PERSISTED schema uses a shape
  this version refuses raises ``PersistedSchemaRefused`` from EVERY entry point, the set
  engine included (it raised ``SchemaMismatch`` for a rewritten text and the bare
  ``ShapeNoLongerAccepted`` for the old text or none). Controls: a fresh store id, and a
  refused text passed for a store whose stored text is fine, keep the parser's refusal.
- **F8.** ``DeltaProcessor`` is public in ``zanzibar.graphindex`` and
  ``MissingDeltaProcessor`` names that import; following the message works.
- **F9.** ``[team#member]`` with no ``type team`` reports the undeclared TYPE (DSL and
  JSON front ends); a declared type with an undeclared relation keeps the relation message.
- **F11.** A write to an undeclared relation leads with ``names an undeclared relation``
  on the store and both backends' admission gates.
- **F6.** ``RuleSet``, ``SchemaRecord`` and ``IndexCursor`` print short, field-naming
  reprs, also after a commit expired the row (it printed as ``SchemaRecord()``) and when a
  value cannot be read (``?``, never a raise from ``repr``).

Sabotage (2026-10-17, TK153 agent; runner ``.scratch/ultracode-2026-10-17/tk153-probes/
sabotage.py``, gitignored, so this docstring is the record). One asserted-unique anchor per
mutation, the file restored byte-for-byte and sha256-checked after each; this module only
(54 tests), ``-p no:cacheprovider``. Literal output, every one RED:

- SB1 ``engine.py::_refuse_persisted_shape`` returns at once: ``8 failed, 46 passed``
  (``[<shape>-SetEngine(id)]`` and ``[<shape>-SetEngine(id, old)]``, all four shapes).
- SB2 ``engine.py::_assert_schema_matches_record`` raises ``SchemaMismatch`` again for a
  refused stored text: ``4 failed, 50 passed`` (``[<shape>-SetEngine(id, rewritten)]``).
- SB3 ``from .processor import DeltaProcessor`` deleted from ``zanzibar/graphindex``:
  ``2 failed, 52 passed``; ``ImportError: cannot import name 'DeltaProcessor' from
  'zanzibar.graphindex'``.
- SB4 ``parser.py::_validate_ast_consistency``'s undeclared-type branch disabled
  (``if False:``): ``1 failed, 53 passed``; ``AssertionError: Regex pattern did not match``.
- SB5 ``syntax.py::no_restriction_message``'s undeclared lead disabled: ``1 failed,
  53 passed`` (``test_f11_undeclared_relation_write_says_so``).
- SB6 ``SchemaRecord.__repr__`` deleted: ``2 failed, 52 passed``; ``assert 'SchemaRecord()'
  not in '(SchemaReco... relations))'`` and ``assert 'SchemaRecord()' ==
  'SchemaRecord...ard_shapes=?)'``.

Review fixes (2026-10-17, TK153 review agent; runner ``.scratch/ultracode-2026-10-17/
tk153-review2-sabotage.py``, same discipline, ``-k`` on the new tests). Literal output:

- SB10 ``syntax.py::declared_relations`` ignores ``declared_types`` (``types = set()``):
  ``1 failed, 65 deselected``; ``AssertionError: tuple folder:f#member@user:a#... names an
  undeclared relation folder#member: type 'folder' is not declared in the schema``.
- SB11 ``parser.py::_validate_ast_consistency`` renders ``f'{r.type}#{r.predicate}'``
  again instead of ``_render_restriction(r)``: ``2 failed, 64 deselected``; ``Actual
  message: "doc#v: restriction [team#member] names an undeclared type 'team', ..."`` and
  ``'doc#v: restriction [team#member] names an undeclared relation team#member'``.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
import zanzibar.schema as zschema
import zanzibar.store as zstore
from zanzibar.schema import (AdmissionRejected, Entity, RelationalTriple, SchemaError,
                             ShapeNoLongerAccepted, parse_openfga_json, parse_openfga_schema)
from zanzibar.setengine import SetEngine
from zanzibar.store import (PersistedSchemaRefused, SchemaRecord, Store, build_index,
                            save_schema)
from zanzibar.store.schema_io import ensure_schema, open_set_engine
from tests.test_tk137_persisted_schema_refused import CASES


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk153.db").as_posix()}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _persist_old(engine, store_id: str, text: str) -> None:
    with Session(engine) as s:
        s.add(SchemaRecord(store_id=store_id, schema_text=text, object_wildcard_shapes='[]'))
        s.commit()


# ------------------------------------------------------------------------------ F17

#: entry point -> call(session, store_id, old_text, rewritten_text)
ENTRY_POINTS = {
    'Store(id)': lambda s, i, old, new: Store(s, i),
    'Store(id, old)': lambda s, i, old, new: Store(s, i, schema=old),
    'Store(id, rewritten)': lambda s, i, old, new: Store(s, i, schema=new),
    'open_set_engine': lambda s, i, old, new: open_set_engine(s, i),
    'SetEngine(id)': lambda s, i, old, new: SetEngine(s, i),
    'SetEngine(id, old)': lambda s, i, old, new: SetEngine(s, i, old),
    'SetEngine(id, rewritten)': lambda s, i, old, new: SetEngine(s, i, new),
    'save_schema(rewritten)': lambda s, i, old, new: save_schema(s, i, new),
    'save_schema(old)': lambda s, i, old, new: save_schema(s, i, old),
    'ensure_schema(rewritten)': lambda s, i, old, new: ensure_schema(s, i, new),
    'ensure_schema(old)': lambda s, i, old, new: ensure_schema(s, i, old),
    'build_index(other id)': lambda s, i, old, new: build_index(s, i, index_store_id='other'),
}


@pytest.mark.parametrize('entry', sorted(ENTRY_POINTS))
@pytest.mark.parametrize('name', sorted(CASES))
def test_every_entry_point_raises_persisted_schema_refused(engine, name, entry):
    """Sabotage (2026-10-17, review fix): moving ``schema_io.py::_schema_difference``'s
    identical-text ``return None`` back above the stored-text parse gave '8 failed, 40
    passed' (``-k entry_point``), every ``save_schema(old)`` / ``ensure_schema(old)`` row:
    'Failed: DID NOT RAISE PersistedSchemaRefused', the save_schema rows raising the bare
    'ShapeNoLongerAccepted: unsupported schema version line 'schema 1.2' ...'."""
    old, _refusal, rewrite, fixed = CASES[name]
    _persist_old(engine, 'old', old)
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            ENTRY_POINTS[entry](s, 'old', old, fixed)
    exc = info.value
    assert type(exc) is PersistedSchemaRefused
    assert exc.store_id == 'old' and rewrite in exc.instead
    assert isinstance(exc.__cause__, ShapeNoLongerAccepted)
    assert 'NEW store id' in str(exc)


def test_the_class_is_one_object_everywhere():
    assert zanzibar.PersistedSchemaRefused is zschema.PersistedSchemaRefused
    assert zstore.PersistedSchemaRefused is zschema.PersistedSchemaRefused
    assert 'PersistedSchemaRefused' in zanzibar.__all__   # TK164: the one public home
    assert issubclass(PersistedSchemaRefused, (zanzibar.ZanzibarError, ValueError))


@pytest.mark.parametrize('name', sorted(CASES))
def test_control_a_fresh_store_keeps_the_parser_refusal(engine, name):
    """Nothing stored, nothing to migrate: the caller's own text is the problem."""
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            SetEngine(s, 'fresh', CASES[name][0])
    assert not isinstance(info.value, PersistedSchemaRefused)


def test_control_a_refused_text_over_a_good_stored_schema_is_the_callers(engine):
    """The stored text parses; the text passed here does not: the parser's refusal, not a
    version break of the store."""
    old, _r, _w, fixed = CASES['S7-but-not-beside-or']
    with Session(engine) as s:
        Store(s, 'good', schema=fixed)
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            SetEngine(s, 'good', old)
    assert not isinstance(info.value, PersistedSchemaRefused)


# ------------------------------------------------------------------------------- F8

BOOL = ('type user\ntype doc\n  relations\n    define banned: [user]\n'
        '    define viewer: [user] but not banned\n')


def test_f8_delta_processor_is_public():
    from zanzibar.graphindex import DeltaProcessor
    from zanzibar.graphindex.processor import DeltaProcessor as Defined
    assert DeltaProcessor is Defined
    assert 'DeltaProcessor' in zanzibar.graphindex.__all__


def test_f8_the_advice_works(engine):
    """Do exactly what ``MissingDeltaProcessor`` says, importing from where it says."""
    from zanzibar.store.apply import advance_index
    from zanzibar.store.build import ensure_cursor
    from zanzibar.store.schema_io import open_graph_index
    with Session(engine) as s:
        save_schema(s, 'src', BOOL)
        s.commit()
        src = zstore.TupleSource(s, 'src')
        src.add('user:alice', 'viewer', 'doc:d')
        src.add('user:bob', 'viewer', 'doc:d')
        src.add('user:bob', 'banned', 'doc:d')
        s.commit()
        cursor = ensure_cursor(s, 'src', 'src')
        widx, ruleset = open_graph_index(s, 'src')
        with pytest.raises(zanzibar.MissingDeltaProcessor) as info:
            advance_index(s, cursor, widx, ruleset, None)
        msg = str(info.value)
        assert 'from zanzibar.graphindex import DeltaProcessor' in msg, msg
        namespace: dict = {}
        exec('from zanzibar.graphindex import DeltaProcessor', namespace)
        proc = namespace['DeltaProcessor'](widx, ruleset.compiled)
        assert advance_index(s, cursor, widx, ruleset, proc) == 3
        s.commit()
        assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd') is True
        assert widx.check('...', 'user', 'bob', 'viewer', 'doc', 'd') is False


# ------------------------------------------------------------------------------- F9

def test_f9_undeclared_userset_type_is_named_as_a_type():
    text = 'type user\ntype doc\n  relations\n    define v: [user, team#member]\n'
    with pytest.raises(SchemaError, match=r"\[team#member\] names an undeclared type 'team'") as info:
        parse_openfga_schema(text)
    msg = str(info.value)
    assert 'undeclared relation' in msg            # the rejection witness genswarm matches
    assert not isinstance(info.value, ShapeNoLongerAccepted)  # refused before 0.0.4 too
    model = {'schema_version': '1.1', 'type_definitions': [
        {'type': 'user'},
        {'type': 'doc', 'relations': {'v': {'this': {}}},
         'metadata': {'relations': {'v': {'directly_related_user_types': [
             {'type': 'user'}, {'type': 'team', 'relation': 'member'}]}}}}]}
    with pytest.raises(SchemaError, match="names an undeclared type 'team'"):
        parse_openfga_json(model)


def test_f9_control_declared_type_undeclared_relation_keeps_the_relation_message():
    text = 'type user\ntype team\ntype doc\n  relations\n    define v: [user, team#member]\n'
    with pytest.raises(SchemaError) as info:
        parse_openfga_schema(text)
    assert 'names an undeclared relation team#member' in str(info.value)
    assert 'undeclared type' not in str(info.value)


@pytest.mark.parametrize('types, expected', [
    ('type user\n', r"restriction \[team:\*#member\] names an undeclared type 'team'"),
    ('type user\ntype team\n', r"restriction \[team:\*#member\] names an undeclared "
                               r"relation team#member"),
])
def test_f9_wildcard_userset_restriction_keeps_its_star(types, expected):
    """TK153 review (2026-10-17): both dangling-userset messages rendered
    ``[team:*#member]`` as ``[team#member]``, dropping the ``:*``; they now share
    ``syntax.py::_render_restriction`` with the admission messages."""
    text = types + 'type doc\n  relations\n    define v: [user, team:*#member]\n'
    with pytest.raises(SchemaError, match=expected):
        parse_openfga_schema(text)


# ------------------------------------------------------------------------------ F11

SIMPLE = 'type user\ntype doc\n  relations\n    define viewer: [user]\n    define owner: viewer\n'


def test_f11_undeclared_relation_write_says_so(engine):
    with Session(engine) as s:
        st = Store(s, 'w', schema=SIMPLE)
        with pytest.raises(AdmissionRejected) as info:
            st.add_tuple('user:a', 'vewer', 'doc:d')
    msg = str(info.value)
    assert 'names an undeclared relation doc#vewer' in msg, msg
    assert "did you mean 'viewer'" in msg
    assert 'matches no declared type restriction' not in msg
    with Session(engine) as s:   # a declared but computed-only relation keeps its lead
        st = Store(s, 'w')
        with pytest.raises(AdmissionRejected, match='matches no declared type restriction '
                                                    'for doc#owner'):
            st.add_tuple('user:a', 'owner', 'doc:d')


RELATION_LESS = ('model\n  schema 1.1\ntype user\ntype folder\ntype doc\n  relations\n'
                 '    define viewer: [user]\n')


def test_f11_relation_less_declared_type_is_not_called_undeclared(engine):
    """TK153 review (2026-10-17): ``type folder`` with no relations, named by no
    restriction, leaves no trace in a ``SchemaAST``, so a write on ``folder`` was told
    "type 'folder' is not declared in the schema" -- false. The text parse's type set now
    reaches ``syntax.py::declared_relations`` on both backends, and the reason is "declares
    no relations". The two backends' messages stay identical."""
    reason = ": type 'folder' declares no relations"
    lead = 'names an undeclared relation folder#member'
    msgs = []
    with Session(engine) as s:
        with pytest.raises(AdmissionRejected) as info:
            SetEngine(s, 'raw', RELATION_LESS).add_tuple('...', 'user', 'a', 'member',
                                                          'folder', 'f')
        msgs.append(str(info.value))
        s.rollback()
    rs = parse_openfga_schema(RELATION_LESS)
    with pytest.raises(AdmissionRejected) as info:
        list(rs.apply(RelationalTriple(Entity('user', 'a'), 'member', Entity('folder', 'f'),
                                       Ellipsis)))
    msgs.append(str(info.value))
    with Session(engine) as s:
        with pytest.raises(AdmissionRejected) as info:
            Store(s, 'st', schema=RELATION_LESS).add_tuple('user:a', 'member', 'folder:f')
        msgs.append(str(info.value))
    for m in msgs:
        assert lead in m and m.endswith(reason), m
        assert 'not declared in the schema' not in m, m
    assert msgs[0] == msgs[1], msgs          # one helper, so both backends say the same
    # control: a type no ``type`` line declares keeps the "not declared" reason
    with pytest.raises(AdmissionRejected, match="type 'fodler' is not declared in the "
                                                "schema; did you mean 'folder'?"):
        list(rs.apply(RelationalTriple(Entity('user', 'a'), 'member', Entity('fodler', 'f'),
                                       Ellipsis)))


# ------------------------------------------------------------------------------- F6

def test_f6_save_schema_return_value_prints_short(engine):
    with Session(engine) as s:
        result = save_schema(s, 'r', SIMPLE)
        s.commit()                                   # expires the row
        text = repr(result)
    assert 'SchemaRecord()' not in text
    assert "SchemaRecord(store_id='r', schema_text=<" in text
    assert 'RuleSet(' in text and 'Filter(' not in text
    assert len(text) < 200, text


def test_f6_index_cursor_and_unreadable_rows(engine):
    from zanzibar.store.build import ensure_cursor
    with Session(engine) as s:
        save_schema(s, 'c', SIMPLE)
        cursor = ensure_cursor(s, 'c', 'c')
        s.commit()
        assert repr(cursor) == ("IndexCursor(index_store_id='c', source_store_id='c', "
                                "applied_log_id=0, stalled_after=None)")
        row = s.get(SchemaRecord, 'c')
        s.commit()                                   # expired again ...
    assert repr(row) == ('SchemaRecord(store_id=?, schema_text=?, '
                         'object_wildcard_shapes=?)')  # ... and detached: '?', no raise


def test_f6_repr_never_flushes_the_session(engine):
    """Printing a committed (expired) row reloads it, but must not flush pending writes:
    a conflicting pending row used to make ``repr`` swallow the IntegrityError (fields
    '?') and leave the session needing a rollback.

    Sabotage (2026-10-17, review fix): ``models.py::_row_repr``'s guard replaced by
    ``contextlib.nullcontext()`` gave '1 failed' for this test: 'assert 0 == 1' on the
    pending-count check (the repr had flushed the pending ``SchemaRecord('b')``)."""
    with Session(engine) as s:
        row, _ = save_schema(s, 'a', SIMPLE)
        s.commit()                                   # expires the row
        s.add(SchemaRecord(store_id='b', schema_text=SIMPLE, object_wildcard_shapes='[]'))
        assert len(s.new) == 1
        assert repr(row).startswith("SchemaRecord(store_id='a', schema_text=<")
        assert len(s.new) == 1                       # still pending: repr did not flush
        s.rollback()
    with Session(engine) as s:
        row = s.get(SchemaRecord, 'a')
        s.commit()
        clash = SchemaRecord(store_id='a', schema_text='x', object_wildcard_shapes='[]')
        s.add(clash)
        assert repr(row).startswith("SchemaRecord(store_id='a', schema_text=<")
        s.expunge(clash)                             # the caller's own conflict, removed
        assert s.get(SchemaRecord, 'a') is row       # the session is still usable


def test_f6_ruleset_repr_counts_instead_of_listing():
    rs = parse_openfga_schema(BOOL)
    assert repr(rs) == (f'RuleSet({len(rs.rules_and_filters)} rules and filters, '
                        f'{len(rs.compiled.plans)} boolean relations)')
    assert len(rs.compiled.plans) >= 1
