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
    direct_edge_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)  # {(source, dest): count}
    
    # index for "indirect" edges, which include direct edges
    index_paths: dict[str, set[str]] = field(default_factory=dict)  # {source: {dest, ...}}
    inverted_index_paths: dict[str, set[str]] = field(default_factory=dict)  # {dest: {source, ...}}
    index_path_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)  # {(source, dest): count}

    def _check(self):
        for node_from in self.index_paths:
            for node_to in self.index_paths[node_from]:
                assert node_to in self.inverted_index_paths
                assert node_from in self.inverted_index_paths[node_to]
                assert self.index_path_counts[(node_from, node_to)] > 0

    def _reachable_backwards(self, _node):
        reachable_backwards = MultiSet()
        for reachable_node in self.inverted_index_paths.get(_node, set()):
            reachable_backwards[reachable_node] = self.index_path_counts[(reachable_node, _node)]
        assert reachable_backwards[_node] == 0
        return reachable_backwards

    def _reachable_forwards(self, _node):
        reachable_forwards = MultiSet()
        for reachable_node in self.index_paths.get(_node, set()):
            reachable_forwards[reachable_node] = self.index_path_counts[(_node, reachable_node)]
        assert reachable_forwards[_node] == 0
        return reachable_forwards

    def _add_indirect_edge(self, _from, _to, _add_count):
        self._check()
        self.index_path_counts[(_from, _to)] += _add_count
        if self.index_path_counts[(_from, _to)]:
            self.index_paths.setdefault(_from, set()).add(_to)
            self.inverted_index_paths.setdefault(_to, set()).add(_from)
        else:
            if _to in self.index_paths[_from]:
                self.index_paths[_from].remove(_to)
                if not self.index_paths[_from]:
                    del self.index_paths[_from]
            if _from in self.inverted_index_paths[_to]:
                self.inverted_index_paths[_to].remove(_from)
                if not self.inverted_index_paths[_to]:
                    del self.inverted_index_paths[_to]
        self._check()

    def add_edge(self, node_from, node_to):
        # sanity check
        self._check()
        assert node_from != node_to

        # ensure acyclic invariant holds
        if self.index_path_counts[(node_to, node_from)] > 0:
            raise ValueError(f'{node_from=} is reachable from {node_to=}, adding this edge would create a cycle')

        # get the reachable nodes and check invariants
        reachable_from_node_from = self._reachable_backwards(node_from)
        reachable_from_node_to = self._reachable_forwards(node_to)
        assert reachable_from_node_from[node_to] == 0, reachable_from_node_from
        assert reachable_from_node_to[node_from] == 0, reachable_from_node_to

        # add the indirect edges:
        for from_node, from_count in reachable_from_node_from.items():
            for to_node, to_count in reachable_from_node_to.items():
                self._add_indirect_edge(from_node, to_node, from_count * to_count)

        # add the node_to's reachable nodes to node_from
        for to_node, count in reachable_from_node_to.items():
            self._add_indirect_edge(node_from, to_node, count)

        # make node_to reachable from all the nodes that can reach node_from
        for from_node, count in reachable_from_node_from.items():
            self._add_indirect_edge(from_node, node_to, count)

        # add the direct edge
        self._add_indirect_edge(node_from, node_to, 1)
        self.direct_edge_counts[(node_from, node_to)] += 1
        self._check()

    def remove_edge(self, node_from, node_to):
        # sanity check
        self._check()
        assert node_from != node_to

        # ensure there's an edge to remove
        if self.direct_edge_counts[(node_from, node_to)] == 0:
            raise ValueError(f'{node_from=} has no direct edge to {node_to=}, cannot remove nonexistent edge')

        # get the reachable nodes and check invariants
        reachable_from_node_from = self._reachable_backwards(node_from)
        reachable_from_node_to = self._reachable_forwards(node_to)
        assert reachable_from_node_from[node_to] == 0, reachable_from_node_from
        assert reachable_from_node_to[node_from] == 0, reachable_from_node_to

        # remove the indirect edges:
        for from_node, from_count in reachable_from_node_from.items():
            for to_node, to_count in reachable_from_node_to.items():
                self._add_indirect_edge(from_node, to_node, -(from_count * to_count))

        # remove the node_to's reachable nodes from node_from
        for to_node, count in reachable_from_node_to.items():
            self._add_indirect_edge(node_from, to_node, -count)

        # make node_to less reachable from all the nodes that can reach node_from
        for from_node, count in reachable_from_node_from.items():
            self._add_indirect_edge(from_node, node_to, -count)

        # remove the direct edge
        self._add_indirect_edge(node_from, node_to, -1)
        self.direct_edge_counts[(node_from, node_to)] -= 1
        self._check()


if __name__ == '__main__':
    idx = AcyclicGraphReachabilityIndex()
    idx.add_edge('a', 'b')
    idx.add_edge('b', 'c')
    idx.add_edge('b', 'c')
    idx.add_edge('c', 'd')
    idx.remove_edge('b', 'c')
    print(idx.index_paths)
    print(idx.inverted_index_paths)
    print(idx.index_path_counts)
    print(idx.direct_edge_counts)
