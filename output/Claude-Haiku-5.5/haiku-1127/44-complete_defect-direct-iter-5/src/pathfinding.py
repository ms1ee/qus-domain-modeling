"""Path calculation for the Beijing Subway network.

Implements Dijkstra's algorithm on a binary-heap priority queue (``MinPQ``),
giving O((V+E) log V) complexity. The search runs over states of the form
``(station_number, arriving_line)`` so that line changes (transfers) can be
counted, limited, and penalised. Supported modes:

* ``shortest_distance`` - minimise total distance in meters.
* ``least_transfer``    - minimise number of transfers, then distance.
* ``comprehensive``     - minimise distance plus a penalty per transfer.

``PathfindingConfig.preferred_lines`` adds a penalty to segments on
non-preferred lines; ``PathfindingConfig.max_transfers`` prunes routes that
exceed the transfer limit.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES: Tuple[str, ...] = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged per transfer in comprehensive mode.
TRANSFER_PENALTY_M: float = 500.0
# Equivalent distance (meters) charged per segment on a non-preferred line.
PREFERENCE_PENALTY_M: float = 300.0

State = Tuple[int, Optional[str]]


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``MODES``.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: Line names preferred by the passenger.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers cannot be negative")
        self.mode: str = mode
        self.max_transfers: Optional[int] = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min priority queue implemented on top of ``heapq`` (binary heap).

    Items with equal keys are dequeued in insertion order.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, Any]] = []
        self._counter = itertools.count()

    def insert(self, key: Any, item: Any) -> None:
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self) -> Tuple[Any, Any]:
        """Remove and return ``(key, item)`` with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self) -> Any:
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("min_key from an empty priority queue")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class _Label:
    """Best-known information for a search state."""

    __slots__ = ("key", "distance", "transfers", "penalty", "prev", "edge")

    def __init__(
        self,
        key: Tuple[Any, ...],
        distance: float,
        transfers: int,
        penalty: float,
        prev: Optional[State],
        edge: Optional[Edge],
    ) -> None:
        self.key = key
        self.distance = distance
        self.transfers = transfers
        self.penalty = penalty
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Dijkstra-based shortest path computation from a single source station.

    Attributes:
        dist_to: Mapping from station number to the travelled distance (meters)
            of the best route found from the source.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config: PathfindingConfig = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._transfers: Dict[int, int] = {}
        self._best_state: Dict[int, State] = {}
        self._labels: Dict[State, _Label] = {}
        self._run()

    def _make_key(self, distance: float, transfers: int, penalty: float) -> Tuple[Any, ...]:
        """Build the comparison key of a label according to the query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, distance, penalty)
        if mode == MODE_COMPREHENSIVE:
            score = distance + TRANSFER_PENALTY_M * transfers + penalty
            return (score, distance, transfers)
        return (distance, transfers, penalty)

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        preferred: Set[str] = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start: State = (self.source, None)
        start_key = self._make_key(0.0, 0, 0.0)
        self._labels[start] = _Label(start_key, 0.0, 0, 0.0, None, None)

        pq = MinPQ()
        pq.insert(start_key, start)
        settled: Set[State] = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, arrive_line = state
            label = self._labels[state]

            # The first settled state of a station is its best label.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = label.distance
                self._transfers[node] = label.transfers

            for edge in self.graph.adj(node):
                transfers = label.transfers
                if arrive_line is not None and edge.line != arrive_line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                next_state: State = (edge.dest, edge.line)
                if next_state in settled:
                    continue

                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_M

                distance = label.distance + edge.distance
                key = self._make_key(distance, transfers, penalty)
                old = self._labels.get(next_state)
                if old is None or key < old.key:
                    self._labels[next_state] = _Label(key, distance, transfers, penalty, state, edge)
                    pq.insert(key, next_state)

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable from the source under the current config."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and traversed edges from source to target.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` starts with the
            source and ends with the target, and ``edges`` has one fewer
            element. If the target is unreachable, both lists are empty.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        states: List[State] = [state]
        edges: List[Edge] = []
        while True:
            label = self._labels[state]
            if label.prev is None or label.edge is None:
                break
            edges.append(label.edge)
            state = label.prev
            states.append(state)
        states.reverse()
        edges.reverse()
        return [s[0] for s in states], edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the best route to ``target``.

        Returns 0 if the target is unreachable.
        """
        return self._transfers.get(target, 0)
