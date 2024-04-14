import random
from dataclasses import dataclass
from dataclasses import field
from uuid import uuid4

from index_v1 import MultiSet


@dataclass(frozen=True, unsafe_hash=True, order=True, slots=True)
class Node:
    name: str


@dataclass(frozen=True)
class AcyclicGraphReachabilityIndexV2:
    __skip_check_invariants: bool = False
    direct_edge_counts: MultiSet[tuple[Node, Node], int] = field(default_factory=MultiSet)  # {(source, dest): count}

    # index for "indirect" edges, which include direct edges
    index_paths_counts: dict[Node, MultiSet] = field(default_factory=dict)  # {source: {dest: count}}
    inverted_index_paths: dict[Node, set[Node]] = field(default_factory=dict)  # {dest: {source, ...}}

    def _check_invariants(self):
        if self.__skip_check_invariants:
            return

        def _check_node_name(_node: Node):
            assert isinstance(_node, Node), _node
            assert len(_node.name) > 0, _node

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

    def _reachable_backwards(self, _node: Node):
        reachable_backwards = MultiSet()
        for reachable_node in self.inverted_index_paths.get(_node, set()):
            reachable_backwards[reachable_node] = self.index_paths_counts[reachable_node][_node]
        return reachable_backwards

    def _reachable_forwards(self, _node: Node):
        reachable_forwards = self.index_paths_counts.get(_node, MultiSet()).copy()
        return reachable_forwards

    def _add_indirect_edge(self, _from: Node, _to: Node, _add_count: int):
        assert _add_count != 0
        assert _from != _to

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
        assert multiplier in {-1, 1}

        # we need to remove direct edge first to preserve the invariant
        if node_from != node_to and multiplier < 0:
            self.direct_edge_counts[(node_from, node_to)] += multiplier
            self._add_indirect_edge(node_from, node_to, multiplier)

        # alternatively, remove the entire node from direct edges
        if node_from == node_to:
            assert multiplier == -1
            _to_remove = [edge for edge in self.direct_edge_counts if node_from in edge]
            for edge in _to_remove:
                del self.direct_edge_counts[edge]

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
        if node_from != node_to and multiplier > 0:
            self._add_indirect_edge(node_from, node_to, multiplier)
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

    def remove_edge(self, node_from: Node, node_to: Node):
        # sanity check
        assert node_from != node_to

        # ensure there's an edge to remove
        if self.direct_edge_counts[(node_from, node_to)] == 0:
            raise ValueError(f'{node_from=} has no direct edge to {node_to=}, cannot remove nonexistent edge')

        self._add_edge_unsafe(node_from, node_to, -1)

    def remove_node(self, node: Node):
        self._add_edge_unsafe(node, node, -1)

    def check_reachable(self, node_from: Node, node_to: Node):
        # probably slightly faster than using the forward index
        return node_from in self.inverted_index_paths.get(node_to, set())

    def lookup_reachable(self, node_from: Node):
        return list(self.index_paths_counts.get(node_from, MultiSet()).keys())

    def lookup_reverse(self, node_to: Node):
        return list(self.inverted_index_paths.get(node_to))


def random_test(edges):
    edges = [(Node(x), Node(y)) for x, y in edges]

    def create_index(_edges: list[tuple[Node, Node, bool]]):
        _index = AcyclicGraphReachabilityIndexV2()
        for _from, _to, _add in _edges:
            if _add:
                _index.add_edge(_from, _to)
            else:
                _index.remove_edge(_from, _to)
        return _index

    original_edges = [(_from, _to, True) for _from, _to in edges]
    original_index = create_index(original_edges)
    assert original_index == create_index(sorted(original_edges))

    # randomize
    test_edges = []
    for _ in range(1000):
        temp_edges = original_edges.copy()
        random.shuffle(temp_edges)
        assert original_index == create_index(temp_edges)
        test_edges.append(temp_edges)

    # randomly insert a new edge and delete it later
    for temp_edges in test_edges:
        add_edges = []  # new edges to insert
        for node_from, node_to, _ in temp_edges:
            for _ in range(random.randint(0, 5)):  # add each edge up to 5 extra times
                if random.random() < 0.5:
                    add_edges.append((node_from, node_to))
                else:
                    new_node = Node(str(uuid4()))  # randomly add an intermediate node
                    add_edges.append((node_from, new_node))
                    add_edges.append((new_node, node_to))
        random.shuffle(add_edges)  # randomizing the order means some intermediate nodes may never connect, but wtv
        for node_from, node_to in add_edges:
            _idx = random.randint(0, len(temp_edges))  # insert into a random location
            temp_edges.insert(_idx, (node_from, node_to, True))
            _idx = random.randint(_idx + 1, len(temp_edges))  # remove sometime afterwards
            temp_edges.insert(_idx, (node_from, node_to, False))
        assert original_index == create_index(temp_edges)

    return original_index


if __name__ == '__main__':
    idx = random_test(['ab', 'bc', 'bd', 'ac', 'cd'])
    print(idx.index_paths_counts)
    print(idx.inverted_index_paths)
    print(idx.direct_edge_counts)
    idx.remove_node(Node('d'))
    print(idx.index_paths_counts)
    print(idx.inverted_index_paths)
    print(idx.direct_edge_counts)
