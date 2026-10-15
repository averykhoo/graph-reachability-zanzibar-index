"""TK123 items 4, 5, 6 and 24 (A11-A15, A18-A20; 2026-10-15): the public surface.

* Item 4 -- ``import zanzibar`` exposes ``Store``, ``LookupResult``, ``parse_openfga_schema``
  and every exception class in the package, LAZILY (PEP 562 ``__getattr__``): importing
  the top level, or ``zanzibar.schema``, must not drag in ``sqlmodel`` or the store.
* Item 5 -- each subpackage's ``__all__`` is the real surface, not every helper, and
  ``SetOps`` has a short repr.
* Item 6 -- ``ZanzibarError`` is the root of every package exception, each keeping its
  builtin base; ``SchemaError`` is what the schema parsers raise.
* Item 24 -- ``InvariantViolation`` (store corruption) stays OUTSIDE ``ZanzibarError``.

Sabotage evidence (2026-10-15, first-hand; the permanent ones run every time):

* lazy import -- ``test_eager_import_is_detected`` runs the same probe against a tmp copy
  whose ``__init__`` imports ``Store`` eagerly and asserts the probe reports ``sqlmodel``
  loaded (the instrument control).
* exception census -- ``test_census_detects_a_missing_export`` drops ``WriteLockUnsafe``
  from a copy of the lazy map and asserts the census names it.
* ``raise ValueError`` scan -- ``test_valueerror_scan_detects_an_injection`` injects one
  ``raise ValueError`` into a tmp copy of ``parser.py`` and asserts exactly one finding.
* root -- by hand: with ``ZanzibarError`` removed from ``WriteLockUnsafe``'s bases,
  ``test_every_exception_is_rooted_and_keeps_its_builtin_base`` went red with
  ``AssertionError: not rooted at ZanzibarError: ['zanzibar.graphindex.core.WriteLockUnsafe']``.
* item 24 -- by hand: with ``InvariantViolation(ZanzibarError, AssertionError)``,
  ``test_invariant_violation_stays_outside_the_root`` went red with
  ``AssertionError: InvariantViolation must not be a ZanzibarError``.
"""
import importlib
import inspect
import json
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

import zanzibar

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'


# --------------------------------------------------------------------------- item 4

_PROBE = r'''
import json, sys
import zanzibar
after_top = sorted(m for m in sys.modules if m == 'sqlmodel' or m.startswith('zanzibar.'))
import zanzibar.schema
after_schema = sorted(m for m in sys.modules
                      if m in ('sqlmodel', 'sqlalchemy', 'pyroaring') or m.startswith('zanzibar.store')
                      or m.startswith('zanzibar.graphindex') or m.startswith('zanzibar.setengine'))
print(json.dumps({'file': zanzibar.__file__, 'after_top': after_top,
                  'after_schema': after_schema}))
'''


