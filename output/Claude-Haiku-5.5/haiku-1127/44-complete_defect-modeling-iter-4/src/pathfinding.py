"""Shortest path calculation for the subway network.

Implements a binary-heap priority queue (``MinPQ``), path configuration
(``PathfindingConfig``) and Dijkstra's algorithm (``ShortestPath``).

The search runs over states ``(station number, current line)`` so that line
changes (transfers) can be counted, limited and penalised. This allows the
three query modes (shortest distance, least transfers, comprehensive), the
maximum transfer limit and the line preference to be supported by a single
Dijkstra implementation with time complexity O((V+E) log V).
"""

import heapq
import itertools
from typing import Dict, List, Optional, Tuple

from models import Edge, Graph

# Supported path query modes.
MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Cost parameters (expressed in meters for comparability with distances).
TRANSFER_PENALTY_METERS = 1500.0      # used by comprehensive mode
PREFERENCE_PENALTY_METERS = 800.0     # applied to edges on non-preferred lines
TRANSFER_TIE_BREAK_METERS = 0.001     # tiny cost so that unnecessary transfers are avoided
LEAST_TRANSFER_WEIGHT = 1e9           # dominates distance in least transfer mode

State = Tuple[str, str]


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items with equal keys are returned in insertion order.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[float, int, object]] = []
        self._counter = itertools.count()

    @property
    def size(self) -> int:
        """Number of items currently stored in the queue."""
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True when the queue holds no items."""
        return not self._heap

    def insert(self, key: float, item: object) -> None:
        """Insert an item with the given priority key in O(log n)."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def min_key(self) -> float:
        """Return the smallest key without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("min_key() called on an empty MinPQ")
        return self._heap[0][0]

    def del_min(self) -> Tuple[float, object]:
        """Remove and return ``(key, item)`` with the smallest key in O(log n).

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("del_min() called on an empty MinPQ")
        key, _, item = heapq.heappop(self._heap)
        return key, item


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: Lines that are preferred; empty list means no preference.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}'. Choose from {VALID_MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines) if preferred_lines else []

    def is_preferred(self, line: str) -> bool:
        """Return True when the line is acceptable without penalty."""
        return not self.preferred_lines or line in self.preferred_lines


class ShortestPath:
    """Dijkstra-based shortest path computation on a subway graph.

    Args:
        graph: The subway network graph.
        source: Station number of the origin.
        config: Path configuration; defaults to ``PathfindingConfig()``.

    Attributes:
        dist_to: Mapping of station number to the physical distance (meters)
            of the best path found to that station.
    """

    def __init__(
        self,
        graph: Graph,
        source: str,
        config: Optional[PathfindingConfig] = None,
    ) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Source station '{source}' is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[str, float] = {}
        self._score: Dict[State, float] = {}
        self._distance: Dict[State, float] = {}
        self._transfers: Dict[State, int] = {}
        self._prev: Dict[State, Optional[Tuple[State, Optional[Edge]]]] = {}
        self._best_state: Dict[str, State] = {}
        self._run()

    # ------------------------------------------------------------------
    # Cost model
    # ------------------------------------------------------------------
    def _increment(self, distance_inc: float, transfer_inc: int, penalty: float) -> float:
        """Return the additive score increment of one search step."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return transfer_inc * LEAST_TRANSFER_WEIGHT + distance_inc + penalty
        if mode == MODE_COMPREHENSIVE:
            return distance_inc + transfer_inc * TRANSFER_PENALTY_METERS + penalty
        return distance_inc + transfer_inc * TRANSFER_TIE_BREAK_METERS + penalty

    def _relax(
        self,
        pq: MinPQ,
        from_state: State,
        to_state: State,
        edge: Optional[Edge],
        distance_inc: float,
        transfer_inc: int,
        penalty: float,
    ) -> None:
        """Relax a transition between two search states."""
        new_transfers = self._transfers[from_state] + transfer_inc
        max_transfers = self.config.max_transfers
        if max_transfers is not None and new_transfers > max_transfers:
            return
        new_score = self._score[from_state] + self._increment(distance_inc, transfer_inc, penalty)
        if to_state not in self._score or new_score < self._score[to_state]:
            self._score[to_state] = new_score
            self._distance[to_state] = self._distance[from_state] + distance_inc
            self._transfers[to_state] = new_transfers
            self._prev[to_state] = (from_state, edge)
            pq.insert(new_score, to_state)

    # ------------------------------------------------------------------
    # Dijkstra main loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        pq = MinPQ()
        for line in self.graph.lines_at(self.source):
            state = (self.source, line)
            self._score[state] = 0.0
            self._distance[state] = 0.0
            self._transfers[state] = 0
            self._prev[state] = None
            pq.insert(0.0, state)

        finalized = set()
        while not pq.is_empty():
            _, state = pq.del_min()
            if state in finalized:
                continue
            finalized.add(state)
            node, line = state

            # Transfer to another line served by the same interchange station.
            for other_line in self.graph.lines_at(node):
                if other_line != line:
                    self._relax(pq, state, (node, other_line), None, 0.0, 1, 0.0)

            # Ride along an edge operated by the current line.
            for edge in self.graph.adjacent(node):
                if edge.line != line:
                    continue
                next_node = edge.other_endpoint(node)
                penalty = 0.0 if self.config.is_preferred(line) else PREFERENCE_PENALTY_METERS
                self._relax(pq, state, (next_node, line), edge, edge.distance, 0, penalty)

        # Choose the best state for every reached station.
        for state, score in self._score.items():
            node = state[0]
            best = self._best_state.get(node)
            if best is None or score < self._score[best]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._distance[state]

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------
    def has_path(self, target: str) -> bool:
        """Return True if ``target`` is reachable under the configuration."""
        return target in self._best_state

    def path_with_edges(self, target: str) -> Tuple[List[str], List[Edge]]:
        """Reconstruct the path from the source to ``target``.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` is the ordered list
            of station numbers (transfers do not repeat a station) and ``edges``
            are the traversed edges in order. Both are empty when unreachable.
        """
        if target not in self._best_state:
            return [], []
        state: Optional[State] = self._best_state[target]
        nodes: List[str] = []
        edges: List[Edge] = []
        while state is not None:
            nodes.append(state[0])
            previous = self._prev[state]
            if previous is None:
                break
            prev_state, edge = previous
            if edge is not None:
                edges.append(edge)
            state = prev_state
        nodes.reverse()
        edges.reverse()

        stations: List[str] = []
        for node in nodes:
            if not stations or stations[-1] != node:
                stations.append(node)
        return stations, edges

    def get_transfer_count(self, target: str) -> int:
        """Return the number of line transfers on the best path to ``target``."""
        state = self._best_state.get(target)
        if state is None:
            return 0
        return self._transfers[state]
