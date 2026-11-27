"""Shortest path computation for the subway network.

The search is Dijkstra's algorithm driven by a binary-heap priority queue
(MinPQ). To support transfer counting, line preferences and transfer limits,
the search runs over labelled states (station, current line, transfers used).
Boarding a different line at a station counts as one transfer. Each state is
settled at most once, giving O((V+E) log V) behaviour per transfer layer.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Extra cost (in meters-equivalent) charged per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 500
# Extra cost charged for each edge not on a preferred line.
NON_PREFERRED_LINE_PENALTY_M = 300
# Transfer cap used when no --max_transfers limit is given (keeps search finite).
DEFAULT_TRANSFER_CAP = 8


class PathfindingConfig:
    """Query configuration.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed transfers, or None for no explicit limit.
        preferred_lines: lines to prefer; edges on other lines are penalized.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines) if preferred_lines else []

    def __repr__(self) -> str:
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class MinPQ:
    """Binary-heap min priority queue keyed by comparable keys.

    Ties are broken by insertion order so arbitrary items never need to be
    compared directly.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, Any]] = []
        self._counter = itertools.count()

    def insert(self, key: Any, item: Any) -> None:
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self) -> Tuple[Any, Any]:
        """Remove and return (key, item) with the smallest key.

        Raises:
            IndexError: if the queue is empty.
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
        """True when the queue holds no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class _Label:
    """Best known cost data for one search state."""

    __slots__ = ("key", "dist", "transfers", "penalty")

    def __init__(self, key: Tuple[Any, ...], dist: int, transfers: int, penalty: int) -> None:
        self.key = key
        self.dist = dist
        self.transfers = transfers
        self.penalty = penalty


State = Tuple[int, Optional[str], int]  # (station number, line used to arrive, transfers)


class ShortestPath:
    """Dijkstra-based optimal path finder from one source station.

    Attributes:
        dist_to: station number -> actual travelled distance (meters) of the
            best path found to it.
    """

    def __init__(
        self,
        graph: Graph,
        source: int,
        config: Optional[PathfindingConfig] = None,
    ) -> None:
        if not graph.has_station(source):
            raise ValueError(f"unknown source station number {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[int, int] = {}
        self._labels: Dict[State, _Label] = {}
        self._predecessor: Dict[State, Optional[Tuple[State, Edge]]] = {}
        self._settled: Set[State] = set()
        self._best_state: Dict[int, State] = {}
        self._start: State = (source, None, 0)
        self._run()

    # ----------------------------------------------------------- cost helpers
    def _make_key(self, dist: int, transfers: int, penalty: int) -> Tuple[Any, ...]:
        """Priority key of a label according to the configured mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, dist + penalty)
        if mode == MODE_COMPREHENSIVE:
            return (dist + penalty + transfers * TRANSFER_PENALTY_M,)
        return (dist + penalty,)

    def _transfer_cap(self) -> int:
        if self.config.max_transfers is not None:
            return self.config.max_transfers
        return DEFAULT_TRANSFER_CAP

    # --------------------------------------------------------------- search
    def _run(self) -> None:
        start_label = _Label(self._make_key(0, 0, 0), 0, 0, 0)
        self._labels[self._start] = start_label
        self._predecessor[self._start] = None

        pq = MinPQ()
        pq.insert(start_label.key, self._start)

        cap = self._transfer_cap()
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            key, state = pq.del_min()
            label = self._labels[state]
            if state in self._settled or key != label.key:
                continue  # stale queue entry
            self._settled.add(state)

            station, line, transfers = state
            for edge in self.graph.adjacent(station):
                transfer = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + transfer
                if new_transfers > cap:
                    continue
                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += NON_PREFERRED_LINE_PENALTY_M
                new_dist = label.dist + edge.distance
                new_state: State = (edge.dest, edge.line, new_transfers)
                new_key = self._make_key(new_dist, new_transfers, penalty)
                existing = self._labels.get(new_state)
                if existing is None or new_key < existing.key:
                    self._labels[new_state] = _Label(new_key, new_dist, new_transfers, penalty)
                    self._predecessor[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

        # Choose the best settled state for each station.
        for state in self._settled:
            station = state[0]
            current = self._best_state.get(station)
            if current is None or self._labels[state].key < self._labels[current].key:
                self._best_state[station] = state
        self._best_state[self.source] = self._start
        for station, state in self._best_state.items():
            self.dist_to[station] = self._labels[state].dist

    # ------------------------------------------------------------- queries
    def has_path(self, target: int) -> bool:
        """Return True if the target station is reachable under the config."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and traversed edges from source to target.

        Returns:
            (stations, edges): stations has len(edges) + 1 entries, starting
            with the source and ending with the target. Each edge is oriented
            in the direction of travel.

        Raises:
            ValueError: if the target is unreachable.
        """
        if target not in self._best_state:
            raise ValueError(f"station {target} is unreachable from {self.source}")
        state = self._best_state[target]
        edges: List[Edge] = []
        while True:
            pred = self._predecessor[state]
            if pred is None:
                break
            prev_state, edge = pred
            edges.append(edge)
            state = prev_state
        edges.reverse()
        stations = [self.source] + [edge.dest for edge in edges]
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line transfers on the best path to target.

        Raises:
            ValueError: if the target is unreachable.
        """
        if target not in self._best_state:
            raise ValueError(f"station {target} is unreachable from {self.source}")
        return self._best_state[target][2]
