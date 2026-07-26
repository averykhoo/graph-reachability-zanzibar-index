from .models import PermissionDelta, StoreV4, NodeV4, EdgeV4, Store, Node, Edge
from .core import ReachabilityIndex, AdmissionRejected
from .invariants import InvariantViolation
from .wildcard import WildcardIndex, LookupResult

__all__ = [
    "PermissionDelta",
    "StoreV4",
    "NodeV4",
    "EdgeV4",
    "Store",
    "Node",
    "Edge",
    "ReachabilityIndex",
    # The two disjoint failure classes a caller must distinguish:
    # AdmissionRejected (ValueError)  -- a CORRECT refusal of an inadmissible write
    # InvariantViolation (AssertionError) -- store corruption, never an op rejection
    "AdmissionRejected",
    "InvariantViolation",
    "WildcardIndex",
    "LookupResult",
]
