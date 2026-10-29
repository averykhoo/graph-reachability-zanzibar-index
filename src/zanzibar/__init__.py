"""zanzibar: Zanzibar-style relationship/permission evaluation.

Two backends with identical semantics and opposite cost models:

* `zanzibar.setengine` -- stores raw tuples, evaluates on the fly with bitmap algebra;
* `zanzibar.graphindex` -- materializes the transitive closure, O(1) `check`;

sharing the schema layer `zanzibar.schema`, and composed with a tuple log in
`zanzibar.store`.

The names most programs need are importable from here: ``Store``, ``LookupResult``,
``parse_openfga_schema``, and every exception the package raises (rooted at
``ZanzibarError``, except ``InvariantViolation``, which reports corruption). This is the
exceptions' ONE public home: no subpackage lists an exception in its ``__all__``.
They load
LAZILY: ``import zanzibar`` imports nothing else, and ``zanzibar.Store`` pulls in the
database stack only when first touched, so a schema-only user never pays for it.
"""
from typing import TYPE_CHECKING

__version__ = "0.1.1"

# name -> the module that defines it. Resolved on first attribute access (PEP 562).
_LAZY = {
    'Store': 'zanzibar.store._store',
    'LookupResult': 'zanzibar.graphindex.wildcard',
    'ExpandResult': 'zanzibar.store._store',
    'parse_openfga_schema': 'zanzibar.schema.compiler',
    # exceptions: the root, the schema layer
    'ZanzibarError': 'zanzibar.schema.errors',
    'SchemaError': 'zanzibar.schema.errors',
    'ShapeNoLongerAccepted': 'zanzibar.schema.errors',
    'AdmissionRejected': 'zanzibar.schema.errors',
    'IndexResourceLimit': 'zanzibar.schema.errors',
    'ClosureFanoutExceeded': 'zanzibar.schema.errors',
    'PathCountExceeded': 'zanzibar.schema.errors',
    'UnsupportedByGraphIndex': 'zanzibar.schema.errors',
    'DoublyBridgedShapeError': 'zanzibar.schema.errors',
    'CyclicDerivedDependency': 'zanzibar.schema.errors',
    'SchemaMismatch': 'zanzibar.schema.errors',
    'PersistedSchemaRefused': 'zanzibar.schema.errors',
    'MalformedTupleString': 'zanzibar.schema.tuplestr',
    'UnprovenExtensionWarning': 'zanzibar.schema.compiler',
    # the backends
    'UnloggedWriteRefused': 'zanzibar.setengine.engine',
    'StaleLookupIds': 'zanzibar.setengine.engine',
    'WriteLockUnsafe': 'zanzibar.graphindex.core',
    'CascadeNotRun': 'zanzibar.graphindex.cascade_mark',
    'InvariantViolation': 'zanzibar.graphindex.invariants',
    # the store
    'StaleRead': 'zanzibar.store.source',
    'ForeignToken': 'zanzibar.store.source',
    'WatermarkGap': 'zanzibar.store.source',
    'UnsafeIsolationLevel': 'zanzibar.store.source',
    'LookupNotFresh': 'zanzibar.store._store',
    'IndexStalled': 'zanzibar.store._store',
    'UnloggedTuplesPresent': 'zanzibar.store._store',
    'MissingDeltaProcessor': 'zanzibar.store.apply',
    'StoreNotFound': 'zanzibar.store.schema_io',
    'IndexExists': 'zanzibar.store.build',
    'TablesNotCreated': 'zanzibar.store.schema_io',
    'TablesOutdated': 'zanzibar.store.schema_io',
}

__all__ = ['__version__', *_LAZY]


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        # AttributeError (not ImportError) so ``from zanzibar import store`` falls
        # through to importing the submodule.
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    import importlib
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value          # cache: __getattr__ runs once per name
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY))


if TYPE_CHECKING:  # pragma: no cover -- for type checkers and IDEs only
    from zanzibar.graphindex.cascade_mark import CascadeNotRun
    from zanzibar.graphindex.core import WriteLockUnsafe
    from zanzibar.graphindex.invariants import InvariantViolation
    from zanzibar.graphindex.wildcard import LookupResult
    from zanzibar.schema.compiler import UnprovenExtensionWarning, parse_openfga_schema
    from zanzibar.schema.errors import (AdmissionRejected, ClosureFanoutExceeded,
                                        CyclicDerivedDependency, DoublyBridgedShapeError,
                                        IndexResourceLimit, PathCountExceeded,
                                        PersistedSchemaRefused, SchemaError,
                                        SchemaMismatch, ShapeNoLongerAccepted,
                                        UnsupportedByGraphIndex, ZanzibarError)
    from zanzibar.schema.tuplestr import MalformedTupleString
    from zanzibar.setengine.engine import StaleLookupIds, UnloggedWriteRefused
    from zanzibar.store._store import (ExpandResult, IndexStalled, LookupNotFresh, Store,
                                       UnloggedTuplesPresent)
    from zanzibar.store.apply import MissingDeltaProcessor
    from zanzibar.store.build import IndexExists
    from zanzibar.store.schema_io import StoreNotFound, TablesNotCreated, TablesOutdated
    from zanzibar.store.source import (ForeignToken, StaleRead, UnsafeIsolationLevel,
                                       WatermarkGap)