def _import_probe(src_root: Path) -> dict:
    """Run ``_PROBE`` in a FRESH interpreter that can only see ``src_root``."""
    env = dict(os.environ, PYTHONPATH=str(src_root))
    out = subprocess.run([sys.executable, '-c', _PROBE], env=env, cwd=str(src_root),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert Path(res['file']).resolve().is_relative_to(src_root.resolve()), res['file']
    return res


def test_top_level_and_schema_imports_are_lazy():
    res = _import_probe(SRC)
    assert res['after_top'] == [], res
    assert res['after_schema'] == [], res


def test_eager_import_is_detected(tmp_path):
    """The instrument control: an eager ``from .store import Store`` in a tmp copy must
    show up as ``sqlmodel`` in ``sys.modules`` after the bare ``import zanzibar``."""
    shutil.copytree(SRC / 'zanzibar', tmp_path / 'zanzibar',
                    ignore=shutil.ignore_patterns('__pycache__'))
    init = tmp_path / 'zanzibar' / '__init__.py'
    init.write_text(init.read_text(encoding='utf-8') + '\nfrom .store import Store\n',
                    encoding='utf-8')
    res = _import_probe(tmp_path)
    assert 'sqlmodel' in res['after_top'], res


def test_top_level_names_resolve_to_the_defining_objects():
    import zanzibar.graphindex
    import zanzibar.schema
    import zanzibar.store
    assert zanzibar.Store is zanzibar.store.Store
    assert zanzibar.LookupResult is zanzibar.graphindex.LookupResult
    assert zanzibar.parse_openfga_schema is zanzibar.schema.parse_openfga_schema
    assert zanzibar.WriteLockUnsafe is zanzibar.graphindex.WriteLockUnsafe
    assert zanzibar.WriteLockUnsafe is zanzibar.store.WriteLockUnsafe
    with pytest.raises(AttributeError):
        zanzibar.nope  # noqa: B018
    from zanzibar import store  # a SUBMODULE still imports through __getattr__
    assert store is zanzibar.store
    assert set(zanzibar.__all__) <= set(dir(zanzibar))
    for name in zanzibar.__all__:
        assert getattr(zanzibar, name) is not None, name
    assert not hasattr(zanzibar.graphindex.core, '__all_exceptions__')  # A18: dead dunder


def _exception_census() -> dict[str, type]:
    """Every public exception/warning class DEFINED in the package, by name."""
    found: dict[str, type] = {}
    for info in pkgutil.walk_packages(zanzibar.__path__, 'zanzibar.'):
        mod = importlib.import_module(info.name)
        for name, obj in vars(mod).items():
            if (inspect.isclass(obj) and issubclass(obj, BaseException)
                    and obj.__module__ == mod.__name__ and not name.startswith('_')):
                assert name not in found or found[name] is obj, f'two classes named {name}'
                found[name] = obj
    return found


def _missing_exports(census: dict[str, type], lazy: dict[str, str]) -> list[str]:
    missing = []
    for name, cls in sorted(census.items()):
        if name not in lazy:
            missing.append(name)
        elif getattr(importlib.import_module(lazy[name]), name) is not cls:
            missing.append(f'{name} (wrong object)')
    return missing


def test_every_exception_is_exported_from_the_top_level():
    census = _exception_census()
    assert len(census) >= 21, sorted(census)   # 2026-10-15: 23 incl. the warning
    assert _missing_exports(census, zanzibar._LAZY) == []
    for name, cls in census.items():
        assert name in zanzibar.__all__, name
        assert getattr(zanzibar, name) is cls, name


def test_census_detects_a_missing_export():
    census = _exception_census()
    lazy = dict(zanzibar._LAZY)
    del lazy['WriteLockUnsafe']
    assert _missing_exports(census, lazy) == ['WriteLockUnsafe']


# --------------------------------------------------------------------------- item 5

_EXPECTED_ALL = {
    'zanzibar.schema': {
        'parse_openfga_schema', 'parse_openfga_json', 'openfga_json_to_dsl',
        'parse_schema_ast', 'unparse_schema_ast', 'compile_ruleset', 'RuleSet',
        'SchemaAST', 'Expr', 'Direct', 'Restriction', 'Computed', 'TTU', 'Union',
        'Intersection', 'Exclusion', 'IDENTIFIER_CHARSET', 'is_valid_identifier',
        'validate_store_id', 'ZanzibarError', 'SchemaError', 'ShapeNoLongerAccepted',
        'AdmissionRejected', 'IndexResourceLimit', 'ClosureFanoutExceeded',
        'PathCountExceeded', 'UnsupportedByGraphIndex', 'DoublyBridgedShapeError',
        'CyclicDerivedDependency', 'SchemaMismatch', 'UnprovenExtensionWarning',
        'MalformedTupleString'},
    'zanzibar.setengine': {
        'SetEngine', 'SetLookupResult', 'MemberSet', 'RelationTuple', 'SetOps', 'PySets',
        'RoaringSets', 'UnloggedWriteRefused'},
    'zanzibar.graphindex': {
        'ReachabilityIndex', 'WildcardIndex', 'LookupResult', 'Node', 'Edge', 'IndexStore',
        'AdmissionRejected', 'InvariantViolation', 'WriteLockUnsafe', 'outbox_watermark',
        'prune_outbox'},
    'zanzibar.store': {
        'Store', 'TupleSource', 'build_index', 'rebuild_index', 'save_schema',
        'SchemaRecord', 'TupleLog', 'PARANOIA_ENV_VAR', 'StaleRead', 'LookupNotFresh',
        'IndexStalled', 'UnloggedTuplesPresent', 'WatermarkGap', 'UnsafeIsolationLevel',
        'MissingDeltaProcessor', 'SchemaMismatch', 'PersistedSchemaRefused', 'SchemaError',
        'StoreNotFound', 'TablesNotCreated', 'IndexExists', 'BuildReport',
        'CyclicDerivedDependency', 'AdmissionRejected', 'IndexResourceLimit',
        'ClosureFanoutExceeded', 'PathCountExceeded', 'WriteLockUnsafe', 'MalformedTupleString'},
}

# Internals the review found in __all__ (A11, A13, A15). They still import by name.
_DROPPED = {
    'zanzibar.schema': {'Plan', 'PUnion', 'PIntersection', 'PExclusion', 'LeafSpec',
                        'compute_taint', 'norm_pred', 'replace_relation',
                        'w4_fragment_report', 'PClosureLeaf'},
    'zanzibar.setengine': {'SetEngineBackend', 'Interner', 'NodeSets', 'DEFAULT_SETOPS',
                           'ALL_SETOPS'},
    'zanzibar.graphindex': {'PermissionDelta'},
    'zanzibar.store': {'advance_index', 'ensure_cursor', 'assert_read_isolation', 'log_gap',
                       'log_rows', 'log_watermark', 'open_set_engine', 'open_graph_index',
                       'load_schema', 'ensure_schema', 'IndexCursor'},
}


@pytest.mark.parametrize('modname', sorted(_EXPECTED_ALL))
def test_subpackage_all_is_the_real_surface(modname):
    mod = importlib.import_module(modname)
    assert len(mod.__all__) == len(set(mod.__all__)), 'duplicate in __all__'
    assert set(mod.__all__) == _EXPECTED_ALL[modname]
    for name in mod.__all__:
        assert hasattr(mod, name), name
    for name in _DROPPED[modname]:
        assert name not in mod.__all__, name
        assert hasattr(mod, name), f'{name} must still import by name'


def test_setops_repr_is_short():
    from zanzibar.setengine import PySets, RoaringSets
    assert repr(PySets) == "SetOps('py')"
    assert repr(RoaringSets) == "SetOps('roaring')"


# --------------------------------------------------------------------------- items 6, 24

# Every package exception keeps the builtin base it had before the root existed.
_BUILTIN_BASE = {
    'SchemaError': ValueError, 'ShapeNoLongerAccepted': ValueError,
    'AdmissionRejected': ValueError, 'IndexResourceLimit': ValueError,
    'ClosureFanoutExceeded': ValueError, 'PathCountExceeded': ValueError,
    'CyclicDerivedDependency': ValueError, 'SchemaMismatch': ValueError,
    'MissingDeltaProcessor': ValueError, 'PersistedSchemaRefused': ValueError,
    'MalformedTupleString': ValueError,
    'UnsupportedByGraphIndex': Exception, 'DoublyBridgedShapeError': Exception,
    'WriteLockUnsafe': RuntimeError, 'UnloggedWriteRefused': RuntimeError,
    'StaleRead': RuntimeError, 'WatermarkGap': RuntimeError,
    'UnsafeIsolationLevel': RuntimeError, 'LookupNotFresh': RuntimeError,
    'IndexStalled': RuntimeError, 'UnloggedTuplesPresent': RuntimeError,
    'StoreNotFound': KeyError, 'TablesNotCreated': RuntimeError, 'IndexExists': ValueError,
}
_OUTSIDE_THE_ROOT = {'InvariantViolation', 'UnprovenExtensionWarning'}


def test_every_exception_is_rooted_and_keeps_its_builtin_base():
    census = _exception_census()
    root = zanzibar.ZanzibarError
    unrooted = sorted(f'{c.__module__}.{n}' for n, c in census.items()
                      if n not in _OUTSIDE_THE_ROOT and n != 'ZanzibarError'
                      and not issubclass(c, root))
    assert not unrooted, f'not rooted at ZanzibarError: {unrooted}'
    for name, base in _BUILTIN_BASE.items():
        assert issubclass(census[name], base), (name, base)
    # A new exception class must be classified here, not silently waved through.
    assert set(census) == set(_BUILTIN_BASE) | _OUTSIDE_THE_ROOT | {'ZanzibarError'}, \
        sorted(set(census) ^ (set(_BUILTIN_BASE) | _OUTSIDE_THE_ROOT | {'ZanzibarError'}))


def test_invariant_violation_stays_outside_the_root():
    """Item 24: ``except ZanzibarError`` must never swallow a corruption report."""
    from zanzibar.graphindex import InvariantViolation
    assert not issubclass(InvariantViolation, zanzibar.ZanzibarError), \
        'InvariantViolation must not be a ZanzibarError'
    assert issubclass(InvariantViolation, AssertionError)
    assert not issubclass(zanzibar.UnprovenExtensionWarning, zanzibar.ZanzibarError)


@pytest.mark.parametrize('call', [
    lambda: zanzibar.parse_openfga_schema('model\n  schema 1.1\ntype user\ntype doc\n'
                                          '  relations\n    define viewer: [nobody]\n'),
    lambda: zanzibar.parse_openfga_schema('this is not a schema'),
    lambda: importlib.import_module('zanzibar.schema').parse_openfga_json('{"nope": 1}'),
    lambda: importlib.import_module('zanzibar.schema').parse_schema_ast(
        'model\n  schema 1.1\ntype doc\n  relations\n    define viewer: editor\n'),
], ids=['undeclared-type', 'garbage', 'json', 'dangling-ref'])
def test_schema_refusals_raise_schema_error(call):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        with pytest.raises(zanzibar.SchemaError) as ei:
            call()
    assert isinstance(ei.value, ValueError) and isinstance(ei.value, zanzibar.ZanzibarError)


_SCHEMA_PARSERS = ('parser.py', 'json_frontend.py', 'rules.py')
_RAISE_VALUEERROR = re.compile(r'\braise\s+ValueError\b')


def _bare_valueerror_raises(schema_dir: Path) -> list[str]:
    hits = []
    for fname in _SCHEMA_PARSERS:
        for i, line in enumerate((schema_dir / fname).read_text(encoding='utf-8').splitlines(), 1):
            if _RAISE_VALUEERROR.search(line):
                hits.append(f'{fname}:{i}')
    return hits


def test_schema_parsers_raise_no_bare_valueerror():
    assert _bare_valueerror_raises(SRC / 'zanzibar' / 'schema') == []


def test_valueerror_scan_detects_an_injection(tmp_path):
    for fname in _SCHEMA_PARSERS:
        shutil.copy(SRC / 'zanzibar' / 'schema' / fname, tmp_path / fname)
    assert _bare_valueerror_raises(tmp_path) == []
    p = tmp_path / 'parser.py'
    p.write_text(p.read_text(encoding='utf-8') + "\n\ndef _x():\n    raise ValueError('x')\n",
                 encoding='utf-8')
    assert len(_bare_valueerror_raises(tmp_path)) == 1
