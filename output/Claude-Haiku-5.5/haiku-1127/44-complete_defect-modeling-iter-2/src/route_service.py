"""
Query service: validates user input, runs the path search, and assembles
a ``RouteResult`` containing the path, distance, fare, transfers and time.
"""

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a query cannot be answered (bad station, no path, calculation failure)."""


@dataclass
class RouteResult:
    """Outcome of a successful route query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: object
    preferred_lines: list
    station_names: list
    edges: list
    total_distance_m: float
    fare_yuan: int
    transfer_count: int
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    estimated_time_minutes: float = 0.0

    @property
    def total_distance_km(self):
        """Total distance converted from meters to kilometers."""
        return self.total_distance_m / 1000.0


def parse_query(text):
    """
    Parse a query of the form ``Starting Station; Ending Station``.

    Full-width semicolons are accepted as separators too.

    Returns:
        (str, str): The stripped starting and ending station names.

    Raises:
        ValueError: If the format is wrong or a name is empty.
    """
    normalized = text.replace("\uff1b", ";")
    parts = normalized.split(";")
    if len(parts) != 2:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    start = " ".join(parts[0].split())
    end = " ".join(parts[1].split())
    if not start or not end:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return start, end


def resolve_station(graph, name, role):
    """
    Standardise a station name against the official names in the graph.

    Matching is whitespace-normalised and case-insensitive.

    Args:
        graph: The subway ``Graph``.
        name: The user-supplied name.
        role: "Starting" or "Ending" (used in error messages).

    Returns:
        str: The official station name.

    Raises:
        RouteError: If no unique matching station exists.
    """
    cleaned = " ".join(name.split())
    if not cleaned:
        raise RouteError(f"{role} station name cannot be empty")
    if graph.has_station(cleaned):
        return cleaned

    lowered = cleaned.casefold()
    matches = [station for station in graph.station_names() if station.casefold() == lowered]
    if len(matches) == 1:
        return matches[0]

    raise RouteError(f"{role} station '{cleaned}' does not exist, please check the station name")


def find_transfers(station_names, edges):
    """
    Identify transfer stations along a path.

    Returns:
        list[dict]: Each item has ``station``, ``from_line`` and ``to_line``.
    """
    transfers = []
    for index in range(len(edges) - 1):
        if edges[index].line != edges[index + 1].line:
            transfers.append({
                "station": station_names[index + 1],
                "from_line": edges[index].line,
                "to_line": edges[index + 1].line,
            })
    return transfers


def unique_lines(edges):
    """Return the lines used by the path, in order of first use."""
    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def query_route(graph, start_name, end_name, config=None):
    """
    Compute the best route and its fare between two stations.

    Args:
        graph: The subway ``Graph``.
        start_name: Official starting station name.
        end_name: Official ending station name.
        config: Optional ``PathfindingConfig``.

    Returns:
        RouteResult

    Raises:
        RouteError: On invalid stations, identical endpoints, no route, or
                    calculation failures.
    """
    config = config if config is not None else PathfindingConfig()

    if not graph.has_station(start_name):
        raise RouteError(f"Starting station '{start_name}' does not exist, please check the station name")
    if not graph.has_station(end_name):
        raise RouteError(f"Ending station '{end_name}' does not exist, please check the station name")
    if start_name == end_name:
        raise RouteError("Starting station cannot be the same as the ending station")

    try:
        search = ShortestPath(graph, graph.get_number(start_name), config)
    except ValueError as exc:
        raise RouteError(f"Path calculation failed: {exc}") from exc

    target = graph.get_number(end_name)
    if not search.has_path_to(target):
        raise RouteError(
            f"No route found from '{start_name}' to '{end_name}' "
            f"under the current settings (mode={config.mode}, "
            f"max_transfers={config.max_transfers}, line_preference={config.preferred_lines or 'none'})"
        )

    try:
        numbers, edges = search.path_with_edges(target)
        station_names = [graph.get_name(number) for number in numbers]
        total_distance = float(sum(edge.weight for edge in edges))
        transfer_count = search.get_transfer_count(target)
        transfers = find_transfers(station_names, edges)
        lines = unique_lines(edges)
    except (KeyError, ValueError) as exc:
        raise RouteError(f"Path calculation failed: {exc}") from exc

    try:
        fare = Sum_money(total_distance)
        estimated_time = calculate_estimated_time(total_distance, transfer_count)
    except (TypeError, ValueError) as exc:
        raise RouteError(f"Fare calculation failed: {exc}") from exc

    return RouteResult(
        start_station=start_name,
        end_station=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        station_names=station_names,
        edges=edges,
        total_distance_m=total_distance,
        fare_yuan=fare,
        transfer_count=transfer_count,
        transfers=transfers,
        lines=lines,
        estimated_time_minutes=estimated_time,
    )
