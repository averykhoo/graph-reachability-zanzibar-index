"""
setengine -- a raw-tuple, bitmap-backed evaluation backend (spec: set-engine).

The opposite endpoint of the memoization spectrum from the graph index: it stores only
raw set memberships and computes reachability on the fly with bitmap algebra, adding
boolean operators (`and`, `but not`) the closure index cannot represent.
"""

from .setops import SetOps, PySets, RoaringSets, DEFAULT_SETOPS, ALL_SETOPS
from .memberset import MemberSet
from .models import TupleV1
from .engine import SetEngine, SetEngineBackend, Interner, NodeSets, LookupResult

__all__ = [
    'SetOps', 'PySets', 'RoaringSets', 'DEFAULT_SETOPS', 'ALL_SETOPS',
    'MemberSet',
    'TupleV1', 'SetEngine', 'SetEngineBackend', 'Interner', 'NodeSets', 'LookupResult',
]
