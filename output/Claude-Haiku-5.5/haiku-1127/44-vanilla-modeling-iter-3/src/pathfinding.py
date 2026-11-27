"""Shortest-path computation on the subway graph.

The search runs Dijkstra's algorithm over *states* ``(station, arriving_line)``
so that line changes (transfers) can be counted exactly. Priorities are kept in
a binary-heap based priority queue (``MinPQ``), giving O((V+E) log V) behaviour.

Supported modes:
    shortest_distance: minimise total distance in meters.
    least_transfer:    minimise transfers, breaking ties by distance.
    comprehensive:     minimise distance plus a transfer penalty expressed in
                       meters (about 5 minutes of travel time, i.e. roughly
                       3333 m at 1.5 min/km).
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Transfer cost in the composite score: ~5 minutes at ~1.5 minutes per km.
TRANSFER_EQUIVALENT_DISTANCE_M = 5.0 / 1.5 * 1000.0
# Soft penalty added for each edge that is not on a preferred line.
PREFERENCE_PENALTY_M = 1000.0

State = Tuple[int, Optional[str]]


@dataclass
class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: Lines the passenger prefers; edges on other lines
            incur a soft penalty.
    """

    mode: str = MODE_SHORTEST_DISTANCE
    max_transfers: Optional[int] = None
    preferred_lines: List[str] = field(default_factory=list)

    def validate(self) -> None:
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}"
            )
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if not isinstance(self.preferred_lines, list):
            raise ValueError("preferred_lines must be a list of line names")


class MinPQ:
    """Min-priority queue built on ``heapq`` (binary heap).

    Items with equal priority are served in insertion order; the sequence
    counter also prevents comparison of the items themselves.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, Any]] = []
        self._seq = itertools.count()

    def insert(self, item: Any, priority: Any) -> None:
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._seq), item))

    def del_min(self) -> Any:
        """Remove and return the item with the smallest priority.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        return heapq.heappop(self._heap)[2]

    def min_priority(self) -> Any:
        """Return the smallest priority without removing the item."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class ShortestPath:
    """Single-source optimal path computation (Dijkstra over line-aware states).

    Attributes:
        graph: The graph searched.
        source: Source station number.
        config: The ``PathfindingConfig`` used.
        dist_to: Mapping from station number to the actual distance (meters)
            of the chosen path reaching it.
    """

    def __init__(
        self,
        graph: Graph,
        source: int,
        config: Optional[PathfindingConfig] = None,
    ) -> None:
        if source not in graph.adjacency:
            raise KeyError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()

        self.dist_to: Dict[int, float] = {}
        # state -> (score, distance, transfers, accumulated penalty)
        self._labels: Dict[State, Tuple[Tuple[float, ...], float, int, float]] = {}
        # state -> (parent state, edge used to reach it)
        self._parent: Dict[State, Tuple[State, Edge]] = {}
        # station number -> best state reaching it
        self._best_state: Dict[int, State] = {}
        self._preferred = set(self.config.preferred_lines)
        self._run()

    def _score(self, distance: float, transfers: int, penalty: float) -> Tuple[float, ...]:
        """Compute the comparable cost of a partial path according to the mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (float(transfers), distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            return (distance + penalty + transfers * TRANSFER_EQUIVALENT_DISTANCE_M,)
        return (distance + penalty,)

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over line-aware states."""
        start: State = (self.source, None)
        self._labels[start] = (self._score(0.0, 0, 0.0), 0.0, 0, 0.0)
        queue = MinPQ()
        queue.insert(start, self._labels[start][0])
        settled = set()
        max_transfers = self.config.max_transfers

        while not queue.is_empty():
            state = queue.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, last_line = state
            _, dist_here, transfers_here, penalty_here = self._labels[state]

            for edge in self.graph.neighbors(node):
                next_node = edge.other(node)
                is_transfer = last_line is not None and last_line != edge.line
                new_transfers = transfers_here + (1 if is_transfer else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                penalty = penalty_here
                if self._preferred and edge.line not in self._preferred:
                    penalty += PREFERENCE_PENALTY_M
                new_distance = dist_here + edge.distance
                next_state: State = (next_node, edge.line)
                if next_state in settled:
                    continue
                score = self._score(new_distance, new_transfers, penalty)
                existing = self._labels.get(next_state)
                if existing is None or score < existing[0]:
                    self._labels[next_state] = (score, new_distance, new_transfers, penalty)
                    self._parent[next_state] = (state, edge)
                    queue.insert(next_state, score)

        # Choose the best state for every reachable station.
        best_score: Dict[int, Tuple[float, ...]] = {}
        for state, (score, _dist, _trans, _pen) in self._labels.items():
            node = state[0]
            if node not in best_score or score < best_score[node]:
                best_score[node] = score
                self._best_state[node] = state

        for node, state in self._best_state.items():
            self.dist_to[node] = self._labels[state][1]

        self._best_state[self.source] = start
        self.dist_to[self.source] = 0.0

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and edges of the optimal path to ``target``.

        Returns:
            ``(stations, edges)`` where ``stations`` starts at the source and
            ends at the target and ``edges`` has one fewer element. Both lists
            are empty if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations: List[int] = []
        edges: List[Edge] = []
        while True:
            stations.append(state[0])
            if state not in self._parent:
                break
            previous, edge = self._parent[state]
            edges.append(edge)
            state = previous
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the optimal path to ``target``.

        Returns 0 if the target is unreachable.
        """
        if target not in self._best_state:
            return 0
        return self._labels[self._best_state[target]][2]
