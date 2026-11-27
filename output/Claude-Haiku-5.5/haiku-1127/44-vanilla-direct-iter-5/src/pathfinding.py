"""Shortest-path computation with Dijkstra's algorithm over the subway graph.

The search runs over *states* ``(station_number, arrival_line)`` so that the
number of line transfers can be tracked exactly. Each state's cost depends on
the optimisation mode:

* ``shortest_distance``: cost = distance (meters).
* ``least_transfer``:    cost = transfers * LARGE + distance (transfers first,
                         distance as tie-breaker).
* ``comprehensive``:     cost = distance + transfers * TRANSFER_PENALTY, where
                         the penalty is the distance-equivalent of 5 minutes at
                         1.5 minutes per km (about 3.33 km).

Optional line preference adds a soft penalty to edges not on a preferred
line, and ``max_transfers`` prunes routes that exceed the transfer limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from min_pq import MinPQ
from models import Edge, Graph, NoPathError, SubwayError

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Weight that makes one transfer outweigh any realistic network distance.
TRANSFER_WEIGHT_LARGE = 1e9
# Distance-equivalent of one transfer: 5 min / (1.5 min per km) ~= 3333 m.
TRANSFER_PENALTY_METERS = 5.0 / 1.5 * 1000.0
# Soft penalty for riding a line that is not in the preference list.
LINE_PREFERENCE_PENALTY_METERS = 500.0


class PathfindingConfig:
    """Query configuration for path computation.

    Attributes:
        mode: one of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: list of preferred line names (empty means no preference).
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[list[str]] = None,
    ) -> None:
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self) -> None:
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}"
            )
        if self.max_transfers is not None:
            if not isinstance(self.max_transfers, int) or isinstance(self.max_transfers, bool):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")


