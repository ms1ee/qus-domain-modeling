"""Path calculation: a binary-heap priority queue, a Dijkstra shortest-path
engine over (station, line) states, and route assembly.

Modes:
    shortest_distance  minimise total distance (meters)
    least_transfer     minimise number of transfers, then distance
    comprehensive      minimise distance plus an equivalent cost per transfer
                       (5 minutes of travel time at 1.5 minutes per km)

Line preference adds a penalty to edges that are not on a preferred line.
Maximum transfer limits prune any path that would exceed them.
"""

from typing import Dict, List, Optional, Tuple

from .models import Edge, Graph, Query, Route

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Five minutes of transfer time expressed in meters at 1.5 minutes per km.
TRANSFER_PENALTY_METERS = 5.0 * 1000.0 / 1.5
# Penalty for travelling on a line that is not preferred.
PREFERENCE_PENALTY_METERS = 500.0


class NoPathError(ValueError):
    """Raised when no route satisfies the constraints between two stations."""


class MinPQ:
    """Min-priority queue implemented as a binary heap.

    Only the keys are compared, so values need not be orderable.
    """

    def __init__(self) -> None:
        self.keys: list = []
        self.values: list = []
        self.size: int = 0

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return self.size == 0

    def insert(self, key, value) -> None:
        """Insert a value with the given priority key."""
        self.keys.append(key)
        self.values.append(value)
        self.size += 1
        self._swim(self.size - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        return self.keys[0]

    def del_min(self) -> tuple:
        """Remove and return (key, value) with the smallest key."""
        if self.is_empty():
            raise IndexError("priority queue underflow")
        key, value = self.keys[0], self.values[0]
        self._exchange(0, self.size - 1)
        self.keys.pop()
        self.values.pop()
        self.size -= 1
        if self.size > 0:
            self._sink(0)
        return key, value

    def _less(self, i: int, j: int) -> bool:
        return self.keys[i] < self.keys[j]

    def _exchange(self, i: int, j: int) -> None:
        self.keys[i], self.keys[j] = self.keys[j], self.keys[i]
        self.values[i], self.values[j] = self.values[j], self.values[i]

    def _swim(self, k: int) -> None:
        """Move the element at index k up until the heap order holds."""
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._exchange(k, parent)
            k = parent

    def _sink(self, k: int) -> None:
        """Move the element at index k down until the heap order holds."""
        while True:
            child = 2 * k + 1
            if child >= self.size:
                break
            if child + 1 < self.size and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._exchange(k, child)
            k = child


class PathfindingConfig:
    """Configuration of a path search.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: Lines that are favoured (others are penalised).
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{mode}'")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = [line for line in (preferred_lines or []) if line]


class ShortestPath:
    """Dijkstra's algorithm over (station number, current line) states.

    Tracking the current line in the state makes transfer counting exact.
    After construction:
        dist_to[node]        real travelled distance (meters) to a station
        path_with_edges(t)   station numbers and edges from source to t
        get_transfer_count(t) number of line changes on the chosen path
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"source station number {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._transfers: Dict[int, int] = {}
        self._best_state: Dict[int, tuple] = {}
        self._info: Dict[tuple, tuple] = {}
        self._pred: Dict[tuple, tuple] = {}
        self._run()

    def _penalty(self, edge: Edge) -> float:
        """Preference penalty for an edge."""
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            return PREFERENCE_PENALTY_METERS
        return 0.0

    def _key(self, cost_dist: float, transfers: int, real_dist: float) -> tuple:
        """Priority key of a state according to the search mode."""
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return (cost_dist, transfers)
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, cost_dist)
        return (cost_dist + transfers * TRANSFER_PENALTY_METERS, real_dist)

    def _run(self) -> None:
        start = (self.source, None)
        # info[state] = (cost distance incl. penalties, transfers, real distance)
        info: Dict[tuple, tuple] = {start: (0.0, 0, 0.0)}
        best_key: Dict[tuple, tuple] = {start: self._key(*info[start])}
        pred: Dict[tuple, tuple] = {}
        pq = MinPQ()
        pq.insert(best_key[start], start)
        done = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in done or key > best_key[state]:
                continue
            done.add(state)
            node, current_line = state
            cost_dist, transfers, real_dist = info[state]
            for edge in self.graph.adjacent(node):
                new_transfers = transfers
                if current_line is not None and edge.line != current_line:
                    new_transfers += 1
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_info = (
                    cost_dist + edge.weight + self._penalty(edge),
                    new_transfers,
                    real_dist + edge.weight,
                )
                new_state = (edge.dest, edge.line)
                new_key = self._key(*new_info)
                old_key = best_key.get(new_state)
                if old_key is None or new_key < old_key:
                    best_key[new_state] = new_key
                    info[new_state] = new_info
                    pred[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

        # Pick the best state for every reachable station.
        best_state: Dict[int, tuple] = {}
        for state, key in best_key.items():
            node = state[0]
            if node not in best_state or key < best_key[best_state[node]]:
                best_state[node] = state
        best_state[self.source] = start

        self._info = info
        self._pred = pred
        self._best_state = best_state
        for node, state in best_state.items():
            self.dist_to[node] = info[state][2]
            self._transfers[node] = info[state][1]

    def is_reachable(self, target: int) -> bool:
        """Return True if the target station can be reached."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station numbers and edges of the shortest path to target.

        Raises:
            NoPathError: If the target is unreachable under the constraints.
        """
        if target not in self._best_state:
            raise NoPathError(f"no path to station number {target}")
        start = (self.source, None)
        state = self._best_state[target]
        edges: List[Edge] = []
        while state != start:
            prev, edge = self._pred[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        nodes = [self.source] + [edge.dest for edge in edges]
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the path to target.

        Raises:
            NoPathError: If the target is unreachable.
        """
        if target not in self._transfers:
            raise NoPathError(f"no path to station number {target}")
        return self._transfers[target]


def _split_segments(names: List[str], edges: List[Edge]) -> Tuple[list, list]:
    """Group consecutive edges on the same line into segments and transfers."""
    segments: List[Tuple[str, List[str]]] = []
    transfers: List[Tuple[str, str, str]] = []
    if not edges:
        return segments, transfers
    current_line = edges[0].line
    current_stations = [names[0]]
    for i, edge in enumerate(edges):
        if edge.line != current_line:
            transfers.append((names[i], current_line, edge.line))
            segments.append((current_line, current_stations))
            current_line = edge.line
            current_stations = [names[i]]
        current_stations.append(names[i + 1])
    segments.append((current_line, current_stations))
    return segments, transfers


def find_route(network, query: Query) -> Route:
    """Compute the route for a query on a SubwayNetwork.

    Args:
        network: A network.SubwayNetwork instance.
        query: The passenger query with canonical station names.

    Returns:
        The Route with station sequence, distance, transfers and segments.

    Raises:
        ValueError: If the start and end stations are identical or unknown.
        NoPathError: If no route satisfies the constraints.
    """
    if query.start_station == query.end_station:
        raise ValueError("Starting station cannot be the same as the ending station")
    preferred = [query.line_preference] if query.line_preference else []
    config = PathfindingConfig(query.mode, query.max_transfers, preferred)
    source = network.station_number(query.start_station)
    target = network.station_number(query.end_station)

    search = ShortestPath(network.graph, source, config)
    nodes, edges = search.path_with_edges(target)
    names = [network.station_name(n) for n in nodes]
    segments, transfers = _split_segments(names, edges)

    involved: List[str] = []
    for line, _ in segments:
        if line not in involved:
            involved.append(line)

    return Route(
        station_sequence=names,
        total_distance_meters=sum(edge.distance for edge in edges),
        transfer_count=search.get_transfer_count(target),
        involved_lines=involved,
        segments=segments,
        transfers=transfers,
    )
