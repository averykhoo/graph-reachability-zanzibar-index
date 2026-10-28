"""
setengine -- a raw-tuple, bitmap-backed evaluation backend.

The opposite endpoint of the memoization spectrum from the graph index: it stores only
raw set memberships and computes reachability on the fly with bitmap algebra, `and` and
`but not` included. Both backends give the same answers; ``zanzibar.store.Store`` keeps a
set engine next to the graph index and falls back to it when the index is behind.
"""

from .setops import SetOps, PySets, RoaringSets, DEFAULT_SETOPS, ALL_SETOPS
from .memberset import MemberSet
from .models import RelationTuple
from .engine import (SetEngine, SetEngineBackend, Interner, NodeSets, SetLookupResult,
                     StaleLookupIds, UnloggedWriteRefused)

# The public surface (`TK123` item 5). The import lines above stay, so the internal names
# (``SetEngineBackend``, ``Interner``, ``NodeSets``, ``DEFAULT_SETOPS``, ``ALL_SETOPS``)
# still import by name; they are just not part of the API.
# Exceptions and warnings are NOT listed here (`TK164`): their one public home is the
# top-level package (``from zanzibar import StaleRead``). The import lines stay, so an
# old ``from zanzibar.setengine import <Exception>`` still resolves, but it is not API.
__all__ = [
    'SetEngine', 'SetLookupResult', 'MemberSet', 'RelationTuple',
    'SetOps', 'PySets', 'RoaringSets',
]
