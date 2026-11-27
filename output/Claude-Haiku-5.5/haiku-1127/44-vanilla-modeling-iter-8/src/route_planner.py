"""Route planning: combines the network, Dijkstra path search and fare calculation."""

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, PathNotFoundError, ShortestPath


class FareCalculationError(Exception):
    """Raised when the fare of a route cannot be calculated."""


class TransferInfo:
    """A transfer point on a route.

    Attributes:
        station: Name of the interchange station.
        from_line: Line the passenger arrives on.
        to_line: Line the passenger departs on.
    """

    def __init__(self, station, from_line, to_line):
        self.station = station
        self.from_line = from_line
        self.to_line = to_line


class Route:
    """The result of a route query.

    Attributes:
        start, end: Official station names.
        mode: Query mode used.
        max_transfers: Transfer limit used (None = unlimited).
        line_preference: List of preferred lines used.
        station_names: Ordered list of station names on the route.
        edges: Ordered list of Edge objects on the route.
        segments: List of (line name, list of station names) segments.
        transfers: List of TransferInfo.
        lines: Unique line names involved, in travel order.
        total_distance_m: Total distance in meters.
        transfer_count: Number of transfers.
        fare_yuan: Fare in yuan.
        estimated_time_min: Estimated travel time in minutes.
        composite_score: Composite score (distance in km + transfer penalty).
    """

    def __init__(self, start, end, mode, max_transfers, line_preference, station_names, edges,
                 segments, transfers, lines, total_distance_m, transfer_count, fare_yuan,
                 estimated_time_min, composite_score):
        self.start = start
        self.end = end
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = list(line_preference)
        self.station_names = station_names
        self.edges = edges
        self.segments = segments
        self.transfers = transfers
        self.lines = lines
        self.total_distance_m = total_distance_m
        self.transfer_count = transfer_count
        self.fare_yuan = fare_yuan
        self.estimated_time_min = estimated_time_min
        self.composite_score = composite_score

    @property
    def total_distance_km(self):
        return self.total_distance_m / 1000.0

    def summary(self):
        """Return the key figures of the route as a dictionary."""
        return {
            "totalDistanceKm": round(self.total_distance_km, 3),
            "totalFareYuan": self.fare_yuan,
            "transferCount": self.transfer_count,
            "estimatedTimeMinutes": round(self.estimated_time_min, 1),
        }


def _build_segments(names, edges):
    """Group consecutive stations travelled on the same line into segments."""
    segments = []
    if not edges:
        return segments
    current_line = edges[0].line
    current = [names[0]]
    for i, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append((current_line, current))
            current_line = edge.line
            current = [names[i]]
        current.append(names[i + 1])
    segments.append((current_line, current))
    return segments


def plan_route(network, start_name, end_name, config=None):
    """Compute the best route between two official station names.

    Args:
        network: A ``SubwayNetwork``.
        start_name: Official name of the starting station.
        end_name: Official name of the ending station.
        config: ``PathfindingConfig`` (defaults to shortest distance, no limits).

    Returns:
        Route: the computed route with fare and time estimates.

    Raises:
        ValueError: If start and end are the same station.
        UnknownStationError: If a station does not exist.
        PathNotFoundError: If no route satisfies the constraints.
        FareCalculationError: If the fare cannot be computed.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise ValueError("Starting station cannot be the same as the ending station")

    source = network.get_number(start_name)
    target = network.get_number(end_name)
    search = ShortestPath(network.graph, source, config)
    if not search.has_path_to(target):
        raise PathNotFoundError(
            "No route found from '%s' to '%s' under the given constraints" % (start_name, end_name)
        )

    nodes, edges = search.path_with_edges(target)
    names = [network.get_name(n) for n in nodes]
    total_distance = float(sum(edge.weight for edge in edges))

    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append(TransferInfo(names[i], edges[i - 1].line, edges[i].line))
    transfer_count = len(transfers)

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    try:
        fare = Sum_money(total_distance)
    except ValueError as exc:
        raise FareCalculationError(str(exc)) from exc

    estimated_time = calculate_estimated_time(total_distance, transfer_count)
    composite = total_distance / 1000.0 + transfer_count * config.transfer_penalty_m / 1000.0

    return Route(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=config.preferred_lines,
        station_names=names,
        edges=edges,
        segments=_build_segments(names, edges),
        transfers=transfers,
        lines=lines,
        total_distance_m=total_distance,
        transfer_count=transfer_count,
        fare_yuan=fare,
        estimated_time_min=estimated_time,
        composite_score=composite,
    )
