"""Subway network model: station registry, line index, data updates and integrity checks."""

import difflib
import re
import unicodedata
from collections import deque

from models import Edge, Graph

# Representative main lines that must be covered by the station data.
EXPECTED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range for a single inter-station distance (meters), used for accuracy checks.
MIN_REASONABLE_DISTANCE_M = 50
MAX_REASONABLE_DISTANCE_M = 10000


def normalize_name(name):
    """Normalize a station or line name for lookup (NFKC, no whitespace, case-insensitive)."""
    text = unicodedata.normalize("NFKC", str(name))
    text = re.sub(r"\s+", "", text)
    return text.casefold()


class SubwayNetwork:
    """Beijing Subway network built from the subway_data.json structure.

    Attributes:
        graph: Graph instance (adjacency lists keyed by station number).
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        line_stations: dict line name -> list of station names served by the line.
        load_warnings: list of messages produced while loading the data.
    """

    def __init__(self, data=None):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.line_stations = {}
        self.load_warnings = []
        self._normalized_index = {}  # normalized name -> canonical name
        self._next_number = 0
        if data is not None:
            self.load_data(data)

    # ------------------------------------------------------------------ loading
    def load_data(self, data):
        """Populate the network from a dict with 'stations' and 'connections' lists."""
        for station in data.get("stations", []):
            if not isinstance(station, dict) or not station.get("name"):
                self.load_warnings.append(f"Skipped station entry without a name: {station!r}")
                continue
            try:
                self.add_station(station["name"], station.get("lines", []))
            except ValueError as exc:
                self.load_warnings.append(f"Skipped station {station!r}: {exc}")

        for conn in data.get("connections", []):
            try:
                source = conn["source"]
                dest = conn["dest"]
                line = conn["line"]
                distance = conn["distance"]
            except (KeyError, TypeError) as exc:
                self.load_warnings.append(f"Skipped malformed connection {conn!r}: missing {exc}")
                continue
            # Connections referencing unknown stations get the station registered with a warning.
            for name in (source, dest):
                if name not in self.station_to_number:
                    self.load_warnings.append(
                        f"Station '{name}' referenced by a connection is missing from 'stations'; added automatically")
                    self.add_station(name, [line])
            try:
                self.add_connection(source, dest, distance, line)
            except ValueError as exc:
                self.load_warnings.append(f"Skipped connection {source} - {dest} ({line}): {exc}")

    # ------------------------------------------------------------- basic access
    def add_station(self, name, lines=()):
        """Register a station (or merge lines into an existing one). Returns its number."""
        name = str(name).strip()
        if not name:
            raise ValueError("Station name cannot be empty")
        lines = [str(line) for line in lines]

        if name in self.station_to_number:
            number = self.station_to_number[name]
            merged = list(self.graph.get_station_lines(name))
            for line in lines:
                if line not in merged:
                    merged.append(line)
            self.graph.set_station_lines(name, merged)
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.set_station_lines(name, lines)
            self.graph.add_vertex(number)
            self._normalized_index.setdefault(normalize_name(name), name)

        for line in self.graph.get_station_lines(name):
            self._register_line(line, name)
        return number

    def add_connection(self, source, dest, distance, line):
        """Add a connection between two existing stations. Returns the created Edge."""
        if source not in self.station_to_number:
            raise ValueError(f"Unknown station '{source}'")
        if dest not in self.station_to_number:
            raise ValueError(f"Unknown station '{dest}'")
        if source == dest:
            raise ValueError("A station cannot be connected to itself")
        distance = self._validate_distance(distance)
        line = str(line)

        a = self.station_to_number[source]
        b = self.station_to_number[dest]
        edge = Edge(a, b, distance, line)
        self.graph.add_edge(edge)
        self._register_line(line, source)
        self._register_line(line, dest)
        return edge

    def get_station_number(self, name):
        """Return the number of a station by its exact canonical name."""
        if name not in self.station_to_number:
            raise ValueError(f"Unknown station '{name}'")
        return self.station_to_number[name]

    def station_name(self, number):
        """Return the canonical name of a station number."""
        return self.number_to_station[number]

    def all_station_names(self):
        """Sorted list of all station names."""
        return sorted(self.station_to_number.keys())

    def all_lines(self):
        """Sorted list of all line names known to the network."""
        lines = set(self.line_stations.keys())
        for name in self.station_to_number:
            lines.update(self.graph.get_station_lines(name))
        return sorted(lines)

    def find_station(self, raw_name):
        """Resolve a user-typed name to the canonical station name, or None if unknown."""
        if raw_name in self.station_to_number:
            return raw_name
        return self._normalized_index.get(normalize_name(raw_name))

    def suggest_stations(self, raw_name, count=3):
        """Return up to `count` canonical station names similar to `raw_name`."""
        keys = list(self._normalized_index.keys())
        matches = difflib.get_close_matches(normalize_name(raw_name), keys, n=count, cutoff=0.5)
        return [self._normalized_index[key] for key in matches]

    # ------------------------------------------------------------ data updates
    def add_line(self, line_name, station_names, distances):
        """Add a new line through the given ordered stations.

        Args:
            line_name: name of the new line (must not already exist).
            station_names: ordered list of station names (>= 2). Unknown names are created.
            distances: list of positive int distances (meters), one per consecutive pair.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if line_name in self.all_lines():
            raise ValueError(f"Line '{line_name}' already exists")
        station_names = [str(name).strip() for name in station_names]
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Expected one distance per consecutive station pair")
        if len(set(station_names)) != len(station_names):
            raise ValueError("Station names on a line must be unique")
        distances = [self._validate_distance(d) for d in distances]

        for name in station_names:
            self.add_station(name, [line_name])
        for i, distance in enumerate(distances):
            self.add_connection(station_names[i], station_names[i + 1], distance, line_name)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its list of lines."""
        if old_name not in self.station_to_number:
            raise ValueError(f"Unknown station '{old_name}'")
        number = self.station_to_number[old_name]
        current = old_name

        if new_name is not None and new_name != old_name:
            new_name = str(new_name).strip()
            if not new_name:
                raise ValueError("New station name cannot be empty")
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            del self.station_to_number[old_name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            self.graph.station_lines[new_name] = self.graph.station_lines.pop(old_name)
            if self._normalized_index.get(normalize_name(old_name)) == old_name:
                del self._normalized_index[normalize_name(old_name)]
            self._normalized_index.setdefault(normalize_name(new_name), new_name)
            current = new_name

        if lines is not None:
            self.graph.set_station_lines(current, lines)

        self._rebuild_line_index()

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two directly connected stations.

        Returns the number of connections updated. Raises ValueError if none exist.
        """
        if name_a not in self.station_to_number or name_b not in self.station_to_number:
            raise ValueError("Both stations must exist")
        distance = self._validate_distance(distance)
        a = self.station_to_number[name_a]
        b = self.station_to_number[name_b]
        updated = 0
        for edge in self.graph.neighbors(a):
            if edge.other(a) == b and (line is None or edge.line == line):
                edge.distance = distance
                updated += 1
        if updated == 0:
            raise ValueError(f"No connection between '{name_a}' and '{name_b}'")
        return updated

    # --------------------------------------------------------------- integrity
    def check_integrity(self):
        """Run data integrity checks.

        Returns:
            list of (level, message) tuples where level is 'ERROR', 'WARNING' or 'INFO'.
        """
        issues = []

        def add(level, message):
            issues.append((level, message))

        for warning in self.load_warnings:
            add("WARNING", warning)

        if not self.station_to_number:
            add("ERROR", "No stations loaded")

        all_lines = self.all_lines()
        normalized_lines = {normalize_name(line) for line in all_lines}
        for line in EXPECTED_LINES:
            if normalize_name(line) not in normalized_lines:
                add("WARNING", f"Representative main line '{line}' is not covered by the station data")

        edges = self.graph.edges()
        add("INFO", f"Loaded {len(self.station_to_number)} stations, {len(edges)} connections, "
                    f"{len(all_lines)} lines")

        for name in self.all_station_names():
            number = self.station_to_number[name]
            if not self.graph.get_station_lines(name):
                add("WARNING", f"Station '{name}' has no line information")
            if not self.graph.neighbors(number):
                add("WARNING", f"Station '{name}' has no connections")

        seen_pairs = set()
        for edge in edges:
            a = self.number_to_station[edge.source]
            b = self.number_to_station[edge.dest]
            label = f"{a} - {b} ({edge.line})"

            if not isinstance(edge.weight, (int, float)) or edge.weight <= 0:
                add("ERROR", f"Connection {label} has invalid distance {edge.weight!r}")
            elif not (MIN_REASONABLE_DISTANCE_M <= edge.weight <= MAX_REASONABLE_DISTANCE_M):
                add("WARNING", f"Connection {label} distance {edge.weight} m is outside the "
                               f"expected range {MIN_REASONABLE_DISTANCE_M}-{MAX_REASONABLE_DISTANCE_M} m")

            for name in (a, b):
                if edge.line not in self.graph.get_station_lines(name):
                    add("WARNING", f"Connection {label}: station '{name}' does not list line '{edge.line}'")

            key = (frozenset((a, b)), edge.line)
            if key in seen_pairs:
                add("WARNING", f"Duplicate connection {label}")
            seen_pairs.add(key)

        if self.number_to_station:
            start = next(iter(self.number_to_station))
            visited = {start}
            queue = deque([start])
            while queue:
                vertex = queue.popleft()
                for edge in self.graph.neighbors(vertex):
                    nxt = edge.other(vertex)
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            unreachable = [self.number_to_station[n] for n in self.number_to_station if n not in visited]
            if unreachable:
                preview = ", ".join(unreachable[:5])
                add("ERROR", f"{len(unreachable)} station(s) are not connected to the network: {preview}")

        if not any(level in ("ERROR", "WARNING") for level, _ in issues):
            add("INFO", "All integrity checks passed")
        return issues

    # ----------------------------------------------------------------- helpers
    def _register_line(self, line, station_name):
        stations = self.line_stations.setdefault(line, [])
        if station_name not in stations:
            stations.append(station_name)

    def _rebuild_line_index(self):
        self.line_stations = {}
        for name in self.station_to_number:
            for line in self.graph.get_station_lines(name):
                self._register_line(line, name)
        for edge in self.graph.edges():
            self._register_line(edge.line, self.number_to_station[edge.source])
            self._register_line(edge.line, self.number_to_station[edge.dest])

    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool):
            raise ValueError("Distance must be a number of meters")
        try:
            value = float(distance)
        except (TypeError, ValueError):
            raise ValueError(f"Distance must be a number of meters, got {distance!r}")
        if value <= 0 or value != value or value == float("inf"):
            raise ValueError("Distance must be a positive finite number of meters")
        return int(value) if value.is_integer() else value
