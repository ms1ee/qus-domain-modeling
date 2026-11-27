"""
Path computation for the Beijing Subway network.

Implements Dijkstra's algorithm over the weighted directed graph with:
    * a heap-based minimum priority queue (MinPQ),
    * composite costs for the three query modes (shortest distance,
      least transfers, comprehensive optimum),
    * a maximum transfer limit and line preferences.

Search states are (station number, arriving line) pairs so that line changes
(transfers) can be counted correctly at multi-line interchange stations.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance of one transfer (about 5 minutes at 1.5 minutes per km).
TRANSFER_PENALTY_METERS = 5.0 / 1.5 * 1000.0

# Extra distance-equivalent cost for riding a line that is not preferred.
PREFERENCE_PENALTY_METERS = 500.0

Cost = Tuple[float, float]
State = Tuple[int, Optional[str]]


class PathfindingError(Exception):
    """Base class for path computation errors."""


class NoRouteError(PathfindingError):
    """Raised when no route satisfies the constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: Lines preferred by the passenger. When non-empty,
            riding other lines incurs a small penalty.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])

    def is_preferred(self, line: str) -> bool:
        """Return True if riding this line carries no preference penalty."""
        return not self.preferred_lines or line in self.preferred_lines


class MinPQ:
    """Minimum priority queue based on a binary heap.

    Items are ordered by their key; ties are broken by insertion order so
    that items themselves are never compared.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, Any]] = []
        self._counter = itertools.count()

    def insert(self, item: Any, key: Any) -> None:
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self) -> Any:
        """Remove and return the item with the smallest key."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        _, _, item = heapq.heappop(self._heap)
        return item

    def min_key(self) -> Any:
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._heap)


class ShortestPath:
    """Single-source shortest path computation using Dijkstra's algorithm.

    Attributes:
        graph: The graph searched.
        source: Source station number.
        config: Query configuration.
        dist_to: Actual travelled distance in meters to each reached station
            along its optimal path (source maps to 0.0).
        cost_to: Composite optimisation cost to each reached station.
    """

    def __init__(
        self,
        graph: Graph,
        source: int,
        config: Optional[PathfindingConfig] = None,
    ) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()

        self.dist_to: Dict[int, float] = {}
        self.cost_to: Dict[int, Cost] = {}

        self._state_cost: Dict[State, Cost] = {}
        self._state_dist: Dict[State, float] = {}
        self._state_transfers: Dict[State, int] = {}
        self._edge_to: Dict[State, Tuple[State, Edge]] = {}
        self._best_state: Dict[int, State] = {}

        self._run()

    # ----- cost model --------------------------------------------------------
    def _increment(self, edge: Edge, transfer: int) -> Cost:
        """Return the cost increment for traversing an edge."""
        penalty = 0.0 if self.config.is_preferred(edge.line) else PREFERENCE_PENALTY_METERS
        effective = edge.weight + penalty
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (float(transfer), effective)
        if mode == MODE_COMPREHENSIVE:
            return (effective + transfer * TRANSFER_PENALTY_METERS, 0.0)
        return (effective, 0.0)

    # ----- Dijkstra ----------------------------------------------------------
    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        start: State = (self.source, None)
        zero: Cost = (0.0, 0.0)
        self._state_cost[start] = zero
        self._state_dist[start] = 0.0
        self._state_transfers[start] = 0

        pq = MinPQ()
        pq.insert(start, zero)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line = state
            cost = self._state_cost[state]
            dist = self._state_dist[state]
            transfers = self._state_transfers[state]

            for edge in self.graph.adjacent(node):
                transfer = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + transfer
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                next_state: State = (edge.dest, edge.line)
                if next_state in settled:
                    continue

                inc = self._increment(edge, transfer)
                new_cost = (cost[0] + inc[0], cost[1] + inc[1])
                if next_state not in self._state_cost or new_cost < self._state_cost[next_state]:
                    self._state_cost[next_state] = new_cost
                    self._state_dist[next_state] = dist + edge.weight
                    self._state_transfers[next_state] = new_transfers
                    self._edge_to[next_state] = (state, edge)
                    pq.insert(next_state, new_cost)

        # Pick the best state for each station.
        for state, cost in self._state_cost.items():
            node = state[0]
            if node not in self._best_state or cost < self.cost_to[node]:
                self._best_state[node] = state
                self.cost_to[node] = cost
                self.dist_to[node] = self._state_dist[state]

    # ----- queries -----------------------------------------------------------
    def has_path_to(self, target: int) -> bool:
        """Return True if the target station is reachable under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Reconstruct the optimal path to a target station.

        Returns:
            A tuple (stations, edges) where stations are station numbers in
            travel order from source to target, and edges are the traversed
            edges in the same order. Both are empty if the target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []

        state = self._best_state[target]
        nodes: List[int] = []
        edges: List[Edge] = []
        while True:
            nodes.append(state[0])
            if state not in self._edge_to:
                break
            prev_state, edge = self._edge_to[state]
            edges.append(edge)
            state = prev_state

        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the optimal path to the target."""
        if not self.has_path_to(target):
            return 0
        return self._state_transfers[self._best_state[target]]


