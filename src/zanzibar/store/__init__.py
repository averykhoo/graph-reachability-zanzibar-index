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
from .source import (ForeignToken, StaleRead, TupleSource, UnsafeIsolationLevel, WatermarkGap,
                     assert_read_isolation, log_gap, log_rows, log_watermark)
from .apply import MissingDeltaProcessor, advance_index, ensure_cursor
from .build import BuildReport, IndexExists, build_index, rebuild_index
from ._store import (Store, ExpandResult, IndexStalled, LookupNotFresh, PARANOIA_ENV_VAR,
                    UnloggedTuplesPresent)
# Imported here before `TK164` so a caller could catch what a ``Store`` raises from this
# package; kept so those imports still resolve. The documented home is ``zanzibar``.
from zanzibar.graphindex.core import WriteLockUnsafe
from zanzibar.schema.errors import (AdmissionRejected, ClosureFanoutExceeded,
                                    CyclicDerivedDependency, IndexResourceLimit,
                                    PathCountExceeded, SchemaError)
from zanzibar.schema.tuplestr import MalformedTupleString
from zanzibar.setengine.engine import StaleLookupIds

# The public surface (`TK123` item 5). The import lines above stay, so the internal
# helpers (``advance_index``, ``ensure_cursor``, ``assert_read_isolation``, ``log_gap``,
# ``log_rows``, ``log_watermark``, ``open_graph_index``, ``load_schema``,
# ``ensure_schema``, ``IndexCursor``) still import by name. ``open_set_engine`` is public
# since `TK164`: the set engine's ``SchemaMismatch`` message names it as the remedy.
# Exceptions and warnings are NOT listed here (`TK164`): their one public home is the
# top-level package (``from zanzibar import StaleRead``). The import lines stay, so an
# old ``from zanzibar.store import <Exception>`` still resolves, but it is not API.
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
    "open_set_engine",
]
