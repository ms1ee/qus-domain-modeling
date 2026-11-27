"""Route computation service: combines the network, path finding and fare modules."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Base class for route query errors."""


class InvalidQueryError(RouteError):
    """Raised for logically invalid queries (e.g. identical start and end)."""


class StationNotFoundError(RouteError):
    """Raised when a station does not exist in the network."""


class NoRouteError(RouteError):
    """Raised when no path satisfies the query constraints."""


@dataclass
class Route:
    """Result of a route query.

    Attributes:
        start, end: official station names.
        mode: path query mode used.
        max_transfers: transfer limit used (None = unlimited).
        preferred_lines: preferred lines used.
        station_names: ordered station names from start to end.
        segments: list of {"line": str, "stations": [str, ...]} line segments.
        transfer_details: list of {"station", "from_line", "to_line", "all_lines"}.
        lines: ordered list of distinct lines used.
        distance_m: total travelled distance in meters.
        transfer_count: number of transfers.
        fare: fare in yuan.
        estimated_time_min: estimated travel time in minutes.
    """

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    station_names: List[str]
    segments: List[Dict[str, Any]] = field(default_factory=list)
    transfer_details: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    distance_m: int = 0
    transfer_count: int = 0
    fare: int = 0
    estimated_time_min: float = 0.0


def _build_segments(names, edges):
    """Group the path into consecutive same-line segments."""
    if not edges:
        return []
    segments = []
    current_line = edges[0].line
    current_stations = [names[0]]
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append({"line": current_line, "stations": current_stations})
            current_line = edge.line
            current_stations = [names[index]]
        current_stations.append(names[index + 1])
    segments.append({"line": current_line, "stations": current_stations})
    return segments


def _build_transfers(names, edges, network):
    """Describe every station where the path changes line."""
    details = []
    for index in range(1, len(edges)):
        previous_line = edges[index - 1].line
        next_line = edges[index].line
        if previous_line != next_line:
            station = names[index]
            details.append(
                {
                    "station": station,
                    "from_line": previous_line,
                    "to_line": next_line,
                    "all_lines": network.graph.get_station_lines(station),
                }
            )
    return details


def compute_route(network, start, end, config=None) -> Route:
    """Compute the route between two stations and its summary information.

    Args:
        network: a SubwayNetwork instance.
        start: starting station name.
        end: ending station name.
        config: PathfindingConfig (defaults to shortest-distance mode).

    Raises:
        StationNotFoundError, InvalidQueryError, NoRouteError
    """
    config = config if config is not None else PathfindingConfig()

    start_name = network.resolve_station(start)
    if start_name is None:
        raise StationNotFoundError(
            f"Starting station '{start}' does not exist, please check the station name"
        )
    end_name = network.resolve_station(end)
    if end_name is None:
        raise StationNotFoundError(
            f"Ending station '{end}' does not exist, please check the station name"
        )
    if start_name == end_name:
        raise InvalidQueryError("Starting station cannot be the same as the ending station")

    source = network.station_number(start_name)
    target = network.station_number(end_name)
    shortest = ShortestPath(network.graph, source, config)
    if not shortest.has_path_to(target):
        raise NoRouteError(
            f"No route found from '{start_name}' to '{end_name}' with the current settings "
            f"(mode={config.mode}, max_transfers={config.max_transfers})"
        )

    numbers, edges = shortest.path_with_edges(target)
    names = [network.station_name(number) for number in numbers]
    distance = sum(edge.weight for edge in edges)
    transfers = shortest.get_transfer_count(target)

    segments = _build_segments(names, edges)
    transfer_details = _build_transfers(names, edges, network)
    lines = []
    for segment in segments:
        if segment["line"] not in lines:
            lines.append(segment["line"])

    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, transfers)

    return Route(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        station_names=names,
        segments=segments,
        transfer_details=transfer_details,
        lines=lines,
        distance_m=distance,
        transfer_count=transfers,
        fare=fare,
        estimated_time_min=estimated,
    )
