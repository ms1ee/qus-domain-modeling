"""Shortest-path computation over the subway graph.

The search is a Dijkstra variant whose search states are ``(station, line)``
pairs, where ``line`` is the line of the segment used to arrive at the
station. This allows transfers (line changes) to be counted exactly, which
is required for the transfer limit, the minimum-transfer mode, and for
correct handling of multi-line interchange stations.

Priority queue: ``MinPQ`` is a binary-heap priority queue, giving the
O((V+E) log V) running time for Dijkstra's algorithm.
"""

import heapq
import itertools
from typing import Any, List, Optional, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Penalty (in meter-equivalents) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000
# Penalty (in meter-equivalents) per segment not on a preferred line in comprehensive mode.
PREFERENCE_PENALTY_M = 500


class NoPathError(Exception):
    """Raised when no route satisfies the query constraints."""


class PathCalculationError(Exception):
    """Raised when an unexpected error occurs during path computation."""


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items are stored as ``(key, counter, item)`` tuples; the monotonically
    increasing counter guarantees that items themselves are never compared.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, Any]] = []
        self._counter = itertools.count()

    def insert(self, key: Any, item: Any) -> None:
        """Insert ``item`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self) -> Tuple[Any, Any]:
        """Remove and return ``(key, item)`` with the smallest key."""
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
        return not self._heap

    def size(self) -> int:
        return len(self._heap)


class PathfindingConfig:
    """Query configuration.

    Attributes:
        mode: one of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: line names preferred by the passenger (may be empty).

    Mode semantics (priority is compared lexicographically / additively):
        shortest_distance: distance, then line-preference violations, then transfers.
        least_transfer: transfers, then line-preference violations, then distance.
        comprehensive: distance + TRANSFER_PENALTY_M * transfers
                       + PREFERENCE_PENALTY_M * violations.
    """

    def __init__(self, mode: str = MODE_SHORTEST_DISTANCE,
                 max_transfers: Optional[int] = None,
                 preferred_lines: Optional[List[str]] = None) -> None:
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])


class _Label:
    """Best-known cost information for a search state."""

    __slots__ = ("priority", "dist", "transfers", "pref_off")

    def __init__(self, priority: Tuple[int, ...], dist: int, transfers: int, pref_off: int) -> None:
        self.priority = priority
        self.dist = dist
        self.transfers = transfers
        self.pref_off = pref_off


class ShortestPath:
    """Dijkstra-based path finder from a single source station.

    Attributes:
        dist_to: mapping station number -> actual travelled distance (meters)
            of the selected route to that station.
        transfers_to: mapping station number -> number of transfers on the
            selected route to that station.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to: dict = {}
        self.transfers_to: dict = {}
        self._prefs = set(self.config.preferred_lines)
        self._start_state: Tuple[int, Optional[str]] = (source, None)
        self._labels: dict = {}
        self._edge_to: dict = {}
        self._best_state: dict = {}
        self._run()

    # ----- cost model ---------------------------------------------------
    def _priority(self, dist: int, transfers: int, pref_off: int) -> Tuple[int, ...]:
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, pref_off, dist)
        if mode == MODE_COMPREHENSIVE:
            scalar = dist + TRANSFER_PENALTY_M * transfers + PREFERENCE_PENALTY_M * pref_off
            return (scalar, transfers)
        return (dist, pref_off, transfers)

    # ----- Dijkstra -----------------------------------------------------
    def _run(self) -> None:
        start_label = _Label(self._priority(0, 0, 0), 0, 0, 0)
        self._labels[self._start_state] = start_label

        pq = MinPQ()
        pq.insert(start_label.priority, self._start_state)
        done = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)

            station, line = state
            label = self._labels[state]
            if station not in self._best_state:
                self._best_state[station] = state
                self.dist_to[station] = label.dist
                self.transfers_to[station] = label.transfers

            for edge in self.graph.neighbors(station):
                nxt = edge.other(station)
                nstate = (nxt, edge.line)
                if nstate in done:
                    continue

                transfers = label.transfers
                if line is not None and edge.line != line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                pref_off = label.pref_off
                if self._prefs and edge.line not in self._prefs:
                    pref_off += 1

                dist = label.dist + edge.distance
                candidate = _Label(self._priority(dist, transfers, pref_off), dist, transfers, pref_off)
                old = self._labels.get(nstate)
                if old is None or candidate.priority < old.priority:
                    self._labels[nstate] = candidate
                    self._edge_to[nstate] = (state, edge)
                    pq.insert(candidate.priority, nstate)

    # ----- public query API --------------------------------------------
    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the query constraints."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station sequence and edge sequence from source to target.

        Returns:
            ``(stations, edges)`` where ``stations`` starts with the source and
            ends with the target, and ``edges[i]`` joins ``stations[i]`` and
            ``stations[i+1]``. If the target is unreachable, returns ``([], [])``.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        states = [state]
        edges: List[Edge] = []
        while state != self._start_state:
            prev_state, edge = self._edge_to[state]
            edges.append(edge)
            states.append(prev_state)
            state = prev_state
        states.reverse()
        edges.reverse()
        return [s[0] for s in states], edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the selected route to ``target``.

        Returns 0 if the target is unreachable (use ``has_path_to`` to check).
        """
        return self.transfers_to.get(target, 0)
