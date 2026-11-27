"""Route query service: runs path search, builds route details, fare and time estimates."""

from dataclasses import dataclass, field
from typing import Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class FareCalculationError(Exception):
    """Raised when the fare or time for a computed route cannot be calculated."""


@dataclass
class RouteSegment:
    """A maximal run of consecutive stops on the same line."""

    line: str
    start: str
    end: str
    edge_count: int
    distance_m: float

    @property
    def stop_count(self) -> int:
        """Number of stations covered by the segment, including both ends."""
        return self.edge_count + 1


@dataclass
class TransferInfo:
    """A transfer between two line segments at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Complete result of a route query."""

    start: str
    destination: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: list = field(default_factory=list)
    stations: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    distance_m: float = 0
    fare: int = 0
    transfer_count: int = 0
    estimated_minutes: float = 0.0

    @property
    def distance_km(self) -> float:
        """Total distance in kilometers."""
        return self.distance_m / 1000.0

    @property
    def stop_count(self) -> int:
        """Number of stations on the route."""
        return len(self.stations)

    def to_summary(self) -> dict:
        """Return the key figures of the route as a dictionary."""
        return {
            "total_distance_km": round(self.distance_km, 3),
            "total_distance_m": self.distance_m,
            "fare_yuan": self.fare,
            "transfer_count": self.transfer_count,
            "estimated_time_minutes": self.estimated_minutes,
            "stop_count": self.stop_count,
        }


def _build_segments(names, edges) -> list:
    """Group consecutive edges that share a line into RouteSegment objects."""
    segments = []
    for index, edge in enumerate(edges):
        end_name = names[index + 1]
        if segments and segments[-1].line == edge.line:
            current = segments[-1]
            current.end = end_name
            current.edge_count += 1
            current.distance_m += edge.weight
        else:
            segments.append(RouteSegment(
                line=edge.line,
                start=names[index],
                end=end_name,
                edge_count=1,
                distance_m=edge.weight,
            ))
    return segments


def _build_transfers(segments) -> list:
    """Derive transfer points from consecutive segments."""
    transfers = []
    for previous, following in zip(segments, segments[1:]):
        transfers.append(TransferInfo(
            station=previous.end,
            from_line=previous.line,
            to_line=following.line,
        ))
    return transfers


def query_route(network, start_name, destination_name, config=None) -> RouteResult:
    """Compute the route between two stations and assemble the full result.

    Args:
        network: A models.SubwayNetwork instance.
        start_name: Official name of the starting station.
        destination_name: Official name of the ending station.
        config: PathfindingConfig (defaults are used if None).

    Raises:
        ValueError: If the start and end stations are identical.
        StationNotFoundError: If a station does not exist.
        PathNotFoundError: If no route satisfies the configuration.
        FareCalculationError: If the fare or time cannot be computed.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == destination_name:
        raise ValueError("Starting station cannot be the same as the ending station")

    source = network.get_station_number(start_name)
    target = network.get_station_number(destination_name)
    search = ShortestPath(network.graph, source, config)
    nodes, edges = search.path_with_edges(target)

    names = [network.station_name(number) for number in nodes]
    segments = _build_segments(names, edges)
    transfers = _build_transfers(segments)
    lines = []
    for segment in segments:
        if segment.line not in lines:
            lines.append(segment.line)
    distance = sum(edge.weight for edge in edges)
    transfer_count = search.get_transfer_count(target)

    try:
        fare = Sum_money(distance)
        minutes = calculate_estimated_time(distance, transfer_count)
    except (ValueError, TypeError) as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    return RouteResult(
        start=start_name,
        destination=destination_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_minutes=minutes,
    )
