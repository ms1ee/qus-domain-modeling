"""Shortest-path computation on the subway graph using Dijkstra's algorithm.

Search runs on states (station number, line used to arrive). This lets the
algorithm count transfers exactly: a transfer happens when the outgoing edge
belongs to a different line than the incoming edge.

Cost of a path is a tuple of additive components, so that Dijkstra's
algorithm remains valid and comparisons are lexicographic:
    shortest_distance : (distance, transfers, preference_penalty)
    least_transfer    : (transfers, distance, preference_penalty)
    comprehensive     : (distance + TRANSFER_PENALTY * transfers + preference, 0, 0)

By default the frontier is selected with a linear scan. A binary-heap
priority queue (MinPQ) can be enabled with use_priority_queue=True.
"""

import heapq
import itertools
from dataclasses import dataclass, field

from models import Edge, Graph, line_matches

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite-score penalty per transfer, in meters-equivalent (comprehensive mode).
TRANSFER_PENALTY_METERS = 3000
# Composite-score penalty for riding a non-preferred line, in meters-equivalent.
PREFERENCE_PENALTY_METERS = 500


class PathNotFoundError(Exception):
    """Raised when no path exists between two stations under the given constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names the passenger prefers.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown query mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary-heap min priority queue used to optimise Dijkstra's algorithm."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()  # tie-breaker so items are never compared

    def insert(self, priority, item) -> None:
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return (priority, item) with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min(self):
        """Return (priority, item) with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self) -> bool:
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


@dataclass
class Route:
    """A computed route between two stations.

    Attributes:
        stations: Station numbers in travel order, from start to end.
        edges: Edges travelled, in order (len(edges) == len(stations) - 1).
        total_distance: Total distance in meters.
        transfer_count: Number of line changes along the route.
    """

    stations: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    total_distance: int = 0
    transfer_count: int = 0

    @property
    def involved_lines(self) -> list:
        """Unique line names used by the route, in order of first appearance."""
        seen = []
        for edge in self.edges:
            if edge.line not in seen:
                seen.append(edge.line)
        return seen


class _Label:
    """Best known label of a search state."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(self, cost, distance, transfers, prev, edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev = prev  # previous state (station, line) or None for the source
        self.edge = edge  # edge used to reach this state, or None for the source


class ShortestPath:
    """Dijkstra-based shortest path computation from a single source station.

    Attributes:
        dist_to: dict mapping reachable station number to travelled distance (meters).
        cost_to: dict mapping reachable station number to the optimised cost tuple.
    """

    def __init__(self, graph: Graph, source, config=None, use_priority_queue=False):
        if not graph.has_node(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.use_priority_queue = use_priority_queue
        self.dist_to = {}
        self.cost_to = {}
        self._labels = {}
        self._best_state = {}
        self._run()

    # ----- algorithm -------------------------------------------------------
    def _is_non_preferred(self, line) -> bool:
        preferred = self.config.preferred_lines
        if not preferred:
            return False
        return not any(line_matches(line, wanted) for wanted in preferred)

    def _edge_cost(self, edge: Edge, transfer_inc: int, pref_inc: int) -> tuple:
        """Return the additive cost tuple of traversing an edge."""
        weight = edge.weight
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return (weight, transfer_inc, pref_inc)
        if mode == MODE_LEAST_TRANSFER:
            return (transfer_inc, weight, pref_inc)
        # Comprehensive: composite scalar score balancing distance and transfers.
        primary = weight + TRANSFER_PENALTY_METERS * transfer_inc + PREFERENCE_PENALTY_METERS * pref_inc
        return (primary, 0, 0)

    def _relax(self, state, settled, push) -> None:
        """Relax all outgoing edges of a settled state."""
        label = self._labels[state]
        station, last_line = state
        max_transfers = self.config.max_transfers
        for edge in self.graph.adjacent(station):
            transfer_inc = 1 if (last_line is not None and edge.line != last_line) else 0
            new_transfers = label.transfers + transfer_inc
            if max_transfers is not None and new_transfers > max_transfers:
                continue  # violates the transfer limit
            pref_inc = 1 if self._is_non_preferred(edge.line) else 0
            increment = self._edge_cost(edge, transfer_inc, pref_inc)
            new_cost = tuple(a + b for a, b in zip(label.cost, increment))
            new_state = (edge.dest, edge.line)
            if new_state in settled:
                continue
            existing = self._labels.get(new_state)
            if existing is None or new_cost < existing.cost:
                self._labels[new_state] = _Label(
                    new_cost, label.distance + edge.weight, new_transfers, state, edge
                )
                push(new_state, new_cost)

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        start = (self.source, None)
        self._labels[start] = _Label((0, 0, 0), 0, 0, None, None)
        settled = set()

        if self.use_priority_queue:
            pq = MinPQ()
            pq.insert((0, 0, 0), start)

            def push_pq(state, cost):
                pq.insert(cost, state)

            while not pq.is_empty():
                _, state = pq.del_min()
                if state in settled:
                    continue
                settled.add(state)
                self._relax(state, settled, push_pq)
        else:
            frontier = {start}

            def push_scan(state, cost):
                frontier.add(state)

            while frontier:
                # Simple linear scan for the state with minimum cost.
                state = min(frontier, key=lambda s: self._labels[s].cost)
                frontier.discard(state)
                if state in settled:
                    continue
                settled.add(state)
                self._relax(state, settled, push_scan)

        # Pick, for every station, the best settled state arriving at it.
        for state in settled:
            station = state[0]
            current = self._best_state.get(station)
            if current is None or self._labels[state].cost < self._labels[current].cost:
                self._best_state[station] = state
        for station, state in self._best_state.items():
            label = self._labels[state]
            self.dist_to[station] = label.distance
            self.cost_to[station] = label.cost

    # ----- queries ---------------------------------------------------------
    def has_path_to(self, target) -> bool:
        """Return True if the target station is reachable under the constraints."""
        return target in self._best_state

    def _require(self, target) -> None:
        if not self.has_path_to(target):
            raise PathNotFoundError(
                f"No path found from station {self.source} to station {target}"
                " under the current constraints"
            )

    def path_with_edges(self, target):
        """Return (station numbers in travel order, edges in travel order) to target.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        self._require(target)
        label = self._labels[self._best_state[target]]
        stations = [target]
        edges = []
        while label.prev is not None:
            edges.append(label.edge)
            prev_state = label.prev
            stations.append(prev_state[0])
            label = self._labels[prev_state]
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target) -> int:
        """Return the number of transfers on the path to target.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        self._require(target)
        return self._labels[self._best_state[target]].transfers

    def route_to(self, target) -> Route:
        """Return a Route object describing the path to target."""
        stations, edges = self.path_with_edges(target)
        return Route(
            stations=stations,
            edges=edges,
            total_distance=self.dist_to[target],
            transfer_count=self.get_transfer_count(target),
        )
