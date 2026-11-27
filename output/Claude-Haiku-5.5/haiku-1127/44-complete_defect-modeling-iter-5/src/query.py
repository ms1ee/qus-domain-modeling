"""Route planning: combines the network, the path algorithm and the fare module."""

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import NoPathError, PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Base class for route planning errors."""


class NoRouteError(RouteError):
    """Raised when no route satisfies the query constraints."""


class FareCalculationError(RouteError):
    """Raised when the fare or time estimate cannot be computed."""


class Route:
    """Result of a route query.

    Attributes:
        start_station / end_station: Official station names.
        config: The ``PathfindingConfig`` used.
        stations: Ordered list of station names from start to end.
        edges: Ordered list of ``Edge`` objects traversed.
        distance_m: Total distance in meters.
        transfer_count: Number of line transfers.
        transfer_stations: Names of stations where the line changes.
        transfer_details: List of dicts with station, from_line and to_line.
        lines: Ordered list of unique line names used.
        segments: List of dicts with line and stations (one per line segment).
        fare: Fare in yuan.
        estimated_time_minutes: Estimated travel time in minutes.
    """

    def __init__(
        self,
        start_station,
        end_station,
        config,
        stations,
        edges,
        distance_m,
        transfer_count,
        transfer_details,
        lines,
        segments,
        fare,
        estimated_time_minutes,
    ):
        self.start_station = start_station
        self.end_station = end_station
        self.config = config
        self.stations = stations
        self.edges = edges
        self.distance_m = distance_m
        self.transfer_count = transfer_count
        self.transfer_details = transfer_details
        self.transfer_stations = [item["station"] for item in transfer_details]
        self.lines = lines
        self.segments = segments
        self.fare = fare
        self.estimated_time_minutes = estimated_time_minutes


def plan_route(network, start_name, end_name, config=None):
    """Compute the best route between two stations and its fare.

    Args:
        network: ``SubwayNetwork`` instance.
        start_name: Starting station name entered by the user.
        end_name: Ending station name entered by the user.
        config: Optional ``PathfindingConfig``.

    Returns:
        Route: The computed route.

    Raises:
        UnknownStationError: If a station name is not recognized.
        ValueError: If start and end are the same station.
        NoRouteError: If no route exists under the given constraints.
        FareCalculationError: If the fare cannot be computed.
    """
    config = config or PathfindingConfig()
    start = network.resolve_station_name(start_name, "Starting station")
    end = network.resolve_station_name(end_name, "Ending station")
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")

    src = network.station_number(start)
    dst = network.station_number(end)
    search = ShortestPath(network.graph, src, config)
    if not search.has_path_to(dst):
        if config.max_transfers is not None:
            raise NoRouteError(
                f"No route from '{start}' to '{end}' within {config.max_transfers} transfer(s)"
            )
        raise NoRouteError(f"No route from '{start}' to '{end}'")

    try:
        node_path, edges = search.path_with_edges(dst)
    except NoPathError as exc:
        raise NoRouteError(str(exc)) from exc

    names = [network.station_name(node) for node in node_path]
    distance = int(round(search.dist_to[dst]))
    transfer_count = search.get_transfer_count(dst)

    transfer_details = []
    for index in range(1, len(edges)):
        if edges[index - 1].line != edges[index].line:
            transfer_details.append(
                {
                    "station": names[index],
                    "from_line": edges[index - 1].line,
                    "to_line": edges[index].line,
                }
            )

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    segments = []
    if edges:
        current = {"line": edges[0].line, "stations": [names[0]]}
        for index, edge in enumerate(edges):
            current["stations"].append(names[index + 1])
            if index + 1 < len(edges) and edges[index + 1].line != edge.line:
                segments.append(current)
                current = {"line": edges[index + 1].line, "stations": [names[index + 1]]}
        segments.append(current)

    try:
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, transfer_count)
    except (ValueError, TypeError) as exc:
        raise FareCalculationError(str(exc)) from exc

    return Route(
        start_station=start,
        end_station=end,
        config=config,
        stations=names,
        edges=edges,
        distance_m=distance,
        transfer_count=transfer_count,
        transfer_details=transfer_details,
        lines=lines,
        segments=segments,
        fare=fare,
        estimated_time_minutes=estimated,
    )
