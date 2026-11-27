"""Subway network data management: modelling, integrity checks and updates."""

from data_loader import DATA_FILE_PATH, load_subway_data
from errors import DataLoadError, DataUpdateError, StationNotFoundError
from models import Edge, Graph

# Main lines that the dataset is expected to cover (PRD section 4.1).
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range for distances between adjacent stations (meters).
MIN_REASONABLE_DISTANCE_M = 100
MAX_REASONABLE_DISTANCE_M = 10000


def _normalize_key(name):
    """Build a lookup key: case-insensitive, whitespace-insensitive, without trailing '站'."""
    text = "".join(str(name).split()).casefold()
    if len(text) > 1 and text.endswith("站"):
        text = text[:-1]
    return text


def _validate_distance(value):
    """Validate a distance in meters and return it as a positive int."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataUpdateError("Distance must be a number of meters")
    if value != value or value <= 0:
        raise DataUpdateError("Distance must be a positive number of meters")
    return int(round(value))


class IntegrityReport:
    """Result of a data integrity check."""

    def __init__(self, station_count=0, connection_count=0, line_count=0):
        self.errors = []
        self.warnings = []
        self.station_count = station_count
        self.connection_count = connection_count
        self.line_count = line_count

    @property
    def is_ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def render(self):
        """Return a human-readable text summary of the report."""
        lines = [
            "Data integrity check",
            f"Stations: {self.station_count}, connections: {self.connection_count}, lines: {self.line_count}",
        ]
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            lines.extend(f"  - {msg}" for msg in self.errors)
        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            lines.extend(f"  - {msg}" for msg in self.warnings)
        if not self.errors and not self.warnings:
            lines.append("No issues found.")
        lines.append("Result: PASS" if self.is_ok else "Result: FAIL")
        return "\n".join(lines)


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    Station numbers are assigned here (index in ``number_to_station``) and used
    as vertices of ``self.graph``.

    Attributes:
        graph: Graph instance (weighted undirected).
        station_to_number: dict station name -> station number.
        number_to_station: list station name, indexed by station number.
    """

    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = []
        self._line_order = []
        self._line_stations = {}
        self._name_index = {}
        self._build_issues = []
        self._build(data)

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Create a network from the subway JSON file."""
        return cls(load_subway_data(path))

    # ----- construction ---------------------------------------------------
    def _build(self, data):
        for entry in data.get("stations", []):
            if not isinstance(entry, dict):
                raise DataLoadError(f"Malformed station entry: {entry!r}")
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                raise DataLoadError(f"Station entry without a valid name: {entry!r}")
            name = " ".join(name.split())
            lines = [" ".join(str(line).split()) for line in (entry.get("lines") or []) if str(line).strip()]
            if name in self.station_to_number:
                self._build_issues.append(("error", f"duplicate station name '{name}'"))
                self.graph.set_station_lines(name, self.graph.get_station_lines(name) + lines)
            else:
                self._create_station(name, lines)

        for conn in data.get("connections", []):
            if not isinstance(conn, dict):
                self._build_issues.append(("error", f"malformed connection entry: {conn!r}"))
                continue
            src, dst, line = conn.get("source"), conn.get("dest"), conn.get("line")
            distance = conn.get("distance")
            if not all(isinstance(x, str) and x.strip() for x in (src, dst, line)):
                self._build_issues.append(("error", f"incomplete connection entry: {conn!r}"))
                continue
            src = " ".join(src.split())
            dst = " ".join(dst.split())
            line = " ".join(line.split())
            if src == dst:
                self._build_issues.append(("error", f"connection from '{src}' to itself on {line}"))
                continue
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                self._build_issues.append(("error", f"non-numeric distance for {src} -> {dst}"))
                continue
            if not isinstance(distance, int):
                self._build_issues.append(("warning", f"non-integer distance {distance} for {src} -> {dst} was rounded"))
                distance = int(round(distance))
            for name in (src, dst):
                if name not in self.station_to_number:
                    self._build_issues.append(("error", f"connection references unknown station '{name}'"))
                    self._create_station(name, [line])
            self.graph.add_edge(Edge(self.station_to_number[src], self.station_to_number[dst], distance, line))
            self._register_line_station(line, src)
            self._register_line_station(line, dst)

    def _create_station(self, name, lines):
        number = len(self.number_to_station)
        self.station_to_number[name] = number
        self.number_to_station.append(name)
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, lines)
        self._name_index.setdefault(_normalize_key(name), name)
        return number

    def _register_line_station(self, line, station):
        if line not in self._line_stations:
            self._line_stations[line] = []
            self._line_order.append(line)
        if station not in self._line_stations[line]:
            self._line_stations[line].append(station)

    def _rebuild_name_index(self):
        self._name_index = {}
        for name in self.number_to_station:
            self._name_index.setdefault(_normalize_key(name), name)

    # ----- queries --------------------------------------------------------
    def station_count(self):
        """Return the number of stations."""
        return len(self.number_to_station)

    def station_names(self):
        """Return all station names ordered by station number."""
        return list(self.number_to_station)

    def has_station(self, name):
        """Return True if the exact official name exists."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number of an official station name.

        Raises:
            StationNotFoundError: If the name is not an official station name.
        """
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def standardize_station_name(self, raw):
        """Map user input to an official station name.

        Matching ignores surrounding/internal whitespace, letter case and a
        trailing '站'. Returns None if no official station matches.
        """
        if not isinstance(raw, str):
            return None
        cleaned = " ".join(raw.split())
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        return self._name_index.get(_normalize_key(cleaned))

    def line_names(self):
        """Return the names of all lines in the dataset."""
        return list(self._line_order)

    def resolve_line_name(self, raw):
        """Return the canonical line name for user input, or None if unknown."""
        cleaned = " ".join(str(raw).split())
        for line in self._line_order:
            if line == cleaned:
                return line
        for line in self._line_order:
            if line.casefold() == cleaned.casefold():
                return line
        return None

    def stations_on_line(self, line):
        """Return the ordered station names of a line."""
        return list(self._line_stations.get(line, []))

    def station_lines(self, name):
        """Return the line affiliation of a station."""
        return self.graph.get_station_lines(name)

    def transfer_stations(self):
        """Return names of interchange stations (stations on more than one line)."""
        return [name for name in self.number_to_station
                if len(set(self.graph.get_station_lines(name))) > 1]

    # ----- data updates ---------------------------------------------------
    def add_station(self, name, lines):
        """Add a new station that belongs to the given lines.

        Returns:
            int: The new station number.
        """
        cleaned = " ".join(str(name).split())
        if not cleaned:
            raise DataUpdateError("Station name must not be empty")
        if self.standardize_station_name(cleaned) is not None:
            raise DataUpdateError(f"Station '{cleaned}' already exists")
        cleaned_lines = [" ".join(str(line).split()) for line in lines if str(line).strip()]
        if not cleaned_lines:
            raise DataUpdateError("A station must belong to at least one line")
        return self._create_station(cleaned, cleaned_lines)

    def add_line(self, line_name, segments):
        """Add a new line described by consecutive station segments.

        Args:
            line_name: Name of the new line.
            segments: Iterable of (station_a, station_b, distance_m) tuples.
                Unknown stations are created; known stations join the new line.

        Returns:
            int: Number of connections added.
        """
        line = " ".join(str(line_name).split())
        if not line:
            raise DataUpdateError("Line name must not be empty")
        if self.resolve_line_name(line) is not None:
            raise DataUpdateError(f"Line '{line}' already exists")
        prepared = []
        for segment in segments:
            try:
                a, b, distance = segment
            except (TypeError, ValueError) as exc:
                raise DataUpdateError("Each segment must be (station_a, station_b, distance)") from exc
            if not isinstance(a, str) or not isinstance(b, str):
                raise DataUpdateError("Segment station names must be strings")
            a = " ".join(a.split())
            b = " ".join(b.split())
            if not a or not b or a == b:
                raise DataUpdateError(f"Invalid segment between '{a}' and '{b}'")
            prepared.append((a, b, _validate_distance(distance)))
        if not prepared:
            raise DataUpdateError("A new line needs at least one segment")

        for a, b, distance in prepared:
            names = []
            for raw_name in (a, b):
                official = self.standardize_station_name(raw_name)
                if official is None:
                    official = raw_name
                    self._create_station(official, [line])
                else:
                    current = self.graph.get_station_lines(official)
                    if line not in current:
                        self.graph.set_station_lines(official, current + [line])
                names.append(official)
            left, right = names
            self.graph.add_edge(Edge(self.station_to_number[left], self.station_to_number[right], distance, line))
            self._register_line_station(line, left)
            self._register_line_station(line, right)
        return len(prepared)

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line affiliation.

        Returns:
            str: The (possibly new) official name of the station.
        """
        official = self.standardize_station_name(name)
        if official is None:
            raise DataUpdateError(f"Station '{name}' does not exist")
        number = self.station_to_number[official]

        if new_name is not None:
            cleaned = " ".join(str(new_name).split())
            if not cleaned:
                raise DataUpdateError("New station name must not be empty")
            if cleaned != official and self.has_station(cleaned):
                raise DataUpdateError(f"Station '{cleaned}' already exists")
            old_lines = self.graph.get_station_lines(official)
            self.graph.station_lines.pop(official, None)
            del self.station_to_number[official]
            self.station_to_number[cleaned] = number
            self.number_to_station[number] = cleaned
            self.graph.set_station_lines(cleaned, old_lines)
            for line in list(self._line_stations.keys()):
                self._line_stations[line] = [cleaned if s == official else s
                                             for s in self._line_stations[line]]
            self._rebuild_name_index()
            official = cleaned

        if lines is not None:
            cleaned_lines = [" ".join(str(line).split()) for line in lines if str(line).strip()]
            if not cleaned_lines:
                raise DataUpdateError("A station must belong to at least one line")
            self.graph.set_station_lines(official, cleaned_lines)
        return official

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Returns:
            int: Number of connections updated.
        """
        a = self.standardize_station_name(station_a)
        b = self.standardize_station_name(station_b)
        if a is None or b is None:
            raise DataUpdateError("Both stations must exist before updating a distance")
        value = _validate_distance(distance)
        canonical_line = None
        if line is not None:
            canonical_line = self.resolve_line_name(line)
            if canonical_line is None:
                raise DataUpdateError(f"Line '{line}' does not exist")
        na, nb = self.station_to_number[a], self.station_to_number[b]
        updated = 0
        for edge in self.graph.adj(na):
            if edge.connects(na, nb) and (canonical_line is None or edge.line == canonical_line):
                edge.distance = value
                updated += 1
        if updated == 0:
            raise DataUpdateError(f"No connection exists between '{a}' and '{b}'")
        return updated

    # ----- integrity ------------------------------------------------------
    def check_data_integrity(self):
        """Run data integrity checks and return an IntegrityReport."""
        report = IntegrityReport(
            station_count=self.station_count(),
            connection_count=self.graph.edge_count(),
            line_count=len(self._line_order),
        )

        for level, message in self._build_issues:
            (report.errors if level == "error" else report.warnings).append(message)

        # Coverage of main lines.
        present = set(self._line_order)
        for line in MAIN_LINES:
            if line not in present:
                report.warnings.append(f"Main line '{line}' is not covered by the dataset")
            elif len(self._line_stations.get(line, [])) < 2:
                report.errors.append(f"Main line '{line}' has fewer than two stations")

        # Station data and line affiliation consistency.
        for number, name in enumerate(self.number_to_station):
            lines = self.graph.get_station_lines(name)
            if not lines:
                report.errors.append(f"Station '{name}' has no line affiliation")
            edge_lines = {edge.line for edge in self.graph.adj(number)}
            if not edge_lines:
                report.warnings.append(f"Station '{name}' has no connections")
            for line in lines:
                if line not in edge_lines:
                    report.warnings.append(f"Station '{name}' is listed on '{line}' but has no connection on that line")

        # Connection accuracy and consistency.
        seen = {}
        for edge in self.graph.edges():
            a = self.name_of(edge.source)
            b = self.name_of(edge.dest)
            label = f"{a} - {b} ({edge.line})"
            if isinstance(edge.distance, bool) or not isinstance(edge.distance, int):
                report.errors.append(f"Distance of {label} is not an integer number of meters")
            elif edge.distance <= 0:
                report.errors.append(f"Distance of {label} must be positive")
            elif edge.distance < MIN_REASONABLE_DISTANCE_M:
                report.warnings.append(f"Distance of {label} is unusually short ({edge.distance} m)")
            elif edge.distance > MAX_REASONABLE_DISTANCE_M:
                report.warnings.append(f"Distance of {label} is unusually long ({edge.distance} m)")
            for name in (a, b):
                if edge.line not in self.graph.get_station_lines(name):
                    report.warnings.append(f"Connection {label} uses line not listed for station '{name}'")
            key = (frozenset((a, b)), edge.line)
            if key in seen and seen[key] != edge.distance:
                report.errors.append(
                    f"Inconsistent distances for {label}: {seen[key]} m and {edge.distance} m")
            seen.setdefault(key, edge.distance)

        # Connectivity of the whole network.
        if self.station_count():
            visited = {0}
            stack = [0]
            while stack:
                vertex = stack.pop()
                for edge in self.graph.adj(vertex):
                    nxt = edge.other(vertex)
                    if nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
            unreachable = [self.name_of(n) for n in range(self.station_count()) if n not in visited]
            if unreachable:
                report.warnings.append(f"{len(unreachable)} station(s) not connected to the main network: "
                                       + ", ".join(unreachable[:10]))
        return report
