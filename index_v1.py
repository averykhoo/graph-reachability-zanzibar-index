from collections import Counter
from dataclasses import dataclass
from dataclasses import field


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


@dataclass(frozen=True)
class AcyclicGraphReachabilityIndex:
    index_paths: dict[str, set[str]] = field(default_factory=dict)  # {source: {dest, ...}}
    inverted_index_paths: dict[str, set[str]] = field(default_factory=dict)  # {dest: {source, ...}}
    index_path_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)  # {(source, dest): count}
    edge_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)  # {(source, dest): count}

    def add_edge(self, node_from, node_to):
        # sanity check
        assert node_from != node_to

        # ensure acyclic invariant holds
        if self.index_path_counts[(node_to, node_from)] > 0:
            raise ValueError(f'{node_from=} is reachable from {node_to=}, adding this edge would create a cycle')

        # get the nodes that can reach node_from
        reachable_from_node_from = MultiSet()
        for node in self.inverted_index_paths.get(node_from, set()):
            reachable_from_node_from[node] = self.index_path_counts[(node, node_from)]
        assert reachable_from_node_from[node_from] == 0, reachable_from_node_from
        assert reachable_from_node_from[node_to] == 0, reachable_from_node_from

        # get the nodes that are reachable from node_to
        reachable_from_node_to = MultiSet()
        for node in self.index_paths.get(node_to, set()):
            reachable_from_node_to[node] = self.index_path_counts[(node_to, node)]
        assert reachable_from_node_to[node_from] == 0, reachable_from_node_to
        assert reachable_from_node_to[node_to] == 0, reachable_from_node_to

        # add the node_to's reachable nodes to node_from
        for to_node, count in reachable_from_node_to.items():
            self.index_path_counts[(node_from, to_node)] += count
            self.index_paths.setdefault(node_from, set()).add(to_node)
            self.inverted_index_paths.setdefault(to_node, set()).add(node_from)

        # make node_to reachable from all the nodes that can reach node_from
        for from_node, count in reachable_from_node_from.items():
            self.index_path_counts[(from_node, node_to)] += count
            self.index_paths.setdefault(from_node, set()).add(node_to)
            self.inverted_index_paths.setdefault(node_to, set()).add(from_node)

        # add the direct edge
        self.index_path_counts[(node_from, node_to)] += 1
        self.index_paths.setdefault(node_from, set()).add(node_to)
        self.inverted_index_paths.setdefault(node_to, set()).add(node_from)
        self.edge_counts[(node_from, node_to)] += 1

    def remove_edge(self, node_from, node_to):
        # sanity check
        assert node_from != node_to

        # ensure there's an edge to remove
        if self.edge_counts[(node_from, node_to)] == 0:
            raise ValueError(f'{node_from=} has no direct edge to {node_to=}, cannot remove nonexistent edge')

        # get the nodes that can reach node_from
        reachable_from_node_from = MultiSet()
        for node in self.inverted_index_paths.get(node_from, set()):
            reachable_from_node_from[node] = self.index_path_counts[(node, node_from)]
        assert reachable_from_node_from[node_from] == 0, reachable_from_node_from
        assert reachable_from_node_from[node_to] == 0, reachable_from_node_from

        # get the nodes that are reachable from node_to
        reachable_from_node_to = MultiSet()
        for node in self.index_paths.get(node_to, set()):
            reachable_from_node_to[node] = self.index_path_counts[(node_to, node)]
        assert reachable_from_node_to[node_from] == 0, reachable_from_node_to
        assert reachable_from_node_to[node_to] == 0, reachable_from_node_to

        # remove the node_to's reachable nodes from node_from
        for to_node, count in reachable_from_node_to.items():
            self.index_path_counts[(node_from, to_node)] -= count
            if self.index_path_counts[(node_from, to_node)] == 0:
                self.index_paths[node_from].remove(to_node)
                if not self.index_paths[node_from]:
                    del self.index_paths[node_from]
                self.inverted_index_paths[to_node].remove(node_from)
                if not self.inverted_index_paths[to_node]:
                    del self.inverted_index_paths[to_node]

        # make node_to less reachable from all the nodes that can reach node_from
        for from_node, count in reachable_from_node_from.items():
            self.index_path_counts[(from_node, node_to)] -= count
            if self.index_path_counts[(from_node, node_to)] == 0:
                self.index_paths[from_node].remove(node_to)
                if not self.index_paths[from_node]:
                    del self.index_paths[from_node]
                self.inverted_index_paths[node_to].remove(from_node)
                if not self.inverted_index_paths[node_to]:
                    del self.inverted_index_paths[node_to]

        # remove the direct edge
        self.index_path_counts[(node_from, node_to)] -= 1
        if self.index_path_counts[(node_from, node_to)] == 0:
            self.index_paths[node_from].remove(node_to)
            if not self.index_paths[node_from]:
                del self.index_paths[node_from]
            self.inverted_index_paths[node_to].remove(node_from)
            if not self.inverted_index_paths[node_to]:
                del self.inverted_index_paths[node_to]
        self.edge_counts[(node_from, node_to)] -= 1


if __name__ == '__main__':
    # TODO: error cases
    # ab,bc,bc,cd remove bc leaves behind 2x ad indirect edges
    # ab, cd, bc -> ad not reachable
    idx = AcyclicGraphReachabilityIndex()
    idx.add_edge('a', 'b')
    idx.add_edge('c', 'd')
    idx.add_edge('b', 'c')
    print(idx.index_paths)
    print(idx.inverted_index_paths)
    print(idx.index_path_counts)
    print(idx.edge_counts)
