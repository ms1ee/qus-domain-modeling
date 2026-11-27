"""Query processing: input parsing, station standardization and route building.

``RouteService`` ties together the network, the shortest path search, the
fare calculator and the route model. It raises ``QueryError`` subclasses with
user-facing messages for every recoverable problem.
"""

from fare_calculator import calculate_estimated_time, calculate_fare
from models import Route, Segment, Transfer
from network import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath


class QueryError(Exception):
    """Base class for all user-facing query errors."""


class InputFormatError(QueryError):
    """The query text is not in 'Starting Station; Ending Station' format."""


class StationNotFoundError(QueryError):
    """A station name does not exist in the network."""


class LogicalQueryError(QueryError):
    """The query is logically invalid (e.g. identical start and end)."""


class PathNotFoundError(QueryError):
    """No route exists under the given constraints."""


class PathCalculationError(QueryError):
    """An unexpected error occurred during path calculation."""


class FareCalculationError(QueryError):
    """An error occurred during fare calculation."""


def normalize_station_name(name: str) -> str:
    """Return a comparison key for a station name.

    The key ignores case, whitespace and a trailing '站' / 'station' suffix.
    """
    text = "".join(name.split()).lower()
    if text.endswith("station"):
        text = text[:-len("station")]
    if text.endswith("站"):
        text = text[:-1]
    return text


class RouteService:
    """Parses queries and computes routes over a ``SubwayNetwork``."""

    def __init__(self, network: SubwayNetwork):
        self.network = network

    # ------------------------------------------------------- input handling
    def _build_index(self):
        index = {}
        for name in self.network.station_names():
            index.setdefault(normalize_station_name(name), name)
        return index

    def standardize_station(self, raw: str, role: str) -> str:
        """Map user input to an official station name.

        Args:
            raw: The station name typed by the user.
            role: "Starting" or "Ending", used in error messages.

        Raises:
            StationNotFoundError: If no matching station exists.
        """
        text = raw.strip()
        if self.network.has_station(text):
            return text
        key = normalize_station_name(text)
        if key:
            official = self._build_index().get(key)
            if official is not None:
                return official
        raise StationNotFoundError(
            f"{role} station '{text}' does not exist, please check the station name")

    def parse_query(self, text: str):
        """Parse 'Starting Station; Ending Station' into official station names.

        Raises:
            InputFormatError: If the text is not in the expected format.
            StationNotFoundError: If a station name is unknown.
            LogicalQueryError: If start and end are the same station.
        """
        parts = text.replace("\uff1b", ";").split(";")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise InputFormatError(
                "Input format incorrect, please use 'Starting Station; Ending Station' format")
        start = self.standardize_station(parts[0], "Starting")
        end = self.standardize_station(parts[1], "Ending")
        if start == end:
            raise LogicalQueryError("Starting station cannot be the same as the ending station")
        return start, end

    # ----------------------------------------------------------- computation
    def query(self, start: str, end: str, mode: str = PathfindingConfig.SHORTEST_DISTANCE,
              max_transfers=None, line_preference=None) -> Route:
        """Compute the route between two official station names.

        Args:
            start: Official starting station name.
            end: Official ending station name.
            mode: Path query mode.
            max_transfers: Maximum allowed transfers, or None.
            line_preference: Preferred line name, or None.

        Returns:
            A fully populated ``Route``.

        Raises:
            QueryError (or a subclass) describing the failure.
        """
        if mode not in PathfindingConfig.MODES:
            raise QueryError(f"Unsupported mode '{mode}'")
        if not self.network.has_station(start):
            raise StationNotFoundError(f"Starting station '{start}' does not exist, please check the station name")
        if not self.network.has_station(end):
            raise StationNotFoundError(f"Ending station '{end}' does not exist, please check the station name")
        if start == end:
            raise LogicalQueryError("Starting station cannot be the same as the ending station")
        if line_preference and line_preference not in self.network.line_names():
            raise QueryError(f"Line preference '{line_preference}' does not exist")
        try:
            config = PathfindingConfig(mode, max_transfers,
                                       [line_preference] if line_preference else [])
        except ValueError as exc:
            raise QueryError(str(exc)) from exc

        graph = self.network.graph
        try:
            source_number = graph.get_number(start)
            target_number = graph.get_number(end)
            search = ShortestPath(graph, source_number, config)
            if not search.has_path(target_number):
                if max_transfers is not None:
                    raise PathNotFoundError(
                        f"No route found from '{start}' to '{end}' within {max_transfers} transfers")
                raise PathNotFoundError(f"No route found from '{start}' to '{end}'")
            numbers, edges = search.path_with_edges(target_number)
        except QueryError:
            raise
        except Exception as exc:
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc

        if not edges:
            raise PathNotFoundError(f"No route found from '{start}' to '{end}'")
        names = [graph.get_name(number) for number in numbers]
        return self._build_route(start, end, mode, names, edges)

    def _build_route(self, start, end, mode, names, edges) -> Route:
        """Assemble segments, transfers, distance, fare and time into a Route."""
        segments = []
        segment_start = 0
        segment_distance = 0.0
        for index, edge in enumerate(edges):
            if index > 0 and edge.line != edges[index - 1].line:
                segments.append(Segment(
                    line=edges[index - 1].line,
                    start_station=names[segment_start],
                    end_station=names[index],
                    station_names=names[segment_start:index + 1],
                    distance_m=segment_distance))
                segment_start = index
                segment_distance = 0.0
            segment_distance += edge.distance
        segments.append(Segment(
            line=edges[-1].line,
            start_station=names[segment_start],
            end_station=names[-1],
            station_names=names[segment_start:],
            distance_m=segment_distance))

        transfers = [
            Transfer(station_name=segments[i].start_station,
                     from_line=segments[i - 1].line,
                     to_line=segments[i].line)
            for i in range(1, len(segments))
        ]
        total_distance = sum(segment.distance_m for segment in segments)

        try:
            fare = calculate_fare(total_distance)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError(f"Fare calculation failed: {exc}") from exc
        estimated = calculate_estimated_time(total_distance, len(transfers))

        return Route(
            start_station=start,
            end_station=end,
            mode=mode,
            stations=names,
            segments=segments,
            transfers=transfers,
            total_distance_m=total_distance,
            estimated_time_min=estimated,
            fare=fare,
        )
