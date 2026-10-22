"""TK164 (2026-10-23): the public exception and type surface before the 0.1.0 freeze.

Repro and first-hand output of the defects: ``docs/tk151-repros-2026-10-20/README.md``
sections B2 and B10. Plan and decisions: ``docs/tk164-public-surface-2026-10-23.md``.

Pinned here:

* B2 -- every schema refusal is a ``ValueError``. ``UnsupportedByGraphIndex`` (and its
  subclass ``DoublyBridgedShapeError``) were the only two ``ZanzibarError`` subclasses with
  no builtin base, so ``except ValueError`` around ``parse_openfga_schema`` / ``Store(...)`` /
  ``compile_ruleset`` let them escape. Pinned two ways: the B2 repro calls under
  ``except ValueError``, and a scan of every ``raise`` in ``src/zanzibar/schema/`` (any
  ``ZanzibarError`` raised there must be a ``ValueError``), with an instrument control.
* B10 -- one export rule: no subpackage ``__all__`` lists an exception or warning; their one
  public home is ``zanzibar``. (The old subpackage imports still RESOLVE, which
  ``tests/test_tk123_top_level.py::test_subpackage_all_is_the_real_surface`` pins; they are
  just not API.)
* B10 -- ``SchemaInfo``, ``Entity``, ``RelationalTriple`` and ``CompiledBooleans`` (in public
  signatures) are in ``zanzibar.schema.__all__`` with their own docstrings, and
  ``zanzibar.store.open_set_engine`` (the remedy a ``SchemaMismatch`` names) is in
  ``zanzibar.store.__all__``.
* B10 side finding -- ``typing.get_type_hints(RuleSet)`` resolves (it raised
  ``NameError: name 'CompiledBooleans' is not defined``), and so do the other public
  signatures that carry these types, whatever module is imported first.

Sabotage evidence (2026-10-23, first-hand; each file restored and its sha256 re-checked; the
module had 25 tests then):

* S1 -- ``class UnsupportedByGraphIndex(ZanzibarError)`` (``ValueError`` dropped) in
  ``schema/errors.py``: ``rc=1 | 5 failed, 20 passed``. The three B2 calls fail with the
  refusal escaping ``except ValueError`` (``zanzibar.schema.errors.DoublyBridgedShapeError:
  shape(s) (folder, viewer) are BOTH a wildcard-userset shape ...``), the scan with
  ``AssertionError: schema refusals that are not a ValueError: ['DoublyBridgedShapeError',
  'UnsupportedByGraphIndex']``, and the MRO pin with ``At index 1 diff: <class 'Exception'>
  != <class 'ValueError'>``.
* S2 -- ``"StaleRead"`` appended to ``zanzibar.store.__all__``: ``rc=1 | 1 failed, 24 passed``,
  ``AssertionError: exceptions listed in a subpackage __all__ (their home is zanzibar):
  ['zanzibar.store.StaleRead']``.
* S3 -- ``Entity``'s docstring deleted: ``rc=1 | 1 failed, 24 passed``,
  ``AssertionError: Entity has no docstring of its own: 'Entity(type: str, name: str)'``
  (the dataclass-generated signature is not a docstring).
* S4 -- the bottom ``from .boolean import CompiledBooleans`` in ``schema/rules.py`` replaced
  by ``pass``: ``rc=1 | 6 failed, 19 passed``, ``NameError: name 'CompiledBooleans' is not
  defined`` in both in-process ``RuleSet`` hint tests and all four fresh-interpreter import
  orders.
"""
import importlib
import inspect
import os
import pkgutil
import re
import subprocess
import sys
import typing
import warnings
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'

# --------------------------------------------------------------------------- B2

_F1 = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user, folder:*#viewer, folder#admin]
    define admin: [user] or viewer from parent
