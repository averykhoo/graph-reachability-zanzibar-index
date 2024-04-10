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
            raise ValueError(f'value {value} is negative')
        if value == 0:
            super().__delitem__(key)
        else:
            super().__setitem__(key, value)


@dataclass(frozen=True)
class AcyclicGraphReachabilityIndex:
    edge_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)
    index_nodes_from: dict[str, set[str]] = field(default_factory=dict)
    index_nodes_to: dict[str, set[str]] = field(default_factory=dict)
    index_counter: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)

    def add_edge(self, node_from, node_to):
        # ensure acyclic invariant holds
        if node_from in self.index_nodes_from[node_to]:
            raise ValueError(f'node_from {node_from} reachable from {node_to}, adding this edge would create a cycle')

        # count the edge
        self.edge_counts[(node_from, node_to)] += 1

        # TODO: ...
        # get downstream nodes of node_to
        # get upstream nodes of node_from
        # add to each other
