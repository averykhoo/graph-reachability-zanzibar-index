from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True)
class GraphIndex:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    index_nodes_from: dict = field(default_factory=dict)
    index_nodes_to: dict = field(default_factory=dict)
    index_counter: dict = field(default_factory=dict)
