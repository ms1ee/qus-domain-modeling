"""Query service: parses user input, resolves stations, runs path and fare calculation."""

from dataclasses import dataclass, field

from data_manager import clean_name, resolve_station_name
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import ShortestPath
from subway_errors import (
    FareCalculationError,
    InputFormatError,
    RouteNotFoundError,
    SameStationError,
    StationNotFoundError,
)

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
# Accepted separators: semicolon (primary) and comma (full-width and ASCII variants).
_SEPARATORS = (";", "；", ",", "，")


@dataclass
class Transfer:
    """A transfer station on a route and all lines serving it."""
    station_name: str
    involved_lines: list


@dataclass
class Segment:
    """A contiguous run of stations travelled on a single line."""
    line: str
    start_station: str
    end_station: str
    stations: list
    distance_m: int


@dataclass
class RouteResult:
    """Complete result of a path query."""
    start: str
    end: str
    mode: str
    max_transfers: object
    line_preference: object
    station_sequence: list           # from start to end
    total_distance_m: int
    fare_yuan: int
    transfer_count: int
    estimated_time_min: float
    transfers: list = field(default_factory=list)
    involved_lines: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    notices: list = field(default_factory=list)


def parse_query(text):
    """Parse a 'Starting Station; Ending Station' query string.

    Returns:
        tuple: (start_name_input, end_name_input) with whitespace normalised.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    if text is None:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    normalized = str(text).strip()
    for sep in _SEPARATORS[1:]:
        normalized = normalized.replace(sep, _SEPARATORS[0])
    parts = normalized.split(_SEPARATORS[0])
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return clean_name(parts[0]), clean_name(parts[1])


def _resolve(query, label, names, notices):
    """Resolve one station query, recording a notice when a fuzzy match is used."""
    try:
        name, exact = resolve_station_name(query, names)
    except StationNotFoundError as exc:
        raise StationNotFoundError(
            f"{label} station '{query}' does not exist, please check the station name") from exc
    if not exact:
        notices.append(f"{label} station '{query}' is not an official name; matched to '{name}'")
    return name


def run_query(network, start_input, end_input, config):
    """Run a complete route query.

    Args:
        network: data_manager.SubwayNetwork instance.
        start_input: User-entered starting station name.
        end_input: User-entered ending station name.
        config: pathfinding.PathfindingConfig.

    Returns:
        RouteResult: Path, distance, fare, transfers, time estimate and segments.

    Raises:
        StationNotFoundError, SameStationError, RouteNotFoundError, FareCalculationError.
    """
    notices = []
    names = network.station_names()
    start = _resolve(start_input, "Starting", names, notices)
    end = _resolve(end_input, "Ending", names, notices)
    if start == end:
        raise SameStationError("Starting station cannot be the same as the ending station")

    graph = network.graph
    src = graph.number_of(start)
    dst = graph.number_of(end)
    sp = ShortestPath(graph, src, config)
    node_numbers, edges = sp.path_with_edges(dst)
    if not node_numbers or not edges:
        hint = " (the transfer limit may be too strict)" if config.max_transfers is not None else ""
        raise RouteNotFoundError(f"No route found from '{start}' to '{end}'{hint}")

    station_sequence = [graph.name_of(n) for n in node_numbers]
    total_distance = sum(e.distance for e in edges)
    total_distance_m = int(round(total_distance))
    transfer_count = sp.get_transfer_count(dst)

    try:
        fare = Sum_money(total_distance_m)
    except FareCalculationError:
        raise
    estimated_time = calculate_estimated_time(total_distance_m, transfer_count)

    # Group consecutive edges operated by the same line into segments.
    groups = []
    group_start = 0
    for i in range(1, len(edges) + 1):
        if i == len(edges) or edges[i].line != edges[group_start].line:
            groups.append((group_start, i))
            group_start = i

    segments = []
    for a, b in groups:
        seg_distance = int(round(sum(e.distance for e in edges[a:b])))
        segments.append(Segment(
            line=edges[a].line,
            start_station=station_sequence[a],
            end_station=station_sequence[b],
            stations=station_sequence[a:b + 1],
            distance_m=seg_distance,
        ))

    # Transfer stations: boundaries between consecutive segments.
    transfers = []
    for idx in range(1, len(groups)):
        boundary = groups[idx][0]
        station_name = station_sequence[boundary]
        lines = []
        for line in [edges[groups[idx - 1][0]].line, edges[groups[idx][0]].line] + graph.lines_of(station_name):
            if line not in lines:
                lines.append(line)
        transfers.append(Transfer(station_name=station_name, involved_lines=lines))

    involved_lines = []
    for e in edges:
        if e.line not in involved_lines:
            involved_lines.append(e.line)

    return RouteResult(
        start=start,
        end=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=", ".join(config.preferred_lines) if config.preferred_lines else None,
        station_sequence=station_sequence,
        total_distance_m=total_distance_m,
        fare_yuan=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated_time,
        transfers=transfers,
        involved_lines=involved_lines,
        segments=segments,
        notices=notices,
    )
