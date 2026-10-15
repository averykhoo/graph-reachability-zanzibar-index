"""TK137 review challenge C10 (2026-10-14) -- a PERSISTED schema refused since TK137 says so.

Property guarded
----------------
Every open re-parses a store's persisted ``SchemaRecord.schema_text``, so a store that
zanzibar-index 0.0.4 or earlier saved with a shape TK137 now refuses (H1 ``schema 1.2``, H2
extra words on a header line, S7 unparenthesised ``but not``, S8 a restriction to an
undeclared type) stops opening. The error must read as a VERSION BREAK, not corruption: it is
``zanzibar.store.PersistedSchemaRefused``, it says the schema was saved by
zanzibar-index 0.0.4 or earlier using a shape this version refuses, quotes the parser's
refusal, and says how to rewrite it. Every parse site of persisted text is covered:

- ``Store(session, id)`` and ``Store(session, id, schema=<same text>)``
  (``schema_io.py::open_graph_index``),
- ``schema_io.py::open_set_engine`` (``TupleSource``'s open path),
- ``schema_io.py::ensure_schema`` with a different passed text (``_same_schema``),
- ``build_index(session, source, index_store_id=<other>)`` copying the SOURCE's text
  (``build.py::build_index``).

And it must NOT fire where it would mislead: a fresh schema the CALLER passes keeps the
parser's own refusal, and a persisted text failing a refusal OLDER than TK137 (which 0.0.4
could not have saved) keeps its plain ``ValueError``. The mechanism is a type, not message
matching: the four TK137 refusal sites raise ``zanzibar.schema.errors.ShapeRefusedSinceTK137``
(a ``ValueError``), and ``schema_io.py::_persisted_schema_parse`` converts only that.

A 0.0.4-era row is simulated by inserting the ``SchemaRecord`` directly, which is exactly
what ``save_schema`` wrote under 0.0.4 (text plus shapes JSON; the compiled schema is cache).
Each rewrite the message names is checked to open in a fresh store.

Map: ``docs/tk137-dsl-openfga-refusals-2026-10-14.md`` § challenge C10.

SABOTAGE (2026-10-14, fix-TK137 builder; gitignored ``.scratch/sabotage_c10.py``, so this
docstring is the tracked record). One asserted-unique anchor per mutation, file restored
byte-for-byte and sha256-checked; this module only (29 tests), ``-p no:cacheprovider``.
Literal tails, every one RED:

- SB1 ``_persisted_schema_parse`` catches nothing (``except KeyError``):
  ``rc=1 | 16 failed, 13 passed`` (the four conversion tests x four shapes).
- SB2 the ``open_graph_index`` wrapper removed: ``rc=1 | 4 failed, 25 passed``.
- SB3 the ``open_set_engine`` wrapper removed: ``rc=1 | 4 failed, 25 passed``.
- SB4 the ``_same_schema`` wrapper removed: ``rc=1 | 4 failed, 25 passed``.
- SB5 the ``build_index`` wrapper removed: ``rc=1 | 4 failed, 25 passed``.
- SB6 parser S8 raises plain ``ValueError`` again: ``rc=1 | 6 failed, 23 passed`` (every
  S8 id).
- SB7 CONTROL, the wrapper catches EVERY ``ValueError``: ``rc=1 | 1 failed, 28 passed``
  (the older-refusal control).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.store import (Store, PersistedSchemaRefused, SchemaRecord,
                                     build_index, ensure_schema, open_set_engine)
from zanzibar.schema import parse_schema_ast
from zanzibar.schema.errors import ShapeRefusedSinceTK137

BASE = '''type user
type doc
  relations
    define a: [user]
    define b: [user]
    define c: [user]
    define x: a or b
'''

#: name -> (persisted 0.0.4-era text, parser refusal fragment, rewrite fragment, the
#: rewritten text the message's advice produces).
CASES = {
    'H1-schema-1.2': ('model\n  schema 1.2\n' + BASE,
                      "unsupported schema version line 'schema 1.2'",
                      "change the line to 'schema 1.1'",
                      'model\n  schema 1.1\n' + BASE),
    'H2-relations-comment': (BASE.replace('  relations\n', '  relations # docs\n'),
                             "'relations' line with extra words",
                             'delete the extra words after the keyword',
                             BASE),
    'S7-but-not-beside-or': (BASE.replace('define x: a or b', 'define x: a or b but not c'),
                             "'but not' may not share a level with 'or'",
                             "'(a or b) but not (c or d)'",
                             BASE.replace('define x: a or b', 'define x: (a or b) but not c')),
    'S8-undeclared-type': (BASE.replace('define a: [user]', 'define a: [usr]'),
                           "undeclared type 'usr'",
                           "add a 'type usr' line",
                           'type usr\n' + BASE.replace('define a: [user]', 'define a: [usr]')),
}

VERSION_BREAK = 'saved by zanzibar-index 0.0.4 or earlier using a shape this version refuses'


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk137_c10.db").as_posix()}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _persist_as_0_0_4(engine, store_id: str, text: str) -> None:
    """What 0.0.4's ``save_schema`` left behind: the text and the shapes JSON, nothing
    compiled (it is cache)."""
    with Session(engine) as s:
        s.add(SchemaRecord(store_id=store_id, schema_text=text, object_wildcard_shapes='[]'))
        s.commit()


def _assert_version_break(exc: PersistedSchemaRefused, store_id: str, name: str) -> None:
    _text, refusal, rewrite, _fixed = CASES[name]
    msg = str(exc)
    assert f"store {store_id!r}" in msg
    assert VERSION_BREAK in msg
    assert refusal in msg  # the parser's refusal, quoted
    assert 'To rewrite: ' in msg and rewrite in msg
    assert 'NEW store id' in msg
    assert isinstance(exc, ValueError)
    assert isinstance(exc.__cause__, ShapeRefusedSinceTK137)
    assert exc.store_id == store_id and exc.instead == exc.refusal.instead


@pytest.mark.parametrize('name', sorted(CASES))
def test_each_tk137_site_raises_the_typed_refusal(name):
    """The four TK137 refusal sites raise ``ShapeRefusedSinceTK137`` carrying a rewrite; that
    type is what the store layer converts."""
    text, refusal, rewrite, fixed = CASES[name]
    with pytest.raises(ShapeRefusedSinceTK137) as info:
        parse_schema_ast(text)
    assert refusal in str(info.value) and rewrite in info.value.instead
    parse_schema_ast(fixed)  # the rewrite parses


@pytest.mark.parametrize('name', sorted(CASES))
def test_reopening_a_0_0_4_store_says_it_is_a_version_break(engine, name):
    text = CASES[name][0]
    _persist_as_0_0_4(engine, 'old', text)
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            Store(s, 'old')
    _assert_version_break(info.value, 'old', name)
    with Session(engine) as s:  # reopening with the identical text takes the same path
        with pytest.raises(PersistedSchemaRefused) as info:
            Store(s, 'old', schema=text)
    _assert_version_break(info.value, 'old', name)


@pytest.mark.parametrize('name', sorted(CASES))
def test_open_set_engine_says_it_is_a_version_break(engine, name):
    _persist_as_0_0_4(engine, 'old', CASES[name][0])
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            open_set_engine(s, 'old')
    _assert_version_break(info.value, 'old', name)


@pytest.mark.parametrize('name', sorted(CASES))
def test_ensure_schema_with_a_different_text_blames_the_stored_one(engine, name):
    """``_same_schema`` parses the STORED text before the passed one, so the stored break is
    named even when the caller passes a valid (here: the rewritten) schema."""
    _persist_as_0_0_4(engine, 'old', CASES[name][0])
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            ensure_schema(s, 'old', CASES[name][3])
    _assert_version_break(info.value, 'old', name)


@pytest.mark.parametrize('name', sorted(CASES))
def test_build_index_into_another_store_blames_the_source(engine, name):
    _persist_as_0_0_4(engine, 'old', CASES[name][0])
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            build_index(s, 'old', index_store_id='old-index')
    _assert_version_break(info.value, 'old', name)


@pytest.mark.parametrize('name', sorted(CASES))
def test_the_rewrite_opens_in_a_new_store(engine, name):
    """The message's advice works: the rewritten schema under a new store id opens."""
    with Session(engine) as s:
        Store(s, 'new', schema=CASES[name][3])
        s.commit()
    with Session(engine) as s:
        Store(s, 'new')


