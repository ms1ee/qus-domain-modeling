"""Query handling: input parsing, station name standardisation and route computation."""

from fare_calculator import FareError
from pathfinding import NoPathError, PathfindingConfig, ShortestPath
from visualizer import build_summary

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for user-facing query errors."""


class InputFormatError(QueryError):
    """The query text does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class LogicError(QueryError):
    """The query is logically invalid (e.g. identical start and end stations)."""


class CalculationError(QueryError):
    """Path or fare calculation failed."""


def parse_query(text):
    """Split a query of the form 'Starting Station; Ending Station'.

    Returns:
        tuple: (starting name, ending name) as raw strings.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    normalized = (text or "").replace("\uff1b", ";").strip()
    parts = normalized.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def resolve_station(network, raw_name, role):
    """Map user input to an official station name.

    Accepts exact names, names with or without the trailing "站" and
    case-insensitive matches.

    Args:
        network: SubwayNetwork.
        raw_name: User-provided name.
        role: "Starting" or "Ending" (used in the error message).

    Returns:
        str: The official station name.

    Raises:
        StationNotFoundError: If no station matches.
    """
    name = raw_name.strip()
    mapping = network.station_to_number
    candidates = [name]
    if name.endswith("站") and len(name) > 1:
        candidates.append(name[:-1])
    else:
        candidates.append(name + "站")
    for candidate in candidates:
        if candidate in mapping:
            return candidate
    lowered = {official.lower(): official for official in mapping}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    raise StationNotFoundError(f"{role} station '{raw_name}' does not exist, please check the station name")


def parse_line_preference(text, known_lines):
    """Parse a comma-separated list of preferred lines.

    Args:
        text: Raw argument text such as "Line 1" or "Line 1,Line 2"; may be None.
        known_lines: All line names in the network.

    Returns:
        list[str]: Canonical line names (empty list when text is empty).

    Raises:
        QueryError: If a line name is unknown.
    """
    if not text or not text.strip():
        return []
    result = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        match = None
        for line in known_lines:
            if line.lower() == item.lower():
                match = line
                break
        if match is None:
            raise QueryError(f"unknown line '{item}' in line preference")
        if match not in result:
            result.append(match)
    return result


def run_query(network, start_name, end_name, mode, max_transfers=None, preferred_lines=None):
    """Compute the route between two official station names.

    Args:
        network: SubwayNetwork.
        start_name: Official starting station name.
        end_name: Official ending station name.
        mode: Query mode (see pathfinding.VALID_MODES).
        max_transfers: Optional transfer limit.
        preferred_lines: Optional list of preferred line names.

    Returns:
        PathSummary: The route summary.

    Raises:
        LogicError: If start and end are the same station.
        CalculationError: If no route is found or calculation fails.
    """
    if start_name == end_name:
        raise LogicError("Starting station cannot be the same as the ending station")
    try:
        config = PathfindingConfig(mode=mode, max_transfers=max_transfers, preferred_lines=preferred_lines)
    except ValueError as exc:
        raise CalculationError(str(exc)) from exc

    source = network.number_of(start_name)
    target = network.number_of(end_name)
    try:
        search = ShortestPath(network.graph, source, config)
        if not search.has_path_to(target):
            raise NoPathError("no route")
        numbers, edges = search.path_with_edges(target)
        transfers = search.get_transfer_count(target)
    except NoPathError as exc:
        raise CalculationError(
            f"no route found from '{start_name}' to '{end_name}' under the given constraints"
        ) from exc
    except (ValueError, KeyError) as exc:
        raise CalculationError(f"path calculation failed: {exc}") from exc

    try:
        return build_summary(
            network, start_name, end_name, numbers, edges, transfers,
            mode, max_transfers, preferred_lines,
        )
    except (FareError, ValueError, KeyError) as exc:
        raise CalculationError(f"fare calculation failed: {exc}") from exc
