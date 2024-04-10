from collections import Counter
from dataclasses import dataclass
from dataclasses import field


class MultiSet(Counter):
    """
    poor man's multiset, based off a Counter with some added safeguards
    also it deletes the key when the value goes down to zero to save a bit of ram
    """
    def __setitem__(self, key, value):
        if not isinstance(value, int):
            raise TypeError(f'value {value} is not an integer')
        if value < 0:
            raise ValueError(f'value {value} is negative')re
        if value == 0:
            super().__delitem__(key)
        else:
            super().__setitem__(key, value)


@dataclass(frozen=True)
class GraphIndex:
    nodes: list = field(default_factory=list)
    edges: MultiSet = field(default_factory=MultiSet)
    index_nodes_from: dict = field(default_factory=dict)
    index_nodes_to: dict = field(default_factory=dict)
    index_counter: MultiSet = field(default_factory=MultiSet)
