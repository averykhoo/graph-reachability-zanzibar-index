"""TK147 (TK137 challenge C7) -- an ``object_wildcard_shapes`` entry naming no declared
relation is REFUSED, on every path that accepts the argument.

Property guarded
----------------
Through 0.0.5, ``parse_openfga_schema(text, object_wildcard_shapes={('nosuch', 'viewer')})``
and ``{('doc', 'nosuchrel')}`` were ACCEPTED and did nothing on either backend (first-hand
probe, ``docs/tk147-owc-shape-refusal-2026-10-17.md`` sec 1): the caller believed an
object wildcard was enabled and it was not. Since TK147 each entry must be a
``(type, relation)`` pair of strings naming a relation the schema declares, else
``zanzibar.schema.errors.ShapeNoLongerAccepted`` (a ``SchemaError``, so a ``ValueError``),
whose message names the entry and whose ``instead`` says what to write. One check,
``src/zanzibar/schema/compiler.py::_validate_object_wildcard_shapes``, called from
``derive_schema_info`` (so ``parse_openfga_schema``), from ``compile_ruleset`` (so a hand-built
``SchemaInfo`` too; TK147 review 2026-10-17) and from ``SetEngine.__init__`` (so the
``ruleset=`` path too). Not checked: a ``RuleSet`` built by hand (not by ``compile_ruleset``)
passed as ``SetEngine(ruleset=)``, and ``WildcardIndex(idx, schema_info)``, which has no AST. A compiled leaf name (``('doc', 'view.0')``) is an undeclared
relation as well: the graph alone used to refuse it, the set engine ran it without a graph
partner (the retired TK116 witness ``owc-names-a-leaf``); now both refuse.

The persisted-store trap (the row's Trap, decided 2026-10-17 as TK137 R1 / C10 was): a
store saved by 0.0.5 CAN hold such an entry (``save_schema`` compiled it and wrote the
JSON), so reopening it must read as a VERSION BREAK, not corruption:
``PersistedSchemaRefused`` saying "saved by zanzibar-index 0.0.5 or earlier", quoting the
refusal, and pointing at the 0.1.0 changelog -- from every open, whatever is passed (the
TK153 F17 "one condition, one type" rule): ``Store`` with no schema, the same schema, the
same schema plus the bad shapes, or the corrected shapes; ``open_set_engine``,
``TupleSource``, ``SetEngine`` (no schema, the text, the text plus the shapes),
``save_schema``, ``ensure_schema`` and ``build_index``. A shape the CALLER passes for a
store with nothing persisted keeps the plain ``ShapeNoLongerAccepted``, and nothing is saved.

No oracle twin: ``tests/oracle.py::Oracle`` takes no ``object_wildcard_shapes`` (it answers
star objects intensionally), so the parser-parity contract (``test_p23_...``), which is over
schema TEXT, is untouched; ``test_the_oracle_takes_no_shapes`` pins that premise and
``test_parity_engine_refuses_on_every_backend`` shows no backend is left accepting.

Map: ``docs/tk147-owc-shape-refusal-2026-10-17.md``.

SABOTAGE (2026-10-17, TK147 workflow agent; gitignored
``.scratch/ultracode-2026-10-17/tk147/sabotage.py``, so this docstring and the map's sec 4
are the tracked record). One asserted-unique anchor per mutation, file restored
byte-for-byte and sha256-checked; this module only (78 tests), ``-p no:cacheprovider``.
Literal tails, every one RED:

- SB1 the whole check deleted (early ``return``): ``rc=1 | 74 failed, 4 passed``
- SB2 the ``derive_schema_info`` call deleted: ``rc=1 | 22 failed, 56 passed``
- SB3 the ``SetEngine.__init__`` call deleted: ``rc=1 | 12 failed, 66 passed``
- SB4 the undeclared-type branch off: ``rc=1 | 19 failed, 59 passed``
- SB5 the undeclared-relation branch off: ``rc=1 | 44 failed, 34 passed``
- SB6 the not-a-pair branch off: ``rc=1 | 11 failed, 67 passed``
- SB7 ``schema_io.py::_verify_same_schema``'s persisted-shape check deleted:
  ``rc=1 | 15 failed, 63 passed``
- SB8 ``engine.py::_assert_schema_matches_record``'s shape check deleted:
  ``rc=1 | 3 failed, 75 passed``
- SB9 ``engine.py::_refuse_persisted_shape``'s shape check deleted:
  ``rc=1 | 6 failed, 72 passed``
- SB10 ``accepted_through='0.0.5'`` dropped from the undeclared-type raise (the message
  would say "0.0.4 or earlier"): ``rc=1 | 19 failed, 59 passed``

Added by the TK147 review fix (2026-10-17; gitignored
``.scratch/ultracode-2026-10-17/tk147-review-fix/sab.py``), module then 105 tests,
baseline ``rc=0 | 105 passed``:

- SB11 ``declared_types`` dropped at every ``_validate_object_wildcard_shapes`` binding
  (monkeypatch; the review's sabotage, which left the 78-test module ``rc=0 | 78 passed``
  before the ``unrestricted-relationless-type`` case existed): ``rc=1 | 19 failed, 86 passed``
- SB12 the ``compile_ruleset`` call deleted: ``rc=1 | 7 failed, 98 passed``
"""
from __future__ import annotations

