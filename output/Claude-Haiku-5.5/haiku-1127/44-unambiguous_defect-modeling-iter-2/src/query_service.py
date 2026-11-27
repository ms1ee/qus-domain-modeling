"""Query service that combines network lookup, path search and fare calculation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

try:
    from .network import StationNotFoundError, NetworkError
    from .pathfinding import PathfindingConfig, ShortestPath
    from .fare_calculator import Sum_money, calculate_estimated_time
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from network import StationNotFoundError, NetworkError
    from pathfinding import PathfindingConfig, ShortestPath
    from fare_calculator import Sum_money, calculate_estimated_time


class QueryError(Exception):
    """Base class for query errors reported to the user."""


class PathNotFoundError(QueryError):
    """Raised when no route satisfies the query constraints."""


@dataclass
class TransferInfo:
    """A transfer between two lines at a station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class PathResult:
    """Complete result of a path query (the Path and Query domain concepts)."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]
    edges: list
    total_distance_m: float
    transfer_count: int
    transfers: List[TransferInfo]
    lines: List[str]
    fare: int
    estimated_time_minutes: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_distance_km(self):
        """Total distance in kilometers (3 decimal places)."""
        return round(self.total_distance_m / 1000.0, 3)


class PathQueryService:
    """Answers route and fare queries against a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def _resolve(self, text, role):
        """Resolve a station name, producing a user-facing error message on failure."""
        try:
            return self.network.resolve_station(text)
        except StationNotFoundError as exc:
            raise StationNotFoundError(
                f"{role} station '{str(text).strip()}' does not exist, please check the station name"
            ) from exc

    def query(self, start, end, config=None):
        """Compute the route and fare between two stations.

        Args:
            start: Starting station name (lenient matching).
            end: Ending station name (lenient matching).
            config: ``PathfindingConfig`` (defaults to shortest distance).

        Returns:
            PathResult: The computed route summary.

        Raises:
            StationNotFoundError: If a station does not exist.
            QueryError: For logical errors or calculation failures.
            PathNotFoundError: If no route satisfies the constraints.
        """
        config = config if config is not None else PathfindingConfig()
        start_name = self._resolve(start, "Starting")
        end_name = self._resolve(end, "Ending")
        if start_name == end_name:
            raise QueryError("Starting station cannot be the same as the ending station")

        try:
            preferred = [self.network.resolve_line(line) for line in config.preferred_lines]
        except NetworkError as exc:
            raise QueryError(str(exc)) from exc
        effective = PathfindingConfig(config.mode, config.max_transfers, preferred)

        source = self.network.number_of(start_name)
        target = self.network.number_of(end_name)
        try:
            search = ShortestPath(self.network.graph, source, effective)
            if not search.has_path(target):
                raise PathNotFoundError(
                    f"No route found from '{start_name}' to '{end_name}' under the given constraints"
                )
            numbers, edges = search.path_with_edges(target)
        except PathNotFoundError:
            raise
        except Exception as exc:
            raise QueryError(f"Path calculation failed: {exc}") from exc

        stations = [self.network.name_of(number) for number in numbers]
        transfers = self._find_transfers(stations, edges)
        total = float(sum(edge.weight for edge in edges))
        try:
            fare = Sum_money(total)
            estimated = calculate_estimated_time(total, len(transfers))
        except (TypeError, ValueError) as exc:
            raise QueryError(f"Fare calculation failed: {exc}") from exc

        lines = []
        for edge in edges:
            if edge.line not in lines:
                lines.append(edge.line)

        return PathResult(
            start_station=start_name,
            end_station=end_name,
            mode=effective.mode,
            max_transfers=effective.max_transfers,
            preferred_lines=preferred,
            stations=stations,
            edges=edges,
            total_distance_m=total,
            transfer_count=len(transfers),
            transfers=transfers,
            lines=lines,
            fare=fare,
            estimated_time_minutes=estimated,
        )

    @staticmethod
    def _find_transfers(stations, edges):
        """Identify the transfer stations where the traveled line changes."""
        transfers = []
        for index in range(len(edges) - 1):
            if edges[index].line != edges[index + 1].line:
                transfers.append(
                    TransferInfo(
                        station_name=stations[index + 1],
                        from_line=edges[index].line,
                        to_line=edges[index + 1].line,
                    )
                )
        return transfers
