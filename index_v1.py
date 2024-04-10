from collections import Counter
from dataclasses import dataclass
from dataclasses import field


class AutoRemoveCounter(Counter):
    def __setitem__(self, key, value):
        if value == 0:
            super().__delitem__(key)
        else:
            super().__setitem__(key, value)


@dataclass(frozen=True)
class GraphIndex:
    nodes: list = field(default_factory=list)
    edges: AutoRemoveCounter = field(default_factory=AutoRemoveCounter)
    index_nodes_from: dict = field(default_factory=dict)
    index_nodes_to: dict = field(default_factory=dict)
    index_counter: AutoRemoveCounter = field(default_factory=AutoRemoveCounter)
