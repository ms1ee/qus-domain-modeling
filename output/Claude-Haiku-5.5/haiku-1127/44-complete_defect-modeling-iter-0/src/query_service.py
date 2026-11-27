"""Query orchestration: input parsing, validation, path search, fare and summary.

``SubwayQueryService.query_route`` is the main entry point used by the CLI. It
returns a ``Route`` object that the reporting module can format.
"""

from dataclasses import dataclass, field
from typing import Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

QUERY_SEPARATOR = ";"
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for all user-facing query errors."""


class InputFormatError(QueryError):
    """The query text does not follow the 'Start; End' format."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class LogicalQueryError(QueryError):
    """The query is logically invalid (e.g. identical start and end)."""


class PathNotFoundError(QueryError):
    """No route exists under the current settings."""


class CalculationError(QueryError):
    """Path, fare or time calculation failed."""


@dataclass
class Route:
    """Result of a route query.

    Attributes:
        start_station / end_station: official station names.
        mode: query mode used.
        max_transfers: transfer limit (None = unlimited).
        line_preference: list of preferred lines.
        stations: ordered list of station names from start to end.
        edges: list of Edge objects along the path.
        total_distance_m: total distance in meters.
        transfer_count: number of line changes.
        fare_yuan: computed fare in yuan.
        estimated_time_min: estimated travel time in minutes.
        segments: list of (line name, station names) segments.
        transfers: list of dicts {station, from_line, to_line}.
        lines: unique line names in travel order.
    """

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: list
    stations: list
    edges: list
    total_distance_m: float
    transfer_count: int
    fare_yuan: int
    estimated_time_min: float
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)


def parse_query_input(text):
    """Split 'Starting Station; Ending Station' into two stripped names.

    Raises:
        InputFormatError: if the separator is missing/duplicated or a name is empty.
    """
    if not isinstance(text, str) or text.count(QUERY_SEPARATOR) != 1:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start, end = (part.strip() for part in text.split(QUERY_SEPARATOR))
    if not start or not end:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start, end


def build_segments(stations, edges):
    """Group the path into consecutive same-line segments.

    Returns:
        list of (line name, list of station names) tuples.
    """
    if not edges:
        return []
    segments = []
    current_line = edges[0].line
    seg_start = 0
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append((current_line, stations[seg_start:index + 1]))
            seg_start = index
            current_line = edge.line
    segments.append((current_line, stations[seg_start:]))
    return segments


def build_transfers(segments):
    """Derive transfer records from consecutive segments."""
    transfers = []
    for index in range(len(segments) - 1):
        from_line, seg_stations = segments[index]
        to_line = segments[index + 1][0]
        transfers.append({
            "station": seg_stations[-1],
            "from_line": from_line,
            "to_line": to_line,
        })
    return transfers


class SubwayQueryService:
    """Validates queries and computes routes, fares and summaries."""

    def __init__(self, network):
        self._network = network

    def resolve_station(self, name, role):
        """Return the official station name or raise ``StationNotFoundError``.

        Args:
            name: user input.
            role: "Starting" or "Ending" (used in the error message).
        """
        official = self._network.standardize_station_name(name)
        if official is None:
            raise StationNotFoundError(
                "{} station '{}' does not exist, please check the station name".format(role, name)
            )
        return official

    def query_from_text(self, text, config=None):
        """Parse 'Start; End' text and compute the route."""
        start_input, end_input = parse_query_input(text)
        return self.query_route(start_input, end_input, config)

    def query_route(self, start_input, end_input, config=None):
        """Compute the route, fare and summary between two stations.

        Raises:
            QueryError subclasses for all user-facing failures.
        """
        config = config if config is not None else PathfindingConfig()
        start = self.resolve_station(start_input, "Starting")
        end = self.resolve_station(end_input, "Ending")
        if start == end:
            raise LogicalQueryError("Starting station cannot be the same as the ending station")

        network = self._network
        start_no = network.station_to_number[start]
        end_no = network.station_to_number[end]

        try:
            search = ShortestPath(network.graph, start_no, config)
            if not search.has_path_to(end_no):
                raise PathNotFoundError(
                    "No route found from '{}' to '{}' under the current settings".format(start, end)
                )
            station_numbers, edges = search.path_with_edges(end_no)
            transfer_count = search.get_transfer_count(end_no)
        except PathNotFoundError:
            raise
        except (KeyError, ValueError, IndexError) as exc:
            raise CalculationError("Path calculation failed: {}".format(exc)) from exc

        stations = [network.station_name(number) for number in station_numbers]
        total_distance = float(sum(edge.distance for edge in edges))
        segments = build_segments(stations, edges)
        transfers = build_transfers(segments)
        lines = []
        for line, _ in segments:
            if line not in lines:
                lines.append(line)

        try:
            fare = Sum_money(total_distance)
            estimated_time = calculate_estimated_time(total_distance, transfer_count)
        except ValueError as exc:
            raise CalculationError("Fare calculation failed: {}".format(exc)) from exc

        return Route(
            start_station=start,
            end_station=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            line_preference=list(config.preferred_lines),
            stations=stations,
            edges=edges,
            total_distance_m=total_distance,
            transfer_count=transfer_count,
            fare_yuan=fare,
            estimated_time_min=estimated_time,
            segments=segments,
            transfers=transfers,
            lines=lines,
        )
