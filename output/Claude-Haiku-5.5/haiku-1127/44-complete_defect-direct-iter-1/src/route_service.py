"""Route query service: ties network, path search, fare and time together.

The service validates station names, runs the shortest path search, and
builds a JSON-serializable result dictionary used by the report and CLI layers.
"""

from fare_calculator import Sum_money, calculate_estimated_time
from network import StationNotFoundError
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class RouteQueryError(Exception):
    """Base class for all query errors."""


class InvalidQueryError(RouteQueryError):
    """Raised when the query input is malformed or logically invalid."""


class EndpointNotFoundError(RouteQueryError):
    """Raised when the starting or ending station does not exist."""

    def __init__(self, side, name, suggestions=None):
        self.side = side
        self.name = name
        self.suggestions = list(suggestions or [])
        super().__init__(f"{side} station '{name}' does not exist, please check the station name")


class PathNotFoundError(RouteQueryError):
    """Raised when no route satisfies the query constraints."""


class FareCalculationError(RouteQueryError):
    """Raised when the fare cannot be calculated."""


def parse_query_input(text):
    """Split 'Starting Station; Ending Station' input into two names.

    Full-width semicolons are accepted as well.

    Returns:
        (start_name, end_name)

    Raises:
        InvalidQueryError: If the format is incorrect.
    """
    if not isinstance(text, str):
        raise InvalidQueryError(FORMAT_MESSAGE)
    normalized = text.replace("\uff1b", ";")
    if normalized.count(";") != 1:
        raise InvalidQueryError(FORMAT_MESSAGE)
    start, end = (part.strip() for part in normalized.split(";"))
    if not start or not end:
        raise InvalidQueryError(FORMAT_MESSAGE)
    return start, end


class RouteService:
    """Executes route queries against a SubwayNetwork."""

    def __init__(self, network):
        self.network = network

    def _resolve(self, name, side):
        """Resolve a station name or raise EndpointNotFoundError."""
        try:
            return self.network.resolve_station(name)
        except StationNotFoundError as exc:
            raise EndpointNotFoundError(side, exc.name, exc.suggestions) from exc

    def query(self, start_name, end_name, config=None):
        """Compute the route between two stations.

        Args:
            start_name: Starting station name (user input).
            end_name: Ending station name (user input).
            config: PathfindingConfig; defaults to shortest-distance mode.

        Returns:
            dict with keys: query, path, segments, transfers, transfer_count,
            lines, distance_m, distance_km, fare, estimated_time_min.

        Raises:
            EndpointNotFoundError, InvalidQueryError, PathNotFoundError,
            FareCalculationError, RouteQueryError.
        """
        config = config if config is not None else PathfindingConfig()

        start = self._resolve(start_name, "Starting")
        end = self._resolve(end_name, "Ending")
        if start == end:
            raise InvalidQueryError("Starting station cannot be the same as the ending station")

        try:
            source_number = self.network.station_number(start)
            target_number = self.network.station_number(end)
            finder = ShortestPath(self.network.graph, source_number, config)
        except Exception as exc:  # defensive: unexpected path calculation failure
            raise RouteQueryError(f"Path calculation failed: {exc}") from exc

        if not finder.has_path_to(target_number):
            if config.max_transfers is not None:
                raise PathNotFoundError(
                    f"No route found from '{start}' to '{end}' within {config.max_transfers} transfer(s)"
                )
            raise PathNotFoundError(f"No route found from '{start}' to '{end}'")

        try:
            numbers, edges = finder.path_with_edges(target_number)
            transfers = finder.get_transfer_count(target_number)
        except Exception as exc:
            raise RouteQueryError(f"Path calculation failed: {exc}") from exc

        names = [self.network.station_name(n) for n in numbers]
        distance_m = sum(edge.distance for edge in edges)

        try:
            fare = Sum_money(distance_m)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

        try:
            estimated = calculate_estimated_time(distance_m, transfers)
        except (TypeError, ValueError) as exc:
            raise RouteQueryError(f"Time estimation failed: {exc}") from exc

        segments, transfer_details = self._build_segments(names, edges)
        lines = []
        for segment in segments:
            if segment["line"] not in lines:
                lines.append(segment["line"])

        return {
            "query": {
                "start": start,
                "end": end,
                "mode": config.mode,
                "max_transfers": config.max_transfers,
                "preferred_lines": list(config.preferred_lines),
            },
            "path": names,
            "segments": segments,
            "transfers": transfer_details,
            "transfer_count": transfers,
            "lines": lines,
            "distance_m": distance_m,
            "distance_km": round(distance_m / 1000.0, 2),
            "fare": fare,
            "estimated_time_min": estimated,
        }

    @staticmethod
    def _build_segments(names, edges):
        """Group consecutive edges on the same line into segments and list transfers.

        Returns:
            (segments, transfer_details)
        """
        segments = []
        transfer_details = []
        for index, edge in enumerate(edges):
            if not segments or segments[-1]["line"] != edge.line:
                if segments:
                    transfer_details.append({
                        "station": names[index],
                        "from_line": segments[-1]["line"],
                        "to_line": edge.line,
                    })
                segments.append({
                    "line": edge.line,
                    "stations": [names[index]],
                    "distance_m": 0,
                })
            segment = segments[-1]
            segment["stations"].append(names[index + 1])
            segment["distance_m"] += edge.distance
        return segments, transfer_details
