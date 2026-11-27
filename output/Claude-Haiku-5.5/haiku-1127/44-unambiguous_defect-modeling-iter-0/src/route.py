"""
Route planning service: combines the network, path algorithm and fare module
into a ``Route`` object describing a complete trip.
"""

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath, MODE_SHORTEST_DISTANCE


class NoPathError(Exception):
    """Raised when no path satisfies the query constraints."""


class Query:
    """A passenger query: start, end, mode and constraints."""

    def __init__(self, start, end, mode=MODE_SHORTEST_DISTANCE,
                 max_transfers=None, preferred_lines=None):
        self.start = start
        self.end = end
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def to_dict(self):
        """Return the query as a JSON-friendly dictionary."""
        return {
            "start": self.start,
            "end": self.end,
            "mode": self.mode,
            "max_transfers": self.max_transfers,
            "line_preference": ", ".join(self.preferred_lines) if self.preferred_lines else None,
        }


class Route:
    """
    A computed trip with its derived summary information.

    Attributes:
        mode (str): Query mode used.
        station_names (list[str]): Ordered station names from start to end.
        edges (list[Edge]): Connections traversed.
        total_distance_meters (float): Total distance in meters.
        transfers (list[dict]): Transfer details (station, from_line, to_line).
        lines (list[str]): Lines involved, in order of first use.
        segments (list[dict]): Continuous rides on one line.
        fare (int): Fare in yuan.
        estimated_time_minutes (float): Estimated travel time.
    """

    def __init__(self, mode, station_names, edges, total_distance_meters, transfers,
                 lines, segments, fare, estimated_time_minutes):
        self.mode = mode
        self.station_names = station_names
        self.edges = edges
        self.total_distance_meters = total_distance_meters
        self.transfers = transfers
        self.lines = lines
        self.segments = segments
        self.fare = fare
        self.estimated_time_minutes = estimated_time_minutes

    @property
    def transfer_count(self):
        """Number of transfers required."""
        return len(self.transfers)

    @property
    def total_distance_km(self):
        """Total distance in kilometers."""
        return self.total_distance_meters / 1000.0

    def summary(self):
        """Return the key figures of the route."""
        return {
            "distance_meters": self.total_distance_meters,
            "distance_km": self.total_distance_km,
            "fare": self.fare,
            "transfer_count": self.transfer_count,
            "estimated_time_minutes": self.estimated_time_minutes,
        }


def build_route(station_names, edges, mode):
    """
    Build a Route from an ordered station list and the edges between them.

    Args:
        station_names: Station names from start to end (len = len(edges) + 1).
        edges: Edge objects along the path.
        mode: Query mode string.

    Returns:
        Route: The assembled route.
    """
    total = sum(edge.distance for edge in edges)

    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append({
                "station": station_names[i],
                "from_line": edges[i - 1].line,
                "to_line": edges[i].line,
            })

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    segments = []
    i = 0
    while i < len(edges):
        j = i
        while j + 1 < len(edges) and edges[j + 1].line == edges[i].line:
            j += 1
        segment_distance = sum(edges[k].distance for k in range(i, j + 1))
        segments.append({
            "line": edges[i].line,
            "from_station": station_names[i],
            "to_station": station_names[j + 1],
            "stops": j - i + 1,
            "distance_meters": segment_distance,
        })
        i = j + 1

    fare = Sum_money(total)
    estimated_time = calculate_estimated_time(total, len(transfers))

    return Route(
        mode=mode,
        station_names=list(station_names),
        edges=list(edges),
        total_distance_meters=round(total, 1),
        transfers=transfers,
        lines=lines,
        segments=segments,
        fare=fare,
        estimated_time_minutes=round(estimated_time, 1),
    )


def plan_route(network, query):
    """
    Compute the route for a query.

    Args:
        network: SubwayNetwork instance.
        query: Query describing start, end and constraints.

    Returns:
        Route: The computed route.

    Raises:
        KeyError: If a station is unknown.
        NoPathError: If no path satisfies the constraints.
        ValueError: If the configuration is invalid.
    """
    config = PathfindingConfig(query.mode, query.max_transfers, query.preferred_lines)
    source = network.number_of(query.start)
    target = network.number_of(query.end)
    shortest = ShortestPath(network.graph, source, config)
    if not shortest.has_path_to(target):
        if query.max_transfers is not None:
            raise NoPathError(
                f"No route from '{query.start}' to '{query.end}' within "
                f"{query.max_transfers} transfer(s)")
        raise NoPathError(f"No route found from '{query.start}' to '{query.end}'")
    nodes, edges = shortest.path_with_edges(target)
    names = [network.name_of(node) for node in nodes]
    return build_route(names, edges, query.mode)