class _StateInfo:
    """Best-known information for one (station, line) search state."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(
        self,
        cost: float,
        distance: float,
        transfers: int,
        prev: Optional[tuple],
        edge: Optional[Edge],
    ) -> None:
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    Attributes:
        source: station number of the start station.
        config: the PathfindingConfig used.
        dist_to: mapping station number -> travel distance (meters) of the
            best path found to that station.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.config.validate()
        self.dist_to: dict[int, float] = {}
        self._states: dict[tuple, _StateInfo] = {}
        self._best: dict[int, tuple] = {}
        self._run()

    # ----- algorithm ------------------------------------------------------
    def _step_cost(self, edge: Edge, transfer_increment: int) -> float:
        """Cost of traversing ``edge`` in the configured mode."""
        cost = float(edge.weight)
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            cost += transfer_increment * TRANSFER_WEIGHT_LARGE
        elif mode == MODE_COMPREHENSIVE:
            cost += transfer_increment * TRANSFER_PENALTY_METERS
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            cost += LINE_PREFERENCE_PENALTY_METERS
        return cost

    def _run(self) -> None:
        start: tuple = (self.source, None)
        self._states[start] = _StateInfo(0.0, 0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        settled: set[tuple] = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            station, line = state
            info = self._states[state]

            for edge in self.graph.adjacent(station):
                next_station = edge.other(station)
                transfer_inc = 1 if (line is not None and edge.line != line) else 0
                new_transfers = info.transfers + transfer_inc
                if max_transfers is not None and new_transfers > max_transfers:
                    continue  # prune routes exceeding the transfer limit

                new_state = (next_station, edge.line)
                if new_state in settled:
                    continue
                new_cost = cost + self._step_cost(edge, transfer_inc)
                old = self._states.get(new_state)
                if old is None or new_cost < old.cost:
                    self._states[new_state] = _StateInfo(
                        new_cost,
                        info.distance + edge.weight,
                        new_transfers,
                        state,
                        edge,
                    )
                    pq.insert(new_cost, new_state)

        # Pick, for every station, the arrival state with the lowest cost.
        for state, info in self._states.items():
            station = state[0]
            current = self._best.get(station)
            if current is None or info.cost < self._states[current].cost:
                self._best[station] = state
        for station, state in self._best.items():
            self.dist_to[station] = self._states[state].distance

    # ----- queries --------------------------------------------------------
    def has_path_to(self, target: int) -> bool:
        """True if ``target`` is reachable under the current configuration."""
        return target in self._best

    def distance_to(self, target: int) -> float:
        """Travel distance (meters) to ``target``; raises NoPathError if unreachable."""
        if target not in self.dist_to:
            raise NoPathError(f"Station {target} is unreachable from {self.source}")
        return self.dist_to[target]

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Return the station sequence and edge sequence from source to ``target``.

        Returns:
            (stations, edges) where ``stations`` contains len(edges) + 1 station
            numbers starting at the source. Returns ([], []) if unreachable.
        """
        if target not in self._best:
            return [], []
        state = self._best[target]
        stations = [target]
        edges: list[Edge] = []
        while True:
            info = self._states[state]
            if info.prev is None:
                break
            edges.append(info.edge)
            state = info.prev
            stations.append(state[0])
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Number of line transfers on the best path to ``target`` (0 if unreachable)."""
        if target not in self._best:
            return 0
        return self._states[self._best[target]].transfers


@dataclass
class RouteResult:
    """Result of a route query, with all information needed for reporting.

    Attributes:
        start: normalized starting station name.
        end: normalized ending station name.
        mode: optimisation mode used.
        station_names: ordered station names from start to end.
        edges: ordered edges traversed.
        distance_m: total distance in meters.
        transfers: number of line transfers.
        lines: unique line names in the order they are ridden.
        transfer_stations: list of (station, from_line, to_line) tuples.
    """

    start: str
    end: str
    mode: str
    station_names: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    distance_m: float = 0.0
    transfers: int = 0
    lines: list[str] = field(default_factory=list)
    transfer_stations: list[tuple[str, str, str]] = field(default_factory=list)

    def segments(self) -> list[tuple[str, list[str]]]:
        """Split the route into consecutive same-line segments.

        Returns:
            list of (line name, station names travelled on that line).
        """
        if not self.edges:
            return []
        segments: list[tuple[str, list[str]]] = []
        current_line = self.edges[0].line
        start_index = 0
        for i, edge in enumerate(self.edges):
            if edge.line != current_line:
                segments.append((current_line, self.station_names[start_index:i + 1]))
                current_line = edge.line
                start_index = i
        segments.append((current_line, self.station_names[start_index:]))
        return segments


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def find_route(network: Any, start_name: str, end_name: str,
               config: Optional[PathfindingConfig] = None) -> RouteResult:
    """Compute the route between two stations of a SubwayNetwork.

    Args:
        network: object providing ``graph``, ``number_for(name)`` and
            ``name_for(number)`` (see ``subway_network.SubwayNetwork``).
        start_name: official name of the starting station.
        end_name: official name of the ending station.
        config: query configuration; defaults to shortest-distance mode.

    Returns:
        A RouteResult describing the path.

    Raises:
        UnknownStationError: if a station name is not in the network.
        NoPathError: if no route satisfies the constraints.
    """
    config = config or PathfindingConfig()
    source = network.number_for(start_name)
    target = network.number_for(end_name)
    sp = ShortestPath(network.graph, source, config)
    if not sp.has_path_to(target):
        limit = ""
        if config.max_transfers is not None:
            limit = f" within {config.max_transfers} transfer(s)"
        raise NoPathError(f"No route found between '{start_name}' and '{end_name}'{limit}")

    numbers, edges = sp.path_with_edges(target)
    names = [network.name_for(n) for n in numbers]

    transfer_stations: list[tuple[str, str, str]] = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfer_stations.append((names[i], edges[i - 1].line, edges[i].line))

    distance = sum(e.weight for e in edges)
    return RouteResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        station_names=names,
        edges=edges,
        distance_m=distance,
        transfers=len(transfer_stations),
        lines=_unique([e.line for e in edges]),
        transfer_stations=transfer_stations,
    )
