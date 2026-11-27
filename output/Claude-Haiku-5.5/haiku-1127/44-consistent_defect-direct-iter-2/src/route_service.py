"""Route planning service.

Combines station resolution, path search, fare calculation and segment
analysis into a single RouteResult that the report module can render.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a route query cannot be answered (bad input, no route, calculation failure)."""


@dataclass
class RouteResult:
    """Result of a single route query.

    Attributes:
        start / end: official station names.
        start_query / end_query: station names as typed by the user.
        start_exact / end_exact: True if the input matched an official name exactly.
        stations: station names from the start to the end (travel order).
        edge_lines: line name of every traversed edge.
        distance_m: total travelled distance in meters.
        fare: fare in yuan.
        transfer_count: number of transfers.
        estimated_minutes: estimated travel time in minutes.
        segments: list of dicts {"line", "from", "to", "stations"} in travel order.
        transfers: list of dicts {"station", "from_line", "to_line", "station_lines"}.
        involved_lines: unique line names in order of first use.
    """

    start: str
    end: str
    start_query: str
    end_query: str
    start_exact: bool
    end_exact: bool
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]
    edge_lines: List[str]
    distance_m: float
    fare: int
    transfer_count: int
    estimated_minutes: float
    segments: List[dict] = field(default_factory=list)
    transfers: List[dict] = field(default_factory=list)
    involved_lines: List[str] = field(default_factory=list)


def _build_segments(stations, edge_lines):
    """Group consecutive edges of the same line into segments."""
    segments = []
    for index, line in enumerate(edge_lines):
        start_station = stations[index]
        end_station = stations[index + 1]
        if not segments or segments[-1]["line"] != line:
            segments.append({
                "line": line,
                "from": start_station,
                "to": end_station,
                "stations": [start_station, end_station],
            })
        else:
            segments[-1]["to"] = end_station
            segments[-1]["stations"].append(end_station)
    return segments


def _build_transfers(network, stations, edge_lines):
    """Identify the stations where the traveller changes line."""
    transfers = []
    for index in range(1, len(edge_lines)):
        if edge_lines[index - 1] != edge_lines[index]:
            station = stations[index]
            transfers.append({
                "station": station,
                "from_line": edge_lines[index - 1],
                "to_line": edge_lines[index],
                "station_lines": network.station_lines(station),
            })
    return transfers


def plan_route(network, start_query, end_query, config=None):
    """Plan the route between two stations and compute its fare.

    Args:
        network: subway_network.SubwayNetwork instance.
        start_query: starting station name as entered by the user.
        end_query: ending station name as entered by the user.
        config: pathfinding.PathfindingConfig (defaults to shortest distance).

    Returns:
        RouteResult describing the route.

    Raises:
        RouteError: on invalid input, unreachable destinations or calculation errors.
    """
    if config is None:
        config = PathfindingConfig()

    try:
        start_num, start_name, start_exact = network.resolve_station(start_query)
        end_num, end_name, end_exact = network.resolve_station(end_query)
    except ValueError as exc:
        raise RouteError(str(exc)) from exc

    if start_num == end_num:
        raise RouteError("Starting station cannot be the same as the ending station")

    try:
        search = ShortestPath(network.graph, start_num, config)
    except ValueError as exc:
        raise RouteError(f"path calculation failed: {exc}") from exc

    if not search.has_path_to(end_num):
        if config.max_transfers is not None:
            raise RouteError(
                f"no route from '{start_name}' to '{end_name}' within "
                f"{config.max_transfers} transfer(s)"
            )
        raise RouteError(f"no route from '{start_name}' to '{end_name}'")

    try:
        node_numbers, edges = search.path_with_edges(end_num)
        stations = [network.number_to_name[number] for number in node_numbers]
        edge_lines = [edge.line for edge in edges]
        distance = search.dist_to[end_num]
        transfer_count = search.get_transfer_count(end_num)
    except (KeyError, IndexError) as exc:
        raise RouteError(f"path calculation failed: {exc}") from exc

    try:
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, transfer_count)
    except (TypeError, ValueError) as exc:
        raise RouteError(f"fare calculation failed: {exc}") from exc

    involved = []
    for line in edge_lines:
        if line not in involved:
            involved.append(line)

    return RouteResult(
        start=start_name,
        end=end_name,
        start_query=str(start_query).strip(),
        end_query=str(end_query).strip(),
        start_exact=start_exact,
        end_exact=end_exact,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=stations,
        edge_lines=edge_lines,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_minutes=estimated,
        segments=_build_segments(stations, edge_lines),
        transfers=_build_transfers(network, stations, edge_lines),
        involved_lines=involved,
    )
