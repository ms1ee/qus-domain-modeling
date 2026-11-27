"""Combines path search, transfer analysis and fare calculation into a route result."""

from dataclasses import dataclass, field
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a route cannot be planned (unknown station, no path, calculation failure)."""


@dataclass
class RouteSegment:
    """A run of consecutive stations on the same line.

    Attributes:
        sequence_number: 1-based position of the segment in the trip.
        line: line name.
        start_station: first station of the segment.
        end_station: last station of the segment.
        distance_m: total distance of the segment in meters.
        station_count: number of stations in the segment (including endpoints).
    """

    sequence_number: int
    line: str
    start_station: str
    end_station: str
    distance_m: float
    station_count: int


@dataclass
class TransferInfo:
    """A transfer (line change) at an interchange station."""

    station: str
    from_line: str
    to_line: str
    station_lines: List[str] = field(default_factory=list)


@dataclass
class RouteResult:
    """Complete result of a route query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: List[str]
    stations: List[str]
    segments: List[RouteSegment]
    transfers: List[TransferInfo]
    total_distance_m: float
    transfer_count: int
    fare: int
    estimated_time_minutes: float
    lines: List[str]


def _build_segments(stations, edges):
    segments = []
    for i, edge in enumerate(edges):
        if segments and segments[-1].line == edge.line:
            seg = segments[-1]
            seg.end_station = stations[i + 1]
            seg.distance_m += edge.weight
            seg.station_count += 1
        else:
            segments.append(RouteSegment(
                sequence_number=len(segments) + 1,
                line=edge.line,
                start_station=stations[i],
                end_station=stations[i + 1],
                distance_m=float(edge.weight),
                station_count=2,
            ))
    return segments


def _build_transfers(network, stations, edges):
    transfers = []
    for i in range(1, len(edges)):
        previous, current = edges[i - 1], edges[i]
        if previous.line != current.line:
            station = stations[i]
            transfers.append(TransferInfo(
                station=station,
                from_line=previous.line,
                to_line=current.line,
                station_lines=network.lines_of(station),
            ))
    return transfers


def plan_route(network, start_name, end_name, config=None):
    """Plan the optimal route between two stations.

    Args:
        network: SubwayNetwork instance.
        start_name: starting station name (matched leniently).
        end_name: ending station name (matched leniently).
        config: PathfindingConfig (defaults to shortest-distance mode).

    Returns:
        RouteResult with path, segments, transfers, distance, fare and time.

    Raises:
        RouteError: on invalid stations, no path, or calculation failure.
    """
    config = config or PathfindingConfig()
    start = network.standardize_name(start_name)
    if start is None:
        raise RouteError(f"Starting station '{start_name}' does not exist, please check the station name")
    end = network.standardize_name(end_name)
    if end is None:
        raise RouteError(f"Ending station '{end_name}' does not exist, please check the station name")
    if start == end:
        raise RouteError("Starting station cannot be the same as the ending station")

    try:
        sp = ShortestPath(network.graph, network.station_number(start), config)
    except ValueError as exc:
        raise RouteError(f"Path calculation failed: {exc}") from exc

    dst_id = network.station_number(end)
    if not sp.has_path_to(dst_id):
        raise RouteError(f"No route found from '{start}' to '{end}' under the given constraints")

    node_ids, edges = sp.path_with_edges(dst_id)
    stations = [network.name_of(n) for n in node_ids]
    segments = _build_segments(stations, edges)
    transfers = _build_transfers(network, stations, edges)
    total_distance = float(sum(e.weight for e in edges))
    transfer_count = len(transfers)

    try:
        fare = Sum_money(total_distance)
    except ValueError as exc:
        raise RouteError(f"Fare calculation failed: {exc}") from exc

    lines = []
    for seg in segments:
        if seg.line not in lines:
            lines.append(seg.line)

    return RouteResult(
        start_station=start,
        end_station=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=list(config.preferred_lines),
        stations=stations,
        segments=segments,
        transfers=transfers,
        total_distance_m=total_distance,
        transfer_count=transfer_count,
        fare=fare,
        estimated_time_minutes=calculate_estimated_time(total_distance, transfer_count),
        lines=lines,
    )
