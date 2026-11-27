"""Route query service: input parsing, path computation and fare/time summary."""

from dataclasses import dataclass

from errors import InvalidQueryError, PathNotFoundError, StationNotFoundError
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


@dataclass
class TransferInfo:
    """A transfer event: passengers change from one line to another at a station."""
    station: str
    from_line: str
    to_line: str


@dataclass
class RouteSegment:
    """A continuous ride on a single line."""
    line: str
    stations: list
    distance_m: float


@dataclass
class RouteResult:
    """Complete result of a route query."""
    start: str
    end: str
    mode: str
    max_transfers: object
    line_preference: list
    stations: list
    segments: list
    transfers: list
    involved_lines: list
    total_distance_m: float
    fare: int
    transfer_count: int
    estimated_time_min: float


def parse_query_input(text):
    """Split a 'Starting Station; Ending Station' input into two raw names.

    Raises:
        InvalidQueryError: If the input does not follow the required format.
    """
    if not isinstance(text, str):
        raise InvalidQueryError(INPUT_FORMAT_MESSAGE)
    normalized = text.replace("\uff1b", ";")  # accept full-width semicolon too
    if ";" not in normalized:
        raise InvalidQueryError(INPUT_FORMAT_MESSAGE)
    parts = normalized.split(";")
    if len(parts) != 2:
        raise InvalidQueryError(INPUT_FORMAT_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InvalidQueryError(INPUT_FORMAT_MESSAGE)
    return start, end


class RouteService:
    """Computes complete route results for station pairs."""

    def __init__(self, network):
        self._network = network

    def resolve_station(self, raw, role):
        """Standardize a user-entered station name.

        Args:
            raw: User input.
            role: "Starting" or "Ending", used in the error message.

        Raises:
            StationNotFoundError: If no official station matches.
        """
        name = self._network.standardize_station_name(raw)
        if name is None:
            raise StationNotFoundError(
                f"{role} station '{str(raw).strip()}' does not exist, please check the station name")
        return name

    def query(self, start_raw, end_raw, config=None):
        """Compute the optimal route between two stations.

        Returns:
            RouteResult: The route with stations, segments, transfers, distance,
            fare, transfer count, involved lines and estimated time.
        """
        config = config if config is not None else PathfindingConfig()
        start = self.resolve_station(start_raw, "Starting")
        end = self.resolve_station(end_raw, "Ending")
        if start == end:
            raise InvalidQueryError("Starting station cannot be the same as the ending station")

        network = self._network
        source = network.number_of(start)
        target = network.number_of(end)

        path = ShortestPath(network.graph, source, config)
        if not path.has_path_to(target):
            raise PathNotFoundError(f"No route found from '{start}' to '{end}' under the current settings")

        vertices, edges = path.path_with_edges(target)
        names = [network.name_of(v) for v in vertices]
        segments = self._build_segments(names, edges)
        transfers = self._build_transfers(segments)

        total_distance = float(sum(edge.weight for edge in edges))
        transfer_count = len(transfers)
        fare = Sum_money(total_distance)
        estimated = calculate_estimated_time(total_distance, transfer_count)

        involved = []
        for segment in segments:
            if segment.line not in involved:
                involved.append(segment.line)

        return RouteResult(
            start=start,
            end=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            line_preference=list(config.preferred_lines),
            stations=names,
            segments=segments,
            transfers=transfers,
            involved_lines=involved,
            total_distance_m=total_distance,
            fare=fare,
            transfer_count=transfer_count,
            estimated_time_min=estimated,
        )

    @staticmethod
    def _build_segments(names, edges):
        """Group consecutive edges on the same line into segments."""
        segments = []
        for index, edge in enumerate(edges):
            if not segments or segments[-1].line != edge.line:
                segments.append(RouteSegment(line=edge.line, stations=[names[index]], distance_m=0.0))
            segments[-1].stations.append(names[index + 1])
            segments[-1].distance_m += edge.weight
        return segments

    @staticmethod
    def _build_transfers(segments):
        """Identify transfer stations where the line changes."""
        transfers = []
        for index in range(1, len(segments)):
            previous = segments[index - 1]
            current = segments[index]
            transfers.append(TransferInfo(station=current.stations[0],
                                          from_line=previous.line,
                                          to_line=current.line))
        return transfers
