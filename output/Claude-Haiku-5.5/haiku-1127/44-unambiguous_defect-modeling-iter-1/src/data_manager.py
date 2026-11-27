"""Management of the subway dataset: loading, name resolution, integrity checks
and data updates (adding lines, modifying stations, updating distances)."""

from __future__ import annotations

import re
import unicodedata

from data_loader import DATA_FILE_PATH, load_subway_data
from errors import DataError, StationNotFoundError
from models import Edge, Graph

# Main lines that must be represented in the dataset.
MAIN_LINES = (
    "Line 1",
    "Line 2",
    "Line 4",
    "Line 5",
    "Line 6",
    "Line 8",
    "Line 10",
    "Line 13",
    "Line 14",
    "Line 15",
    "Changping Line",
    "Yizhuang Line",
    "Fangshan Line",
    "Airport Line",
)

# Plausibility limits for inter-station distances (meters).
MIN_PLAUSIBLE_SEGMENT_M = 100
MAX_PLAUSIBLE_SEGMENT_M = 5000


def normalize_name(name: str) -> str:
    """Return a comparison key for a station name.

    The key ignores case, whitespace, full-width/half-width differences and a
    trailing Chinese '站' character, so 'Xi Zhi Men', 'xizhimen' and
    'Xizhimen Station' style variants resolve to the same station.
    """
    text = unicodedata.normalize("NFKC", str(name)).strip()
    text = re.sub(r"\s+", "", text).lower()
    if text.endswith("站") and len(text) > 1:
        text = text[:-1]
    return text


