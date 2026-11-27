"""
Route service: ties together data lookup, path computation, fare and time.

``find_route`` validates a query, runs the configured Dijkstra search and
assembles a ``RouteResult`` describing the path (the "Path" of the domain model).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RoutingError(Exception):
    """Raised when a query cannot be answered (bad input, no path, calculation failure)."""


@dataclass
class RouteResult:
    """
    The result of a path query.

    Attributes:
        start: Official starting station name.
        end: Official ending station name.
        mode: Query mode used.
        max_transfers: Transfer limit used (None = unlimited).
        line_preference: Canonical preferred line name or None.
        stations: Station names from start to end.
        lines: Ordered unique list of subway lines involved.
        segments: List of dicts {"line": str, "stations": [str, ...]}.
        transfers: List of dicts {"station", "from_line", "to_line"}.
        total_distance_m: Total distance in meters.
        transfer_count: Number of transfers.
        fare: Fare in yuan.
        estimated_time_min: Estimated travel time in minutes.
    """
    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]
    stations: List[str] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    segments: List[dict] = field(default_factory=list)
    transfers: List[dict] = field(default_factory=list)
    total_distance_m: float = 0.0
    transfer_count: int = 0
    fare: int = 0
    estimated_time_min: float = 0.0

    @property
    def total_distance_km(self):
        """Total distance in kilometers."""
        return self.total_distance_m / 1000.0


def find_route(data_manager, start, end, mode="comprehensive",
               max_transfers=None, line_preference=None):
    """
    Compute the best route between two stations.

    Args:
        data_manager: Loaded DataManager.
        start: Starting station name (lenient matching).
        end: Ending station name (lenient matching).
        mode: One of shortest_distance, least_transfer, comprehensive.
        max_transfers: Optional maximum number of transfers.
        line_preference: Optional preferred line name.

    Returns:
        RouteResult

    Raises:
        RoutingError: On invalid input, unknown stations, no route, or calculation errors.
    """
    start_std = data_manager.standard_name(start)
    if start_std is None:
        raise RoutingError(
            f"Starting station '{start}' does not exist, please check the station name")
    end_std = data_manager.standard_name(end)
    if end_std is None:
        raise RoutingError(
            f"Ending station '{end}' does not exist, please check the station name")
    if start_std == end_std:
        raise RoutingError("Starting station cannot be the same as the ending station")

    preferred = []
    canonical_pref = None
    if line_preference:
        wanted = " ".join(line_preference.split()).lower()
        for line in data_manager.line_names():
            if " ".join(line.split()).lower() == wanted:
                canonical_pref = line
                break
        if canonical_pref is None:
            raise RoutingError(f"Unknown line preference '{line_preference}'")
        preferred = [canonical_pref]

    config = PathfindingConfig(mode=mode, max_transfers=max_transfers,
                               preferred_lines=preferred)
    try:
        config.validate()
    except ValueError as exc:
        raise RoutingError(str(exc))

    src = data_manager.get_station_number(start_std)
    dst = data_manager.get_station_number(end_std)
    try:
        sp = ShortestPath(data_manager.graph, src, config)
        if not sp.has_path_to(dst):
            if max_transfers is not None:
                raise RoutingError(
                    f"No route found from '{start_std}' to '{end_std}' "
                    f"within {max_transfers} transfer(s)")
            raise RoutingError(f"No route found from '{start_std}' to '{end_std}'")
        node_numbers, edges = sp.path_with_edges(dst)
    except RoutingError:
        raise
    except (KeyError, IndexError, ValueError) as exc:
        raise RoutingError(f"Path calculation failed: {exc}")

    stations = [data_manager.number_to_station[n] for n in node_numbers]
    distance = sum(e.weight for e in edges)

    # Line segments: consecutive stretches served by the same line.
    segments = []
    if edges:
        current_line = edges[0].line
        current = [stations[0], stations[1]]
        for i in range(1, len(edges)):
            if edges[i].line == current_line:
                current.append(stations[i + 1])
            else:
                segments.append({"line": current_line, "stations": current})
                current_line = edges[i].line
                current = [stations[i], stations[i + 1]]
        segments.append({"line": current_line, "stations": current})

    # Transfer stations and the lines involved.
    transfers = []
    lines = []
    for i, edge in enumerate(edges):
        if edge.line not in lines:
            lines.append(edge.line)
        if i > 0 and edges[i - 1].line != edge.line:
            transfers.append({
                "station": stations[i],
                "from_line": edges[i - 1].line,
                "to_line": edge.line,
            })

    try:
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, len(transfers))
    except ValueError as exc:
        raise RoutingError(f"Fare calculation failed: {exc}")

    return RouteResult(
        start=start_std,
        end=end_std,
        mode=mode,
        max_transfers=max_transfers,
        line_preference=canonical_pref,
        stations=stations,
        lines=lines,
        segments=segments,
        transfers=transfers,
        total_distance_m=distance,
        transfer_count=len(transfers),
        fare=fare,
        estimated_time_min=estimated,
    )