@dataclass
class TransferDetail:
    """A transfer event at an interchange station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class RouteSegment:
    """A contiguous run of stations travelled on one line."""

    line_name: str
    station_count: int
    distance_m: float


@dataclass
class RouteResult:
    """Complete result of a path query.

    Attributes:
        station_names: Station names in travel order (start to end).
        edges: Traversed edges in travel order.
        total_distance_m: Total travelled distance in meters.
        transfer_count: Number of transfers.
        transfers: Transfer details.
        segments: Line segments in travel order.
        lines: Distinct line names involved, in order of first use.
    """

    station_names: List[str]
    edges: List[Edge]
    total_distance_m: float
    transfer_count: int
    transfers: List[TransferDetail] = field(default_factory=list)
    segments: List[RouteSegment] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)


def find_route(
    graph: Graph,
    number_to_name: Dict[int, str],
    source: int,
    target: int,
    config: Optional[PathfindingConfig] = None,
) -> RouteResult:
    """Compute a route between two stations and describe it.

    Args:
        graph: Subway network graph.
        number_to_name: Mapping from station number to station name.
        source: Starting station number.
        target: Ending station number.
        config: Query configuration.

    Returns:
        A RouteResult describing the optimal path.

    Raises:
        NoRouteError: If no route satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    sp = ShortestPath(graph, source, config)
    if not sp.has_path_to(target):
        raise NoRouteError(
            f"No route found between '{number_to_name.get(source, source)}' and "
            f"'{number_to_name.get(target, target)}' under the current constraints"
        )

    nodes, edges = sp.path_with_edges(target)
    names = [number_to_name[n] for n in nodes]

    # Transfers: a change of line between consecutive edges.
    transfers: List[TransferDetail] = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append(
                TransferDetail(
                    station_name=names[i],
                    from_line=edges[i - 1].line,
                    to_line=edges[i].line,
                )
            )

    # Segments: group consecutive edges by line.
    segments: List[RouteSegment] = []
    for edge in edges:
        if segments and segments[-1].line_name == edge.line:
            last = segments[-1]
            last.station_count += 1
            last.distance_m += edge.weight
        else:
            segments.append(RouteSegment(edge.line, 2, edge.weight))

    lines: List[str] = []
    for seg in segments:
        if seg.line_name not in lines:
            lines.append(seg.line_name)

    total_distance = sum(edge.weight for edge in edges)

    return RouteResult(
        station_names=names,
        edges=edges,
        total_distance_m=total_distance,
        transfer_count=len(transfers),
        transfers=transfers,
        segments=segments,
        lines=lines,
    )


def find_shortest_distance_route(
    graph: Graph,
    number_to_name: Dict[int, str],
    source: int,
    target: int,
    max_transfers: Optional[int] = None,
    preferred_lines: Optional[Sequence[str]] = None,
) -> RouteResult:
    """Shortest-distance query (minimises travelled meters)."""
    config = PathfindingConfig(MODE_SHORTEST_DISTANCE, max_transfers, preferred_lines)
    return find_route(graph, number_to_name, source, target, config)


def find_least_transfer_route(
    graph: Graph,
    number_to_name: Dict[int, str],
    source: int,
    target: int,
    max_transfers: Optional[int] = None,
    preferred_lines: Optional[Sequence[str]] = None,
) -> RouteResult:
    """Minimum-transfer query (minimises line changes, then distance)."""
    config = PathfindingConfig(MODE_LEAST_TRANSFER, max_transfers, preferred_lines)
    return find_route(graph, number_to_name, source, target, config)


def find_comprehensive_route(
    graph: Graph,
    number_to_name: Dict[int, str],
    source: int,
    target: int,
    max_transfers: Optional[int] = None,
    preferred_lines: Optional[Sequence[str]] = None,
) -> RouteResult:
    """Comprehensive optimum query (distance plus weighted transfer penalty)."""
    config = PathfindingConfig(MODE_COMPREHENSIVE, max_transfers, preferred_lines)
    return find_route(graph, number_to_name, source, target, config)
