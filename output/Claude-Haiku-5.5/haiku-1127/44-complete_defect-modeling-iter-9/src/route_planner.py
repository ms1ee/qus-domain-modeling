"""Builds a complete passenger route (path, segments, transfers, fare) from a query."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Route, RouteSegment, TransferInfo
from pathfinding import PathfindingConfig, ShortestPath

if TYPE_CHECKING:  # pragma: no cover
    from network import SubwayNetwork


def _group_segments(names: Sequence[str], edges: Sequence[Edge]) -> Tuple[List[RouteSegment], List[TransferInfo]]:
    """Group consecutive edges on the same line into segments and detect transfers."""
    segments: List[RouteSegment] = []
    transfers: List[TransferInfo] = []
    for index, edge in enumerate(edges):
        start_station = names[index]
        end_station = names[index + 1]
        if segments and segments[-1].line_name == edge.line:
            current = segments[-1]
            current.distance_meters += edge.weight
            current.end_station = end_station
            continue
        if segments:
            transfers.append(
                TransferInfo(
                    station_name=start_station,
                    from_line=segments[-1].line_name,
                    to_line=edge.line,
                )
            )
        segments.append(
            RouteSegment(
                line_name=edge.line,
                distance_meters=float(edge.weight),
                sequence_number=len(segments) + 1,
                start_station=start_station,
                end_station=end_station,
            )
        )
    return segments, transfers


def plan_route(
    network: "SubwayNetwork",
    start_name: str,
    end_name: str,
    config: Optional[PathfindingConfig] = None,
) -> Route:
    """Compute the optimal route between two stations and its fare.

    Raises:
        KeyError: if a station name is unknown.
        PathNotFoundError: if no path satisfies the constraints.
    """
    config = config or PathfindingConfig()
    start = network.standardize_station(start_name)
    end = network.standardize_station(end_name)
    if start is None:
        raise KeyError(f"unknown station: {start_name}")
    if end is None:
        raise KeyError(f"unknown station: {end_name}")

    source_number = network.station_to_number[start]
    target_number = network.station_to_number[end]

    search = ShortestPath(network.graph, source_number, config)
    numbers, edges = search.path_with_edges(target_number)
    names = [network.number_to_station[number] for number in numbers]

    segments, transfers = _group_segments(names, edges)
    total_distance = float(sum(edge.weight for edge in edges))
    transfer_count = len(transfers)
    fare = Sum_money(total_distance)
    estimated_time = calculate_estimated_time(total_distance, transfer_count)

    lines_involved: List[str] = []
    for segment in segments:
        if segment.line_name not in lines_involved:
            lines_involved.append(segment.line_name)

    notes = None
    if start == end:
        notes = "start and end station are the same"

    return Route(
        stations=names,
        segments=segments,
        transfers=transfers,
        total_distance_meters=total_distance,
        transfer_count=transfer_count,
        estimated_time_minutes=estimated_time,
        fare_yuan=fare,
        lines_involved=lines_involved,
        notes=notes,
    )
