"""Query orchestration: parses user input, runs path search and assembles results.

This module combines the network, the path search and the fare calculator
into a single RouteResult for one origin/destination query.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from errors import (
    FareCalculationError,
    InputFormatError,
    InvalidQueryError,
    PathNotFoundError,
)
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

# Accepted separators between the starting and ending station (ASCII and full-width).
_QUERY_SEPARATOR = re.compile(r"[;；,，]")


def parse_query(text):
    """Split a "Starting Station; Ending Station" string into two names.

    Returns:
        tuple[str, str]: The starting and ending station texts (stripped).

    Raises:
        InputFormatError: If the input does not contain exactly two parts.
    """
    if text is None or not str(text).strip():
        raise InputFormatError()
    parts = _QUERY_SEPARATOR.split(str(text))
    if len(parts) != 2:
        raise InputFormatError()
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError()
    return start, end


@dataclass
class RouteResult:
    """Complete result of a single route query.

    Attributes:
        start, end: Official station names.
        mode: Path query mode used.
        max_transfers: Transfer limit used (None means unlimited).
        preferred_lines: Preferred lines used.
        station_names: Ordered list of station names on the route.
        edges: Ordered list of Edge objects on the route.
        distance_m: Total distance in meters.
        fare: Fare in yuan.
        transfer_count: Number of line changes.
        transfers: List of dicts {"station", "from_line", "to_line"}.
        lines: Unique line names involved, in order of appearance.
        segments: List of dicts {"line", "stations"} covering the route.
        estimated_time_min: Estimated travel time in minutes.
    """

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    station_names: List[str]
    edges: list
    distance_m: int
    fare: int
    transfer_count: int
    transfers: list = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    segments: list = field(default_factory=list)
    estimated_time_min: float = 0.0


class SubwayService:
    """Answers route queries against a SubwayNetwork."""

    def __init__(self, network):
        self.network = network

    def query(self, start_text, end_text, config=None):
        """Compute the route, fare and summary information for one query.

        Args:
            start_text: Starting station as typed by the user.
            end_text: Ending station as typed by the user.
            config: PathfindingConfig; defaults to the shortest distance mode.

        Returns:
            RouteResult: The computed route.

        Raises:
            StationNotFoundError: If a station does not exist.
            InvalidQueryError: If start and end are the same station or the config is invalid.
            PathNotFoundError: If no route exists under the constraints.
            FareCalculationError: If the fare cannot be computed.
        """
        config = config if config is not None else PathfindingConfig()
        start = self.network.resolve_station(start_text, "Starting station")
        end = self.network.resolve_station(end_text, "Ending station")
        if start == end:
            raise InvalidQueryError("Starting station cannot be the same as the ending station")

        source = self.network.station_number(start)
        target = self.network.station_number(end)
        try:
            search = ShortestPath(self.network.graph, source, config)
        except ValueError as exc:
            raise InvalidQueryError(str(exc)) from exc

        if not search.has_path(target):
            message = f"No route found from '{start}' to '{end}'"
            if config.max_transfers is not None:
                message += f" within {config.max_transfers} transfer(s)"
            raise PathNotFoundError(message)

        numbers, edges = search.path_with_edges(target)
        names = [self.network.station_name(number) for number in numbers]
        distance = sum(edge.distance for edge in edges)
        transfer_count = search.get_transfer_count(target)
        fare = self._calculate_fare(distance)
        estimated = calculate_estimated_time(distance, transfer_count)

        lines = []
        for edge in edges:
            if edge.line not in lines:
                lines.append(edge.line)

        return RouteResult(
            start=start,
            end=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            preferred_lines=list(config.preferred_lines),
            station_names=names,
            edges=edges,
            distance_m=distance,
            fare=fare,
            transfer_count=transfer_count,
            transfers=self._transfer_points(names, edges),
            lines=lines,
            segments=self._segments(names, edges),
            estimated_time_min=estimated,
        )

    def query_text(self, text, config=None):
        """Parse a "Start; End" string and run the query."""
        start, end = parse_query(text)
        return self.query(start, end, config)

    # ----- helpers ------------------------------------------------------

    @staticmethod
    def _calculate_fare(distance):
        """Wrap the fare calculation and convert failures to FareCalculationError."""
        try:
            return Sum_money(distance)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError(f"cannot calculate fare: {exc}") from exc

    @staticmethod
    def _transfer_points(names, edges):
        """List the interchange stations where the line changes."""
        points = []
        for index in range(len(edges) - 1):
            if edges[index].line != edges[index + 1].line:
                points.append(
                    {
                        "station": names[index + 1],
                        "from_line": edges[index].line,
                        "to_line": edges[index + 1].line,
                    }
                )
        return points

    @staticmethod
    def _segments(names, edges):
        """Group consecutive edges of the same line into segments."""
        if not edges:
            return []
        segments = []
        current = {"line": edges[0].line, "stations": [names[0], names[1]]}
        for index in range(1, len(edges)):
            if edges[index].line != current["line"]:
                segments.append(current)
                current = {"line": edges[index].line, "stations": [names[index]]}
            current["stations"].append(names[index + 1])
        segments.append(current)
        return segments
