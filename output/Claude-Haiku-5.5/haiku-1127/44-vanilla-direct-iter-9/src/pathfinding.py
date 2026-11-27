"""Route search for the Beijing Subway network.

Implements Dijkstra's algorithm with a binary-heap priority queue (``MinPQ``).
The search runs over states ``(station, incoming_line)`` so that line changes
(transfers) can be counted and optimized exactly.

Supported query modes:
    shortest_distance -- minimize total distance (meters)
    least_transfer    -- minimize transfers, then distance
    comprehensive     -- minimize distance plus a time-equivalent transfer penalty
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# 5 minutes per transfer at 1.5 minutes per kilometer ~= 3.33 km of travel.
TRANSFER_EQUIVALENT_METERS = 3333.0
# Soft penalty applied to edges that are not on a preferred line.
LINE_PREFERENCE_PENALTY_METERS = 1000.0


class MinPQ:
    """Binary min-heap priority queue.

    Items are stored with comparable keys; ``del_min`` returns the item with
    the smallest key. Insertion and removal run in O(log n).
    """

    def __init__(self) -> None:
        self._keys: list = []
        self._items: list = []

    def __len__(self) -> int:
        return len(self._keys)

    def size(self) -> int:
        """Number of elements in the queue."""
        return len(self._keys)

    def is_empty(self) -> bool:
        """Return True if the queue holds no elements."""
        return not self._keys

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._items:
            raise IndexError("priority queue is empty")
        return self._items[0]

    def insert(self, key, item) -> None:
        """Insert an item with the given priority key."""
        self._keys.append(key)
        self._items.append(item)
        self._swim(len(self._keys) - 1)

    def del_min(self):
        """Remove and return a ``(key, item)`` pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue underflow")
        key, item = self._keys[0], self._items[0]
        last = len(self._keys) - 1
        self._swap(0, last)
        self._keys.pop()
        self._items.pop()
        if self._keys:
            self._sink(0)
        return key, item

    def _greater(self, i: int, j: int) -> bool:
        return self._keys[i] > self._keys[j]

    def _swap(self, i: int, j: int) -> None:
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k: int) -> None:
        """Move the element at index ``k`` up until heap order holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._greater(parent, k):
                self._swap(parent, k)
                k = parent
            else:
                break

    def _sink(self, k: int) -> None:
        """Move the element at index ``k`` down until heap order holds."""
        n = len(self._keys)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._greater(child, child + 1):
                child += 1
            if not self._greater(k, child):
                break
            self._swap(k, child)
            k = child


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: Lines that are favoured; other lines carry a soft penalty.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown query mode '{mode}'")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])


class _Label:
    """Best known information for one search state."""

    __slots__ = ("key", "distance", "cost", "transfers", "prev", "edge")

    def __init__(self, key, distance, cost, transfers, prev, edge):
        self.key = key              # priority used for ordering
        self.distance = distance    # actual travelled distance (meters)
        self.cost = cost            # distance plus preference penalties
        self.transfers = transfers  # number of line changes so far
        self.prev = prev            # predecessor state, None for the source
        self.edge = edge            # edge used to reach this state


State = Tuple[int, Optional[str]]


class ShortestPath:
    """Dijkstra-based search from a source station.

    Attributes:
        source: Station number the search starts from.
        config: The ``PathfindingConfig`` used for the search.
        dist_to: Mapping from reachable station number to actual distance (m).
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None):
        if not graph.has_node(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._labels: Dict[State, _Label] = {}
        self._best_state: Dict[int, State] = {}
        self.dist_to: Dict[int, float] = {}
        self._run()

    def _make_key(self, cost: float, transfers: int):
        """Build the ordering key for the configured query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, cost)
        if mode == MODE_COMPREHENSIVE:
            return (cost + transfers * TRANSFER_EQUIVALENT_METERS,)
        return (cost,)

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        start: State = (self.source, None)
        self._labels[start] = _Label(self._make_key(0, 0), 0, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(self._labels[start].key, start)

        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            key, state = pq.del_min()
            label = self._labels[state]
            if key != label.key:
                continue  # stale queue entry
            station, line = state
            for edge in self._graph.adj(station):
                nxt = edge.other(station)
                transfers = label.transfers
                if line is not None and edge.line != line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                distance = label.distance + edge.distance
                penalty = 0.0
                if preferred and edge.line not in preferred:
                    penalty = LINE_PREFERENCE_PENALTY_METERS
                cost = label.cost + edge.distance + penalty
                new_key = self._make_key(cost, transfers)
                nstate: State = (nxt, edge.line)
                existing = self._labels.get(nstate)
                if existing is None or new_key < existing.key:
                    self._labels[nstate] = _Label(new_key, distance, cost, transfers, state, edge)
                    pq.insert(new_key, nstate)

        # Select the best state for every station reached.
        for state, label in self._labels.items():
            station = state[0]
            current = self._best_state.get(station)
            if current is None or label.key < self._labels[current].key:
                self._best_state[station] = state
        for station, state in self._best_state.items():
            self.dist_to[station] = self._labels[state].distance

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable within the configured limits."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and edges of the best path to ``target``.

        Returns ``([], [])`` if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        stations: List[int] = []
        edges: List[Edge] = []
        current: Optional[State] = state
        while current is not None:
            label = self._labels[current]
            stations.append(current[0])
            if label.prev is None:
                break
            edges.append(label.edge)
            current = label.prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the best path to ``target``.

        Returns -1 if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return -1
        return self._labels[state].transfers


@dataclass
class RouteResult:
    """Outcome of a successful route query.

    Attributes:
        station_numbers: Ordered station numbers from start to end.
        edges: Ordered edges traversed between consecutive stations.
        total_distance: Sum of edge distances in meters.
        transfer_count: Number of line changes along the route.
        lines: Unique line names in order of first use.
    """

    station_numbers: List[int]
    edges: List[Edge]
    total_distance: float
    transfer_count: int
    lines: List[str] = field(default_factory=list)


def _unique_lines(edges: Sequence[Edge]) -> List[str]:
    """Return line names in order of first appearance."""
    lines: List[str] = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def compute_route(
    graph: Graph,
    source: int,
    target: int,
    config: Optional[PathfindingConfig] = None,
) -> Optional[RouteResult]:
    """Compute a route between two stations.

    Returns:
        A ``RouteResult``, or None if no route satisfies the configuration.

    Raises:
        ValueError: If the source or target station is not in the graph.
    """
    if not graph.has_node(target):
        raise ValueError(f"Target station {target} is not in the graph")
    search = ShortestPath(graph, source, config)
    if not search.has_path_to(target):
        return None
    numbers, edges = search.path_with_edges(target)
    total = sum(edge.distance for edge in edges)
    return RouteResult(
        station_numbers=numbers,
        edges=edges,
        total_distance=total,
        transfer_count=search.get_transfer_count(target),
        lines=_unique_lines(edges),
    )
