"""
Subway network data management.

SubwayNetwork owns the station registry and the connection list, derives the
weighted undirected graph from them, assigns station numbers (sorted by name so
numbering is stable), resolves user-entered station names, performs data
integrity checks, and supports data updates (adding lines, modifying stations,
updating distances) and saving the dataset back to JSON.
"""
from __future__ import annotations

import difflib
import json
from collections import deque
from dataclasses import dataclass, field

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph, normalize_text

# Main lines the dataset is expected to cover.
MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
# Representative (line, station) pairs used for the coverage check.
REPRESENTATIVE_STATIONS = (
    ("Line 1", "苹果园"),
    ("Line 1", "天安门东"),
    ("Line 2", "西直门"),
    ("Line 2", "建国门"),
    ("Line 10", "国贸"),
)
# Plausible range for inter-station distances (meters); outside is reported as a warning.
MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 5000


class StationNotFoundError(Exception):
    """Raised when a station name cannot be matched to a station in the network."""

    def __init__(self, name: str, suggestions=None) -> None:
        self.name = name
        self.suggestions = list(suggestions or [])
        super().__init__(f"Station '{name}' does not exist")


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def to_text(self) -> str:
        """Render the report as human-readable text."""
        lines = ["Data integrity check"]
        if not self.errors and not self.warnings:
            lines.append("  No problems found.")
        for error in self.errors:
            lines.append(f"  [ERROR] {error}")
        for warning in self.warnings:
            lines.append(f"  [WARNING] {warning}")
        status = "PASSED" if self.ok else "FAILED"
        lines.append(f"Result: {status} ({len(self.errors)} error(s), {len(self.warnings)} warning(s))")
        return "\n".join(lines)


def _clean(text) -> str:
    """Strip and collapse whitespace in a name."""
    return " ".join(str(text).split())


