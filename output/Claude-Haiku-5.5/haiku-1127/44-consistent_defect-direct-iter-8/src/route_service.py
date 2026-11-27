"""Route query service: ties network, path search and fare calculation together."""

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from network import StationNotFoundError
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Raised when a route cannot be computed or priced."""


@dataclass
class TransferPoint:
    """A station where the passenger changes from one line to another."""

    station: str
    from_line: str
    to_line: str


@dataclass
class LineSegment:
    """A run of consecutive stations travelled on one line (travel order)."""

    line: str
    stations: list = field(default_factory=list)


@dataclass
class RouteReport:
    """Complete result of a path query."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    stations: list          # display order: from end to start
    segments: list          # LineSegment objects in travel order
    transfers: list         # TransferPoint objects in travel order
    lines: list             # all lines involved, in travel order, unique
    distance_m: int
    fare: int
    transfer_count: int
    estimated_time: float
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the report."""
        return {
            "query": {
                "start": self.start,
                "end": self.end,
                "mode": self.mode,
                "max_transfers": self.max_transfers,
                "line_preference": self.preferred_lines,
            },
            "path": list(self.stations),
            "distance": self.distance_m,
            "fare": self.fare,
            "estimated_time": self.estimated_time,
            "transfer_count": self.transfer_count,
            "lines": list(self.lines),
            "segments": [{"line": seg.line, "stations": list(seg.stations)}
                         for seg in self.segments],
            "transfers": [{"station": t.station, "from_line": t.from_line,
                           "to_line": t.to_line} for t in self.transfers],
            "notes": list(self.notes),
        }


def _build_segments(travel_stations, travel_edges):
    """Group the travel-ordered path into per-line segments."""
    segments = []
    current = None
    for index, edge in enumerate(travel_edges):
        if current is None or edge.line != current.line:
            if current is not None:
                segments.append(current)
            current = LineSegment(edge.line, [travel_stations[index]])
        current.stations.append(travel_stations[index + 1])
    if current is not None:
        segments.append(current)
    return segments


class RouteService:
    """Answers route queries against a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def _resolve(self, raw_name, role, notes):
        """Resolve a station name, recording a note when a fuzzy match is used."""
        try:
            official, exact = self.network.resolve_station(raw_name)
        except StationNotFoundError as exc:
            raise StationNotFoundError(
                f"{role} station '{raw_name}' does not exist, please check the station name"
            ) from exc
        if not exact:
            notes.append(f"{role} station '{raw_name}' matched to nearest station '{official}'")
        return official

    def query(self, start_input, end_input, config=None) -> RouteReport:
        """Compute the optimal route, its fare and summary information.

        Args:
            start_input: Starting station name as typed by the user.
            end_input: Ending station name as typed by the user.
            config: ``PathfindingConfig`` (defaults to shortest distance).

        Returns:
            A ``RouteReport``.

        Raises:
            StationNotFoundError: If a station name cannot be resolved.
            RouteError: If the stations are equal, unreachable, or pricing fails.
        """
        config = (config or PathfindingConfig()).validate()
        notes = []
        start = self._resolve(start_input, "Starting", notes)
        end = self._resolve(end_input, "Ending", notes)
        if start == end:
            raise RouteError("Starting station cannot be the same as the ending station")

        source = self.network.number_of(start)
        target = self.network.number_of(end)
        try:
            search = ShortestPath(self.network.graph, source, config)
        except ValueError as exc:
            raise RouteError(f"Path calculation failed: {exc}") from exc

        if not search.has_path_to(target):
            raise RouteError(
                f"No route found from '{start}' to '{end}' with the given constraints")

        stations, edges = search.path_with_edges(target)
        transfer_count = search.get_transfer_count(target)
        display_stations = [self.network.name_of(number) for number in stations]
        travel_stations = list(reversed(display_stations))
        travel_edges = list(reversed(edges))

        segments = _build_segments(travel_stations, travel_edges)
        transfers = []
        for previous, following in zip(segments, segments[1:]):
            transfers.append(TransferPoint(previous.stations[-1], previous.line, following.line))

        lines = []
        for segment in segments:
            if segment.line not in lines:
                lines.append(segment.line)

        try:
            distance = sum(edge.distance for edge in edges)
            fare = Sum_money(distance)
            estimated = calculate_estimated_time(distance, transfer_count)
        except (TypeError, ValueError) as exc:
            raise RouteError(f"Fare calculation failed: {exc}") from exc

        return RouteReport(
            start=start,
            end=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            preferred_lines=list(config.preferred_lines),
            stations=display_stations,
            segments=segments,
            transfers=transfers,
            lines=lines,
            distance_m=int(distance),
            fare=fare,
            transfer_count=transfer_count,
            estimated_time=estimated,
            notes=notes,
        )