import inspect
import json
import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tests import oracle as oracle_mod
from tests.parity import ParityEngine
from zanzibar.schema import (SchemaError, SchemaInfo, compile_ruleset, derive_schema_info,
                             parse_openfga_schema, parse_schema_ast)
from zanzibar.schema.parser import _parse_schema_ast_checked
from zanzibar.schema.errors import PersistedSchemaRefused, SchemaMismatch, ShapeNoLongerAccepted
from zanzibar.setengine import SetEngine
from zanzibar.store import (SchemaRecord, Store, TupleSource, build_index, ensure_schema,
                            open_set_engine, save_schema)

TEXT = '''type user
type folder
type team
type doc
  relations
    define parent: [folder]
    define viewer: [user]
    define editor: [user]
    define banned: [user]
    define view: editor but not banned
'''
GOOD = frozenset({('doc', 'viewer')})

#: name -> (shapes, fragment of the message naming the shape and the cause)
BAD = {
    'undeclared-type': (frozenset({('nosuch', 'viewer')}),
                        "('nosuch', 'viewer') names the undeclared type 'nosuch'"),
    'undeclared-relation': (frozenset({('doc', 'nosuchrel')}),
                            "('doc', 'nosuchrel') names the undeclared relation doc#nosuchrel"),
    'relationless-type': (frozenset({('folder', 'viewer')}),
                          "('folder', 'viewer') names the undeclared relation folder#viewer"),
    # ``team`` is declared by its ``type`` line ONLY: no relation, no restriction names it,
    # so only ``declared_types`` tells the check it exists (``folder`` above is also a
    # restriction type, which hid a dropped ``declared_types`` -- TK147 review 2026-10-17).
    'unrestricted-relationless-type': (
        frozenset({('team', 'viewer')}),
        "('team', 'viewer') names the undeclared relation team#viewer "
        "(type 'team' declares: no relations)"),
    'compiled-leaf': (frozenset({('doc', 'view.0')}),
                      "('doc', 'view.0') names the undeclared relation doc#view.0"),
    'not-a-pair': (frozenset({('doc', 'viewer', 'x')}),
                   "('doc', 'viewer', 'x') is not a (type, relation) pair"),
    'two-char-string': (frozenset({'ab'}), "'ab' is not a (type, relation) pair"),
}
#: The ones a 0.0.5 ``save_schema`` could persist (JSON lists of two strings; the store
#: path compiled the graph too, which refused the leaf name, so it never persisted).
PERSISTABLE = ('undeclared-type', 'undeclared-relation', 'relationless-type',
               'unrestricted-relationless-type')

