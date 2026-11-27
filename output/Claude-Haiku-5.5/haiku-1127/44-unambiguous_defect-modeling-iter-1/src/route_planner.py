"""High-level route planning: combines path search, fare and time estimates.

The result object (``RouteResult``) carries everything the reporting layer
needs: station sequence, line segments, transfers, distance, fare and time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from errors import PathNotFoundError, SubwayError, ValidationError
from fare_calculator import Sum_money, calculate_estimated_time
from models import Graph
from pathfinding import PathfindingConfig, ShortestPath


@dataclass(frozen=True)
class TransferInfo:
    """A line change at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Full description of a computed route.

    Attributes:
        origin: Official name of the starting station.
        destination: Official name of the ending station.
        mode: Path query mode used.
        max_transfers: Transfer limit used (``None`` means unlimited).
        preferred_lines: Line preferences used.
        stations: Ordered station names from origin to destination.
        segments: List of ``(line name, station names on that line)`` in travel order.
        transfers: Transfer stations with the lines joined.
        involved_lines: Unique line names in order of first use.
        total_distance_m: Total travelled distance in meters.
        transfer_count: Number of line changes.
        fare: Fare in yuan.
        estimated_time_min: Estimated travel time in minutes.
    """

    origin: str
    destination: str
    mode: str
    max_transfers: int | None
    preferred_lines: list[str]
    stations: list[str]
    segments: list[tuple[str, list[str]]]
    transfers: list[TransferInfo]
    involved_lines: list[str]
    total_distance_m: float
    transfer_count: int
    fare: int
    estimated_time_min: float = 0.0

    @property
    def total_distance_km(self) -> float:
        """Total distance converted from meters to kilometers."""
        return self.total_distance_m / 1000.0


def _build_segments(names: list[str], edges) -> tuple[list[tuple[str, list[str]]], list[TransferInfo]]:
    """Split the route into per-line segments and collect transfer details."""
    segments: list[tuple[str, list[str]]] = []
    transfers: list[TransferInfo] = []
    if not edges:
        return segments, transfers

    current_line = edges[0].line
    current_stations = [names[0]]
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append((current_line, current_stations))
            transfers.append(TransferInfo(names[index], current_line, edge.line))
            current_line = edge.line
            current_stations = [names[index]]
        current_stations.append(names[index + 1])
    segments.append((current_line, current_stations))
    return segments, transfers


def plan_route(
    graph: Graph,
    origin: str,
    destination: str,
    config: PathfindingConfig | None = None,
) -> RouteResult:
    """Compute the route between two official station names.

    Args:
        graph: The subway network.
        origin: Official starting station name.
        destination: Official ending station name.
        config: Query options; defaults to ``PathfindingConfig()``.

    Returns:
        A ``RouteResult`` describing the route.

    Raises:
        ValidationError: If the stations are equal or unknown.
        PathNotFoundError: If no route satisfies the constraints.
        SubwayError: If fare or time calculation fails.
    """
    config = config or PathfindingConfig()
    if origin == destination:
        raise ValidationError("Starting station cannot be the same as the ending station")
    if not graph.has_station(origin) or not graph.has_station(destination):
        raise ValidationError("both stations must exist in the subway network")

    source_number = graph.number_of(origin)
    target_number = graph.number_of(destination)
    search = ShortestPath(graph, source_number, config)
    numbers, edges = search.path_with_edges(target_number)
    if not edges:
        raise PathNotFoundError("the origin and destination resolve to the same route")

    names = [graph.name_of(number) for number in numbers]
    segments, transfers = _build_segments(names, edges)
    transfer_count = len(transfers)
    total_distance = float(sum(edge.weight for edge in edges))

    involved: list[str] = []
    for line, _ in segments:
        if line not in involved:
            involved.append(line)

    fare = Sum_money(total_distance)
    estimated_time = calculate_estimated_time(total_distance, transfer_count)

    return RouteResult(
        origin=origin,
        destination=destination,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        segments=segments,
        transfers=transfers,
        involved_lines=involved,
        total_distance_m=total_distance,
        transfer_count=transfer_count,
        fare=fare,
        estimated_time_min=estimated_time,
    )
