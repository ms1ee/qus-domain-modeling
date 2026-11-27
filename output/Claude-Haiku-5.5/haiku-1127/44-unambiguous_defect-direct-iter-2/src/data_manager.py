"""Subway network construction, data management and integrity checking."""

import copy
import re
from collections import deque

from data_loader import DATA_FILE_PATH, save_subway_data
from models import Edge, Graph

# Lines that must be covered by the dataset (Section 4.1 of the PRD).
REQUIRED_LINES = (
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

# Representative stations of the main lines; missing ones are reported as warnings.
REPRESENTATIVE_STATIONS = (
    "Pingguoyuan",
    "Xizhimen",
    "Dongzhimen",
    "Tiananmen East",
    "Fuxingmen",
    "Yonghegong",
    "Sihui",
    "Guomao",
)

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000
MAX_LISTED_UNREACHABLE = 20


class NetworkError(Exception):
    """Raised when the network cannot be built or a data update is invalid."""


def _clean(value):
    """Return a stripped non-empty string, or None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _unique(values):
    return list(dict.fromkeys(values))


def _normalize_station(name):
    """Normalize a station name for lenient matching (case, spaces, '站' suffix)."""
    text = re.sub(r"[\s\-_·]+", "", str(name)).lower()
    if text.endswith("站"):
        text = text[:-1]
    return text


def _normalize_line(name):
    return re.sub(r"\s+", " ", str(name).strip()).lower()


class SubwayNetwork:
    """The subway network model used by the query system.

    Holds the raw dataset (which can be updated), the weighted undirected graph,
    and name lookup indexes.
    """

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.graph = None
        self.line_stations = {}
        self._station_index = {}
        self._line_index = {}
        self._build()

    # ----- construction -----------------------------------------------------

    def _build(self):
        stations = self.data.get("stations")
        connections = self.data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise NetworkError("subway data must contain 'stations' and 'connections' lists")

        lines_of = {}
        order = []
        for entry in stations:
            name = _clean(entry.get("name")) if isinstance(entry, dict) else None
            if name is None:
                raise NetworkError("station entry without a valid name")
            if name in lines_of:
                raise NetworkError(f"duplicate station name '{name}'")
            raw_lines = entry.get("lines", [])
            if not isinstance(raw_lines, list):
                raise NetworkError(f"lines of station '{name}' must be a list")
            lines_of[name] = _unique(l for l in (_clean(x) for x in raw_lines) if l)
            order.append(name)

        parsed = []
        for conn in connections:
            if not isinstance(conn, dict):
                raise NetworkError("connection entry must be an object")
            line = _clean(conn.get("line"))
            source = _clean(conn.get("source"))
            dest = _clean(conn.get("dest"))
            if line is None or source is None or dest is None:
                raise NetworkError("connection entry needs non-empty source, dest and line")
            for name in (source, dest):
                if name not in lines_of:
                    lines_of[name] = []
                    order.append(name)
                if line not in lines_of[name]:
                    lines_of[name].append(line)
            parsed.append((source, dest, conn.get("distance"), line))

        graph = Graph()
        for number, name in enumerate(order):
            graph.register_station(name, number)
            graph.set_station_lines(name, lines_of[name])
        for source, dest, distance, line in parsed:
            try:
                edge = Edge(
                    graph.station_to_number[source],
                    graph.station_to_number[dest],
                    distance,
                    line,
                )
                graph.add_edge(edge)
            except (TypeError, ValueError) as exc:
                raise NetworkError(
                    f"invalid connection {source} - {dest} on {line}: {exc}"
                ) from exc

        self.graph = graph
        self.line_stations = {}
        for name in order:
            for line in lines_of[name]:
                self.line_stations.setdefault(line, []).append(name)

        self._station_index = {}
        for name in order:
            self._station_index.setdefault(_normalize_station(name), name)
        self._line_index = {}
        for line in self.line_stations:
            self._line_index.setdefault(_normalize_line(line), line)

    # ----- lookups ----------------------------------------------------------

    def station_names(self):
        """All station names in the network, sorted."""
        return sorted(self.graph.station_to_number)

    def standardize_station(self, text):
        """Map user input to the official station name, or None if unknown."""
        cleaned = _clean(text)
        if cleaned is None:
            return None
        return self._station_index.get(_normalize_station(cleaned))

    def standardize_line(self, text):
        """Map user input to the official line name, or None if unknown."""
        cleaned = _clean(text)
        if cleaned is None:
            return None
        return self._line_index.get(_normalize_line(cleaned))

    def number_of(self, name):
        try:
            return self.graph.station_to_number[name]
        except KeyError as exc:
            raise NetworkError(f"unknown station '{name}'") from exc

    def name_of(self, number):
        try:
            return self.graph.number_to_station[number]
        except KeyError as exc:
            raise NetworkError(f"unknown station number {number}") from exc

    def lines_of(self, name):
        return self.graph.get_station_lines(name)

    def all_lines(self):
        return sorted(self.line_stations)

    def line_station_names(self, line):
        return list(self.line_stations.get(line, []))

    # ----- data updates -----------------------------------------------------

    def add_line(self, line_name, station_names, distances):
        """Add a new line through an ordered list of stations.

        Unknown stations are created; known stations gain the new line.

        Args:
            line_name: name of the new line.
            station_names: ordered list of station names along the line.
            distances: distances in meters between consecutive stations
                (length must be len(station_names) - 1).
        """
        line = _clean(line_name)
        if line is None:
            raise NetworkError("line name cannot be empty")
        if self.standardize_line(line) is not None:
            raise NetworkError(f"line '{line}' already exists")

        names = []
        for raw in station_names:
            name = _clean(raw)
            if name is None:
                raise NetworkError("station names on a line cannot be empty")
            names.append(self.standardize_station(name) or name)
        if len(names) < 2:
            raise NetworkError("a new line needs at least two stations")
        if len(set(names)) != len(names):
            raise NetworkError("a line cannot visit the same station twice")
        if len(distances) != len(names) - 1:
            raise NetworkError("one distance is required between each pair of consecutive stations")
        clean_distances = []
        for value in distances:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise NetworkError("distances must be positive numbers of meters")
            clean_distances.append(int(value))

        by_name = {entry["name"]: entry for entry in self.data["stations"]}
        for name in names:
            if name not in by_name:
                entry = {"name": name, "lines": []}
                self.data["stations"].append(entry)
                by_name[name] = entry
            if line not in by_name[name]["lines"]:
                by_name[name]["lines"].append(line)
        for a, b, distance in zip(names, names[1:], clean_distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": distance, "line": line}
            )
        self._build()

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its list of lines."""
        current = self.standardize_station(name)
        if current is None:
            raise NetworkError(f"unknown station '{name}'")

        entry = next(
            (e for e in self.data["stations"] if e.get("name") == current), None
        )
        if entry is None:
            entry = {"name": current, "lines": []}
            self.data["stations"].append(entry)

        if new_name is not None:
            target = _clean(new_name)
            if target is None:
                raise NetworkError("new station name cannot be empty")
            if target != current and self.standardize_station(target) is not None:
                raise NetworkError(f"station '{target}' already exists")
            entry["name"] = target
            for conn in self.data["connections"]:
                if conn.get("source") == current:
                    conn["source"] = target
                if conn.get("dest") == current:
                    conn["dest"] = target

        if lines is not None:
            cleaned = _unique(l for l in (_clean(x) for x in lines) if l)
            entry["lines"] = cleaned
        self._build()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations."""
        a = self.standardize_station(source)
        b = self.standardize_station(dest)
        if a is None or b is None:
            raise NetworkError("both stations must exist to update a distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise NetworkError("distance must be a positive number of meters")
        official_line = None
        if line is not None:
            official_line = self.standardize_line(line)
            if official_line is None:
                raise NetworkError(f"unknown line '{line}'")

        matches = [
            conn
            for conn in self.data["connections"]
            if {conn.get("source"), conn.get("dest")} == {a, b}
            and (official_line is None or conn.get("line") == official_line)
        ]
        if not matches:
            raise NetworkError(f"no connection between '{a}' and '{b}' found")
        for conn in matches:
            conn["distance"] = int(distance)
        self._build()

    def to_dict(self):
        """Return a copy of the current dataset."""
        return copy.deepcopy(self.data)

    def save(self, path=DATA_FILE_PATH):
        """Persist the current dataset to a JSON file."""
        save_subway_data(self.data, path)


class IntegrityReport:
    """Result of a data integrity check."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    @property
    def ok(self):
        return not self.errors

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def format(self):
        lines = ["Data integrity check"]
        if self.stats:
            lines.append(
                f"Stations: {self.stats.get('stations', 0)}, "
                f"connections: {self.stats.get('connections', 0)}, "
                f"lines: {self.stats.get('lines', 0)}"
            )
        lines.append(f"Errors: {len(self.errors)}")
        for message in self.errors:
            lines.append(f"  [ERROR] {message}")
        lines.append(f"Warnings: {len(self.warnings)}")
        for message in self.warnings:
            lines.append(f"  [WARN] {message}")
        lines.append("Result: PASSED" if self.ok else "Result: FAILED")
        return "\n".join(lines)


def check_data_integrity(data):
    """Check the raw subway dataset for coverage, connection and distance problems.

    Checks performed:
        - Coverage: required main lines exist; representative stations exist.
        - Connections: endpoints exist, no self-loops or duplicates, lines are
          listed by their endpoint stations, network is connected.
        - Distances: positive integers, with a plausibility range as warning.

    Returns:
        IntegrityReport with errors (failures) and warnings (suspicious data).
    """
    report = IntegrityReport()
    if not isinstance(data, dict):
        report.error("dataset must be a JSON object")
        return report
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list) or not isinstance(connections, list):
        report.error("dataset must contain 'stations' and 'connections' lists")
        return report

    station_lines = {}
    for index, entry in enumerate(stations):
        name = _clean(entry.get("name")) if isinstance(entry, dict) else None
        if name is None:
            report.error(f"station entry #{index} has no valid name")
            continue
        if name in station_lines:
            report.error(f"duplicate station '{name}'")
            continue
        raw_lines = entry.get("lines", [])
        if not isinstance(raw_lines, list):
            report.error(f"lines of station '{name}' must be a list")
            raw_lines = []
        station_lines[name] = {
            str(item).strip() for item in raw_lines if str(item).strip()
        }
        if not station_lines[name]:
            report.warn(f"station '{name}' is not assigned to any line")

    all_lines = set()
    for lines in station_lines.values():
        all_lines |= lines
    for conn in connections:
        if isinstance(conn, dict) and _clean(conn.get("line")):
            all_lines.add(_clean(conn.get("line")))

    report.stats = {
        "stations": len(station_lines),
        "connections": len(connections),
        "lines": len(all_lines),
    }

    # Coverage checks.
    for line in REQUIRED_LINES:
        if line not in all_lines:
            report.error(f"coverage: required line '{line}' has no stations or connections")
    normalized_names = {_normalize_station(name) for name in station_lines}
    for station in REPRESENTATIVE_STATIONS:
        if _normalize_station(station) not in normalized_names:
            report.warn(f"coverage: representative station '{station}' is not in the dataset")

    # Connection and distance checks.
    seen = set()
    adjacency = {name: set() for name in station_lines}
    for index, conn in enumerate(connections):
        label = f"connection #{index}"
        if not isinstance(conn, dict):
            report.error(f"{label} is not an object")
            continue
        source = _clean(conn.get("source"))
        dest = _clean(conn.get("dest"))
        line = _clean(conn.get("line"))
        distance = conn.get("distance")
        if source is None or dest is None or line is None:
            report.error(f"{label} is missing source, dest or line")
            continue
        label = f"{label} ({source} - {dest}, {line})"

        if source == dest:
            report.error(f"{label}: a station cannot connect to itself")
            continue

        endpoints_ok = True
        for endpoint in (source, dest):
            if endpoint not in station_lines:
                report.error(f"{label}: station '{endpoint}' is not in the station list")
                endpoints_ok = False
        if endpoints_ok:
            for endpoint in (source, dest):
                if line not in station_lines[endpoint]:
                    report.warn(
                        f"{label}: station '{endpoint}' does not list line '{line}'"
                    )
            adjacency[source].add(dest)
            adjacency[dest].add(source)

        key = (frozenset((source, dest)), line)
        if key in seen:
            report.error(f"{label}: duplicate connection")
        seen.add(key)

        if isinstance(distance, bool) or not isinstance(distance, int):
            report.error(f"{label}: distance must be an integer number of meters")
        elif distance <= 0:
            report.error(f"{label}: distance must be positive")
        elif not MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M:
            report.warn(
                f"{label}: distance {distance} m is outside the plausible range "
                f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
            )

    # Connectivity check.
    if station_lines:
        start = next(iter(station_lines))
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        unreachable = sorted(name for name in station_lines if name not in visited)
        for name in unreachable[:MAX_LISTED_UNREACHABLE]:
            report.error(f"connectivity: station '{name}' is not connected to the network")
        if len(unreachable) > MAX_LISTED_UNREACHABLE:
            report.error(
                f"connectivity: {len(unreachable) - MAX_LISTED_UNREACHABLE} more "
                "stations are not connected to the network"
            )
    return report