class DataManager:
    """Owns the subway graph and the source dataset.

    Attributes:
        source_file: Path of the JSON dataset.
        graph: The ``Graph`` built from the dataset.
        raw_data: The parsed JSON content as loaded.
        last_check_passed: Result of the most recent integrity check.
    """

    def __init__(self, source_file: str = DATA_FILE_PATH) -> None:
        self.source_file = source_file
        self.graph = Graph()
        self.raw_data: dict = {"stations": [], "connections": []}
        self.last_check_passed = False
        self._name_index: dict[str, str] = {}
        self._undeclared: set[str] = set()

    # ------------------------------------------------------------------ loading
    def load(self) -> None:
        """Read the dataset and build the graph.

        Stations get sequential numbers starting at 1. Stations that only appear
        in connections are registered too, and reported by the integrity check.

        Raises:
            DataError: If the dataset structure is malformed.
        """
        data = load_subway_data(self.source_file)
        stations = data.get("stations")
        connections = data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise DataError("dataset must contain 'stations' and 'connections' lists")

        self.raw_data = data
        self.graph = Graph()
        self._undeclared = set()

        for record in stations:
            name, lines = self._parse_station_record(record)
            self._ensure_station(name)
            merged = self.graph.lines_of(name) + [l for l in lines if l not in self.graph.lines_of(name)]
            self.graph.set_station_lines(name, merged)

        for record in connections:
            source, dest, distance, line = self._parse_connection(record)
            if source == dest or distance <= 0:
                continue  # reported by check_integrity()
            for name in (source, dest):
                if not self.graph.has_station(name):
                    self._undeclared.add(name)
                    self._ensure_station(name)
            a = self.graph.number_of(source)
            b = self.graph.number_of(dest)
            if self.graph.find_edges(a, b, line):
                continue  # duplicate record (e.g. both directions listed)
            self.graph.add_edge(Edge(a, b, distance, line))

        self._rebuild_index()

    def _ensure_station(self, name: str) -> int:
        """Register a station if needed and return its number."""
        if self.graph.has_station(name):
            return self.graph.number_of(name)
        number = max(self.graph.number_to_name, default=0) + 1
        self.graph.add_station(name, number)
        return number

    def _rebuild_index(self) -> None:
        """Rebuild the normalised-name lookup table."""
        self._name_index = {normalize_name(name): name for name in self.graph.station_to_number}

    @staticmethod
    def _parse_station_record(record) -> tuple[str, list[str]]:
        """Validate and extract (name, lines) from a station record."""
        if not isinstance(record, dict):
            raise DataError(f"station record must be an object: {record!r}")
        name = record.get("name")
        lines = record.get("lines", [])
        if not isinstance(name, str) or not name.strip():
            raise DataError(f"station record has no valid name: {record!r}")
        if not isinstance(lines, list) or not all(isinstance(l, str) for l in lines):
            raise DataError(f"station '{name}' has invalid 'lines'")
        return name.strip(), [l.strip() for l in lines]

    @staticmethod
    def _parse_connection(record) -> tuple[str, str, float, str]:
        """Validate and extract (source, dest, distance, line) from a connection record."""
        if not isinstance(record, dict):
            raise DataError(f"connection record must be an object: {record!r}")
        source = record.get("source")
        dest = record.get("dest")
        distance = record.get("distance")
        line = record.get("line")
        if not isinstance(source, str) or not isinstance(dest, str):
            raise DataError(f"connection has invalid endpoints: {record!r}")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise DataError(f"connection {source}-{dest} has a non-numeric distance")
        if not isinstance(line, str) or not line.strip():
            raise DataError(f"connection {source}-{dest} has no line")
        return source.strip(), dest.strip(), distance, line.strip()

    # ------------------------------------------------------------ name lookup
    def station_names(self) -> list[str]:
        """Return all official station names, sorted."""
        return self.graph.station_names()

    def resolve_station(self, raw_name: str, role: str = "Starting") -> str:
        """Map user input to the official station name.

        Args:
            raw_name: Name typed by the user.
            role: "Starting" or "Ending", used in the error message.

        Returns:
            The official station name.

        Raises:
            StationNotFoundError: If no station matches.
        """
        key = normalize_name(raw_name or "")
        if key and key in self._name_index:
            return self._name_index[key]
        raise StationNotFoundError(role, (raw_name or "").strip())

    def _require_station(self, name: str) -> str:
        """Return the official name for ``name`` or raise DataError."""
        try:
            return self.resolve_station(name)
        except StationNotFoundError as exc:
            raise DataError(str(exc)) from exc

    # ------------------------------------------------------- integrity check
    def check_integrity(self) -> tuple[list[str], list[str]]:
        """Run data integrity checks.

        Checks performed:
            * coverage of every main line by at least one station;
            * stations referenced by connections but not declared;
            * malformed, self-looping, duplicate or non-positive connections;
            * lines of each connection being served by both endpoints;
            * distance plausibility;
            * isolated stations and disconnected network components.

        Returns:
            ``(errors, warnings)`` as lists of human-readable messages.
        """
        errors: list[str] = []
        warnings: list[str] = []
        graph = self.graph

        # Coverage of main lines.
        for line in MAIN_LINES:
            count = sum(1 for lines in graph.station_lines.values() if line in lines)
            if count == 0:
                errors.append(f"main line '{line}' has no stations in the dataset")

        # Duplicate station declarations.
        seen_names: set[str] = set()
        for record in self.raw_data.get("stations", []):
            if isinstance(record, dict):
                name = record.get("name")
                if name in seen_names:
                    warnings.append(f"station '{name}' is declared more than once")
                seen_names.add(name)

        for name in sorted(self._undeclared):
            errors.append(f"station '{name}' appears in connections but is not declared in stations")

        # Connection integrity and distance accuracy.
        seen_pairs: set[tuple[frozenset, str]] = set()
        for index, record in enumerate(self.raw_data.get("connections", []), start=1):
            try:
                source, dest, distance, line = self._parse_connection(record)
            except DataError as exc:
                errors.append(f"connection #{index}: {exc}")
                continue
            label = f"connection #{index} ({source} - {dest}, {line})"
            if source == dest:
                errors.append(f"{label}: connects a station to itself")
                continue
            if distance <= 0:
                errors.append(f"{label}: distance must be positive, got {distance}")
            elif distance > MAX_PLAUSIBLE_SEGMENT_M:
                warnings.append(f"{label}: distance {distance} m is unusually long")
            elif distance < MIN_PLAUSIBLE_SEGMENT_M:
                warnings.append(f"{label}: distance {distance} m is unusually short")
            if not float(distance).is_integer():
                warnings.append(f"{label}: distance {distance} m is not an integer number of meters")

            key = (frozenset((source, dest)), line)
            if key in seen_pairs:
                errors.append(f"{label}: duplicate connection")
            seen_pairs.add(key)

            for name in (source, dest):
                if line not in graph.lines_of(name):
                    errors.append(f"{label}: line '{line}' is not served by station '{name}'")

        # Connectivity.
        for name in graph.station_names():
            if not graph.adjacent(graph.number_of(name)):
                warnings.append(f"station '{name}' has no connections")
        components = graph.connected_components()
        if components > 1:
            warnings.append(f"network is split into {components} disconnected parts")

        self.last_check_passed = not errors
        return errors, warnings

    # ------------------------------------------------------------ data updates
    def add_line(self, line_name: str, station_names: list[str], distances: list[int]) -> None:
        """Add a new line as an ordered sequence of stations.

        Stations that do not yet exist are created. ``distances[i]`` is the
        distance in meters between ``station_names[i]`` and ``station_names[i+1]``.

        Raises:
            DataError: If the input is invalid or the line already exists.
        """
        line_name = (line_name or "").strip()
        if not line_name:
            raise DataError("line name must not be empty")
        if line_name in self.graph.lines():
            raise DataError(f"line '{line_name}' already exists")
        names = [s.strip() for s in station_names]
        if len(names) < 2:
            raise DataError("a line needs at least two stations")
        if len(set(names)) != len(names):
            raise DataError("a line cannot visit the same station twice")
        if len(distances) != len(names) - 1:
            raise DataError("number of distances must be one less than number of stations")
        for distance in distances:
            if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
                raise DataError("distances must be positive integers (meters)")

        for name in names:
            self._ensure_station(name)
            current = self.graph.lines_of(name)
            if line_name not in current:
                self.graph.set_station_lines(name, current + [line_name])
        for index, distance in enumerate(distances):
            a = self.graph.number_of(names[index])
            b = self.graph.number_of(names[index + 1])
            self.graph.add_edge(Edge(a, b, distance, line_name))
        self._rebuild_index()

    def modify_station(self, name: str, new_name: str | None = None, lines: list[str] | None = None) -> str:
        """Change a station's name and/or the lines serving it.

        Returns:
            The station's official name after the modification.

        Raises:
            DataError: If the station is unknown, or the new name is already taken.
        """
        official = self._require_station(name)
        if lines is not None:
            cleaned = [l.strip() for l in lines if l and l.strip()]
            self.graph.set_station_lines(official, cleaned)
        if new_name and new_name.strip() and new_name.strip() != official:
            target = new_name.strip()
            if self.graph.has_station(target):
                raise DataError(f"station '{target}' already exists")
            self.graph.rename_station(official, target)
            official = target
        self._rebuild_index()
        return official

    def update_distance(self, station_a: str, station_b: str, distance: int, line: str | None = None) -> int:
        """Update the distance of the segment(s) between two adjacent stations.

        Returns:
            The number of segments updated.

        Raises:
            DataError: If the stations are unknown, not adjacent, or the distance is invalid.
        """
        a_name = self._require_station(station_a)
        b_name = self._require_station(station_b)
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise DataError("distance must be a positive integer (meters)")
        edges = self.graph.find_edges(self.graph.number_of(a_name), self.graph.number_of(b_name), line)
        if not edges:
            raise DataError(f"no direct connection between '{a_name}' and '{b_name}'")
        for edge in edges:
            edge.distance = distance
        return len(edges)
