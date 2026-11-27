"""Route query service: combines path search, fare and time estimation.

``run_query`` is the single entry point used by the CLI. It validates the
stations, runs the configured path search, and assembles a ``RouteResult``
containing the station sequence, line segments, transfers, distance, fare and
estimated time.
"""

from dataclasses import dataclass
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from network import StationNotFoundError
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a route cannot be computed or priced."""


@dataclass
class RouteResult:
    """Complete result of a path query.

    Attributes:
        start: Official starting station name.
        end: Official ending station name.
        mode: Path query mode used.
        max_transfers: Transfer limit used (None if unlimited).
        line_preference: Preferred lines used.
        stations: Ordered station names from start to end.
        segments: Consecutive same-line runs, each a dict with keys
            ``line``, ``from``, ``to``, ``station_count``, ``distance_m``, ``stations``.
        transfers: Transfer points, each a dict with keys ``station``,
            ``from_line``, ``to_line``.
        lines: Unique line names involved, in travel order.
        distance_m: Total distance in meters.
        fare: Fare in yuan.
        transfer_count: Number of transfers.
        estimated_time_min: Estimated travel time in minutes.
    """

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    line_preference: List[str]
    stations: List[str]
    segments: List[dict]
    transfers: List[dict]
    lines: List[str]
    distance_m: int
    fare: int
    transfer_count: int
    estimated_time_min: float


def _build_segments(stations, edges):
    """Group the path into runs of consecutive edges that share a line."""
    segments = []
    index = 0
    while index < len(edges):
        line = edges[index].line
        end = index
        distance = 0
        while end < len(edges) and edges[end].line == line:
            distance += edges[end].distance
            end += 1
        segments.append({
            "line": line,
            "from": stations[index],
            "to": stations[end],
            "station_count": end - index + 1,
            "distance_m": distance,
            "stations": stations[index:end + 1],
        })
        index = end
    return segments


def _build_transfers(segments):
    """Derive transfer points from consecutive segments."""
    transfers = []
    for previous, current in zip(segments, segments[1:]):
        transfers.append({
            "station": current["from"],
            "from_line": previous["line"],
            "to_line": current["line"],
        })
    return transfers


def run_query(network, start_name, end_name, config=None):
    """Compute the route, fare and estimated time between two stations.

    Args:
        network: A ``SubwayNetwork`` instance.
        start_name: Official starting station name.
        end_name: Official ending station name.
        config: Optional ``PathfindingConfig``.

    Returns:
        RouteResult: The complete query result.

    Raises:
        RouteError: If the stations are invalid, no route exists under the
            current settings, or fare/time calculation fails.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise RouteError("Starting station cannot be the same as the ending station")

    try:
        source = network.get_number(start_name)
        target = network.get_number(end_name)
    except StationNotFoundError as exc:
        raise RouteError(str(exc)) from exc

    try:
        search = ShortestPath(network.graph, source, config)
    except ValueError as exc:
        raise RouteError(f"Path calculation failed: {exc}") from exc

    if not search.has_path_to(target):
        limit = config.max_transfers
        detail = f" within {limit} transfer(s)" if limit is not None else ""
        raise RouteError(f"No route found from '{start_name}' to '{end_name}'{detail}")

    vertices, edges = search.path_with_edges(target)
    stations = [network.name_of(v) for v in vertices]
    distance = sum(edge.distance for edge in edges)
    transfer_count = search.get_transfer_count(target)
    segments = _build_segments(stations, edges)
    transfers = _build_transfers(segments)

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    try:
        fare = Sum_money(distance)
        estimated_time = calculate_estimated_time(distance, transfer_count)
    except (TypeError, ValueError) as exc:
        raise RouteError(f"Fare calculation failed: {exc}") from exc

    return RouteResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=list(config.preferred_lines),
        stations=stations,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated_time,
    )
