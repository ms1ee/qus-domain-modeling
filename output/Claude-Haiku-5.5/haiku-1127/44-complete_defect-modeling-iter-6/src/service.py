"""Query service: input parsing, validation, path computation, fare and route assembly."""
from __future__ import annotations

from typing import List, Tuple

from fare_calculator import Sum_money, calculate_estimated_time
from models import Query, Route
from network import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for all user-facing query errors."""


class InputFormatError(QueryError):
    """The input does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(QueryError):
    """A station name does not exist in the network."""


class SameStationError(QueryError):
    """Origin and destination are the same station."""


class PathNotFoundError(QueryError):
    """No path exists between origin and destination under the given constraints."""


class CalculationError(QueryError):
    """Fare or time calculation failed."""


def parse_query(raw: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' into its two raw station names."""
    parts = raw.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


class QueryService:
    """Runs subway fare queries against a SubwayNetwork."""

    def __init__(self, network: SubwayNetwork) -> None:
        self.network = network

    def validate_stations(self, origin_raw: str, dest_raw: str) -> Tuple[str, str]:
        """Standardize and validate origin and destination names."""
        origin = self.network.resolve_station(origin_raw)
        if origin is None:
            raise StationNotFoundError(
                f"Starting station '{origin_raw}' does not exist, please check the station name"
            )
        dest = self.network.resolve_station(dest_raw)
        if dest is None:
            raise StationNotFoundError(
                f"Ending station '{dest_raw}' does not exist, please check the station name"
            )
        if origin == dest:
            raise SameStationError("Starting station cannot be the same as the ending station")
        return origin, dest

    def run(self, raw_input: str, config: PathfindingConfig) -> Tuple[Query, Route]:
        """Execute one query and return the query description and computed route."""
        origin_raw, dest_raw = parse_query(raw_input)
        origin, dest = self.validate_stations(origin_raw, dest_raw)

        try:
            source_no = self.network.number_of(origin)
            target_no = self.network.number_of(dest)
            sp = ShortestPath(self.network.graph, source_no, config)
        except ValueError as exc:
            raise PathNotFoundError(f"path calculation failed: {exc}") from exc

        if not sp.has_path(target_no):
            raise PathNotFoundError(
                f"no route found from '{origin}' to '{dest}' under the current settings"
            )

        stations, edges = sp.path_with_edges(target_no)
        names = [self.network.name_of(n) for n in stations]
        route = self._build_route(names, edges)

        query = Query(
            raw_input=raw_input,
            origin_station=origin,
            destination_station=dest,
            mode=config.mode,
            max_transfers=config.max_transfers,
            line_preference=config.preferred_lines[0] if config.preferred_lines else None,
        )
        return query, route

    def _build_route(self, names: List[str], edges) -> Route:
        """Assemble a Route (distance, fare, time, transfers, segments) from a path."""
        total_distance = float(sum(e.distance for e in edges))
        transfer_count = sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)

        segments: List[Tuple[str, List[str]]] = []
        if edges:
            current_line = edges[0].line
            current = [names[0], names[1]]
            for i in range(1, len(edges)):
                edge = edges[i]
                if edge.line == current_line:
                    current.append(names[i + 1])
                else:
                    segments.append((current_line, current))
                    current_line = edge.line
                    current = [names[i], names[i + 1]]
            segments.append((current_line, current))

        involved: List[str] = []
        for line, _ in segments:
            if line not in involved:
                involved.append(line)

        try:
            fare = Sum_money(total_distance)
            estimated = calculate_estimated_time(total_distance, transfer_count)
        except (ValueError, TypeError) as exc:
            raise CalculationError(f"fare or time calculation failed: {exc}") from exc

        return Route(
            station_sequence=list(names),
            total_distance=total_distance,
            transfer_count=transfer_count,
            estimated_time=estimated,
            fare=fare,
            involved_lines=involved,
            segments=segments,
        )
