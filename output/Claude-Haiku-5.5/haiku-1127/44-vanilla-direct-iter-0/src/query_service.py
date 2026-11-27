"""
Query service: validates user queries, computes routes and fares, and builds
structured query results used by the reporting and CLI modules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    find_route,
)


class QueryError(Exception):
    """Raised when a query cannot be validated or answered."""


@dataclass
class QueryResult:
    """Complete result of one path and fare query."""

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]
    segments: List[Tuple[str, List[str]]]
    transfers: List[Dict[str, str]]
    lines: List[str]
    distance_m: int
    fare: int
    transfer_count: int
    estimated_time: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        """Return a JSON-serialisable representation of the result."""
        return {
            "query": {
                "start": self.start,
                "end": self.end,
                "mode": self.mode,
                "max_transfers": self.max_transfers,
                "preferred_lines": list(self.preferred_lines),
            },
            "path": {
                "stations": list(self.stations),
                "station_count": len(self.stations),
                "segments": [
                    {"line": line, "stations": list(stations)}
                    for line, stations in self.segments
                ],
            },
            "distance": {
                "meters": self.distance_m,
                "kilometers": round(self.distance_m / 1000.0, 3),
            },
            "fare": self.fare,
            "estimated_time_minutes": round(self.estimated_time, 1),
            "transfer_count": self.transfer_count,
            "transfers": [dict(item) for item in self.transfers],
            "lines": list(self.lines),
        }


def _summarize_route(names, edges):
    """
    Build line segments, transfer details and the involved line list.

    Args:
        names: Station names along the route (len = len(edges) + 1).
        edges: Edges along the route.

    Returns:
        tuple: (segments, transfers, lines)
    """
    if not edges:
        return [], [], []

    segments = []
    current_line = edges[0].line
    current_stations = [names[0]]
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append((current_line, current_stations))
            current_line = edge.line
            current_stations = [names[index]]
        current_stations.append(names[index + 1])
    segments.append((current_line, current_stations))

    transfers = []
    for index in range(1, len(edges)):
        if edges[index - 1].line != edges[index].line:
            transfers.append({
                "station": names[index],
                "from_line": edges[index - 1].line,
                "to_line": edges[index].line,
            })

    lines = []
    for line, _ in segments:
        if line not in lines:
            lines.append(line)
    return segments, transfers, lines


class SubwayQueryService:
    """Answers route and fare queries against a SubwayNetwork."""

    def __init__(self, network):
        self.network = network

    def validate_pair(self, start_raw, end_raw):
        """
        Standardize and validate the starting and ending station names.

        Returns:
            tuple: (official start name, official end name)

        Raises:
            QueryError: If a station does not exist or both stations are equal.
        """
        start = self.network.standardize_station_name(start_raw)
        if start is None:
            raise QueryError(
                f"Starting station '{start_raw}' does not exist, please check the station name"
            )
        end = self.network.standardize_station_name(end_raw)
        if end is None:
            raise QueryError(
                f"Ending station '{end_raw}' does not exist, please check the station name"
            )
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")
        return start, end

    def query(self, start_name, end_name, mode=MODE_SHORTEST_DISTANCE,
              max_transfers=None, preferred_lines=None):
        """
        Compute the route, fare and summary between two stations.

        Args:
            start_name: Starting station name (official or lenient spelling).
            end_name: Ending station name.
            mode: Path query mode.
            max_transfers: Optional maximum number of transfers.
            preferred_lines: Optional list of preferred line names.

        Returns:
            QueryResult

        Raises:
            QueryError: On validation, path calculation or fare calculation failure.
        """
        start, end = self.validate_pair(start_name, end_name)

        try:
            config = PathfindingConfig(mode, max_transfers, preferred_lines)
        except ValueError as exc:
            raise QueryError(f"Invalid query configuration: {exc}") from exc

        try:
            route = find_route(
                self.network.get_graph(),
                self.network.number_of(start),
                self.network.number_of(end),
                config,
            )
        except Exception as exc:  # defensive: path computation must not crash the CLI
            raise QueryError(f"Path calculation failed: {exc}") from exc

        if route is None:
            if config.max_transfers is not None:
                raise QueryError(
                    f"No route found from '{start}' to '{end}' within "
                    f"{config.max_transfers} transfer(s)"
                )
            raise QueryError(f"No route found from '{start}' to '{end}'")

        names = [self.network.name_of(number) for number in route.stations]
        segments, transfers, lines = _summarize_route(names, route.edges)
        transfer_count = len(transfers)

        try:
            fare = Sum_money(route.distance)
            estimated = calculate_estimated_time(route.distance, transfer_count)
        except (TypeError, ValueError) as exc:
            raise QueryError(f"Fare calculation failed: {exc}") from exc

        return QueryResult(
            start=start,
            end=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            preferred_lines=list(config.preferred_lines),
            stations=names,
            segments=segments,
            transfers=transfers,
            lines=lines,
            distance_m=route.distance,
            fare=fare,
            transfer_count=transfer_count,
            estimated_time=estimated,
        )