VERSION_BREAK = 'saved by zanzibar-index 0.0.5 or earlier using a shape this version refuses'


@pytest.fixture(autouse=True)
def _quiet_unproven():
    # A declared object wildcard is an UNPROVEN extension (ASK-2); the warning is not
    # under test here.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        yield


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk147.db").as_posix()}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _assert_refusal(exc: BaseException, name: str) -> None:
    assert isinstance(exc, ShapeNoLongerAccepted), type(exc)
    assert not isinstance(exc, PersistedSchemaRefused)
    assert isinstance(exc, SchemaError) and isinstance(exc, ValueError)
    assert 'object_wildcard_shapes entry ' + BAD[name][1] in str(exc), str(exc)
    assert exc.instead and (' or drop it' in exc.instead or 'drop ' in exc.instead)
    assert (exc.accepted_through, exc.refused_since) == ('0.0.5', '0.1.0')


# --- the check itself, on each construction path ------------------------------------------

@pytest.mark.parametrize('name', sorted(BAD))
def test_parse_openfga_schema_refuses(name):
    with pytest.raises(ShapeNoLongerAccepted) as info:
        parse_openfga_schema(TEXT, object_wildcard_shapes=BAD[name][0])
    _assert_refusal(info.value, name)


@pytest.mark.parametrize('name', sorted(BAD))
def test_derive_schema_info_refuses(name):
    ast, declared_types = _parse_schema_ast_checked(TEXT)
    with pytest.raises(ShapeNoLongerAccepted) as info:
        derive_schema_info(ast, BAD[name][0], declared_types=declared_types)
    _assert_refusal(info.value, name)


def test_without_declared_types_a_relationless_type_reads_as_undeclared():
    """The documented limit of ``derive_schema_info(ast, shapes)`` with no
    ``declared_types``: the verdict is the same refusal, only the wording differs."""
    with pytest.raises(ShapeNoLongerAccepted) as info:
        derive_schema_info(parse_schema_ast(TEXT), frozenset({('team', 'viewer')}))
    assert "names the undeclared type 'team'" in str(info.value), str(info.value)


@pytest.mark.parametrize('name', sorted(BAD))
def test_compile_ruleset_refuses_a_hand_built_schema_info(name):
    """A hand-built ``SchemaInfo`` skips ``derive_schema_info``; ``compile_ruleset`` checks
    its declared shapes itself (TK147 review 2026-10-17: before this, the shape was
    ACCEPTED and carried into the RuleSet)."""
    ast, declared_types = _parse_schema_ast_checked(TEXT)
    with pytest.raises(ShapeNoLongerAccepted) as info:
        compile_ruleset(ast, SchemaInfo(object_wildcard_shapes=BAD[name][0]),
                        declared_types=declared_types)
    _assert_refusal(info.value, name)
    with pytest.raises(ShapeNoLongerAccepted):
        compile_ruleset(ast, SchemaInfo(object_wildcard_shapes=BAD[name][0]),
                        enable_boolean=False, declared_types=declared_types)


@pytest.mark.parametrize('name', sorted(BAD))
def test_standalone_set_engine_refuses(engine, name):
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            SetEngine(s, 'standalone', TEXT, object_wildcard_shapes=BAD[name][0])
    _assert_refusal(info.value, name)


@pytest.mark.parametrize('name', sorted(BAD))
def test_set_engine_refuses_on_the_ruleset_path(engine, name):
    """``ruleset=`` skips ``derive_schema_info``; ``SetEngine.__init__`` checks anyway."""
    good_ruleset = parse_openfga_schema(TEXT, object_wildcard_shapes=GOOD)
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            SetEngine(s, 'standalone', TEXT, object_wildcard_shapes=BAD[name][0],
                      ruleset=good_ruleset)
    _assert_refusal(info.value, name)


