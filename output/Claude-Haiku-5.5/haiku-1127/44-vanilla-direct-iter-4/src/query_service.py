"""Route query service: validation, path search, fare and summary assembly."""

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import MODE_SHORTEST_DISTANCE, PathfindingConfig, ShortestPath

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for all query-related errors shown to the user."""


class InputFormatError(QueryError):
    """The query string does not follow the 'Start; End' format."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class LogicalValidationError(QueryError):
    """The query is logically invalid (e.g. identical start and end)."""


class PathCalculationError(QueryError):
    """No path could be computed or the search failed."""


class FareCalculationError(QueryError):
    """The fare could not be computed."""


def parse_query_input(text):
    """Split a 'Starting Station; Ending Station' string.

    Returns:
        tuple: ``(start, end)`` with surrounding whitespace removed.

    Raises:
        InputFormatError: If the separator is missing or a name is empty.
    """
    if text is None or text.count(";") != 1:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start, end


def resolve_station(network, name, role):
    """Map user input to an official station name.

    Args:
        network: ``data_manager.SubwayNetwork``.
        name: User-provided station name.
        role: ``"Starting"`` or ``"Ending"`` (used in the error message).

    Raises:
        StationNotFoundError: If the station does not exist.
    """
    canonical = network.find_station(name)
    if canonical is None:
        raise StationNotFoundError(f"{role} station '{name}' does not exist, please check the station name")
    return canonical


def query_route(network, start_name, end_name, mode=MODE_SHORTEST_DISTANCE,
                max_transfers=None, preferred_lines=None):
    """Compute the route, fare and summary between two stations.

    Returns:
        dict: Result with keys ``query``, ``path``, ``distance_m``, ``distance_km``,
        ``fare``, ``estimated_time_min``, ``transfer_count``, ``lines``,
        ``segments``, ``transfer_stations`` and ``station_count``.

    Raises:
        QueryError: Subclass describing the failure.
    """
    start = resolve_station(network, start_name, "Starting")
    end = resolve_station(network, end_name, "Ending")
    if start == end:
        raise LogicalValidationError("Starting station cannot be the same as the ending station")

    try:
        config = PathfindingConfig(mode=mode, max_transfers=max_transfers, preferred_lines=preferred_lines)
        search = ShortestPath(network.graph, network.get_number(start), config)
        target = network.get_number(end)
        nodes, edges = search.path_with_edges(target)
        transfers = search.get_transfer_count(target)
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc

    if not nodes:
        message = f"No route found from '{start}' to '{end}'"
        if max_transfers is not None:
            message += f" within {max_transfers} transfer(s)"
        raise PathCalculationError(message)

    try:
        total_distance = sum(edge.weight for edge in edges)
        fare = Sum_money(total_distance)
        estimated = calculate_estimated_time(total_distance, transfers)
    except Exception as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    path_names = [network.name_of(n) for n in nodes]
    segments = []
    for i, edge in enumerate(edges):
        from_name = path_names[i]
        to_name = path_names[i + 1]
        if segments and segments[-1]["line"] == edge.line:
            segments[-1]["to"] = to_name
            segments[-1]["distance_m"] += edge.weight
        else:
            segments.append({"line": edge.line, "from": from_name, "to": to_name,
                             "distance_m": edge.weight})

    transfer_stations = []
    for k in range(1, len(segments)):
        transfer_stations.append({
            "station": segments[k]["from"],
            "from_line": segments[k - 1]["line"],
            "to_line": segments[k]["line"],
        })

    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])

    return {
        "query": {
            "start": start,
            "end": end,
            "mode": mode,
            "max_transfers": max_transfers,
            "preferred_lines": list(preferred_lines or []),
        },
        "path": path_names,
        "station_count": len(path_names),
        "distance_m": total_distance,
        "distance_km": round(total_distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(estimated, 1),
        "transfer_count": transfers,
        "lines": lines,
        "segments": segments,
        "transfer_stations": transfer_stations,
    }
