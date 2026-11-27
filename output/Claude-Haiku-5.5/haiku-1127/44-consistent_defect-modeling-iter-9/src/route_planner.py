"""Route planning service: combines shortest-path search, transfer analysis and fare."""

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from models import LogicalValidationError, PathNotFoundError
from pathfinding import PathfindingConfig, ShortestPath


@dataclass
class Segment:
    """A contiguous ride on one line."""

    line: str
    stations: list = field(default_factory=list)
    distance: float = 0.0


@dataclass
class TransferInfo:
    """A line change at an interchange station."""

    station: str
    from_line: str
    to_line: str
    involved_lines: list = field(default_factory=list)


@dataclass
class Route:
    """Complete result of a route query."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    station_path: list
    total_distance: float
    transfer_count: int
    segments: list
    transfers: list
    involved_lines: list
    fare: int
    estimated_time: float


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_m: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


def summarize(route):
    """Extract a PathSummary from a Route."""
    return PathSummary(
        total_distance_m=route.total_distance,
        total_fare=route.fare,
        transfer_count=route.transfer_count,
        estimated_time_minutes=route.estimated_time,
    )


def _build_segments(station_path, edges):
    """Group consecutive edges by line into segments."""
    segments = []
    for index, edge in enumerate(edges):
        if not segments or segments[-1].line != edge.line:
            segments.append(Segment(line=edge.line, stations=[station_path[index]], distance=0.0))
        segment = segments[-1]
        segment.stations.append(station_path[index + 1])
        segment.distance += edge.distance
    return segments


def _build_transfers(segments, network):
    """Describe each line change between consecutive segments."""
    transfers = []
    for index in range(1, len(segments)):
        previous = segments[index - 1]
        current = segments[index]
        station = current.stations[0]
        served = network.graph.station_lines.get(station, [])
        involved = list(dict.fromkeys([previous.line, current.line] + list(served)))
        transfers.append(
            TransferInfo(
                station=station,
                from_line=previous.line,
                to_line=current.line,
                involved_lines=involved,
            )
        )
    return transfers


def plan_route(network, start, end, config=None):
    """Compute the route between two official station names.

    Args:
        network: a SubwayNetwork instance.
        start: official starting station name.
        end: official ending station name.
        config: PathfindingConfig (defaults to comprehensive mode).

    Raises:
        LogicalValidationError: if start equals end.
        PathNotFoundError: if no route exists under the constraints.
        FareCalculationError: if the fare cannot be computed.
    """
    config = config if config is not None else PathfindingConfig()
    if start == end:
        raise LogicalValidationError("Starting station cannot be the same as the ending station")

    source = network.station_number(start)
    target = network.station_number(end)
    searcher = ShortestPath(network.graph, source, config)
    if not searcher.has_path_to(target):
        raise PathNotFoundError(
            f"No route found between '{start}' and '{end}' under the given constraints"
        )

    node_path, edges = searcher.path_with_edges(target)
    station_path = [network.station_name(node) for node in node_path]
    segments = _build_segments(station_path, edges)
    transfers = _build_transfers(segments, network)
    total_distance = float(sum(edge.distance for edge in edges))
    transfer_count = len(transfers)
    fare = Sum_money(total_distance)
    estimated = calculate_estimated_time(total_distance, transfer_count)
    involved_lines = list(dict.fromkeys(segment.line for segment in segments))

    return Route(
        start=start,
        end=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        station_path=station_path,
        total_distance=total_distance,
        transfer_count=transfer_count,
        segments=segments,
        transfers=transfers,
        involved_lines=involved_lines,
        fare=fare,
        estimated_time=estimated,
    )
