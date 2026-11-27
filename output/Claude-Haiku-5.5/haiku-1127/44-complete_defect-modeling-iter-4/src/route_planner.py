"""Route planning service combining path search, segmentation and fare calculation.

``find_route`` turns a Dijkstra result into a ``Route`` object containing the
station sequence, line segments, transfer details, total distance, fare and
estimated travel time.
"""

from typing import List, Optional, Tuple

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Route, RouteSegment, TransferPoint
from network import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath


class RouteNotFoundError(Exception):
    """Raised when no route satisfies the query and its constraints."""


def find_route(
    network: SubwayNetwork,
    start_name: str,
    end_name: str,
    config: Optional[PathfindingConfig] = None,
) -> Route:
    """Compute the optimal route between two official station names.

    Args:
        network: The loaded subway network.
        start_name: Official name of the origin station.
        end_name: Official name of the destination station.
        config: Path query configuration (mode, transfer limit, preference).

    Returns:
        A fully populated ``Route``.

    Raises:
        RouteNotFoundError: If no path exists or the transfer limit cannot be met.
        KeyError: If a station name is unknown.
    """
    config = config if config is not None else PathfindingConfig()
    source_number = network.number_of(start_name)
    target_number = network.number_of(end_name)

    search = ShortestPath(network.graph, source_number, config)
    if not search.has_path(target_number):
        raise RouteNotFoundError(f"No route found from '{start_name}' to '{end_name}'")

    node_numbers, edges = search.path_with_edges(target_number)
    names = [network.name_of(number) for number in node_numbers]
    segments, transfers = _build_segments(names, edges)

    transfer_count = len(transfers)
    if config.max_transfers is not None and transfer_count > config.max_transfers:
        raise RouteNotFoundError(
            f"No route found within {config.max_transfers} transfer(s); "
            f"the best route requires {transfer_count}"
        )

    total_distance = float(sum(edge.distance for edge in edges))
    lines_involved: List[str] = []
    for segment in segments:
        if segment.line_name not in lines_involved:
            lines_involved.append(segment.line_name)

    return Route(
        stations=names,
        segments=segments,
        transfers=transfers,
        total_distance_meters=total_distance,
        transfer_count=transfer_count,
        estimated_time_minutes=calculate_estimated_time(total_distance, transfer_count),
        fare_yuan=Sum_money(total_distance),
        lines_involved=lines_involved,
    )


def _build_segments(
    names: List[str], edges: List[Edge]
) -> Tuple[List[RouteSegment], List[TransferPoint]]:
    """Group consecutive edges on the same line into segments and derive transfers.

    The station list has exactly one more element than the edge list, because
    transfers do not repeat a station in the reconstructed path.

    Raises:
        RuntimeError: If the station and edge sequences are inconsistent.
    """
    segments: List[RouteSegment] = []
    transfers: List[TransferPoint] = []
    if not edges:
        return segments, transfers
    if len(names) != len(edges) + 1:
        raise RuntimeError("Inconsistent path reconstruction: station/edge count mismatch")

    start_index = 0
    for index, edge in enumerate(edges):
        is_last = index == len(edges) - 1
        if is_last or edges[index + 1].line != edge.line:
            segment_edges = edges[start_index : index + 1]
            segments.append(
                RouteSegment(
                    line_name=edge.line,
                    start_station=names[start_index],
                    end_station=names[index + 1],
                    distance_meters=float(sum(item.distance for item in segment_edges)),
                    hop_count=len(segment_edges),
                )
            )
            start_index = index + 1

    for position in range(len(segments) - 1):
        current = segments[position]
        following = segments[position + 1]
        transfers.append(
            TransferPoint(
                station_name=current.end_station,
                from_line=current.line_name,
                to_line=following.line_name,
            )
        )
    return segments, transfers
