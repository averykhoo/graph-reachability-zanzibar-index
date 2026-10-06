"""
The pluggable set-representation seam (spec §1.1).

All set state and algebra in the engine go through ``SetOps`` -- a factory pair, not a
class hierarchy, because ``pyroaring`` bitmaps and builtin ``set`` already share the
operator surface the engine needs (``in``, ``|``, ``&``, ``-``, ``add``, ``discard``,
iteration, ``len``, ``bool``). Never write ``isinstance`` checks against either type.

Rationale (spec §1.1): builtin ``set`` is typically faster for small, membership-heavy
work (no C-boundary crossing, no bitmap construction); roaring wins on large
populations and bulk union/intersection/difference -- exactly the ``expand`` path. Ship
both, default roaring, and let the benchmark inform the per-deployment choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SetOps:
    """A factory pair selecting the concrete set representation.

    ``new`` builds a mutable set, ``freeze`` an immutable one, each from an optional
    iterable of int32 ids (the intern table issues sequential int32s, so 32-bit roaring
    is sufficient). ``update`` unions an arbitrary iterable INTO an existing mutable set
    in place, without materialising a full intermediate copy -- both backends' native
    ``.update`` normalises any iterable (bare tuples, generators, or a peer set/bitmap),
    so it is a copy-free normaliser (see ``memberset._starpop``).
    """
    name: str
    new: Callable[..., object]      # (Iterable[int] = ()) -> MutSet
    freeze: Callable[..., object]   # (Iterable[int] = ()) -> FrozSet
    update: Callable[[object, object], None]  # (MutSet, Iterable[int]) -> None, in place


PySets = SetOps(
    name='py',
    new=lambda it=(): set(it),
    freeze=lambda it=(): frozenset(it),
    update=lambda acc, it: acc.update(it),      # builtin set.update: any iterable
)

try:
    from pyroaring import BitMap, FrozenBitMap
    RoaringSets: SetOps | None = SetOps(
        name='roaring',
        new=lambda it=(): BitMap(it),
        freeze=lambda it=(): FrozenBitMap(it),
        update=lambda acc, it: acc.update(it),  # BitMap.update: iterables + peer BitMaps
    )
except ImportError:                 # pyroaring is a declared dependency; guard only for dev envs
    RoaringSets = None

# Default is roaring (spec §1); PySets is the always-available fallback.
DEFAULT_SETOPS = RoaringSets if RoaringSets is not None else PySets

# For tests/benchmarks that parametrize over every available implementation.
ALL_SETOPS = [PySets] + ([RoaringSets] if RoaringSets is not None else [])
