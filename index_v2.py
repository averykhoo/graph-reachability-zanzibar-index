from dataclasses import dataclass
from dataclasses import field

from index_v1 import MultiSet


@dataclass(frozen=True)
class AcyclicGraphReachabilityIndexV2:
    direct_edge_counts: MultiSet[tuple[str, str], int] = field(default_factory=MultiSet)  # {(source, dest): count}

    # index for "indirect" edges, which include direct edges
    index_paths_counts: dict[str, MultiSet] = field(default_factory=dict)  # {source: {dest: count}}
    inverted_index_paths: dict[str, set[str]] = field(default_factory=dict)  # {dest: {source, ...}}

    def _check_invariants(self):
        def _check_node_name(_node):
            assert isinstance(_node, str), _node
            assert len(_node) > 0, _node

        for node_from in self.index_paths_counts:
            _check_node_name(node_from)
            assert node_from not in self.index_paths_counts[node_from]  # no cycles
            for node_to, count in self.index_paths_counts[node_from].items():
                assert node_to in self.inverted_index_paths
                assert node_from in self.inverted_index_paths[node_to]
                assert count > 0

        # make sure the inverted index exactly matches the forward index
        for node_to in self.inverted_index_paths:
            for node_from in self.inverted_index_paths[node_to]:
                assert node_to in self.index_paths_counts[node_from]  # might also raise index error if missing

        # the indirect edges must always contain the direct edges
        for (node_from, node_to), count in self.direct_edge_counts.items():
            assert self.index_paths_counts[node_from][node_to] >= count, (
                node_from, node_to, self.direct_edge_counts, self.index_paths_counts)

    def _reachable_backwards(self, _node):
        reachable_backwards = MultiSet()
        for reachable_node in self.inverted_index_paths.get(_node, set()):
            reachable_backwards[reachable_node] = self.index_paths_counts[reachable_node][_node]
        return reachable_backwards

    def _reachable_forwards(self, _node):
        reachable_forwards = self.index_paths_counts.get(_node, MultiSet()).copy()
        return reachable_forwards

    def _add_indirect_edge(self, _from: str, _to: str, _add_count: int):
        self.index_paths_counts.setdefault(_from, MultiSet())[_to] += _add_count
        if self.index_paths_counts[_from][_to]:
            self.inverted_index_paths.setdefault(_to, set()).add(_from)
        else:
            if not self.index_paths_counts[_from]:
                del self.index_paths_counts[_from]
            if _from in self.inverted_index_paths[_to]:
                self.inverted_index_paths[_to].remove(_from)
                if not self.inverted_index_paths[_to]:
                    del self.inverted_index_paths[_to]

        # final safety check
        self._check_invariants()

    def _add_edge_unsafe(self, node_from, node_to, multiplier):
        # if multiplier is zero, there's probably a bug somewhere
        assert multiplier != 0

        # we need to remove direct edge first to preserve the invariant
        if multiplier < 0:
            self.direct_edge_counts[(node_from, node_to)] += multiplier

        # get the reachable nodes
        reachable_from_node_from = self._reachable_backwards(node_from)
        reachable_from_node_to = self._reachable_forwards(node_to)

        # ensure we're not creating a cycle
        assert reachable_from_node_from[node_to] == 0, reachable_from_node_from
        assert reachable_from_node_to[node_from] == 0, reachable_from_node_to

        # add the indirect edges:
        for from_node, from_count in reachable_from_node_from.items():
            for to_node, to_count in reachable_from_node_to.items():
                self._add_indirect_edge(from_node, to_node, from_count * to_count * multiplier)

        # add the node_to's reachable nodes to node_from
        for to_node, count in reachable_from_node_to.items():
            self._add_indirect_edge(node_from, to_node, count * multiplier)

        # make node_to reachable from all the nodes that can reach node_from
        for from_node, count in reachable_from_node_from.items():
            self._add_indirect_edge(from_node, node_to, count * multiplier)

        # add the direct edge last to preserve the invariant
        self._add_indirect_edge(node_from, node_to, multiplier)
        if multiplier > 0:
            self.direct_edge_counts[(node_from, node_to)] += multiplier

        # final safety check
        self._check_invariants()

    def add_edge(self, node_from, node_to):
        # sanity check
        assert node_from != node_to

        # ensure acyclic invariant holds
        if self.index_paths_counts.get(node_to, MultiSet())[node_from] > 0:
            raise ValueError(f'{node_from=} is reachable from {node_to=}, adding this edge would create a cycle')

        self._add_edge_unsafe(node_from, node_to, 1)

    def remove_edge(self, node_from, node_to):
        # sanity check
        assert node_from != node_to

        # ensure there's an edge to remove
        if self.direct_edge_counts[(node_from, node_to)] == 0:
            raise ValueError(f'{node_from=} has no direct edge to {node_to=}, cannot remove nonexistent edge')

        self._add_edge_unsafe(node_from, node_to, -1)


if __name__ == '__main__':
    idx = AcyclicGraphReachabilityIndexV2()
    idx.add_edge('a', 'b')
    idx.add_edge('b', 'c')
    idx.add_edge('c', 'd')
    idx.add_edge('b', 'c')
    idx.remove_edge('b', 'c')
    print(idx.index_paths_counts)
    print(idx.inverted_index_paths)
    print(idx.direct_edge_counts)
