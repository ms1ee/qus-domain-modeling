"""Query service: runs a passenger query from start to finish.

Resolves station names, runs the pathfinding algorithm, builds the route
(segments, transfers, distance), computes the fare, and extracts the summary.
"""

from .fare_calculator import Sum_money, calculate_estimated_time
from .models import (
    FareCalculationError,
    NoRouteError,
    PathCalculationError,
    PathSummary,
    Query,
    QueryResult,
    Route,
    RouteSegment,
    SubwayError,
    Transfer,
)
from .pathfinding import MODES, PathfindingConfig, ShortestPath


class QueryService:
    """Executes path queries against a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def _require_station(self, name):
        """Return the official name of a station or raise StationNotFoundError."""
        resolved = self.network.resolve_station(name)
        if resolved is None:
            from .models import StationNotFoundError
            raise StationNotFoundError(f"Station '{name}' does not exist, please check the station name")
        return resolved[0]

    def run(self, origin, destination, mode="shortest_distance",
            max_transfers=None, line_preference=None):
        """Execute a query.

        Args:
            origin: Starting station name.
            destination: Ending station name.
            mode: One of ``MODES``.
            max_transfers: Optional maximum number of transfers.
            line_preference: Optional preferred line name.

        Returns:
            QueryResult: Query, route, and summary.

        Raises:
            SubwayError: On invalid input, no route, or calculation failure.
        """
        if mode not in MODES:
            raise SubwayError(f"Unknown mode '{mode}'")
        origin_name = self._require_station(origin)
        dest_name = self._require_station(destination)
        if origin_name == dest_name:
            raise SubwayError("Starting station cannot be the same as the ending station")

        query = Query(origin_name, dest_name, mode, max_transfers, line_preference)
        preferred = [line_preference] if line_preference else []

        try:
            config = PathfindingConfig(mode, max_transfers, preferred)
            source = self.network.number_of(origin_name)
            target = self.network.number_of(dest_name)
            shortest = ShortestPath(self.network.graph, source, config)
            if not shortest.has_path(target):
                if max_transfers is not None:
                    raise NoRouteError(
                        f"No route from '{origin_name}' to '{dest_name}' within {max_transfers} transfer(s)"
                    )
                raise NoRouteError(f"No route from '{origin_name}' to '{dest_name}'")
            numbers, edges = shortest.path_with_edges(target)
        except SubwayError:
            raise
        except Exception as exc:
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc

        route = self._build_route(numbers, edges)

        try:
            fare = Sum_money(route.total_distance_meters)
        except Exception as exc:
            raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

        summary = PathSummary(
            total_distance_meters=route.total_distance_meters,
            total_fare_yuan=fare,
            transfer_count=route.transfer_count,
            estimated_time_minutes=calculate_estimated_time(
                route.total_distance_meters, route.transfer_count
            ),
        )
        return QueryResult(query=query, route=route, summary=summary)

    def _build_route(self, numbers, edges):
        """Build a ``Route`` (stations, line segments, transfers) from a path."""
        stations = [self.network.name_of(number) for number in numbers]
        total = sum(edge.distance for edge in edges)

        segments = []
        current = None
        for edge in edges:
            if current is None or current.line_name != edge.line:
                current = RouteSegment(line_name=edge.line, distance_meters=0.0, station_count=1)
                segments.append(current)
            current.distance_meters += edge.distance
            current.station_count += 1

        transfers = []
        for index in range(1, len(edges)):
            previous, following = edges[index - 1], edges[index]
            if previous.line != following.line:
                transfers.append(Transfer(
                    station_name=stations[index],
                    from_line=previous.line,
                    to_line=following.line,
                ))

        return Route(
            stations=stations,
            segments=segments,
            transfers=transfers,
            total_distance_meters=total,
        )


# Imported late-bound to keep the public import list above readable.
from .models import SubwayError  # noqa: E402
