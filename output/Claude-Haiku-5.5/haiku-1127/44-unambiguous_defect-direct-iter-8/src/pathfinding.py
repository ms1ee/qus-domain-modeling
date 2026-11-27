"""Shortest-path computation (Dijkstra with a priority queue) and route assembly.

Supported query modes:
    shortest_distance - minimise the total distance in meters.
    least_transfer    - minimise the number of line transfers, then distance.
    comprehensive     - minimise distance plus a penalty per transfer.

Line preference: edges that do not belong to the preferred lines receive a
penalty in the cost function (the reported distance stays the real distance).
Max transfers: labels that would exceed the limit are never generated.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from errors import InvalidInputError, PathCalculationError, PathNotFoundError
from fare_calculator import Sum_money, calculate_estimated_time
from min_pq import MinPQ
from models import Edge, Graph

MODE_SHORTEST = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) added for every transfer in comprehensive mode.
TRANSFER_PENALTY_M = 500.0
# Equivalent distance (meters) added for every edge off the preferred lines.
PREFERENCE_PENALTY_M = 2000.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines)
        self.validate()

    def validate(self):
        """Raise InvalidInputError if any setting is invalid."""
        if self.mode not in VALID_MODES:
            raise InvalidInputError(
                f"unknown mode '{self.mode}', expected one of: {', '.join(VALID_MODES)}"
            )
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise InvalidInputError("max_transfers must be an integer or None")
            if self.max_transfers < 0:
                raise InvalidInputError("max_transfers must not be negative")
        if not all(isinstance(line, str) for line in self.preferred_lines):
            raise InvalidInputError("preferred_lines must contain only strings")


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    Complexity: O((V + E) log V) with the binary-heap MinPQ.

    Attributes:
        dist_to: Actual distance in meters from the source to each reached station.
        edge_to: Last edge on the best path to each reached station.
        transfers_to: Number of line transfers on the best path to each station.
    """

    def __init__(self, graph, source, config=None):
        if not isinstance(graph, Graph):
            raise TypeError("graph must be a Graph instance")
        if not graph.has_vertex(source):
            raise ValueError(f"source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.dist_to: Dict[int, float] = {}
        self.edge_to: Dict[int, Edge] = {}
        self.transfers_to: Dict[int, int] = {}
        self.preference_misses_to: Dict[int, int] = {}
        self._labels: Dict[int, tuple] = {}
        self._run()

    def _key(self, dist, transfers, misses):
        """Build the priority key of a label according to the query mode."""
        mode = self.config.mode
        penalty = PREFERENCE_PENALTY_M * misses
        if mode == MODE_SHORTEST:
            return (dist + penalty,)
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, misses, dist)
        return (dist + TRANSFER_PENALTY_M * transfers + penalty,)

    def _run(self):
        """Execute Dijkstra's algorithm from the source."""
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers
        pq = MinPQ()

        self.dist_to[self.source] = 0
        self.transfers_to[self.source] = 0
        self.preference_misses_to[self.source] = 0
        self._labels[self.source] = self._key(0, 0, 0)
        pq.insert(self._labels[self.source], self.source)

        settled = set()
        while not pq.is_empty():
            u = pq.del_min()
            if u in settled:
                continue
            settled.add(u)
            for edge in self.graph.adj(u):
                v = edge.other(u)
                if v in settled:
                    continue
                transfers = self.transfers_to[u]
                if u != self.source and self.edge_to[u].line != edge.line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                dist = self.dist_to[u] + edge.weight
                misses = self.preference_misses_to[u]
                if preferred and edge.line not in preferred:
                    misses += 1
                key = self._key(dist, transfers, misses)
                current = self._labels.get(v)
                if current is None or key < current:
                    self._labels[v] = key
                    self.dist_to[v] = dist
                    self.edge_to[v] = edge
                    self.transfers_to[v] = transfers
                    self.preference_misses_to[v] = misses
                    pq.insert(key, v)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self.dist_to

    def path_with_edges(self, target):
        """Return the station numbers and edges of the best path to ``target``.

        Returns:
            (list[int], list[Edge]): Station numbers from source to target and
            the edges between them. Both lists are empty if unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        edges = []
        vertex = target
        while vertex != self.source:
            edge = self.edge_to[vertex]
            edges.append(edge)
            vertex = edge.other(vertex)
        edges.reverse()
        path = [self.source]
        current = self.source
        for edge in edges:
            current = edge.other(current)
            path.append(current)
        return path, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``."""
        _, edges = self.path_with_edges(target)
        return sum(1 for prev, cur in zip(edges, edges[1:]) if prev.line != cur.line)


@dataclass
class RouteResult:
    """Complete answer to a route query."""

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    station_names: List[str]
    edges: List[Edge]
    distance_m: int
    transfer_count: int
    transfer_points: List[dict] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    fare: int = 0
    estimated_minutes: float = 0.0

    @property
    def distance_km(self):
        """Total distance in kilometers (rounded to two decimals)."""
        return round(self.distance_m / 1000.0, 2)


def find_route(network, start_name, end_name, config=None):
    """Compute the route, fare and estimated time between two stations.

    Args:
        network: A network.SubwayNetwork instance.
        start_name: Starting station (standardized automatically).
        end_name: Ending station (standardized automatically).
        config: PathfindingConfig, or None for default settings.

    Returns:
        RouteResult: The computed route.

    Raises:
        StationNotFoundError: If a station does not exist.
        InvalidInputError: If the stations are equal or the config is invalid.
        PathNotFoundError: If no path satisfies the constraints.
        PathCalculationError: If the path computation fails.
    """
    config = config if config is not None else PathfindingConfig()
    config.validate()
    start = network.require_station(start_name)
    end = network.require_station(end_name)
    if start == end:
        raise InvalidInputError("Starting station cannot be the same as the ending station")

    src_number = network.station_number(start)
    dst_number = network.station_number(end)
    try:
        shortest = ShortestPath(network.graph, src_number, config)
    except (ValueError, TypeError) as exc:
        raise PathCalculationError(f"path computation failed: {exc}") from exc
    if not shortest.has_path_to(dst_number):
        raise PathNotFoundError(
            f"No route found from '{start}' to '{end}' under the current settings"
        )

    station_numbers, edges = shortest.path_with_edges(dst_number)
    names = [network.station_name(number) for number in station_numbers]

    transfer_points = []
    for idx in range(1, len(edges)):
        prev_edge, cur_edge = edges[idx - 1], edges[idx]
        if prev_edge.line != cur_edge.line:
            transfer_points.append(
                {
                    "station": names[idx],
                    "from_line": prev_edge.line,
                    "to_line": cur_edge.line,
                }
            )

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    distance = sum(edge.distance for edge in edges)
    transfer_count = len(transfer_points)
    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, transfer_count)

    return RouteResult(
        start=start,
        end=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        station_names=names,
        edges=edges,
        distance_m=distance,
        transfer_count=transfer_count,
        transfer_points=transfer_points,
        lines=lines,
        fare=fare,
        estimated_minutes=estimated,
    )
