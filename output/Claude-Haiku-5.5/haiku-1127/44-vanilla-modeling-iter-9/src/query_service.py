"""Route query service: validates user input, runs the path search, and
assembles a Route with segments, transfers, distance, fare, and time."""

from fare_calculator import Sum_money, calculate_estimated_time
from models import Route, Transfer
from pathfinding import MODES, PathfindingConfig, ShortestPath

INPUT_FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Raised for any user-facing query error (input, station, path, or fare)."""


def _build_segments_and_transfers(names, edges):
    """Group the path into line segments and list transfer events.

    Args:
        names: station names along the path (length = len(edges) + 1).
        edges: Edge objects along the path.

    Returns:
        (segments, transfers) where segments is a list of
        {"line": str, "stations": [str]} and transfers is a list of Transfer.
    """
    segments = []
    transfers = []
    if not edges:
        return segments, transfers

    segment_line = edges[0].line
    segment_stations = [names[0]]
    for index, edge in enumerate(edges):
        if edge.line != segment_line:
            segments.append({"line": segment_line, "stations": segment_stations})
            transfers.append(Transfer(names[index], segment_line, edge.line))
            segment_line = edge.line
            segment_stations = [names[index]]
        segment_stations.append(names[index + 1])
    segments.append({"line": segment_line, "stations": segment_stations})
    return segments, transfers


class RouteQueryService:
    """Coordinates station validation, path calculation, and fare calculation."""

    def __init__(self, data_manager):
        self.data_manager = data_manager

    @staticmethod
    def parse_query_text(text):
        """Split 'Starting Station; Ending Station' into two stripped names.

        Raises:
            QueryError: if the text does not contain exactly two non-empty parts.
        """
        parts = text.split(";")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise QueryError(INPUT_FORMAT_ERROR)
        return parts[0].strip(), parts[1].strip()

    def resolve_station(self, text, role):
        """Return the official station name for user input.

        Args:
            text: station name typed by the user.
            role: "Starting" or "Ending", used in error messages.

        Raises:
            QueryError: if the station does not exist.
        """
        canonical = self.data_manager.standardize_station_name(text)
        if canonical is None:
            raise QueryError(f"{role} station '{text}' does not exist, please check the station name")
        return canonical

    def query(self, start_text, end_text, mode="shortest_distance",
              max_transfers=None, line_preference=None):
        """Compute the route between two stations.

        Returns:
            A Route object.

        Raises:
            QueryError: on any validation, path, or fare calculation failure.
        """
        start = self.resolve_station(start_text, "Starting")
        end = self.resolve_station(end_text, "Ending")
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")
        if mode not in MODES:
            raise QueryError(f"Unsupported mode '{mode}'")
        if max_transfers is not None and max_transfers < 0:
            raise QueryError("Maximum transfer limit must be a non-negative integer")

        preferred = [line_preference] if line_preference else []
        try:
            config = PathfindingConfig(mode, max_transfers, preferred)
        except ValueError as exc:
            raise QueryError(str(exc)) from exc

        data = self.data_manager
        source = data.get_number(start)
        target = data.get_number(end)
        try:
            shortest = ShortestPath(data.graph, source, config)
        except Exception as exc:  # defensive: any search failure becomes a query error
            raise QueryError(f"Path calculation failed: {exc}") from exc

        if not shortest.has_path(target):
            raise QueryError(f"No route found from '{start}' to '{end}' under the given constraints")

        node_path, edges = shortest.path_with_edges(target)
        names = [data.number_to_station[node] for node in node_path]
        segments, transfers = _build_segments_and_transfers(names, edges)
        total_distance = shortest.dist_to[target]

        try:
            fare = Sum_money(total_distance)
            minutes = calculate_estimated_time(total_distance, len(transfers))
        except ValueError as exc:
            raise QueryError(f"Fare calculation failed: {exc}") from exc

        return Route(
            start_name=start,
            end_name=end,
            mode=mode,
            max_transfers=max_transfers,
            line_preference=line_preference,
            stations=names,
            segments=segments,
            transfers=transfers,
            total_distance_m=total_distance,
            fare=fare,
            estimated_time_minutes=minutes,
        )