@pytest.mark.parametrize('name', sorted(CASES))
def test_a_fresh_schema_keeps_the_parser_refusal(engine, name):
    """Not persisted, so not a version break: the caller's own text keeps the parser's
    refusal and nothing is saved."""
    with Session(engine) as s:
        with pytest.raises(ShapeRefusedSinceTK137) as info:
            Store(s, 'fresh', schema=CASES[name][0])
    assert not isinstance(info.value, PersistedSchemaRefused)
    assert VERSION_BREAK not in str(info.value)
    with Session(engine) as s:
        assert s.get(SchemaRecord, 'fresh') is None


def test_an_older_refusal_of_a_persisted_text_is_not_called_a_version_break(engine):
    """CONTROL. A dangling reference (ASK-1, refused since 2026-09-26, before 0.0.4) cannot
    have been saved by 0.0.4, so it is not labelled as a 0.0.4 store: plain ``ValueError``."""
    _persist_as_0_0_4(engine, 'corrupt', BASE.replace('define x: a or b', 'define x: a or zz'))
    with Session(engine) as s:
        with pytest.raises(ValueError) as info:
            Store(s, 'corrupt')
    assert not isinstance(info.value, PersistedSchemaRefused)
    assert not isinstance(info.value, ShapeRefusedSinceTK137)
    assert VERSION_BREAK not in str(info.value)

