"""TK136 -- reopening a store with ``schema=`` compares the PARSED schema, not the bytes.

Property guarded
----------------
``src/zanzibar/store/schema_io.py::ensure_schema`` (reached by
``Store(session, store_id, schema=...)`` and ``build_index``) accepts a passed
schema whose ``parse_schema_ast`` equals the persisted text's, and still raises
``SchemaMismatch`` for a different schema. The persisted text is never rewritten.

Accepted variants: trailing newline, CRLF line endings, a different indent, an added
comment, a ``model`` / ``schema 1.1`` header, reordered type blocks, reordered ``define``
lines. Refused: a changed, added or removed relation, a changed ``object_wildcard_shapes``.

Pinned as REFUSED although semantically equal: reordered operands of ``or`` and reordered
``[...]`` restrictions. The AST keeps that order (tuples), and a loud refusal on a reopen
is the safe side of the write-once contract; widening it needs a canonical form that the
oracle does not pin, so it is not done here.

Pre-fix evidence (0.0.3 install trial probe06, ``docs/pypi-trial-0.0.3-2026-10-08.md``;
re-run first-hand 2026-10-08b against ``src/``): identical text accepted; trailing newline,
CRLF, 4-space indent and an appended comment each refused with ``SchemaMismatch``.

SABOTAGE (2026-10-12, ``.scratch/tk136/sabotage.py``, gitignored -- this is the record):
the last line of ``schema_io.py::_same_schema`` replaced, anchor count asserted == 1, file
restored and sha256-checked; this module only. Literal summary lines::

    S1 byte compare (pre-fix)    rc=1 | 9 failed, 8 passed in 5.92s
       (8 accepted variants -- all but ``identical`` -- plus the unparseable-text case)
    S2 always equal (guard off)  rc=1 | 7 failed, 10 passed in 6.12s
       (all 6 refused variants plus the unparseable-text case)
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar.store import (Store, SchemaMismatch, SchemaRecord,
                                     ensure_schema, load_schema)

BASE = '''type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define owner: [user]
    define editor: [user] or owner
    define viewer: [user, group#member] or editor
'''

ACCEPTED = {
    'identical': BASE,
    'trailing_newline': BASE + '\n',
    'no_final_newline': BASE.rstrip('\n'),
    'crlf': BASE.replace('\n', '\r\n'),
    'indent_4': BASE.replace('  relations', '    relations').replace('    define', '        define'),
    'comment': '# the app schema\n' + BASE + '# end\n',
    'model_header': 'model\n  schema 1.1\n' + BASE,
    'type_order': '''type doc
  relations
    define owner: [user]
    define editor: [user] or owner
    define viewer: [user, group#member] or editor
type group
  relations
    define member: [user, group#member]
type user
''',
    'define_order': BASE.replace(
        '    define owner: [user]\n    define editor: [user] or owner\n',
        '    define editor: [user] or owner\n    define owner: [user]\n'),
}

REFUSED = {
    'changed_relation': BASE.replace('define owner: [user]', 'define owner: [user, group#member]'),
    'added_relation': BASE + '    define blocked: [user]\n',
    'removed_relation': BASE.replace('    define viewer: [user, group#member] or editor\n', ''),
    'renamed_relation': BASE.replace('define owner: [user]', 'define admin: [user]')
                            .replace('[user] or owner', '[user] or admin'),
    # semantically equal, but the AST keeps the order (module docstring)
    'or_operand_order': BASE.replace('[user] or owner', 'owner or [user]'),
    'restriction_order': BASE.replace('define viewer: [user, group#member]',
                                      'define viewer: [group#member, user]'),
}


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk136.db").as_posix()}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _bootstrap(engine):
    with Session(engine) as s:
        cs = Store(s, 'x', schema=BASE)
        cs.add_tuple('...', 'user', 'alice', 'owner', 'doc', 'd1')
        s.commit()


@pytest.mark.parametrize('name', sorted(ACCEPTED))
def test_reopen_with_an_equal_schema_is_accepted(engine, name):
    _bootstrap(engine)
    with Session(engine) as s:
        cs = Store(s, 'x', schema=ACCEPTED[name])
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
    with Session(engine) as s:
        # the persisted text is the source of truth and is never rewritten
        assert load_schema(s, 'x') == (BASE, frozenset())
        assert len(s.exec(select(SchemaRecord)).all()) == 1


@pytest.mark.parametrize('name', sorted(REFUSED))
def test_reopen_with_a_different_schema_is_refused(engine, name):
    _bootstrap(engine)
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch, match='disagrees with its persisted schema'):
            Store(s, 'x', schema=REFUSED[name])
    with Session(engine) as s:
        assert load_schema(s, 'x') == (BASE, frozenset())


def test_changed_wildcard_shapes_are_still_refused_with_equal_text(engine):
    _bootstrap(engine)
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch):
            ensure_schema(s, 'x', BASE + '\n', frozenset({('group', 'member')}))


def test_an_unparseable_passed_schema_raises_the_parse_error(engine):
    _bootstrap(engine)
    with Session(engine) as s:
        with pytest.raises(ValueError, match='unrecognized schema line'):
            ensure_schema(s, 'x', BASE + 'bogus line\n')
