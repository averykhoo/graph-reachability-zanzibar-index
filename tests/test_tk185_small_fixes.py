"""TK185 (0.1.3 batch, items C4 / C3 / C6 / docs) -- small fixes from the 0.1.2 install trial.

The findings are in ``docs/pypi-trial-0.1.2-2026-11-01.md``; each was re-run first-hand
against ``src/`` before the fix (2026-11-20).

- **C4** ``object_wildcard_shapes=[["folder", "viewer"]]`` raised Python's own
  ``TypeError: unhashable type: 'list'``, naming neither the argument nor the entry. A
  2-item list of strings is now a pair (JSON-loaded config has lists); any other entry that
  cannot be a set member is a ``TypeError`` naming ``object_wildcard_shapes`` and the entry.
  A hashable non-pair (``'folder'``, ``('doc', 5)``) keeps its ``ShapeNoLongerAccepted``.
  Site: ``src/zanzibar/schema/argcheck.py::require_shapes``.
- **C3** ``ShapeNoLongerAccepted`` for an ``object_wildcard_shapes`` entry had the rewrite
  only in ``e.instead``; ``str(e)`` now ends with ``". To rewrite: " + e.instead``, and
  ``PersistedSchemaRefused`` still quotes it once. Sites: the three raises in
  ``src/zanzibar/schema/compiler.py`` pass ``rewrite_in_message=True`` to
  ``src/zanzibar/schema/errors.py::ShapeNoLongerAccepted``. The parser's sites are left
  alone: their messages already end with the advice in words of their own.
- **C6** ``SetEngine.check("user:a", "viewer", "doc:1")`` / ``lookup("user:a")`` gave
  Python's "missing 3 required positional arguments". Every SetEngine read and write now
  says it takes the six-part (or three-part) form and names ``Store`` for the short one
  (``src/zanzibar/setengine/engine.py::_long_form_only``). No short form was added.
- **Docs** ``userdocs/how-to/test-permissions.md`` says pytest must be installed (it is
  not a dependency). The six missing docstrings are pinned in
  ``tests/test_tk169_public_docstrings.py``.

SABOTAGE (2026-11-20, agent A; each guarded line broken with the Edit tool, this module run
alone with ``-p no:cacheprovider``, restored with the Edit tool, re-run green ``47 passed``).
Literal observed lines:

- SB1 ``require_shapes``: ``entry = tuple(entry)`` -> ``pass``:
  ``E  TypeError: parse_openfga_schema(): object_wildcard_shapes entry ['folder', 'viewer']
  is not a (type, relation) pair of strings; ...`` -- ``5 failed, 42 passed in 0.85s``
- SB2 ``require_shapes``: ``hash(entry)`` -> ``pass`` (the guard gone, frozenset crashes):
  ``E  AssertionError: unhashable type: 'list'`` -- ``25 failed, 22 passed in 1.23s``
- SB3 ``ShapeNoLongerAccepted.__init__``: always ``super().__init__(message)``:
  ``E  AssertionError: object_wildcard_shapes entry 'folder' is not a (type, relation) pair
  of strings`` -- ``3 failed, 44 passed in 1.08s``
- SB4 ``PersistedSchemaRefused.__init__``: back to quoting ``{refusal}`` (the full message,
  rewrite included): ``E  assert 2 == 1`` -- ``1 failed, 46 passed in 0.94s``
- SB5 ``_long_form_only``: a bare ``raise`` as the first line of the ``except`` (the bind
  error escapes unshaped): ``E  AssertionError: missing a required argument: 'relation'``
  -- ``6 failed, 41 passed in 1.07s``
- SB6 the pytest paragraph deleted from ``userdocs/how-to/test-permissions.md``:
  ``E  AssertionError: test-permissions.md must say how to install pytest`` --
  ``1 failed, 46 passed in 1.08s``
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import (PersistedSchemaRefused, ShapeNoLongerAccepted, Store,
                      parse_openfga_schema)
from zanzibar.setengine import SetEngine
from zanzibar.store import SchemaRecord, save_schema

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = ("model\n  schema 1.1\ntype user\ntype folder\n  relations\n    define viewer: [user]\n"
          "type doc\n  relations\n    define viewer: [user]\n")


@pytest.fixture(autouse=True)
def _quiet_unproven():
    # An object wildcard is an unproven extension; its warning is not under test here.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        yield


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _entry_points(session):
    """Every public entry point that takes ``object_wildcard_shapes``."""
    return {
        'parse_openfga_schema': lambda shapes: parse_openfga_schema(
            SCHEMA, object_wildcard_shapes=shapes).schema_info.object_wildcard_shapes,
        'Store': lambda shapes: Store(session, 'st', schema=SCHEMA,
                                      object_wildcard_shapes=shapes).ruleset.schema_info
        .object_wildcard_shapes,
        'Store.adopt': lambda shapes: Store.adopt(session, 'ad', schema=SCHEMA,
                                                  object_wildcard_shapes=shapes)
        [0].ruleset.schema_info.object_wildcard_shapes,
        'SetEngine': lambda shapes: SetEngine(session, 'se', SCHEMA,
                                              object_wildcard_shapes=shapes)
        .schema_info.object_wildcard_shapes,
        'save_schema': lambda shapes: save_schema(session, 'sv', SCHEMA, shapes)[1]
        .schema_info.object_wildcard_shapes,
    }


ENTRY_POINTS = ('parse_openfga_schema', 'Store', 'Store.adopt', 'SetEngine', 'save_schema')


# --- C4 ------------------------------------------------------------------------------------

@pytest.mark.parametrize('where', ENTRY_POINTS)
def test_c4_a_two_item_list_is_a_pair(session, where):
    """``[["folder", "viewer"]]`` (what ``json.load`` gives) means ``{("folder", "viewer")}``."""
    got = _entry_points(session)[where]([['folder', 'viewer']])
    assert got == frozenset({('folder', 'viewer')})
    assert all(type(shape) is tuple for shape in got)


UNHASHABLE = [['folder'], ['folder', 'viewer', 'x'], ['folder', 5], {'a': 1},
              ('folder', ['viewer'])]


@pytest.mark.parametrize('entry', UNHASHABLE, ids=repr)
@pytest.mark.parametrize('where', ENTRY_POINTS)
def test_c4_an_unhashable_entry_is_a_typeerror_naming_it(session, where, entry):
    with pytest.raises(TypeError) as info:
        _entry_points(session)[where]([entry])
    msg = str(info.value)
    assert 'unhashable' not in msg, msg
    assert f'object_wildcard_shapes entry {entry!r} is not a (type, relation) pair' in msg, msg
    assert '("folder", "viewer")' in msg, msg


@pytest.mark.parametrize('entry', ['folder', ('doc', 5), ('doc', 'viewer', 'x')], ids=repr)
def test_c4_control_a_hashable_non_pair_keeps_shape_no_longer_accepted(entry):
    """CONTROL: the TK147 refusal of a hashable non-pair is unchanged (class kept)."""
    with pytest.raises(ShapeNoLongerAccepted) as info:
        parse_openfga_schema(SCHEMA, object_wildcard_shapes=[entry])
    assert f'object_wildcard_shapes entry {entry!r} is not a (type, relation) pair' in str(
        info.value)


# --- C3 ------------------------------------------------------------------------------------

C3_CASES = {
    'not-a-pair': ['folder'],
    'undeclared-type': [('nosuch', 'viewer')],
    'undeclared-relation': [('folder', 'nosuch')],
}


@pytest.mark.parametrize('name', sorted(C3_CASES))
def test_c3_the_message_ends_with_the_rewrite(name):
    with pytest.raises(ShapeNoLongerAccepted) as info:
        parse_openfga_schema(SCHEMA, object_wildcard_shapes=C3_CASES[name])
    exc = info.value
    assert exc.instead
    assert str(exc).endswith(f'. To rewrite: {exc.instead}'), str(exc)


def test_c3_a_persisted_refusal_quotes_the_rewrite_once(session):
    """``PersistedSchemaRefused`` already appended ``To rewrite:``; it must not now say it
    twice."""
    session.add(SchemaRecord(store_id='old', schema_text=SCHEMA,
                             object_wildcard_shapes='[["folder", "nosuch"]]'))
    session.commit()
    with pytest.raises(PersistedSchemaRefused) as info:
        Store(session, 'old')
    msg = str(info.value)
    assert msg.count(info.value.instead) == 1, msg
    assert msg.count('To rewrite: ') == 1, msg
    assert 'names the undeclared relation folder#nosuch' in msg, msg


def test_c3_control_parser_messages_are_unchanged():
    """CONTROL: a parser refusal's message is not given a second rewrite
    (``userdocs/how-to/errors.md`` prints this one verbatim)."""
    with pytest.raises(ShapeNoLongerAccepted) as info:
        parse_openfga_schema('type user\ntype doc\n  relations\n    define viewer: [usr]\n')
    assert str(info.value) == ("doc#viewer: restriction [usr] names an undeclared type 'usr'; "
                               "declare it (type usr) or fix the spelling")


# --- C6 ------------------------------------------------------------------------------------

C6_CALLS = {
    'check': (('user:a', 'viewer', 'doc:1'), 6, "'user:alice'"),
    'lookup': (('user:a',), 3, "'user:alice'"),
    'lookup_reverse': (('viewer', 'doc:1'), 3, "'doc:1'"),
    'expand': (('viewer', 'doc:1'), 3, "'doc:1'"),
    'add_tuple': (('user:a', 'viewer', 'doc:1'), 6, "'user:alice'"),
    'remove_tuple': (('user:a', 'viewer', 'doc:1'), 6, "'user:alice'"),
}


@pytest.mark.parametrize('method', sorted(C6_CALLS))
def test_c6_the_short_form_on_set_engine_names_the_form_it_takes(session, method):
    args, n, short = C6_CALLS[method]
    se = SetEngine(session, 'se', SCHEMA)
    with pytest.raises(TypeError) as info:
        getattr(se, method)(*args)
    msg = str(info.value)
    assert 'required positional argument' not in msg, msg
    assert msg.startswith(f'SetEngine.{method}() takes {n} arguments ('), msg
    assert f'; got {len(args)}. SetEngine has only this form, with no {short} short form' in msg
    assert f'or call Store.{method}, which takes both forms' in msg


def test_c6_control_the_six_part_form_still_works(session):
    se = SetEngine(session, 'se', SCHEMA)
    assert se.add_tuple('...', 'user', 'a', 'viewer', 'doc', '1') is True
    assert se.check('...', 'user', 'a', 'viewer', 'doc', '1') is True
    assert se.check(subject_predicate='...', subject_type='user', subject_name='a',
                    relation='viewer', object_type='doc', object_name='1') is True
    assert ('doc', '1', '...') not in se.result_keys(se.lookup('...', 'user', 'b'))
    assert se.expand('viewer', 'doc', '1', None) is not None


def test_c6_an_error_inside_the_method_is_not_rewritten(session):
    """CONTROL: the guard only shapes ARITY errors; a wrong-typed part keeps its own
    ``TypeError`` from the method body."""
    se = SetEngine(session, 'se', SCHEMA)
    with pytest.raises(TypeError, match=r"check\(\): relation must be a str") as info:
        se.check('...', 'user', 'a', None, 'doc', '1')
    assert 'has only this form' not in str(info.value)


# --- docs ----------------------------------------------------------------------------------

def test_test_permissions_page_says_pytest_is_not_a_dependency():
    text = (ROOT / 'userdocs' / 'how-to' / 'test-permissions.md').read_text(encoding='utf-8')
    assert 'pip install pytest' in text, 'test-permissions.md must say how to install pytest'
    assert 'It is not a dependency' in text, ('test-permissions.md must say that pytest is '
                                              'not a dependency')
