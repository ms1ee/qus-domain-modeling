"""Path calculation based on Dijkstra's shortest path algorithm.

The search runs over labelled states ``(station, incoming line, transfers)``
so that line transfers can be counted and limited exactly. Three query modes
are supported:

    * ``shortest_distance``: minimise the total distance in meters.
    * ``least_transfer``: minimise the number of transfers, then the distance.
    * ``comprehensive``: minimise a composite score combining distance and a
      transfer penalty (5 minutes per transfer converted to meters).

An optional line preference adds a penalty to edges on lines that are not
preferred, steering the route towards the preferred lines.
"""

import heapq
import itertools
from dataclasses import dataclass

from fare_calculator import (MINUTES_PER_KM, MINUTES_PER_TRANSFER, FareCalculationError,
                             Sum_money)

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

DEFAULT_MAX_TRANSFERS = 10
# One transfer expressed in meters, so that comprehensive mode can trade distance for transfers.
TRANSFER_PENALTY_METERS = MINUTES_PER_TRANSFER / MINUTES_PER_KM * 1000.0
# Very large cost per transfer used for lexicographic (transfers, distance) ordering.
TRANSFER_LEXICOGRAPHIC_COST = 1e9
# Penalty added for riding a line that is not in the preference list.
PREFERENCE_PENALTY_METERS = 1000.0


class PathfindingError(Exception):
    """Base class for path calculation errors."""


class NoPathError(PathfindingError):
    """Raised when no route satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of ``VALID_MODES``.
        max_transfers: maximum number of line transfers allowed.
        preferred_lines: list of preferred line names.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=DEFAULT_MAX_TRANSFERS,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown query mode '{mode}', expected one of {VALID_MODES}")
        if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
            raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary-heap min priority queue used by Dijkstra's algorithm.

    Items with equal keys are dequeued in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, value):
        """Insert a value with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def del_min(self):
        """Remove and return ``(key, value)`` with the smallest key."""
        key, _, value = heapq.heappop(self._heap)
        return key, value

    def min_key(self):
        """Return the smallest key without removing it."""
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)


class ShortestPath:
    """Dijkstra-based single-source path search over a subway ``Graph``.

    Attributes:
        dist_to: dict mapping station number -> actual distance (meters) of the
            best path found from the source to that station.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise PathfindingError(f"Station number {source} does not exist in the network")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}   # station number -> best state (node, line, transfers)
        self._parent = {}       # state -> (previous state, Edge)
        self._preferred = set(self.config.preferred_lines)
        self._run()

    # ------------------------------------------------------------------
    # Cost model
    # ------------------------------------------------------------------
    def _edge_cost(self, edge, transfer_increment):
        """Incremental cost of traversing ``edge`` under the configured mode."""
        cost = edge.weight
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            cost += transfer_increment * TRANSFER_LEXICOGRAPHIC_COST
        elif mode == MODE_COMPREHENSIVE:
            cost += transfer_increment * TRANSFER_PENALTY_METERS
        if self._preferred and edge.line not in self._preferred:
            cost += PREFERENCE_PENALTY_METERS
        return cost

    # ------------------------------------------------------------------
    # Dijkstra's algorithm
    # ------------------------------------------------------------------
    def _run(self):
        """Run Dijkstra's algorithm over (station, line, transfers) states."""
        max_transfers = self.config.max_transfers
        start = (self.source, None, 0)
        best_score = {start: 0.0}
        state_dist = {start: 0.0}
        settled = set()

        pq = MinPQ()
        pq.insert(0.0, start)

        while not pq.is_empty():
            score, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, transfers = state

            # The first settled state of a station has the minimum score for that station.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = state_dist[state]

            for edge in self.graph.adj(node):
                increment = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + increment
                if new_transfers > max_transfers:
                    continue
                next_state = (edge.dest, edge.line, new_transfers)
                if next_state in settled:
                    continue
                new_score = score + self._edge_cost(edge, increment)
                if next_state not in best_score or new_score < best_score[next_state]:
                    best_score[next_state] = new_score
                    state_dist[next_state] = state_dist[state] + edge.weight
                    self._parent[next_state] = (state, edge)
                    pq.insert(new_score, next_state)

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------
    def is_reachable(self, target):
        """Return True if ``target`` can be reached under the constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the distance in meters to ``target`` (``float('inf')`` if unreachable)."""
        return self.dist_to.get(target, float("inf"))

    def get_transfer_count(self, target):
        """Return the number of line transfers on the best path to ``target``.

        Returns:
            int: transfer count, or -1 if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return -1
        return state[2]

    def path_with_edges(self, target):
        """Backtrack the best path from the source to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the list of station
            numbers from the source to the target and ``edges`` the list of
            traversed ``Edge`` objects. Both are empty if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        nodes = [target]
        edges = []
        while state in self._parent:
            previous, edge = self._parent[state]
            edges.append(edge)
            nodes.append(previous[0])
            state = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges


