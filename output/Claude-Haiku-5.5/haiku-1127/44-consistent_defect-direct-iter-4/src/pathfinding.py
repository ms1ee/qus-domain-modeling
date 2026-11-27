"""Shortest path computation over the subway graph using Dijkstra's algorithm.

Search is performed over states (station number, line used to arrive), which
makes transfer counting exact. Edge costs depend on the selected mode:

    shortest_distance : cost = distance (meters)
    least_transfer    : cost = LEAST_TRANSFER_UNIT per transfer + distance
    comprehensive     : cost = distance + TRANSFER_PENALTY_METERS per transfer

If preferred lines are configured, edges on other lines receive an extra
LINE_PREFERENCE_PENALTY_METERS cost. The reported distance is always the
physical distance of the chosen path.
"""

import itertools
import heapq
from dataclasses import dataclass, field

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

TRANSFER_PENALTY_METERS = 500.0
LINE_PREFERENCE_PENALTY_METERS = 300.0
LEAST_TRANSFER_UNIT = 1e12


class NoRouteError(Exception):
    """Raised when no path satisfies the query constraints."""


class MinPQ:
    """Binary-heap min priority queue of (key, value) pairs."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, value):
        """Insert a value with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def del_min(self):
        """Remove and return (key, value) with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, value = heapq.heappop(self._heap)
        return key, value

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    """Dijkstra shortest path computation from a single source station.

    Args:
        graph: models.Graph instance.
        source: Station number of the origin.
        config: PathfindingConfig (defaults to shortest_distance without limits).

    Attributes:
        dist_to: dict mapping reachable station number to physical distance (m).
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        # state (node, arriving_line) -> (search cost, physical distance, transfers)
        self._state_info = {}
        # state -> (previous state, edge used)
        self._edge_to = {}
        # station number -> best state reaching it
        self._best_state = {}
        self._run()

    def _start_state(self):
        return (self.source, None)

    def _edge_cost(self, edge, is_transfer):
        """Return the search cost of traversing an edge."""
        mode = self.config.mode
        if mode == "shortest_distance":
            cost = edge.weight
        elif mode == "least_transfer":
            cost = (LEAST_TRANSFER_UNIT if is_transfer else 0.0) + edge.weight
        else:  # comprehensive
            cost = edge.weight + (TRANSFER_PENALTY_METERS if is_transfer else 0.0)
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += LINE_PREFERENCE_PENALTY_METERS
        return cost

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        start = self._start_state()
        self._state_info[start] = (0.0, 0.0, 0)
        pq = MinPQ()
        pq.insert(0.0, start)
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.del_min()
            if cost > self._state_info[state][0]:
                continue  # stale queue entry
            node, line = state
            _, distance, transfers = self._state_info[state]

            for edge in self.graph.adj(node):
                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + (1 if is_transfer else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_cost = cost + self._edge_cost(edge, is_transfer)
                next_state = (edge.dest, edge.line)
                old = self._state_info.get(next_state)
                if old is None or new_cost < old[0]:
                    self._state_info[next_state] = (
                        new_cost,
                        distance + edge.weight,
                        new_transfers,
                    )
                    self._edge_to[next_state] = (state, edge)
                    pq.insert(new_cost, next_state)

        # Select the best state per station.
        for state, (cost, _, _) in self._state_info.items():
            node = state[0]
            current = self._best_state.get(node)
            if current is None or cost < self._state_info[current][0]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._state_info[state][1]

    def is_reachable(self, target):
        """Return True if the target station can be reached under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Reconstruct the path from the source to target.

        Returns:
            (list of station numbers from source to target, list of Edge objects).
            Both lists are empty if the target is unreachable.
        """
        if not self.is_reachable(target):
            return [], []
        start = self._start_state()
        state = self._best_state[target]
        edges = []
        while state != start:
            previous, edge = self._edge_to[state]
            edges.append(edge)
            state = previous
        edges.reverse()
        nodes = [self.source] + [edge.dest for edge in edges]
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to target (0 if unreachable)."""
        if not self.is_reachable(target):
            return 0
        return self._state_info[self._best_state[target]][2]


@dataclass
class RouteResult:
    """A fully described route ready for fare calculation and reporting.

    Attributes:
        source: Starting station name.
        target: Ending station name.
        mode: Query mode used.
        stations: Station names in travel order.
        edges: Edge objects in travel order.
        segments: List of {"line": str, "stations": [str]} in travel order.
        transfers: List of {"station": str, "from_line": str, "to_line": str}.
        lines: Unique line names in order of first use.
        distance: Total physical distance in meters.
    """

    source: str
    target: str
    mode: str
    stations: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    distance: int = 0

    @property
    def transfer_count(self):
        """Number of transfers on this route."""
        return len(self.transfers)


def build_route(shortest_path, target, number_to_name):
    """Build a RouteResult from a computed ShortestPath.

    Args:
        shortest_path: A ShortestPath instance whose source is the origin.
        target: Station number of the destination.
        number_to_name: List mapping station numbers to station names.

    Returns:
        RouteResult

    Raises:
        NoRouteError: If the destination is unreachable.
    """
    source_name = number_to_name[shortest_path.source]
    target_name = number_to_name[target]
    if not shortest_path.is_reachable(target):
        raise NoRouteError(
            f"No route found from '{source_name}' to '{target_name}' "
            f"under the current settings"
        )

    nodes, edges = shortest_path.path_with_edges(target)
    segments = []
    transfers = []
    lines = []
    for edge in edges:
        if not segments or segments[-1]["line"] != edge.line:
            if segments:
                transfers.append({
                    "station": number_to_name[edge.source],
                    "from_line": segments[-1]["line"],
                    "to_line": edge.line,
                })
            segments.append({"line": edge.line, "stations": [number_to_name[edge.source]]})
            if edge.line not in lines:
                lines.append(edge.line)
        segments[-1]["stations"].append(number_to_name[edge.dest])

    distance = sum(int(round(edge.weight)) for edge in edges)
    return RouteResult(
        source=number_to_name[nodes[0]],
        target=number_to_name[nodes[-1]],
        mode=shortest_path.config.mode,
        stations=[number_to_name[node] for node in nodes],
        edges=edges,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance=distance,
    )
