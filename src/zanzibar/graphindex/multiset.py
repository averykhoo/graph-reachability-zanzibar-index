"""`MultiSet`: a `Counter` that refuses negative and non-integer counts.

Used by `core.py::ReachabilityIndex` for its reachable-before/after counts. Moved here
from the deleted `legacy/index_v1.py` (TK120, 2026-10-06); the class is unchanged.
"""
from collections import Counter


class MultiSet(Counter):
    """
    poor man's multi-set
    based off a Counter, but throws more errors just to be safe
    """

    def __setitem__(self, key, value):
        if not isinstance(value, int):
            raise TypeError(f'value {value} is not an integer')
        if value < 0:
            raise ValueError(f'value {value} is negative')
        if value == 0:
            super().__delitem__(key)
        else:
            super().__setitem__(key, value)

    def __add__(self, other):
        out = self.copy()
        out += other  # error if adding negative counts, instead of ignoring
        return out

    def __sub__(self, other):
        out = self.copy()
        out -= other  # error if subtracting larger counts, instead of ignoring
        return out

    def __neg__(self):
        raise ValueError('cannot negate')
