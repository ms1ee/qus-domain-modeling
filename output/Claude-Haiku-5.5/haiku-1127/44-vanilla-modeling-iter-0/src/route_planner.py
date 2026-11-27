"""
Route planning service.

Combines the subway network, the path search and the fare calculator to
produce a complete Route: station sequence, line segments, transfers, total
distance, fare and estimated travel time.
"""
from __future__ import annotations

from dataclasses import dataclass

from data_manager import SubwayNetwork
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge
from pathfinding import PathfindingConfig, ShortestPath


class NoRouteError(Exception):
    """Raised when no path satisfies the query constraints."""


class FareCalculationError(Exception):
    """Raised when the fare or time estimate cannot be computed."""


@dataclass
class TransferInfo:
    """A line change at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class LineSegment:
    """A continuous ride on a single line."""

    line: str
    start_station: str
    end_station: str
    segment_count: int
    distance_m: float


@dataclass
class Route:
    """A fully computed travel route."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: int | None
    line_preference: list[str]
    stations: list[str]
    edges: list[Edge]
    total_distance_m: float
    transfer_count: int
    transfers: list[TransferInfo]
    segments: list[LineSegment]
    lines: list[str]
    fare_yuan: int
    estimated_time_min: float

    @property
    def station_count(self) -> int:
        """Number of stations on the route, including start and end."""
        return len(self.stations)


def _find_transfers(names: list[str], edges: list[Edge]) -> list[TransferInfo]:
    """Identify stations where the travelled line changes."""
    transfers: list[TransferInfo] = []
    for index in range(1, len(edges)):
        previous_line = edges[index - 1].line
        next_line = edges[index].line
        if previous_line != next_line:
            transfers.append(TransferInfo(names[index], previous_line, next_line))
    return transfers


def _build_segments(names: list[str], edges: list[Edge]) -> list[LineSegment]:
    """Group consecutive edges operated by the same line into segments."""
    segments: list[LineSegment] = []
    if not edges:
        return segments
    start = 0
    for index in range(1, len(edges) + 1):
        if index == len(edges) or edges[index].line != edges[start].line:
            part = edges[start:index]
            segments.append(LineSegment(
                line=edges[start].line,
                start_station=names[start],
                end_station=names[index],
                segment_count=len(part),
                distance_m=sum(edge.weight for edge in part),
            ))
            start = index
    return segments


def _unique_lines(edges: list[Edge]) -> list[str]:
    """Return the lines used by the route, in order of first use."""
    lines: list[str] = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def plan_route(network: SubwayNetwork, start_station: str, end_station: str,
               config: PathfindingConfig | None = None) -> Route:
    """Compute the route between two stations.

    Args:
        network: The loaded subway network.
        start_station: Starting station name (any accepted spelling).
        end_station: Ending station name (any accepted spelling).
        config: Query configuration (mode, transfer limit, line preference).

    Returns:
        The computed Route.

    Raises:
        StationNotFoundError: If a station name is unknown.
        ValueError: If the start and end stations are the same.
        NoRouteError: If no route satisfies the constraints.
        FareCalculationError: If the fare or time cannot be calculated.
    """
    config = config or PathfindingConfig()
    start = network.resolve_name(start_station)
    end = network.resolve_name(end_station)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")

    search = ShortestPath(network.graph, network.station_to_number[start], config)
    target = network.station_to_number[end]
    if not search.has_path(target):
        message = f"No route found between '{start}' and '{end}'"
        if config.max_transfers is not None:
            message += f" within {config.max_transfers} transfer(s)"
        raise NoRouteError(message)

    numbers, edges = search.path_with_edges(target)
    names = [network.number_to_name[number] for number in numbers]
    total_distance = sum(edge.weight for edge in edges)
    transfers = _find_transfers(names, edges)
    transfer_count = len(transfers)

    try:
        fare = Sum_money(total_distance)
        estimated_time = calculate_estimated_time(total_distance, transfer_count)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    return Route(
        start_station=start,
        end_station=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=list(config.preferred_lines),
        stations=names,
        edges=edges,
        total_distance_m=total_distance,
        transfer_count=transfer_count,
        transfers=transfers,
        segments=_build_segments(names, edges),
        lines=_unique_lines(edges),
        fare_yuan=fare,
        estimated_time_min=estimated_time,
    )
