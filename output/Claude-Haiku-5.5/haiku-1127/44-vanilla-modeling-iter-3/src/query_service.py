"""High-level query service tying together graph, pathfinding and fares."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money, calculate_estimated_time
from models import Graph, PathSegment, Transfer
from network import build_graph
from pathfinding import PathfindingConfig, ShortestPath


class SubwayError(Exception):
    """Base class for query-related errors that are safe to show to users."""


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be resolved."""

    def __init__(self, role: str, text: str, suggestions: Sequence[str]) -> None:
        self.role = role
        self.text = text
        self.suggestions = list(suggestions)
        message = f"{role} station '{text}' does not exist, please check the station name"
        if self.suggestions:
            message += ". Did you mean: " + ", ".join(self.suggestions) + "?"
        super().__init__(message)


class SameStationError(SubwayError):
    """Raised when the start and end stations are identical."""


class NoPathError(SubwayError):
    """Raised when no path satisfies the query constraints."""


def normalize_station_name(text: str) -> str:
    """Normalize a station name for lenient matching.

    Removes whitespace and separators, lowercases, and drops a trailing
    Chinese "station" suffix.
    """
    cleaned = re.sub(r"[\s_\-·]", "", text).lower()
    if cleaned.endswith("站"):
        cleaned = cleaned[:-1]
    return cleaned


@dataclass
class QueryResult:
    """Complete result of a single path/fare query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: List[str]
    stations: List[str]
    segments: List[PathSegment]
    transfers: List[Transfer]
    involved_lines: List[str]
    total_distance_m: float
    transfer_count: int
    fare: int
    estimated_time_min: float
    extra: Dict[str, Any] = field(default_factory=dict)


class SubwayService:
    """Loads the network and answers fare/path queries."""

    def __init__(self, data: Optional[Dict[str, Any]] = None, data_path: str = DATA_FILE_PATH) -> None:
        self.data = data if data is not None else load_subway_data(data_path)
        self.graph: Graph = build_graph(self.data)
        self.station_names: List[str] = sorted(self.graph.station_to_number)
        self.line_names: List[str] = self.graph.lines()
        self._normalized_index: Dict[str, List[str]] = {}
        for name in self.station_names:
            self._normalized_index.setdefault(normalize_station_name(name), []).append(name)

    # ------------------------------------------------------------------ #
    # Input standardization
    # ------------------------------------------------------------------ #
    def resolve_station(self, role: str, text: str) -> str:
        """Map user input to an official station name.

        Args:
            role: "Starting" or "Ending", used in error messages.
            text: The raw user input.

        Raises:
            ValueError: If the input is empty.
            StationNotFoundError: If no station matches.
        """
        text = (text or "").strip()
        if not text:
            raise ValueError(f"{role} station name must not be empty")
        if text in self.graph.station_to_number:
            return text
        matches = self._normalized_index.get(normalize_station_name(text), [])
        if len(matches) == 1:
            return matches[0]
        suggestions = difflib.get_close_matches(text, self.station_names, n=3, cutoff=0.6)
        raise StationNotFoundError(role, text, suggestions)

    def resolve_line(self, text: str) -> str:
        """Map user input (e.g. "Line 1" or "1") to an official line name.

        Raises:
            ValueError: If no line matches.
        """
        text = (text or "").strip()
        candidates = [text]
        if text.isdigit():
            candidates.append(f"Line {text}")
        lowered = {line.lower(): line for line in self.line_names}
        for candidate in candidates:
            if candidate in self.line_names:
                return candidate
            if candidate.lower() in lowered:
                return lowered[candidate.lower()]
        raise ValueError(f"Unknown line '{text}'")

    # ------------------------------------------------------------------ #
    # Query execution
    # ------------------------------------------------------------------ #
    def query(
        self,
        start_text: str,
        end_text: str,
        config: Optional[PathfindingConfig] = None,
    ) -> QueryResult:
        """Compute the optimal route, its fare and summary information.

        Raises:
            ValueError: For invalid configuration or empty input.
            StationNotFoundError: If a station name is unknown.
            SameStationError: If start and end are identical.
            NoPathError: If no route satisfies the constraints.
            SubwayError: If path or fare calculation fails unexpectedly.
        """
        config = config if config is not None else PathfindingConfig()
        config.validate()

        start = self.resolve_station("Starting", start_text)
        end = self.resolve_station("Ending", end_text)
        if start == end:
            raise SameStationError("Starting station cannot be the same as the ending station")

        try:
            source = self.graph.number_of(start)
            target = self.graph.number_of(end)
            finder = ShortestPath(self.graph, source, config)
        except KeyError as exc:
            raise SubwayError(f"Path calculation failed: {exc}") from exc

        if not finder.has_path_to(target):
            raise NoPathError(
                f"No route found from '{start}' to '{end}' with the given constraints"
            )

        numbers, edges = finder.path_with_edges(target)
        names = [self.graph.name_of(number) for number in numbers]
        segments = self._build_segments(names, edges)
        transfers = self._detect_transfers(names, edges)
        involved = self._involved_lines(edges)
        total_distance = float(sum(edge.distance for edge in edges))
        transfer_count = len(transfers)

        try:
            fare = Sum_money(total_distance)
            estimated = calculate_estimated_time(total_distance, transfer_count)
        except (TypeError, ValueError) as exc:
            raise SubwayError(f"Fare calculation failed: {exc}") from exc

        return QueryResult(
            start_station=start,
            end_station=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            line_preference=list(config.preferred_lines),
            stations=names,
            segments=segments,
            transfers=transfers,
            involved_lines=involved,
            total_distance_m=total_distance,
            transfer_count=transfer_count,
            fare=fare,
            estimated_time_min=estimated,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_segments(names: List[str], edges: List[Any]) -> List[PathSegment]:
        """Group consecutive edges on the same line into segments."""
        segments: List[PathSegment] = []
        if not edges:
            return segments
        start_index = 0
        for index in range(len(edges)):
            is_last = index == len(edges) - 1
            if is_last or edges[index + 1].line != edges[index].line:
                distance = sum(edges[i].distance for i in range(start_index, index + 1))
                segments.append(
                    PathSegment(
                        start_station=names[start_index],
                        end_station=names[index + 1],
                        distance_m=float(distance),
                        line=edges[index].line,
                    )
                )
                start_index = index + 1
        return segments

    @staticmethod
    def _detect_transfers(names: List[str], edges: List[Any]) -> List[Transfer]:
        """Return the line changes along the path."""
        transfers: List[Transfer] = []
        for index in range(1, len(edges)):
            previous_line = edges[index - 1].line
            current_line = edges[index].line
            if previous_line != current_line:
                transfers.append(
                    Transfer(
                        station_name=names[index],
                        from_line=previous_line,
                        to_line=current_line,
                    )
                )
        return transfers

    @staticmethod
    def _involved_lines(edges: List[Any]) -> List[str]:
        """Return the unique lines used, in travel order."""
        seen: List[str] = []
        for edge in edges:
            if edge.line not in seen:
                seen.append(edge.line)
        return seen
