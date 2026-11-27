"""Route planning: combines Dijkstra path search with fare and time estimation."""

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a route cannot be planned for the given stations."""


@dataclass
class RouteSegment:
    """A continuous ride on one line.

    Attributes:
        line: Line name.
        stations: Station names travelled on this line, in order.
        distance_m: Distance travelled on this line, in meters.
    """

    line: str
    stations: list = field(default_factory=list)
    distance_m: float = 0


@dataclass
class TransferInfo:
    """A change of line at an interchange station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Complete answer to a path query."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    stations: list
    segments: list
    transfers: list
    total_distance_m: float
    fare: int
    transfer_count: int
    estimated_time_min: float

    @property
    def lines(self):
        """Unique line names involved in the journey, in travel order."""
        result = []
        for segment in self.segments:
            if segment.line not in result:
                result.append(segment.line)
        return result


def _build_segments(names, edges):
    segments = []
    for index, edge in enumerate(edges):
        if not segments or segments[-1].line != edge.line:
            segments.append(RouteSegment(edge.line, [names[index]], 0))
        segments[-1].stations.append(names[index + 1])
        segments[-1].distance_m += edge.distance
    return segments


def _build_transfers(segments):
    transfers = []
    for index in range(1, len(segments)):
        transfers.append(
            TransferInfo(
                station=segments[index].stations[0],
                from_line=segments[index - 1].line,
                to_line=segments[index].line,
            )
        )
    return transfers


def plan_route(network, start_name, end_name, config=None):
    """Plan the optimal route between two stations.

    Args:
        network: A :class:`subway_network.SubwayNetwork`.
        start_name: Official starting station name.
        end_name: Official ending station name.
        config: Optional :class:`pathfinding.PathfindingConfig`.

    Returns:
        RouteResult: Path, segments, transfers, distance, fare and time.

    Raises:
        RouteError: If the stations are identical.
        StationNotFoundError: If a station is unknown.
        PathfindingError / PathNotFoundError: If no route satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise RouteError("Starting station cannot be the same as the ending station")

    source = network.get_number(start_name)
    target = network.get_number(end_name)
    search = ShortestPath(network.graph, source, config)
    node_ids, edges = search.path_with_edges(target)

    names = [network.number_to_station[node] for node in node_ids]
    segments = _build_segments(names, edges)
    transfers = _build_transfers(segments)
    total_distance = sum(edge.distance for edge in edges)
    transfer_count = search.get_transfer_count(target)
    fare = Sum_money(total_distance)
    estimated = calculate_estimated_time(total_distance, transfer_count)

    return RouteResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        segments=segments,
        transfers=transfers,
        total_distance_m=total_distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated,
    )
