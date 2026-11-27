"""Shortest path computation on the subway graph using Dijkstra's algorithm.

The search runs over labels of the form (station, arriving line, transfers),
which lets the algorithm count line changes exactly and enforce a maximum
transfer limit. Labels are kept in an indexed priority queue (MinPQ), so the
running time is O((V+E) log V) for a fixed number of labels per station.

Supported modes:
    shortest_distance: minimise total distance (meters).
    least_transfer:    minimise number of transfers, then distance.
    comprehensive:     minimise distance plus a penalty per transfer.
"""

from typing import Any, Dict, List, Optional, Tuple

from models import Edge, Graph
from priority_queue import MinPQ

# Equivalent distance (meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000.0
# Equivalent distance (meters) added for each edge on a non-preferred line.
LINE_PREFERENCE_PENALTY_M = 500.0
VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: Lines to prefer; empty list means no preference.
    """

    def __init__(self) -> None:
        self.mode: str = "shortest_distance"
        self.max_transfers: Optional[int] = None
        self.preferred_lines: List[str] = []

    def validate(self) -> None:
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if not isinstance(self.preferred_lines, list):
            raise ValueError("preferred_lines must be a list of line names")


class _Label:
    """A search state reached at a station, with the path information to get there."""

    __slots__ = ("node", "line", "transfers", "cost", "distance", "prev", "edge")

    def __init__(self, node: int, line: Optional[str], transfers: int, cost: float,
                 distance: float, prev: Optional["_Label"], edge: Optional[Edge]) -> None:
        self.node = node            # station number
        self.line = line            # line used to arrive (None at the source)
        self.transfers = transfers  # number of line changes so far
        self.cost = cost            # distance plus preference penalties
        self.distance = distance    # real travelled distance in meters
        self.prev = prev            # previous label on the path
        self.edge = edge            # edge used to arrive here


class ShortestPath:
    """Single-source shortest path computation.

    Attributes:
        dist_to: Mapping station number -> real travelled distance in meters
            along the optimal path (only reachable stations are included).
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.dist_to: Dict[int, float] = {}
        self._transfers: Dict[int, int] = {}
        self._best: Dict[int, _Label] = {}
        self._run()

    def _key(self, label: _Label) -> Tuple[float, ...]:
        """Priority key of a label according to the configured mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (float(label.transfers), label.cost)
        if mode == "comprehensive":
            return (label.cost + label.transfers * TRANSFER_PENALTY_M,)
        return (label.cost,)

    def _step_cost(self, edge: Edge) -> float:
        """Cost of traversing an edge, including line preference penalties."""
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            return edge.distance + LINE_PREFERENCE_PENALTY_M
        return float(edge.distance)

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over the (station, line, transfers) labels."""
        max_transfers = self.config.max_transfers
        start = _Label(self.source, None, 0, 0.0, 0.0, None, None)
        start_item = (self.source, None, 0)
        label_of: Dict[Tuple[Any, ...], _Label] = {start_item: start}
        pq = MinPQ()
        pq.insert(start_item, self._key(start))

        while not pq.is_empty():
            item = pq.del_min()
            current = label_of[item]
            node = current.node
            # Labels leave the queue in non-decreasing key order, so the first
            # label popped for a station is the optimal one for that station.
            if node not in self._best:
                self._best[node] = current
                self.dist_to[node] = current.distance
                self._transfers[node] = current.transfers

            for edge in self.graph.adj(node):
                other = edge.other(node)
                transfers = current.transfers
                if current.line is not None and edge.line != current.line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                candidate = _Label(
                    node=other,
                    line=edge.line,
                    transfers=transfers,
                    cost=current.cost + self._step_cost(edge),
                    distance=current.distance + edge.distance,
                    prev=current,
                    edge=edge,
                )
                candidate_item = (other, edge.line, transfers)
                existing = label_of.get(candidate_item)
                candidate_key = self._key(candidate)
                if existing is not None and self._key(existing) <= candidate_key:
                    continue
                label_of[candidate_item] = candidate
                pq.push_or_decrease(candidate_item, candidate_key)

    def has_path_to(self, target: int) -> bool:
        """Return True if the target station is reachable under the configuration."""
        return target in self._best

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the optimal path from the source to ``target``.

        Returns:
            A tuple (stations, edges): the station numbers from source to target
            and the edges traversed between consecutive stations. If the target
            is unreachable, ([], []) is returned.
        """
        if target not in self._best:
            return [], []
        chain: List[_Label] = []
        label: Optional[_Label] = self._best[target]
        while label is not None:
            chain.append(label)
            label = label.prev
        chain.reverse()
        nodes = [item.node for item in chain]
        edges = [item.edge for item in chain[1:] if item.edge is not None]
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the optimal path to ``target``.

        Raises:
            ValueError: If the target is unreachable.
        """
        if target not in self._transfers:
            raise ValueError(f"Station {target} is not reachable from the source")
        return self._transfers[target]
