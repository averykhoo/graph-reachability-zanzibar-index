"""The graph index: the materialized transitive closure (``ReachabilityIndex``) plus
wildcard bridges and the boolean derived-relation read path (``WildcardIndex``).

``check`` is a few indexed lookups whatever the data size; writes pay to keep the closure
current. The state lives in ``zanzibar_*`` tables (``Node``, ``Edge``, ``IndexStore``).
Most programs reach it through ``zanzibar.store.Store``, whose ``lookup`` /
``lookup_reverse`` return this package's ``LookupResult``.
"""
from .models import PermissionDelta, IndexStore, Node, Edge  # noqa: F401  (PermissionDelta: internal)
from .core import ReachabilityIndex, AdmissionRejected, WriteLockUnsafe
from .invariants import InvariantViolation
from .wildcard import WildcardIndex, LookupResult
from .outbox import outbox_watermark, prune_outbox

__all__ = [
    "IndexStore",
    "Node",
    "Edge",
    "ReachabilityIndex",
    # The two disjoint failure classes a caller must distinguish:
    # AdmissionRejected (ValueError)  -- a CORRECT refusal of an inadmissible write
    # InvariantViolation (AssertionError) -- store corruption, never an op rejection
    "AdmissionRejected",
    "InvariantViolation",
    # Raised on a write when the session cannot take the row write lock (SQLite in
    # AUTOCOMMIT); a ZanzibarError, unlike InvariantViolation.
    "WriteLockUnsafe",
    "WildcardIndex",
    "LookupResult",
    # Manual outbox retention (never auto-called).
    "outbox_watermark",
    "prune_outbox",
]