def _unique(items) -> list[str]:
    """Return the cleaned, non-empty items with duplicates removed (order kept)."""
    result: list[str] = []
    for item in items:
        cleaned = _clean(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _is_valid_distance(value) -> bool:
    """Return True if value is a positive real number of meters."""
    return (not isinstance(value, bool)) and isinstance(value, (int, float)) and value > 0


class SubwayNetwork:
    """In-memory model of the subway network and its derived graph.

    Attributes:
        station_to_number: Mapping from station name to station number (graph vertex).
        number_to_name: Station names indexed by station number.
        line_stations: Mapping from line name to the station names serving it.
        graph: The weighted undirected graph built from the connections.
    """

    def __init__(self, raw_data: dict | None = None) -> None:
        self._declared: dict[str, list[str]] = {}   # station name -> declared lines
        self._connections: list[dict] = []          # raw connection records
        self.station_to_number: dict[str, int] = {}
        self.number_to_name: list[str] = []
        self.line_stations: dict[str, list[str]] = {}
        self.graph = Graph()
        if raw_data is not None:
            self._load_raw(raw_data)
        self._rebuild()

    @classmethod
    def from_file(cls, path: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Create a network from a subway dataset JSON file."""
        return cls(load_subway_data(path))

    # ------------------------------------------------------------------ loading

    def _load_raw(self, raw: dict) -> None:
        """Populate the station registry and connection list from raw data."""
        for entry in raw.get("stations", []):
            name = _clean(entry["name"])
            if not name:
                raise ValueError("Station name must not be empty")
            if name in self._declared:
                raise ValueError(f"Duplicate station '{name}' in data")
            self._declared[name] = _unique(entry.get("lines", []))
        for conn in raw.get("connections", []):
            self._connections.append(
                self._make_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])
            )

    @staticmethod
    def _make_connection(source, dest, distance, line) -> dict:
        """Create a normalised connection record."""
        return {
            "source": _clean(source),
            "dest": _clean(dest),
            "distance": distance,
            "line": _clean(line),
        }

    def _rebuild(self) -> None:
        """Recompute station numbers, line membership and the graph from the registry."""
        station_lines: dict[str, list[str]] = {name: list(lines) for name, lines in self._declared.items()}
        for conn in self._connections:
            for end in (conn["source"], conn["dest"]):
                station_lines.setdefault(end, [])
                if conn["line"] not in station_lines[end]:
                    station_lines[end].append(conn["line"])

        names = sorted(station_lines)
        numbers = {name: index for index, name in enumerate(names)}

        graph = Graph()
        for name in names:
            graph.add_vertex(numbers[name])
            graph.set_station_lines(name, station_lines[name])
        for conn in self._connections:
            # Invalid distances are left out of the graph and reported by check_integrity().
            if _is_valid_distance(conn["distance"]):
                graph.add_edge(Edge(numbers[conn["source"]], numbers[conn["dest"]],
                                    float(conn["distance"]), conn["line"]))

        line_stations: dict[str, list[str]] = {}
        for name in names:
            for line in station_lines[name]:
                line_stations.setdefault(line, []).append(name)

        self.station_to_number = numbers
        self.number_to_name = names
        self.graph = graph
        self.line_stations = line_stations

    # ------------------------------------------------------------------ queries

    def resolve_name(self, raw_name) -> str:
        """Map a user-entered station name to the official station name.

        Accepts exact names, names with or without the suffix "站", and
        case-insensitive matches.

        Raises:
            StationNotFoundError: If no station matches; suggestions of similar names are attached.
        """
        text = _clean(raw_name) if raw_name is not None else ""
        if not text:
            raise StationNotFoundError("", [])
        if text in self.station_to_number:
            return text
        candidates = [text + "站"]
        if text.endswith("站") and len(text) > 1:
            candidates.append(text[:-1])
        for candidate in candidates:
            if candidate in self.station_to_number:
                return candidate
        lowered: dict[str, str] = {}
        for name in self.number_to_name:
            lowered.setdefault(normalize_text(name), name)
        key = normalize_text(text)
        if key in lowered:
            return lowered[key]
        suggestions = difflib.get_close_matches(text, self.number_to_name, n=3, cutoff=0.6)
        raise StationNotFoundError(text, suggestions)

    def station_lines_of(self, name: str) -> list[str]:
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.graph.station_lines.get(name, []))

    def _find_connection(self, a: str, b: str) -> dict | None:
        """Return the connection record between two stations, if any."""
        for conn in self._connections:
            if {conn["source"], conn["dest"]} == {a, b}:
                return conn
        return None

    def _connected_names(self) -> set[str]:
        """Return all station names that appear as connection endpoints."""
        names: set[str] = set()
        for conn in self._connections:
            names.add(conn["source"])
            names.add(conn["dest"])
        return names

    # ------------------------------------------------------------------ updates

    def add_station(self, name: str, lines=()) -> None:
        """Add a new station with the given lines.

        Raises:
            ValueError: If the name is empty or already exists.
        """
        clean = _clean(name)
        if not clean:
            raise ValueError("Station name must not be empty")
        if clean in self.station_to_number:
            raise ValueError(f"Station '{clean}' already exists")
        self._declared[clean] = _unique(lines)
        self._rebuild()

    def add_line(self, line_name: str, station_names, distances) -> None:
        """Add a new line through an ordered list of stations.

        Missing stations are created. ``distances[i]`` is the distance in meters
        between ``station_names[i]`` and ``station_names[i + 1]``.

        Raises:
            ValueError: If the input is inconsistent or the line already exists.
        """
        line = _clean(line_name)
        if not line:
            raise ValueError("Line name must not be empty")
        if line in self.line_stations:
            raise ValueError(f"Line '{line}' already exists")
        names = [_clean(name) for name in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not name for name in names):
            raise ValueError("Station names must not be empty")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        for distance in distances:
            if not _is_valid_distance(distance):
                raise ValueError(f"Invalid distance {distance!r}; distances must be positive")
        for a, b in zip(names, names[1:]):
            if a == b:
                raise ValueError(f"Station '{a}' cannot be connected to itself")
            if self._find_connection(a, b) is not None:
                raise ValueError(f"Stations '{a}' and '{b}' are already connected")

        for name in names:
            if name not in self._declared and name not in self._connected_names():
                self._declared[name] = []
        for (a, b), distance in zip(zip(names, names[1:]), distances):
            self._connections.append(self._make_connection(a, b, distance, line))
        self._rebuild()

    def update_station(self, name: str, new_name: str | None = None, lines=None) -> None:
        """Modify a station: optionally rename it and/or replace its declared lines.

        Raises:
            StationNotFoundError: If the station does not exist.
            ValueError: If the new name is empty or already used.
        """
        current = self.resolve_name(name)
        target = current
        if new_name is not None:
            target = _clean(new_name)
            if not target:
                raise ValueError("New station name must not be empty")
            if target != current and target in self.station_to_number:
                raise ValueError(f"Station '{target}' already exists")
        new_lines = _unique(lines) if lines is not None else list(self._declared.get(current, []))

        if target != current:
            for conn in self._connections:
                if conn["source"] == current:
                    conn["source"] = target
                if conn["dest"] == current:
                    conn["dest"] = target
            self._declared.pop(current, None)
        self._declared[target] = new_lines
        self._rebuild()

    def update_distance(self, a: str, b: str, distance: float) -> None:
        """Set the distance (meters) of the connection between two adjacent stations.

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: If the stations are not connected or the distance is invalid.
        """
        first = self.resolve_name(a)
        second = self.resolve_name(b)
        conn = self._find_connection(first, second)
        if conn is None:
            raise ValueError(f"Stations '{first}' and '{second}' are not directly connected")
        if not _is_valid_distance(distance):
            raise ValueError("Distance must be a positive number of meters")
        conn["distance"] = distance
        self._rebuild()

    def save(self, path: str) -> None:
        """Write the current network data to a JSON file in the dataset format."""
        data = {
            "stations": [
                {"name": name, "lines": list(self.graph.station_lines.get(name, []))}
                for name in self.number_to_name
            ],
            "connections": [dict(conn) for conn in self._connections],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ integrity

    def check_integrity(self) -> IntegrityReport:
        """Run data integrity checks: coverage, connections and distances."""
        report = IntegrityReport()

        # Coverage of main lines and representative stations.
        for line in MAIN_LINES:
            if not self.line_stations.get(line):
                report.warnings.append(f"Coverage: main line '{line}' has no stations in the data")
        for line, station in REPRESENTATIVE_STATIONS:
            if station not in self.station_to_number:
                report.warnings.append(f"Coverage: representative station '{station}' of {line} is missing")
            elif line not in self.station_lines_of(station):
                report.warnings.append(f"Coverage: station '{station}' is not registered on {line}")

        # Connection integrity and distance accuracy.
        seen_pairs: set[frozenset] = set()
        for conn in self._connections:
            a, b, line, distance = conn["source"], conn["dest"], conn["line"], conn["distance"]
            label = f"'{a}' <-> '{b}' ({line})"
            if a == b:
                report.errors.append(f"Connection: self-loop at '{a}'")
                continue
            if a not in self._declared or b not in self._declared:
                report.warnings.append(f"Connection: {label} references a station not declared in the station list")
            pair = frozenset((a, b))
            if pair in seen_pairs:
                report.warnings.append(f"Connection: duplicate connection between '{a}' and '{b}'")
            seen_pairs.add(pair)
            if not _is_valid_distance(distance):
                report.errors.append(f"Distance: {label} has invalid distance {distance!r}")
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M):
                report.warnings.append(
                    f"Distance: {label} distance {distance} m is outside the plausible range "
                    f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )

        # Connectivity of the graph.
        components = 0
        seen: set[int] = set()
        for vertex in self.graph.vertices():
            if vertex in seen:
                continue
            components += 1
            queue = deque([vertex])
            seen.add(vertex)
            while queue:
                current = queue.popleft()
                for edge in self.graph.adjacent(current):
                    if edge.dest not in seen:
                        seen.add(edge.dest)
                        queue.append(edge.dest)
            if not self.graph.adjacent(vertex):
                report.warnings.append(
                    f"Connectivity: station '{self.number_to_name[vertex]}' has no connections"
                )
        if components > 1:
            report.warnings.append(f"Connectivity: network splits into {components} disconnected parts")
        return report
