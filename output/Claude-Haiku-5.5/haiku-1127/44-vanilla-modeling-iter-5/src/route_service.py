"""Route planning service: combines the network, path search and fare logic."""

from dataclasses import dataclass, field
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class PathNotFoundError(Exception):
    """Raised when no route satisfies the query constraints."""


class FareCalculationError(Exception):
    """Raised when the fare cannot be calculated for a route."""


@dataclass
class RouteSegment:
    """A contiguous ride on one line."""

    line_name: str
    start_station: str
    end_station: str
    distance_m: float
    station_sequence: List[str] = field(default_factory=list)


@dataclass
class RouteTransfer:
    """A line change at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_km: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Route:
    """Complete result of a route query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]
    station_sequence: List[str]
    total_distance_m: float
    transfer_count: int
    segments: List[RouteSegment]
    transfers: List[RouteTransfer]
    lines_involved: List[str]
    fare_yuan: int
    summary: PathSummary


def plan_route(network, start_name, end_name, mode="shortest_distance",
               max_transfers=None, line_preference=None):
    """Compute the route, fare and summary between two stations.

    Args:
        network: SubwayNetwork instance.
        start_name: canonical starting station name.
        end_name: canonical ending station name.
        mode: one of pathfinding.PATH_MODES.
        max_transfers: optional maximum number of transfers.
        line_preference: optional preferred line name.

    Returns:
        Route

    Raises:
        ValueError: For invalid or identical stations / invalid configuration.
        PathNotFoundError: If no route satisfies the constraints.
        FareCalculationError: If the fare cannot be computed.
    """
    if start_name == end_name:
        raise ValueError("Starting station cannot be the same as the ending station")
    if start_name not in network.station_to_number:
        raise ValueError(f"unknown starting station '{start_name}'")
    if end_name not in network.station_to_number:
        raise ValueError(f"unknown ending station '{end_name}'")

    preferred = [line_preference] if line_preference else []
    config = PathfindingConfig(mode, max_transfers, preferred)
    source = network.get_station_number(start_name)
    target = network.get_station_number(end_name)
    search = ShortestPath(network.graph, source, config)

    if not search.has_path_to(target):
        limit = "" if max_transfers is None else f" within {max_transfers} transfer(s)"
        raise PathNotFoundError(f"No route found from '{start_name}' to '{end_name}'{limit}")

    nodes, edges = search.path_with_edges(target)
    if not edges:
        raise ValueError("Starting station cannot be the same as the ending station")

    names = [network.get_station_name(n) for n in nodes]

    # Group consecutive edges on the same line into segments.
    segments = []
    i = 0
    while i < len(edges):
        line = edges[i].line
        j = i
        distance = 0.0
        while j < len(edges) and edges[j].line == line:
            distance += edges[j].distance
            j += 1
        segments.append(RouteSegment(
            line_name=line,
            start_station=names[i],
            end_station=names[j],
            distance_m=distance,
            station_sequence=names[i:j + 1],
        ))
        i = j

    transfers = []
    for k in range(1, len(segments)):
        transfers.append(RouteTransfer(
            station=segments[k].start_station,
            from_line=segments[k - 1].line_name,
            to_line=segments[k].line_name,
        ))

    lines_involved = []
    for segment in segments:
        if segment.line_name not in lines_involved:
            lines_involved.append(segment.line_name)

    total_distance = sum(edge.distance for edge in edges)
    transfer_count = len(transfers)

    try:
        fare = Sum_money(total_distance)
    except (ValueError, TypeError) as exc:
        raise FareCalculationError(str(exc)) from exc

    try:
        estimated = calculate_estimated_time(total_distance, transfer_count)
    except (ValueError, TypeError) as exc:
        raise FareCalculationError(f"time estimation failed: {exc}") from exc

    summary = PathSummary(
        total_distance_km=total_distance / 1000.0,
        total_fare_yuan=fare,
        transfer_count=transfer_count,
        estimated_time_minutes=estimated,
    )

    return Route(
        start_station=start_name,
        end_station=end_name,
        mode=mode,
        max_transfers=max_transfers,
        line_preference=line_preference,
        station_sequence=names,
        total_distance_m=total_distance,
        transfer_count=transfer_count,
        segments=segments,
        transfers=transfers,
        lines_involved=lines_involved,
        fare_yuan=fare,
        summary=summary,
    )
