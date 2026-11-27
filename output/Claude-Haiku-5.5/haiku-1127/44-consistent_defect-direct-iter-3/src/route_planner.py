"""
Route planning service.

Combines the network, the Dijkstra path search, the fare calculator and the
time estimator into a single ``plan_route`` operation that returns a
RouteResult containing everything needed for reporting.
"""

from dataclasses import dataclass
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteNotFoundError(Exception):
    """Raised when no path exists between two stations (within the constraints)."""


class CalculationError(Exception):
    """Raised when path or fare calculation fails unexpectedly."""


@dataclass
class LineSegment:
    """A continuous ride on one line, in travel order."""
    line: str
    start: str
    end: str
    stops: int  # number of track sections (edges) travelled


@dataclass
class TransferInfo:
    """A transfer station with the lines before and after the interchange."""
    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Complete result of a route query."""
    origin: str
    destination: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]          # station names ordered from end to start
    segments: List[LineSegment]  # travel order
    transfers: List[TransferInfo]
    lines: List[str]             # involved lines in travel order, unique
    distance_m: int
    fare: int
    transfer_count: int
    estimated_minutes: float


def _build_segments(edges_forward, names_forward):
    """Group consecutive edges on the same line into LineSegments."""
    segments = []
    for i, edge in enumerate(edges_forward):
        if segments and segments[-1].line == edge.line:
            segments[-1].end = names_forward[i + 1]
            segments[-1].stops += 1
        else:
            segments.append(LineSegment(edge.line, names_forward[i], names_forward[i + 1], 1))
    return segments


def plan_route(network, origin, destination, config=None):
    """
    Compute the route, fare and summary information between two stations.

    Args:
        network: A SubwayNetwork instance.
        origin: Official starting station name.
        destination: Official ending station name.
        config: PathfindingConfig (defaults to shortest-distance mode).

    Returns:
        RouteResult

    Raises:
        ValueError: If origin and destination are identical.
        RouteNotFoundError: If no path is found.
        CalculationError: If fare calculation fails.
    """
    config = config if config is not None else PathfindingConfig()
    if origin == destination:
        raise ValueError("Starting station cannot be the same as the ending station")

    src = network.number_of(origin)
    dst = network.number_of(destination)

    try:
        sp = ShortestPath(network.graph, src, config)
    except Exception as exc:
        raise CalculationError(f"Path calculation failed: {exc}") from exc

    if not sp.has_path_to(dst):
        raise RouteNotFoundError(
            f"No route found from '{origin}' to '{destination}' under the current constraints"
        )

    stations_num, edges = sp.path_with_edges(dst)
    stations_backtrack = [network.name_of(n) for n in stations_num]
    edges_forward = list(reversed(edges))
    names_forward = list(reversed(stations_backtrack))

    segments = _build_segments(edges_forward, names_forward)
    transfers = [
        TransferInfo(segments[i].end, segments[i].line, segments[i + 1].line)
        for i in range(len(segments) - 1)
    ]
    lines = []
    for seg in segments:
        if seg.line not in lines:
            lines.append(seg.line)

    distance = sum(edge.distance for edge in edges)
    transfer_count = sp.get_transfer_count(dst)

    try:
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, transfer_count)
    except (TypeError, ValueError) as exc:
        raise CalculationError(f"Fare calculation failed: {exc}") from exc

    return RouteResult(
        origin=origin,
        destination=destination,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=stations_backtrack,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_minutes=estimated,
    )
