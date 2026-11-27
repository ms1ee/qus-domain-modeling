"""Query service: parses user input, resolves stations and computes routes."""

from dataclasses import dataclass, field
import re

from fare_calculator import Sum_money, calculate_estimated_time
from network import StationNotFoundError
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Raised for any query that cannot be answered (format, station or path errors)."""


class QueryFormatError(QueryError):
    """Raised when the query text does not follow the expected format."""


@dataclass
class RouteResult:
    """Complete answer to a route query."""

    start_input: str
    end_input: str
    start: str
    end: str
    start_exact: bool
    end_exact: bool
    mode: str
    max_transfers: object
    line_preference: list
    stations: list
    edges: list
    distance_m: int
    fare: int
    estimated_time_min: float
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)

    @property
    def transfer_count(self):
        """Number of transfers on the route."""
        return len(self.transfers)

    def segments(self):
        """Group consecutive edges on the same line into ``(line, stations)`` segments."""
        result = []
        if not self.edges:
            return result
        seg_start = 0
        for i, edge in enumerate(self.edges):
            is_last = i == len(self.edges) - 1
            if is_last or self.edges[i + 1].line != edge.line:
                result.append((edge.line, self.stations[seg_start:i + 2]))
                seg_start = i + 1
        return result


def parse_query(text):
    """Split 'Starting Station; Ending Station' input into two station strings.

    Both ';' and ',' (and their full-width forms) are accepted as separators.

    Raises:
        QueryFormatError: If the text does not contain exactly two non-empty parts.
    """
    if text is None:
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    parts = re.split(r"[;,\uff1b\uff0c]", str(text))
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def _find_transfers(stations, edges):
    """Return transfer records where the travel line changes."""
    transfers = []
    for i in range(1, len(edges)):
        prev_edge, cur_edge = edges[i - 1], edges[i]
        if prev_edge.line != cur_edge.line:
            transfers.append({
                "station": stations[i],
                "from_line": prev_edge.line,
                "to_line": cur_edge.line,
            })
    return transfers


def run_query(network, start_input, end_input, config=None):
    """Compute the route between two stations.

    Args:
        network: A ``network.SubwayNetwork``.
        start_input: Starting station as typed by the user.
        end_input: Ending station as typed by the user.
        config: ``PathfindingConfig`` (defaults to shortest distance).

    Returns:
        RouteResult: The computed route with fare and summary data.

    Raises:
        QueryError: If a station cannot be resolved, the stations are identical,
            no route exists, or the calculation fails.
    """
    config = config or PathfindingConfig()

    try:
        start, start_exact = network.resolve_station(start_input)
    except StationNotFoundError:
        raise QueryError(f"Starting station '{start_input}' does not exist, please check the station name")
    try:
        end, end_exact = network.resolve_station(end_input)
    except StationNotFoundError:
        raise QueryError(f"Ending station '{end_input}' does not exist, please check the station name")

    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        source = network.number_of(start)
        target = network.number_of(end)
        sp = ShortestPath(network.graph, source, config)
        if not sp.has_path_to(target):
            raise QueryError(f"No route found from '{start}' to '{end}' under the current settings")
        numbers, edges = sp.path_with_edges(target)
    except QueryError:
        raise
    except Exception as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    stations = [network.name_of(n) for n in numbers]
    distance = sum(e.weight for e in edges)
    transfers = _find_transfers(stations, edges)

    try:
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, len(transfers))
    except Exception as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    return RouteResult(
        start_input=str(start_input),
        end_input=str(end_input),
        start=start,
        end=end,
        start_exact=start_exact,
        end_exact=end_exact,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=list(config.preferred_lines),
        stations=stations,
        edges=edges,
        distance_m=distance,
        fare=fare,
        estimated_time_min=estimated,
        transfers=transfers,
        lines=lines,
    )
