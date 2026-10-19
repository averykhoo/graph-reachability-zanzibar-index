"""The connected store: source-of-truth tuples + materialized graph index.

Composition layer only: this package imports the set
engine and the graph index; they never import it. The synchronous coupling is a
temporary SCHEDULE, not temporary machinery -- sync mode is the async apply step
inlined into the write transaction.
"""
# Provenance (moved out of the docstring, TK123 item 14): connected-store spec §1.
# Provenance (moved out of the docstring, TK123 item 14): spec §1/§4.

from .models import IndexCursor, SchemaRecord, TupleLog
from .schema_io import (PersistedSchemaRefused, SchemaMismatch, StoreNotFound, TablesNotCreated,
                        TablesOutdated, ensure_schema, load_schema,
                        open_graph_index, open_set_engine, save_schema)
from .source import (StaleRead, TupleSource, UnsafeIsolationLevel, WatermarkGap,
                     assert_read_isolation, log_gap, log_rows, log_watermark)
from .apply import MissingDeltaProcessor, advance_index, ensure_cursor
from .build import BuildReport, IndexExists, build_index, rebuild_index
from ._store import (Store, ExpandResult, IndexStalled, LookupNotFresh, PARANOIA_ENV_VAR,
                    UnloggedTuplesPresent)
# Re-exported because a ``Store`` raises them, so a caller can catch what it gets from here.
from zanzibar.graphindex.core import WriteLockUnsafe
from zanzibar.schema.errors import (AdmissionRejected, ClosureFanoutExceeded,
                                    CyclicDerivedDependency, IndexResourceLimit,
                                    PathCountExceeded, SchemaError)
from zanzibar.schema.tuplestr import MalformedTupleString
from zanzibar.setengine.engine import StaleLookupIds

# The public surface (`TK123` item 5). The import lines above stay, so the internal
# helpers (``advance_index``, ``ensure_cursor``, ``assert_read_isolation``, ``log_gap``,
# ``log_rows``, ``log_watermark``, ``open_set_engine``, ``open_graph_index``,
# ``load_schema``, ``ensure_schema``, ``IndexCursor``) still import by name.
__all__ = [
    "Store",
    "ExpandResult",
    "TupleSource",
    "build_index",
    "rebuild_index",
    "BuildReport",
    "save_schema",
    "SchemaRecord",
    "TupleLog",
    "PARANOIA_ENV_VAR",
    # exceptions a Store raises
    "StaleRead",
    "LookupNotFresh",
    "IndexStalled",
    "UnloggedTuplesPresent",
    "WatermarkGap",
    "UnsafeIsolationLevel",
    "MissingDeltaProcessor",
    "SchemaMismatch",
    "PersistedSchemaRefused",
    "StoreNotFound",
    "IndexExists",
    "TablesNotCreated",
    "TablesOutdated",
    "StaleLookupIds",
    "SchemaError",
    "CyclicDerivedDependency",
    "AdmissionRejected",
    "IndexResourceLimit",
    "ClosureFanoutExceeded",
    "PathCountExceeded",
    "WriteLockUnsafe",
    "MalformedTupleString",
]