@dataclass
class TransferInfo:
    """A line transfer that occurs at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class LineSegment:
    """A continuous ride on one line."""

    line: str
    start: str
    end: str
    intervals: int


@dataclass
class Route:
    """Result of a path query.

    ``station_names`` is in travel order (origin first).
    """

    origin: str
    destination: str
    mode: str
    max_transfers: int
    line_preference: list
    station_names: list
    edges: list
    total_distance_m: float
    transfers: list
    lines: list
    fare_yuan: int

    @property
    def transfer_count(self):
        """Number of line transfers on the route."""
        return len(self.transfers)

    @property
    def segments(self):
        """Group consecutive edges on the same line into ``LineSegment`` objects."""
        result = []
        if not self.edges:
            return result
        start_index = 0
        for index, edge in enumerate(self.edges):
            is_last = index == len(self.edges) - 1
            if is_last or self.edges[index + 1].line != edge.line:
                result.append(LineSegment(
                    line=edge.line,
                    start=self.station_names[start_index],
                    end=self.station_names[index + 1],
                    intervals=index - start_index + 1,
                ))
                start_index = index + 1
        return result


def find_route(network, origin, destination, mode=MODE_SHORTEST_DISTANCE,
               max_transfers=None, line_preference=None):
    """Compute the route between two official station names.

    Args:
        network: a ``network.SubwayNetwork`` instance.
        origin: official name of the starting station.
        destination: official name of the ending station.
        mode: one of ``VALID_MODES``.
        max_transfers: maximum number of transfers (None uses the default).
        line_preference: list of line names, or a comma-separated string.

    Returns:
        Route: the computed route including its fare.

    Raises:
        ValueError: if origin and destination are the same or the mode is invalid.
        KeyError/UnknownStationError: if a station name is unknown.
        NoPathError: if no route satisfies the constraints.
        FareCalculationError: if the fare cannot be calculated.
    """
    if origin == destination:
        raise ValueError("Starting station cannot be the same as the ending station")

    if isinstance(line_preference, str):
        preferences = [item.strip() for item in line_preference.split(",") if item.strip()]
    else:
        preferences = list(line_preference or [])

    limit = DEFAULT_MAX_TRANSFERS if max_transfers is None else max_transfers
    config = PathfindingConfig(mode=mode, max_transfers=limit, preferred_lines=preferences)

    source = network.get_station_number(origin)
    target = network.get_station_number(destination)

    search = ShortestPath(network.graph, source, config)
    if not search.is_reachable(target):
        constraint = f" within {limit} transfers" if limit is not None else ""
        raise NoPathError(f"no route from '{origin}' to '{destination}'{constraint}")

    numbers, edges = search.path_with_edges(target)
    names = [network.get_station_name(number) for number in numbers]
    total = float(sum(edge.weight for edge in edges))

    transfers = []
    lines = []
    for index, edge in enumerate(edges):
        if edge.line not in lines:
            lines.append(edge.line)
        if index > 0 and edges[index - 1].line != edge.line:
            transfers.append(TransferInfo(
                station=names[index],
                from_line=edges[index - 1].line,
                to_line=edge.line,
            ))

    try:
        fare = Sum_money(total)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(str(exc)) from exc

    return Route(
        origin=origin,
        destination=destination,
        mode=mode,
        max_transfers=limit,
        line_preference=preferences,
        station_names=names,
        edges=edges,
        total_distance_m=total,
        transfers=transfers,
        lines=lines,
        fare_yuan=fare,
    )