@pytest.mark.parametrize('name', sorted(BAD))
def test_a_fresh_store_refuses_and_saves_nothing(engine, name):
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            Store(s, 'fresh', schema=TEXT, object_wildcard_shapes=BAD[name][0])
    _assert_refusal(info.value, name)
    for fn in (save_schema, ensure_schema):
        with Session(engine) as s:
            with pytest.raises(ShapeNoLongerAccepted) as info:
                fn(s, 'fresh', TEXT, BAD[name][0])
            _assert_refusal(info.value, name)
    with Session(engine) as s:
        assert s.get(SchemaRecord, 'fresh') is None


def test_parity_engine_refuses_on_every_backend():
    """ParityEngine fans out to graph + both set engines + oracle; the refusal comes first,
    so no backend is left serving the shape (before TK147 a leaf name left the set engines
    running with no graph partner)."""
    for name in sorted(BAD):
        with pytest.raises(ShapeNoLongerAccepted):
            ParityEngine(TEXT, object_wildcard_shapes=BAD[name][0])


def test_the_oracle_takes_no_shapes():
    """The premise of 'no oracle twin': the referee has no object_wildcard_shapes argument
    to validate, and both parsers accept the schema TEXT (the p23 contract is over text)."""
    assert 'object_wildcard_shapes' not in inspect.signature(oracle_mod.Oracle).parameters
    assert set(oracle_mod.parse_schema_ast(TEXT)) == set(parse_schema_ast(TEXT))


# --- controls -------------------------------------------------------------------------------

def test_a_declared_shape_is_still_accepted_everywhere(engine):
    """CONTROL: the check is not a blanket refusal. ``('doc', 'viewer')`` opens on every
    path and a ``doc:*`` object write is admitted (and absent shapes still refuse it)."""
    rs = parse_openfga_schema(TEXT, object_wildcard_shapes=GOOD)
    assert ('doc', 'viewer') in rs.schema_info.object_wildcard_shapes
    with Session(engine) as s:
        SetEngine(s, 'standalone', TEXT, object_wildcard_shapes=GOOD)
        st = Store(s, 'ok', schema=TEXT, object_wildcard_shapes=GOOD)
        st.add_tuple('user:alice', 'viewer', 'doc:*')
        assert st.check('user:alice', 'viewer', 'doc:d1')
    with Session(engine) as s:
        Store(s, 'ok')
        open_set_engine(s, 'ok')
        SetEngine(s, 'ok')
        Store(s, 'ok', schema=TEXT, object_wildcard_shapes=GOOD)


def test_a_mismatched_but_valid_shape_set_is_still_a_mismatch(engine):
    """CONTROL: on a store whose persisted shapes are VALID, passing different valid shapes
    stays ``SchemaMismatch`` -- the version-break type is not a catch-all."""
    with Session(engine) as s:
        Store(s, 'ok', schema=TEXT, object_wildcard_shapes=GOOD)
    with Session(engine) as s:
        with pytest.raises(SchemaMismatch) as info:
            ensure_schema(s, 'ok', TEXT, frozenset())
        assert not isinstance(info.value, PersistedSchemaRefused)
        with pytest.raises(SchemaMismatch) as info:
            SetEngine(s, 'ok', TEXT)
        assert not isinstance(info.value, PersistedSchemaRefused)


def test_callers_bad_shape_on_a_valid_store_keeps_the_plain_refusal(engine):
    """CONTROL: a store persisted with VALID shapes, opened by a caller passing a BAD one,
    is the caller's typo, not a version break."""
    with Session(engine) as s:
        Store(s, 'ok', schema=TEXT, object_wildcard_shapes=GOOD)
    with Session(engine) as s:
        with pytest.raises(ShapeNoLongerAccepted) as info:
            SetEngine(s, 'ok', TEXT, object_wildcard_shapes=BAD['undeclared-type'][0])
    _assert_refusal(info.value, 'undeclared-type')


