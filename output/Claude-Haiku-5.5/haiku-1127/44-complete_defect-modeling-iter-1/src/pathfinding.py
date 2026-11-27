"""Path computation for the Beijing Subway.

Implements Dijkstra's algorithm on a binary-heap priority queue (``MinPQ``).
The search runs over states ``(station, arrival line, transfers)`` so that
transfer limits and line preferences are honoured exactly. Edge distances are
the base weights; the search key adds optional penalties for line preference
and transfers depending on the query mode.
"""

import heapq
import itertools
from typing import Dict, List, Optional, Tuple

from fare_calculator import calculate_estimated_time
from models import Edge, Graph, Route, RouteSegment

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Multiplier applied to edges on non-preferred lines when a preference is set.
PREFERRED_LINE_FACTOR = 1.5
# Penalty per transfer (in meters-equivalent) used by the comprehensive mode.
TRANSFER_PENALTY_M = 500.0
# Very large weight per transfer so that transfers dominate in least_transfer mode.
LEAST_TRANSFER_WEIGHT = 1.0e9


class PathNotFoundError(Exception):
    """Raised when no path satisfying the constraints exists."""


class MinPQ:
    """Min priority queue backed by a binary heap (``heapq``).

    Items with equal priority are returned in insertion order.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[float, int, object]] = []
        self._counter = itertools.count()

    def insert(self, priority: float, item) -> None:
        """Insert ``item`` with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self) -> float:
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum number of line changes allowed, or None for no limit.
        preferred_lines: Lines that are preferred; other lines are penalized.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class _Label:
    """Best known label for a search state."""

    __slots__ = ("key", "distance", "transfers")

    def __init__(self, key: float, distance: float, transfers: int) -> None:
        self.key = key            # search priority (cost including penalties)
        self.distance = distance  # real accumulated distance in meters
        self.transfers = transfers


class ShortestPath:
    """Dijkstra-based path finder from a single source station.

    Args:
        graph: The subway graph.
        source: Station number of the starting station.
        config: Query configuration; defaults to ``PathfindingConfig()``.

    Attributes:
        dist_to: Mapping from station number to the real travel distance (meters)
            of the chosen path to that station.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if source not in graph.number_to_station:
            raise ValueError(f"unknown source station number {source}")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._labels: Dict[tuple, _Label] = {}
        self._parents: Dict[tuple, tuple] = {}
        self._best_state: Dict[int, tuple] = {}
        self._search()

    def _transfer_cost(self) -> float:
        """Search-key penalty added for every transfer, depending on the mode."""
        if self.config.mode == MODE_LEAST_TRANSFER:
            return LEAST_TRANSFER_WEIGHT
        if self.config.mode == MODE_COMPREHENSIVE:
            return TRANSFER_PENALTY_M
        return 0.0

    def _search(self) -> None:
        """Run Dijkstra's algorithm over the state space and pick best labels."""
        config = self.config
        limited = config.max_transfers is not None
        preferred = set(config.preferred_lines)
        transfer_cost = self._transfer_cost()

        start = (self.source, None, 0)
        self._labels[start] = _Label(0.0, 0.0, 0)
        pq = MinPQ()
        pq.insert(0.0, start)
        done = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in done:
                continue
            label = self._labels[state]
            if key > label.key:
                continue
            done.add(state)

            vertex, line, _ = state
            for edge in self.graph.adj(vertex):
                nxt = edge.other(vertex)
                is_transfer = line is not None and edge.line != line
                new_transfers = label.transfers + (1 if is_transfer else 0)
                if limited and new_transfers > config.max_transfers:
                    continue

                factor = 1.0
                if preferred and edge.line not in preferred:
                    factor = PREFERRED_LINE_FACTOR
                step_key = edge.weight * factor + (transfer_cost if is_transfer else 0.0)
                new_key = label.key + step_key
                new_distance = label.distance + edge.weight

                next_state = (nxt, edge.line, new_transfers if limited else 0)
                existing = self._labels.get(next_state)
                if existing is None or new_key < existing.key:
                    self._labels[next_state] = _Label(new_key, new_distance, new_transfers)
                    self._parents[next_state] = (state, edge)
                    pq.insert(new_key, next_state)

        # Choose the best state per station (smallest search key).
        for state, label in self._labels.items():
            vertex = state[0]
            best = self._best_state.get(vertex)
            if best is None or label.key < self._labels[best].key:
                self._best_state[vertex] = state
        for vertex, state in self._best_state.items():
            self.dist_to[vertex] = self._labels[state].distance

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the configured constraints."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and edges of the path from source to target.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` starts with the source
            and ends with the target, and ``edges`` has one fewer element.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        if target not in self._best_state:
            raise PathNotFoundError(f"no path to station number {target}")
        state = self._best_state[target]
        vertices: List[int] = []
        edges: List[Edge] = []
        while state in self._parents:
            vertices.append(state[0])
            previous, edge = self._parents[state]
            edges.append(edge)
            state = previous
        vertices.append(state[0])
        vertices.reverse()
        edges.reverse()
        return vertices, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the path to ``target``.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        if target not in self._best_state:
            raise PathNotFoundError(f"no path to station number {target}")
        return self._labels[self._best_state[target]].transfers


def build_route(graph: Graph, numbers: List[int], edges: List[Edge], mode: str) -> Route:
    """Convert a raw path into a ``Route`` with segments, transfers, and summary data.

    Args:
        graph: The subway graph (used to translate numbers into names).
        numbers: Station numbers along the path.
        edges: Edges between consecutive stations.
        mode: Query mode label stored on the route.

    Returns:
        The populated ``Route``.
    """
    names = [graph.name_of(number) for number in numbers]
    segments: List[RouteSegment] = []
    total = 0.0

    if edges:
        current_line = edges[0].line
        segment_start = 0
        segment_distance = 0.0
        for index, edge in enumerate(edges):
            if edge.line != current_line:
                segments.append(RouteSegment(current_line, names[segment_start], names[index], segment_distance))
                current_line = edge.line
                segment_start = index
                segment_distance = 0.0
            segment_distance += edge.distance
            total += edge.distance
        segments.append(
            RouteSegment(current_line, names[segment_start], names[len(edges)], segment_distance)
        )

    transfers: List[Tuple[str, str, str]] = []
    for previous, following in zip(segments, segments[1:]):
        transfers.append((previous.end_station, previous.line_name, following.line_name))

    lines: List[str] = []
    for segment in segments:
        if segment.line_name not in lines:
            lines.append(segment.line_name)

    transfer_count = len(transfers)
    estimated_time = calculate_estimated_time(total, transfer_count)

    return Route(
        station_sequence=names,
        total_distance_m=total,
        transfer_count=transfer_count,
        segments=segments,
        transfers=transfers,
        lines=lines,
        mode=mode,
        estimated_time=estimated_time,
    )