"""
_OWC = frozenset({('folder', 'parent'), ('folder', 'viewer')})
_BOOL = """model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user] but not banned
"""


def _compile_without_booleans():
    from zanzibar.schema import compile_ruleset, derive_schema_info, parse_schema_ast
    ast = parse_schema_ast(_BOOL)
    compile_ruleset(ast, derive_schema_info(ast), enable_boolean=False)


def _store_on_doubly_bridged():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        zanzibar.Store(s, 's', schema=_F1, object_wildcard_shapes=_OWC)


_B2_CALLS = {
    'parse-doubly-bridged': (lambda: zanzibar.parse_openfga_schema(
        _F1, object_wildcard_shapes=_OWC), 'DoublyBridgedShapeError'),
    'store-doubly-bridged': (_store_on_doubly_bridged, 'DoublyBridgedShapeError'),
    'compile-enable-boolean-false': (_compile_without_booleans, 'UnsupportedByGraphIndex'),
}


@pytest.mark.parametrize('case', sorted(_B2_CALLS))
def test_b2_schema_refusals_are_caught_by_except_valueerror(case):
    call, expected = _B2_CALLS[case]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')     # the F1 shapes warn UnprovenExtensionWarning
        try:
            call()
        except ValueError as e:
            caught = e
        else:
            pytest.fail(f'{case}: no refusal raised')
    assert type(caught).__name__ == expected, repr(caught)
    assert isinstance(caught, zanzibar.UnsupportedByGraphIndex)
    assert isinstance(caught, zanzibar.ZanzibarError)
    assert not isinstance(caught, zanzibar.SchemaError)   # the text parsed; compile refused


_RAISE = re.compile(r'\braise\s+([A-Z][A-Za-z0-9_]*)\b')


def _raised_in(directory: Path) -> set[str]:
    names = set()
    for p in sorted(directory.glob('*.py')):
        names |= set(_RAISE.findall(p.read_text(encoding='utf-8')))
    return names


# Schema refusals raised OUTSIDE src/zanzibar/schema/ (store / set engine opens).
_SCHEMA_REFUSALS_ELSEWHERE = {'SchemaMismatch', 'PersistedSchemaRefused'}


def test_every_schema_refusal_is_a_valueerror():
    raised = _raised_in(SRC / 'zanzibar' / 'schema')
    # Instrument control: the scanner sees the families it guards.
    assert {'SchemaError', 'ShapeNoLongerAccepted', 'UnsupportedByGraphIndex',
            'DoublyBridgedShapeError', 'CyclicDerivedDependency'} <= raised, sorted(raised)
    root = zanzibar.ZanzibarError
    refusals = {n for n in raised | _SCHEMA_REFUSALS_ELSEWHERE
                if n in zanzibar._LAZY and issubclass(getattr(zanzibar, n), root)}
    # 2026-10-23: 9 -- the 7 schema refusals plus AdmissionRejected and
    # MalformedTupleString (write refusals, also raised in schema/; also ValueErrors).
    assert len(refusals) >= 9, sorted(refusals)
    not_value = sorted(n for n in refusals if not issubclass(getattr(zanzibar, n), ValueError))
    assert not not_value, f'schema refusals that are not a ValueError: {not_value}'


def test_doubly_bridged_is_still_its_own_type_under_unsupported():
    """The set engine re-raises exactly this subclass (both backends refuse the shape)."""
    assert issubclass(zanzibar.DoublyBridgedShapeError, zanzibar.UnsupportedByGraphIndex)
    assert zanzibar.UnsupportedByGraphIndex.__mro__[1:3] == (zanzibar.ZanzibarError, ValueError)


# --------------------------------------------------------------------------- B10: exports


def _subpackages() -> list[str]:
    return sorted(info.name for info in pkgutil.walk_packages(zanzibar.__path__, 'zanzibar.')
                  if info.ispkg)


def test_no_subpackage_all_lists_an_exception():
    pkgs = _subpackages()
    assert {'zanzibar.schema', 'zanzibar.setengine', 'zanzibar.graphindex',
            'zanzibar.store'} <= set(pkgs), pkgs
    offenders = []
    for name in pkgs:
        mod = importlib.import_module(name)
        for attr in getattr(mod, '__all__', ()):
            obj = getattr(mod, attr)
            if inspect.isclass(obj) and issubclass(obj, BaseException):
                offenders.append(f'{name}.{attr}')
    assert not offenders, \
        f'exceptions listed in a subpackage __all__ (their home is zanzibar): {offenders}'


def test_every_exception_has_its_home_at_the_top_level():
    for name in zanzibar._LAZY:
        obj = getattr(zanzibar, name)
        if inspect.isclass(obj) and issubclass(obj, BaseException):
            assert name in zanzibar.__all__, name


# --------------------------------------------------------------------------- B10: types

_NEWLY_PUBLIC = {
    'zanzibar.schema': ('SchemaInfo', 'Entity', 'RelationalTriple', 'CompiledBooleans'),
    'zanzibar.store': ('open_set_engine',),
}


@pytest.mark.parametrize('modname,name', [(m, n) for m, ns in sorted(_NEWLY_PUBLIC.items())
                                          for n in ns])
def test_newly_public_names_are_exported_and_documented(modname, name):
    mod = importlib.import_module(modname)
    assert name in mod.__all__, name
    obj = getattr(mod, name)
    doc = obj.__doc__ or ''
    # A dataclass with no docstring gets its generated signature as __doc__.
    assert doc.strip() and not doc.startswith(f'{name}('), \
        f'{name} has no docstring of its own: {doc!r}'
    assert '0.1.0' in doc, f'{name} docstring does not say when it became public'


def test_get_type_hints_resolves_on_ruleset():
    from zanzibar.schema import CompiledBooleans, RuleSet, SchemaInfo
    hints = typing.get_type_hints(RuleSet)
    assert hints['compiled'] == CompiledBooleans | None
    assert hints['schema_info'] == SchemaInfo | None


def _public_signatures():
    import zanzibar.graphindex as gi
    import zanzibar.schema as sc
    import zanzibar.store as st
    return {
        'RuleSet': sc.RuleSet,
        'RuleSet.apply': sc.RuleSet.apply,
        'compile_ruleset': sc.compile_ruleset,
        'WildcardIndex.__init__': gi.WildcardIndex.__init__,
        'DeltaProcessor.__init__': gi.DeltaProcessor.__init__,
        'SchemaInfo': sc.SchemaInfo,
        'RelationalTriple': sc.RelationalTriple,
        'open_set_engine': st.open_set_engine,
    }


@pytest.mark.parametrize('name', sorted(_public_signatures()))
def test_get_type_hints_resolves_on_public_signatures(name):
    typing.get_type_hints(_public_signatures()[name])


_ORDER_PROBE = '''
import importlib, sys, typing
importlib.import_module(sys.argv[1])
from zanzibar.schema import RuleSet
from zanzibar.graphindex import DeltaProcessor
typing.get_type_hints(RuleSet)
typing.get_type_hints(DeltaProcessor.__init__)
print('OK')
'''


@pytest.mark.parametrize('first', ['zanzibar.schema.boolean', 'zanzibar.schema.rules',
                                   'zanzibar.graphindex.processor', 'zanzibar'])
def test_hints_resolve_whatever_module_is_imported_first(first):
    """The binding is a deliberate circular import at the bottom of ``rules.py``; a fresh
    interpreter per first-import order proves no order trips it."""
    env = dict(os.environ, PYTHONPATH=str(SRC))
    out = subprocess.run([sys.executable, '-c', _ORDER_PROBE, first], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip().endswith('OK'), out.stderr[-2000:]