# --- the persisted-store trap -------------------------------------------------------------------

def _persist_as_0_0_5(engine, store_id: str, shapes) -> None:
    """What 0.0.5's ``save_schema`` left behind for these shapes: text plus shapes JSON
    (the compiled schema is cache)."""
    with Session(engine) as s:
        s.add(SchemaRecord(store_id=store_id, schema_text=TEXT,
                           object_wildcard_shapes=json.dumps(sorted(list(x) for x in shapes))))
        s.commit()


def _assert_version_break(exc: BaseException, name: str) -> None:
    assert isinstance(exc, PersistedSchemaRefused), (type(exc), exc)
    msg = str(exc)
    assert "store 'old'" in msg and VERSION_BREAK in msg, msg
    assert BAD[name][1] in msg
    assert 'To rewrite: drop ' in msg and 'see the 0.1.0 changelog' in msg
    assert isinstance(exc.__cause__, ShapeNoLongerAccepted)
    assert exc.store_id == 'old' and exc.instead == exc.refusal.instead


def _opens(name):
    bad = BAD[name][0]
    return {
        'Store()': lambda s: Store(s, 'old'),
        'Store(schema)': lambda s: Store(s, 'old', schema=TEXT),
        'Store(schema, bad)': lambda s: Store(s, 'old', schema=TEXT, object_wildcard_shapes=bad),
        'Store(schema, corrected)': lambda s: Store(s, 'old', schema=TEXT,
                                                    object_wildcard_shapes=GOOD),
        'open_set_engine': lambda s: open_set_engine(s, 'old'),
        'TupleSource': lambda s: TupleSource(s, 'old'),
        'SetEngine()': lambda s: SetEngine(s, 'old'),
        'SetEngine(text)': lambda s: SetEngine(s, 'old', TEXT),
        'SetEngine(text, bad)': lambda s: SetEngine(s, 'old', TEXT, object_wildcard_shapes=bad),
        'save_schema(bad)': lambda s: save_schema(s, 'old', TEXT, bad),
        'ensure_schema(bad)': lambda s: ensure_schema(s, 'old', TEXT, bad),
        'ensure_schema(corrected)': lambda s: ensure_schema(s, 'old', TEXT, GOOD),
        'build_index(other)': lambda s: build_index(s, 'old', index_store_id='old-index'),
    }


OPEN_NAMES = sorted(_opens('undeclared-type'))


@pytest.mark.parametrize('opener', OPEN_NAMES)
@pytest.mark.parametrize('name', PERSISTABLE)
def test_reopening_a_0_0_5_store_with_a_bad_shape_is_a_version_break(engine, name, opener):
    _persist_as_0_0_5(engine, 'old', BAD[name][0])
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            _opens(name)[opener](s)
    _assert_version_break(info.value, name)


@pytest.mark.parametrize('name', PERSISTABLE)
def test_the_rewrite_opens_in_a_new_store(engine, name):
    """The message's advice works: the same text with the entry dropped, under a new id."""
    _persist_as_0_0_5(engine, 'old', BAD[name][0])
    with Session(engine) as s:
        with pytest.raises(PersistedSchemaRefused) as info:
            Store(s, 'old')
    assert 'drop ' in info.value.instead
    with Session(engine) as s:
        Store(s, 'new', schema=TEXT, object_wildcard_shapes=frozenset())
        s.commit()
    with Session(engine) as s:
        Store(s, 'new')


def test_tk137_messages_keep_their_version():
    """CONTROL for the new attributes: a TK137 refusal still says 0.0.4 / 0.0.5."""
    with pytest.raises(ShapeNoLongerAccepted) as info:
        parse_schema_ast('model\n  schema 1.2\n' + TEXT)
    assert (info.value.accepted_through, info.value.refused_since) == ('0.0.4', '0.0.5')
    assert 'saved by zanzibar-index 0.0.4 or earlier' in str(
        PersistedSchemaRefused('x', info.value))
