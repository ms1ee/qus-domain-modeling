"""Query service: combines path search, fare calculation and summaries."""

from dataclasses import dataclass, field

from .fare_calculator import Sum_money, calculate_estimated_time
from .pathfinding import PathfindingConfig, PathNotFoundError, ShortestPath


@dataclass
class TransferInfo:
    """A transfer point: the station and the lines before and after it."""
    station: str
    from_line: str
    to_line: str


@dataclass
class Segment:
    """A continuous ride on one line: the line and its stations in order."""
    line: str
    stations: list = field(default_factory=list)


@dataclass
class PathResult:
    """Complete result of a path query."""
    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    stations: list
    segments: list
    transfers: list
    lines: list
    distance_m: float
    fare: int
    transfer_count: int
    estimated_time_min: float

    @property
    def distance_km(self):
        """Total distance in kilometers."""
        return self.distance_m / 1000.0


def _build_segments(names, edges):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for index, edge in enumerate(edges):
        if not segments or segments[-1].line != edge.line:
            segments.append(Segment(edge.line, [names[index]]))
        segments[-1].stations.append(names[index + 1])
    return segments


def _build_transfers(names, edges):
    """Identify the stations where the line changes."""
    transfers = []
    for index in range(1, len(edges)):
        if edges[index].line != edges[index - 1].line:
            transfers.append(TransferInfo(names[index], edges[index - 1].line, edges[index].line))
    return transfers


class QueryService:
    """Answers route queries against a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def query(self, start_name, end_name, config=None):
        """Compute the optimal route, fare and summary between two stations.

        Args:
            start_name: Starting station (standardised automatically).
            end_name: Ending station (standardised automatically).
            config: ``PathfindingConfig`` or None for defaults.

        Returns:
            PathResult: The route and derived information.

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: If start and end are the same station.
            PathNotFoundError: If no route satisfies the constraints.
        """
        cfg = config if config is not None else PathfindingConfig()
        start = self.network.standardize(start_name)
        end = self.network.standardize(end_name)
        if start == end:
            raise ValueError("Starting station cannot be the same as the ending station")

        source = self.network.number_of(start)
        target = self.network.number_of(end)
        shortest = ShortestPath(self.network.graph, source, cfg)
        if not shortest.has_path_to(target):
            raise PathNotFoundError(f"no route found from '{start}' to '{end}' with the given constraints")

        numbers, edges = shortest.path_with_edges(target)
        names = [self.network.name_of(number) for number in numbers]
        distance = shortest.dist_to[target]
        transfer_count = shortest.get_transfer_count(target)
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, transfer_count)

        lines = []
        for edge in edges:
            if edge.line not in lines:
                lines.append(edge.line)

        return PathResult(
            start=start,
            end=end,
            mode=cfg.mode,
            max_transfers=cfg.max_transfers,
            preferred_lines=list(cfg.preferred_lines),
            stations=names,
            segments=_build_segments(names, edges),
            transfers=_build_transfers(names, edges),
            lines=lines,
            distance_m=distance,
            fare=fare,
            transfer_count=transfer_count,
            estimated_time_min=estimated,
        )
