"""The connected store: source-of-truth tuples + materialized graph index.

Composition layer only (connected-store spec §1): this package imports the set
engine and the graph index; they never import it. The synchronous coupling is a
temporary SCHEDULE, not temporary machinery -- sync mode is the async apply step
inlined into the write transaction (spec §1/§4).
"""

from .models import IndexCursorV1, SchemaV4, TupleLogV1
from .schema_io import (SchemaMismatch, ensure_schema, load_schema,
                        open_graph_index, open_set_engine, save_schema)
from .source import TupleSource, log_rows, log_watermark
from .apply import advance_index, ensure_cursor
from .build import build_index
from .store import ConnectedStore

__all__ = [
    "ConnectedStore",
    "advance_index",
    "ensure_cursor",
    "build_index",
    "SchemaV4",
    "TupleLogV1",
    "IndexCursorV1",
    "SchemaMismatch",
    "save_schema",
    "ensure_schema",
    "load_schema",
    "open_set_engine",
    "open_graph_index",
    "TupleSource",
    "log_rows",
    "log_watermark",
]
