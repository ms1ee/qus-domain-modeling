"""High-level route query: combines validation, path search and fare calculation."""

from __future__ import annotations

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from input_validator import ValidationError, resolve_station
from models import Edge, SubwayNetwork
from pathfinding import PathfindingConfig, PathNotFoundError, ShortestPath


@dataclass
class Segment:
    """A continuous ride on one line, between two interchange points."""

    line: str
    stations: list[str] = field(default_factory=list)
    distance_m: int = 0

    @property
    def start(self) -> str:
        return self.stations[0]

    @property
    def end(self) -> str:
        return self.stations[-1]

    @property
    def stop_count(self) -> int:
        return len(self.stations) - 1


@dataclass
class RouteResult:
    """Complete result of a route query."""

    start: str
    end: str
    mode: str
    max_transfers: int | None
    preferred_lines: list[str]
    stations: list[str]
    edges: list[Edge]
    segments: list[Segment]
    distance_m: int
    fare: int
    transfer_count: int
    transfer_stations: list[str]
    lines: list[str]
    estimated_time_min: float

    @property
    def distance_km(self) -> float:
        return self.distance_m / 1000.0


def build_segments(station_names: list[str], edges: list[Edge]) -> list[Segment]:
    """Group a path into per-line segments; each line change is a transfer."""
    segments: list[Segment] = []
    for index, edge in enumerate(edges):
        if not segments or segments[-1].line != edge.line:
            segments.append(Segment(line=edge.line, stations=[station_names[index]]))
        segments[-1].stations.append(station_names[index + 1])
        segments[-1].distance_m += int(edge.distance)
    return segments


def query_route(network: SubwayNetwork, start_name: str, end_name: str,
                config: PathfindingConfig = None) -> RouteResult:
    """Compute the route, fare and summary between two stations.

    Raises:
        StationNotFoundError: If a station name is unknown (subclass of
            ValidationError).
        ValidationError: If start and end are the same station.
        PathNotFoundError: If no route satisfies the constraints.
        FareCalculationError: If the fare cannot be calculated.
    """
    config = config if config is not None else PathfindingConfig()
    start = resolve_station(start_name, network, "Starting")
    end = resolve_station(end_name, network, "Ending")
    if start == end:
        raise ValidationError("Starting station cannot be the same as the ending station")

    source = network.number_of(start)
    target = network.number_of(end)
    search = ShortestPath(network.graph, source, config)
    if not search.has_path_to(target):
        if config.max_transfers is not None:
            raise PathNotFoundError(
                f"No route found from '{start}' to '{end}' within "
                f"{config.max_transfers} transfer(s)"
            )
        raise PathNotFoundError(f"No route found from '{start}' to '{end}'")

    node_numbers, edges = search.path_with_edges(target)
    names = [network.name_of(number) for number in node_numbers]
    segments = build_segments(names, edges)
    distance = sum(int(edge.distance) for edge in edges)
    transfer_count = len(segments) - 1
    transfer_stations = [segment.end for segment in segments[:-1]]
    lines: list[str] = []
    for segment in segments:
        if segment.line not in lines:
            lines.append(segment.line)

    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, transfer_count)

    return RouteResult(
        start=start,
        end=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        edges=edges,
        segments=segments,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        transfer_stations=transfer_stations,
        lines=lines,
        estimated_time_min=estimated,
    )
