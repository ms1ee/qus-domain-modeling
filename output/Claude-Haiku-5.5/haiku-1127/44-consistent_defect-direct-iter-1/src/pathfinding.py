"""Path computation based on Dijkstra's algorithm.

The search runs over states ``(station number, arrival line)`` so that line
changes (transfers) can be counted and constrained. The cost of a path
depends on the query mode:

* ``shortest_distance``: total distance in meters.
* ``least_transfer``: (number of transfers, total distance).
* ``comprehensive``: distance plus a penalty per transfer.

Line preference adds a penalty to edges that are not on a preferred line.
A priority queue (``MinPQ``, based on ``heapq``) is used for the search.
"""

import heapq
import itertools
from dataclasses import dataclass, field


MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite score: one transfer is worth this many meters of travel.
TRANSFER_PENALTY_METERS = 2000.0
# Extra cost (meters) for each edge that is not on a preferred line.
LINE_PREFERENCE_PENALTY_METERS = 1000.0


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if (isinstance(max_transfers, bool) or not isinstance(max_transfers, int)
                    or max_transfers < 0):
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items with equal keys are returned in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert ``item`` with priority ``key`` (smaller is better)."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)


class _Record:
    """Best-known information about one search state."""

    __slots__ = ("cost", "distance", "transfers", "prev_state", "edge")

    def __init__(self, cost, distance, transfers, prev_state, edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev_state = prev_state
        self.edge = edge


def _add_cost(first, second):
    """Element-wise addition of two equally sized cost tuples."""
    return tuple(a + b for a, b in zip(first, second))


class ShortestPath:
    """Dijkstra-based shortest path search from one source station.

    Args:
        graph: The ``Graph`` to search.
        source: Station number of the starting station.
        config: Optional ``PathfindingConfig``; defaults to shortest distance.

    Attributes:
        dist_to: dict mapping reachable station number -> total distance in
            meters of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        self._graph = graph
        self._source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._records = {}
        self._best_state = {}
        self._run()

    # ----- cost model --------------------------------------------------------
    def _zero_cost(self):
        if self.config.mode == MODE_LEAST_TRANSFER:
            return (0, 0.0)
        return (0.0,)

    def _step_cost(self, distance, is_transfer, penalty):
        """Cost of traversing one edge in the current mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (1 if is_transfer else 0, distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            transfer_cost = TRANSFER_PENALTY_METERS if is_transfer else 0.0
            return (distance + penalty + transfer_cost,)
        return (distance + penalty,)

    # ----- Dijkstra ----------------------------------------------------------
    def _run(self):
        """Run Dijkstra's algorithm over (station, arrival line) states."""
        config = self.config
        preferred = set(config.preferred_lines)
        start_state = (self._source, None)
        start_cost = self._zero_cost()
        self._records[start_state] = _Record(start_cost, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(start_cost, start_state)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line = state
            record = self._records[state]
            for edge in self._graph.adjacent(node):
                is_transfer = line is not None and edge.line != line
                transfers = record.transfers + (1 if is_transfer else 0)
                if config.max_transfers is not None and transfers > config.max_transfers:
                    continue

                penalty = 0.0
                if preferred and edge.line not in preferred:
                    penalty = LINE_PREFERENCE_PENALTY_METERS

                step = self._step_cost(edge.distance, is_transfer, penalty)
                new_cost = _add_cost(record.cost, step)
                next_state = (edge.dest, edge.line)

                old = self._records.get(next_state)
                if old is not None and not new_cost < old.cost:
                    continue
                self._records[next_state] = _Record(
                    new_cost, record.distance + edge.distance,
                    transfers, state, edge)
                pq.insert(new_cost, next_state)

        # Choose the best state for each station.
        for state, record in self._records.items():
            node = state[0]
            current = self._best_state.get(node)
            if current is None or record.cost < self._records[current].cost:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._records[state].distance

    # ----- public queries ----------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Backtrack the path from ``source`` to ``target``.

        Returns:
            tuple: (stations, edges) where ``stations`` lists station numbers
            from ``target`` back to ``source`` and ``edges`` lists the edges
            used in the same backward order (``edges[i]`` goes from
            ``stations[i + 1]`` to ``stations[i]``). Both are empty when the
            target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        stations = []
        edges = []
        current = state
        while current is not None:
            record = self._records[current]
            stations.append(current[0])
            if record.edge is not None:
                edges.append(record.edge)
            current = record.prev_state
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target``.

        Returns 0 when the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return 0
        return self._records[state].transfers


@dataclass
class Route:
    """Result of a path query.

    Attributes:
        source: Official name of the starting station.
        target: Official name of the ending station.
        mode: Query mode used.
        stations: Station names ordered from end to start.
        edges: Edges ordered from end to start.
        distance: Total distance in meters.
        transfer_count: Number of transfers.
        transfers: List of dicts with keys station, from_line, to_line
            (in travel order).
        lines: Line names involved, in travel order without duplicates.
    """

    source: str
    target: str
    mode: str
    stations: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    distance: int = 0
    transfer_count: int = 0
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)


def find_route(network, source_name, target_name, config=None):
    """Compute the route between two stations of a ``SubwayNetwork``.

    Raises:
        UnknownStationError: If a station does not exist.
        PathNotFoundError: If no path satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    src = network.get_number(source_name)
    dst = network.get_number(target_name)

    search = ShortestPath(network.graph, src, config)
    if not search.has_path_to(dst):
        constraint = ""
        if config.max_transfers is not None:
            constraint = f" with at most {config.max_transfers} transfer(s)"
        raise PathNotFoundError(
            f"No path found between '{source_name}' and '{target_name}'{constraint}")

    numbers, edges = search.path_with_edges(dst)
    stations = [network.get_name(number) for number in numbers]
    distance = sum(edge.distance for edge in edges)
    transfer_count = search.get_transfer_count(dst)

    chron_edges = list(reversed(edges))
    chron_stations = list(reversed(stations))

    lines = []
    for edge in chron_edges:
        if edge.line not in lines:
            lines.append(edge.line)

    transfers = []
    for i in range(len(chron_edges) - 1):
        if chron_edges[i].line != chron_edges[i + 1].line:
            transfers.append({
                "station": chron_stations[i + 1],
                "from_line": chron_edges[i].line,
                "to_line": chron_edges[i + 1].line,
            })

    return Route(
        source=source_name,
        target=target_name,
        mode=config.mode,
        stations=stations,
        edges=edges,
        distance=distance,
        transfer_count=transfer_count,
        transfers=transfers,
        lines=lines,
    )


def shortest_distance_path(network, source_name, target_name,
                           max_transfers=None, preferred_lines=None):
    """Route minimizing total distance."""
    config = PathfindingConfig(MODE_SHORTEST_DISTANCE, max_transfers, preferred_lines)
    return find_route(network, source_name, target_name, config)


def least_transfer_path(network, source_name, target_name,
                        max_transfers=None, preferred_lines=None):
    """Route minimizing the number of transfers (ties broken by distance)."""
    config = PathfindingConfig(MODE_LEAST_TRANSFER, max_transfers, preferred_lines)
    return find_route(network, source_name, target_name, config)


def comprehensive_path(network, source_name, target_name,
                       max_transfers=None, preferred_lines=None):
    """Route balancing distance and transfers with a composite score."""
    config = PathfindingConfig(MODE_COMPREHENSIVE, max_transfers, preferred_lines)
    return find_route(network, source_name, target_name, config)
