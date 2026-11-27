"""
Subway network modelling and data management.

Loads station and connection data, assigns station numbers, builds the
weighted undirected graph, and provides data maintenance operations
(adding lines, renaming stations, updating distances) and data integrity checks.
"""

import re
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Main lines expected to be covered by the dataset.
REQUIRED_MAIN_LINES = (
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

# Adjacent-station distances above this value are reported as suspicious.
LONG_DISTANCE_WARNING_METERS = 10000


def _clean(value):
    """Convert a raw value to a stripped string ('' for None)."""
    if value is None:
        return ""
    return str(value).strip()


def _as_distance(value):
    """Convert a raw distance value to a non-negative int, or None if invalid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value.is_integer() and value >= 0:
            return int(value)
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def normalize_station_name(name):
    """
    Normalize a station name for lenient matching.

    Removes whitespace, lowercases ASCII letters and strips a trailing '站'.
    """
    text = re.sub(r"\s+", "", _clean(name)).lower()
    if text.endswith("站") and len(text) > 1:
        text = text[:-1]
    return text


class IntegrityReport:
    """Result of a data integrity check."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    @property
    def is_ok(self):
        """True if no errors were found (warnings are allowed)."""
        return not self.errors

    def format(self):
        """Return a human-readable text representation of the report."""
        lines = ["Data integrity check report", "=" * 40]
        for item in self.info:
            lines.append(f"[INFO]    {item}")
        for item in self.warnings:
            lines.append(f"[WARNING] {item}")
        for item in self.errors:
            lines.append(f"[ERROR]   {item}")
        status = "PASSED" if self.is_ok else "FAILED"
        lines.append(
            f"Result: {status} ({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join(lines)


class SubwayNetwork:
    """
    In-memory model of the Beijing Subway network.

    Attributes:
        station_to_number: dict station name -> station number.
        number_to_station: list where index is station number and value is name.
        graph: Graph instance with station numbers as vertices.
    """

    def __init__(self, data=None, data_path=None):
        if data is None:
            data = load_subway_data(data_path if data_path else DATA_FILE_PATH)
        self._station_lines = {}   # station name -> list of lines (ordered)
        self._connections = []     # list of dicts: source, dest, distance, line
        self._load(data)
        self.station_to_number = {}
        self.number_to_station = []
        self.graph = Graph()
        self._normalized = {}
        self._lines = []
        self.rebuild()

    # ------------------------------------------------------------------
    # Loading and building
    # ------------------------------------------------------------------
    def _load(self, data):
        """Populate internal station and connection records from raw data."""
        for item in data.get("stations", []) or []:
            if not isinstance(item, dict):
                continue
            name = _clean(item.get("name"))
            if not name:
                continue
            lines = self._station_lines.setdefault(name, [])
            for raw_line in item.get("lines", []) or []:
                line = _clean(raw_line)
                if line and line not in lines:
                    lines.append(line)

        for conn in data.get("connections", []) or []:
            if not isinstance(conn, dict):
                continue
            self._connections.append({
                "source": _clean(conn.get("source")),
                "dest": _clean(conn.get("dest")),
                "distance": conn.get("distance"),
                "line": _clean(conn.get("line")),
            })

    def rebuild(self):
        """Rebuild station numbering, lookup tables and the graph from internal records."""
        self.station_to_number = {}
        self.number_to_station = []
        for name in self._station_lines:
            self.station_to_number[name] = len(self.number_to_station)
            self.number_to_station.append(name)

        self._normalized = {}
        for name in self.number_to_station:
            self._normalized.setdefault(normalize_station_name(name), name)

        self.graph = Graph()
        for name in self.number_to_station:
            number = self.station_to_number[name]
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, self._station_lines[name])

        seen_edges = set()
        for conn in self._connections:
            src, dst = conn["source"], conn["dest"]
            if src not in self.station_to_number or dst not in self.station_to_number:
                continue
            if src == dst:
                # Same-station entries represent transfers; lines are already recorded.
                continue
            distance = _as_distance(conn["distance"])
            if distance is None:
                continue
            a = self.station_to_number[src]
            b = self.station_to_number[dst]
            key = (min(a, b), max(a, b), conn["line"])
            if key in seen_edges:
                # Bidirectional duplicates describe the same undirected edge.
                continue
            seen_edges.add(key)
            self.graph.add_edge(Edge(a, b, distance, conn["line"]))

        lines = []
        for station_lines in self._station_lines.values():
            for line in station_lines:
                if line not in lines:
                    lines.append(line)
        for conn in self._connections:
            if conn["line"] and conn["line"] not in lines:
                lines.append(conn["line"])
        self._lines = lines

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_station_names(self):
        """Return all official station names in numbering order."""
        return list(self.number_to_station)

    def get_lines(self):
        """Return all line names known to the network."""
        return list(self._lines)

    def get_line_stations(self, line):
        """Return the names of stations served by ``line``."""
        return [name for name, lines in self._station_lines.items() if line in lines]

    def get_station_lines(self, name):
        """Return the lines serving a station (empty list if unknown)."""
        return list(self._station_lines.get(name, []))

    def station_exists(self, name):
        """Return True if the official station name exists."""
        return name in self.station_to_number

    def standardize_station_name(self, raw_name):
        """
        Map user input to the official station name.

        Returns:
            str or None: The official name, or None if no station matches.
        """
        text = _clean(raw_name)
        if not text:
            return None
        if text in self.station_to_number:
            return text
        return self._normalized.get(normalize_station_name(text))

    def number_of(self, name):
        """Return the station number for a station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def get_graph(self):
        """Return the underlying Graph instance."""
        return self.graph

    # ------------------------------------------------------------------
    # Data update operations
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """
        Add a new line made of consecutive stations.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line. Unknown
                stations are created; known stations gain the new line.
            distances: Distances in meters between consecutive stations
                (length must be len(station_names) - 1).

        Raises:
            ValueError: If the input is invalid.
        """
        line = _clean(line_name)
        if not line:
            raise ValueError("Line name must not be empty")
        if line in self._lines:
            raise ValueError(f"Line '{line}' already exists")
        stations = [_clean(name) for name in station_names]
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not name for name in stations):
            raise ValueError("Station names must not be empty")
        if len(set(stations)) != len(stations):
            raise ValueError("A line must not contain duplicate stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        parsed = []
        for value in distances:
            distance = _as_distance(value)
            if distance is None or distance <= 0:
                raise ValueError(f"Invalid distance value: {value!r}")
            parsed.append(distance)

        for name in stations:
            lines = self._station_lines.setdefault(name, [])
            if line not in lines:
                lines.append(line)
        for index, distance in enumerate(parsed):
            self._connections.append({
                "source": stations[index],
                "dest": stations[index + 1],
                "distance": distance,
                "line": line,
            })
        self.rebuild()

    def rename_station(self, old_name, new_name):
        """
        Rename a station and update all references to it.

        Raises:
            ValueError: If the old station does not exist or the new name is taken.
        """
        old = _clean(old_name)
        new = _clean(new_name)
        if old not in self._station_lines:
            raise ValueError(f"Station '{old}' does not exist")
        if not new:
            raise ValueError("New station name must not be empty")
        if new != old and new in self._station_lines:
            raise ValueError(f"Station '{new}' already exists")

        rebuilt = {}
        for name, lines in self._station_lines.items():
            rebuilt[new if name == old else name] = lines
        self._station_lines = rebuilt
        for conn in self._connections:
            if conn["source"] == old:
                conn["source"] = new
            if conn["dest"] == old:
                conn["dest"] = new
        self.rebuild()

    def set_station_lines(self, name, lines):
        """
        Replace the list of lines serving a station.

        Raises:
            ValueError: If the station does not exist.
        """
        station = _clean(name)
        if station not in self._station_lines:
            raise ValueError(f"Station '{station}' does not exist")
        unique = []
        for line in lines:
            text = _clean(line)
            if text and text not in unique:
                unique.append(text)
        self._station_lines[station] = unique
        self.rebuild()

    def update_distance(self, station_a, station_b, distance, line=None):
        """
        Update the distance between two adjacent stations.

        Args:
            station_a, station_b: Names of the adjacent stations.
            distance: New distance in meters (positive integer).
            line: Optionally restrict the update to connections of this line.

        Returns:
            int: Number of connection records updated.

        Raises:
            ValueError: If the distance is invalid or no connection matches.
        """
        a = _clean(station_a)
        b = _clean(station_b)
        value = _as_distance(distance)
        if value is None or value <= 0:
            raise ValueError(f"Invalid distance value: {distance!r}")
        target_line = _clean(line) if line else None
        count = 0
        for conn in self._connections:
            pair = {conn["source"], conn["dest"]}
            if pair != {a, b}:
                continue
            if target_line and conn["line"] != target_line:
                continue
            conn["distance"] = value
            count += 1
        if count == 0:
            raise ValueError(f"No connection found between '{a}' and '{b}'")
        self.rebuild()
        return count

    # ------------------------------------------------------------------
    # Data integrity
    # ------------------------------------------------------------------
    def check_data_integrity(self):
        """
        Run data integrity checks.

        Checks performed:
            * station data coverage (main lines present with stations)
            * connection integrity (known endpoints, lines, no self-loops)
            * distance accuracy (positive, plausible, consistent between directions)
            * isolated stations and network connectivity

        Returns:
            IntegrityReport
        """
        report = IntegrityReport()
        names = set(self._station_lines)
        lines_present = set(self._lines)

        if not names:
            report.errors.append("No stations are defined in the dataset")

        # Coverage checks
        for main_line in REQUIRED_MAIN_LINES:
            if main_line not in lines_present:
                report.warnings.append(f"Main line '{main_line}' is not covered by the dataset")
            elif len(self.get_line_stations(main_line)) < 2:
                report.warnings.append(f"Main line '{main_line}' has fewer than two stations")
        for name, lines in self._station_lines.items():
            if not lines:
                report.warnings.append(f"Station '{name}' is not assigned to any line")

        # Connection checks
        adjacency = {name: set() for name in names}
        seen = {}
        for index, conn in enumerate(self._connections, 1):
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            label = f"connection #{index} ({src} - {dst}, line '{line}')"
            if src not in names:
                report.errors.append(f"{label}: unknown source station '{src}'")
            if dst not in names:
                report.errors.append(f"{label}: unknown destination station '{dst}'")
            if not line:
                report.errors.append(f"{label}: missing line name")

            distance = _as_distance(conn["distance"])
            if distance is None:
                report.errors.append(f"{label}: invalid distance {conn['distance']!r}")
                continue
            if distance <= 0:
                report.errors.append(f"{label}: distance must be positive")
                continue
            if distance > LONG_DISTANCE_WARNING_METERS:
                report.warnings.append(
                    f"{label}: distance {distance} m is unusually long for adjacent stations"
                )
            if src == dst:
                report.warnings.append(f"{label}: same-station entry is ignored")
                continue
            if src not in names or dst not in names:
                continue

            if line and (line not in self._station_lines[src] or line not in self._station_lines[dst]):
                report.warnings.append(
                    f"{label}: line is not listed for both endpoint stations"
                )

            key = (min(src, dst), max(src, dst), line)
            if key in seen and seen[key] != distance:
                report.warnings.append(
                    f"{label}: conflicting distances {seen[key]} m and {distance} m"
                )
            seen.setdefault(key, distance)
            adjacency[src].add(dst)
            adjacency[dst].add(src)

        # Isolated stations and connectivity
        for name in sorted(names):
            if not adjacency[name]:
                report.warnings.append(f"Station '{name}' has no connections")

        visited = set()
        components = 0
        for start in sorted(names):
            if start in visited:
                continue
            components += 1
            queue = deque([start])
            visited.add(start)
            while queue:
                current = queue.popleft()
                for neighbour in adjacency[current]:
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)
        if components > 1:
            report.warnings.append(
                f"Network is split into {components} disconnected components"
            )

        report.info.append(
            f"Stations: {len(names)}, lines: {len(lines_present)}, "
            f"connection records: {len(self._connections)}"
        )
        return report
