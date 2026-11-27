"""
Path calculation for the subway network.

Implements Dijkstra's shortest path algorithm over a state space made of
(station, arriving line, transfers so far). Tracking the arriving line lets the
algorithm detect line changes (transfers) exactly, which is required for the
minimum-transfer and comprehensive query modes.

Cost model (in meters-equivalent units):
    * base cost        : inter-station distance
    * transfer cost    : mode-dependent penalty per line change
    * preference cost  : small penalty for edges outside the preferred lines

Modes:
    shortest_distance : cost = distance
    least_transfer    : cost = huge penalty per transfer + distance (lexicographic)
    comprehensive     : cost = distance + 3000 m per transfer (about 5 minutes)
"""

import heapq
import itertools
from dataclasses import dataclass, field
from typing import List, Optional

from models import Edge

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Penalty (in meters-equivalent) added for every line change.
TRANSFER_PENALTY_METERS = {
    MODE_SHORTEST_DISTANCE: 0.0,
    MODE_LEAST_TRANSFER: 1.0e7,
    MODE_COMPREHENSIVE: 3000.0,
}

# Penalty added for every edge that is not on a preferred line.
PREFERRED_LINE_PENALTY_METERS = 500.0


class MinPQ:
    """
    Min priority queue implemented on top of a binary heap.

    Items with equal priority are returned in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return the (priority, item) pair with the smallest priority."""
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("min_priority from an empty priority queue")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """
    Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of line names that are preferred (soft constraint).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(
                f"Unknown mode '{mode}', expected one of: {', '.join(VALID_MODES)}"
            )
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        cleaned = []
        for line in preferred_lines or []:
            text = str(line).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = cleaned

    def transfer_penalty(self):
        """Return the transfer penalty (meters-equivalent) for the current mode."""
        return TRANSFER_PENALTY_METERS[self.mode]


@dataclass
class _StateInfo:
    """Best known information for one search state."""
    cost: float
    distance: float
    transfers: int
    parent: Optional[tuple]
    edge: Optional[Edge]


class ShortestPath:
    """
    Dijkstra-based shortest path computation from a single source station.

    Attributes:
        dist_to: dict mapping reachable station number -> travelled distance (meters)
            along the chosen optimal path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._state_info = {}   # state -> _StateInfo
        self._best_state = {}   # station number -> best state
        self._run()

    def _run(self):
        """Run Dijkstra's algorithm over the (station, line, transfers) state space."""
        start = (self.source, None, 0)
        self._state_info[start] = _StateInfo(0.0, 0.0, 0, None, None)
        pq = MinPQ()
        pq.insert(0.0, start)

        settled = set()
        penalty = self.config.transfer_penalty()
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line, transfers_so_far = state
            info = self._state_info[state]

            for edge in self.graph.adjacent(node):
                is_transfer = line is not None and edge.line != line
                transfers = transfers_so_far + (1 if is_transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue

                step = edge.weight
                if preferred and edge.line not in preferred:
                    step += PREFERRED_LINE_PENALTY_METERS
                if is_transfer:
                    step += penalty
                new_cost = info.cost + step

                new_state = (edge.dest, edge.line, transfers)
                if new_state in settled:
                    continue
                old = self._state_info.get(new_state)
                if old is None or new_cost < old.cost:
                    self._state_info[new_state] = _StateInfo(
                        new_cost, info.distance + edge.weight, transfers, state, edge
                    )
                    pq.insert(new_cost, new_state)

        # Choose the cheapest state for every reachable station.
        for state, info in self._state_info.items():
            node = state[0]
            best = self._best_state.get(node)
            if best is None or info.cost < self._state_info[best].cost:
                self._best_state[node] = state

        self.dist_to = {
            node: self._state_info[state].distance
            for node, state in self._best_state.items()
        }

    def has_path(self, target):
        """Return True if ``target`` is reachable from the source under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """
        Return the optimal path from the source to ``target``.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects along the path).
            If the target is unreachable, returns ([], []).
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while state is not None:
            info = self._state_info[state]
            stations.append(state[0])
            if info.edge is not None:
                edges.append(info.edge)
            state = info.parent
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the optimal path to ``target`` (0 if unreachable)."""
        if target not in self._best_state:
            return 0
        return self._state_info[self._best_state[target]].transfers


@dataclass
class Route:
    """A computed route between two stations."""
    stations: List[int] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    distance: int = 0
    transfer_count: int = 0


def find_route(graph, source, target, config=None):
    """
    Compute the optimal route between two stations.

    Returns:
        Route or None: None if no route satisfies the constraints.
    """
    shortest = ShortestPath(graph, source, config)
    if not shortest.has_path(target):
        return None
    stations, edges = shortest.path_with_edges(target)
    distance = sum(edge.weight for edge in edges)
    return Route(
        stations=stations,
        edges=edges,
        distance=distance,
        transfer_count=shortest.get_transfer_count(target),
    )
