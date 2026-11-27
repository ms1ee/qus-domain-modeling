"""Subway network modelling, station/line management and data integrity checks."""

import difflib

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from models import DataIntegrityReport, Edge, Graph, Station

# Main lines that must be represented in the network.
EXPECTED_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

# Representative stations used for coverage checks.
REPRESENTATIVE_STATIONS = ("Xizhimen", "Dongzhimen", "Tiananmen East", "Sihui")

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000
NAME_MATCH_CUTOFF = 0.6


def clean_name(value) -> str:
    """Normalise a station or line name (trim and collapse whitespace)."""
    if value is None:
        raise ValueError("name must not be empty")
    text = " ".join(str(value).split())
    if not text:
        raise ValueError("name must not be empty")
    return text


def parse_distance(value) -> int:
    """Convert a distance value to a non-negative integer number of meters."""
    if isinstance(value, bool):
        raise ValueError(f"invalid distance: {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid distance: {value!r}") from exc
    if number != number or number < 0:
        raise ValueError(f"distance must be a non-negative number: {value!r}")
    return int(round(number))


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    Responsibilities:
        * build the weighted directed graph from the dataset,
        * map station names to numeric station numbers,
        * resolve user-supplied names (exact, case-insensitive, or nearest match),
        * manage stations, lines and distances,
        * run data integrity checks.
    """

    def __init__(self, data=None, data_path=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(data_path)
            self.data_source = str(data_path)
        else:
            self.data_source = "in-memory"

        self.network_id = "beijing-subway"
        self.version = str(data.get("version", "1.0")) if isinstance(data, dict) else "1.0"

        self.station_to_number = {}   # station name -> number
        self.number_to_station = {}   # number -> station name
        self.lines = {}               # line name -> list of station names
        self.graph = Graph()

        self._name_index = {}         # lower-case name -> canonical name
        self._next_number = 0
        self._build(data)

    # ------------------------------------------------------------------ build
    def _build(self, data):
        """Populate stations, lines and edges from the raw dataset."""
        try:
            for entry in data.get("stations", []):
                name = clean_name(entry["name"])
                lines = [clean_name(line) for line in entry.get("lines", [])]
                self._register_station(name, lines)

            for conn in data.get("connections", []):
                src_name = clean_name(conn["source"])
                dst_name = clean_name(conn["dest"])
                line = clean_name(conn["line"])
                distance = parse_distance(conn["distance"])
                src = self._register_station(src_name, [line])
                dst = self._register_station(dst_name, [line])
                self.graph.add_edge(Edge(src, dst, distance, line))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataLoadError(f"malformed subway data: {exc}") from exc

    def _register_station(self, name, lines):
        """Create a station if needed, attach the given lines, and return its number."""
        if name not in self.station_to_number:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self._name_index[name.lower()] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
        for line in lines:
            self._attach_line(name, line)
        return self.station_to_number[name]

    def _attach_line(self, name, line):
        """Record that a station is served by a line (idempotent)."""
        station_lines = self.graph.station_lines[name]
        if line not in station_lines:
            station_lines.append(line)
        stations = self.lines.setdefault(line, [])
        if name not in stations:
            stations.append(name)

    # ---------------------------------------------------------------- lookup
    def station_number(self, name) -> int:
        """Return the number of an exactly named station."""
        if name not in self.station_to_number:
            raise KeyError(f"unknown station: {name}")
        return self.station_to_number[name]

    def station_name(self, number) -> str:
        """Return the name of a station number."""
        return self.number_to_station[number]

    def get_station(self, name) -> Station:
        """Return a Station object for an exactly named station."""
        number = self.station_number(name)
        return Station(number, name, list(self.graph.station_lines[name]))

    def station_lines(self, name):
        """Return the lines serving a station (exact name)."""
        return list(self.graph.station_lines[self.station_number(name) and name])

    def is_transfer_station(self, name) -> bool:
        """Return True if the station is served by two or more lines."""
        return len(self.graph.station_lines.get(name, [])) >= 2

    def transfer_stations(self):
        """Return sorted names of all transfer stations."""
        return sorted(n for n, lines in self.graph.station_lines.items() if len(lines) >= 2)

    def line_names(self):
        """Return sorted names of all lines."""
        return sorted(self.lines)

    def resolve_station(self, query):
        """Resolve a user-supplied station name.

        Returns:
            (canonical_name, exact_match) where canonical_name is None if no
            plausible station matches. Non-exact matches are the nearest name.
        """
        cleaned = " ".join(str(query or "").split())
        if not cleaned:
            return None, False
        if cleaned in self.station_to_number:
            return cleaned, True
        key = cleaned.lower()
        if key in self._name_index:
            return self._name_index[key], True
        matches = difflib.get_close_matches(
            key, list(self._name_index.keys()), n=1, cutoff=NAME_MATCH_CUTOFF)
        if matches:
            return self._name_index[matches[0]], False
        return None, False

    def resolve_line_name(self, query):
        """Resolve a line name such as 'Line 1', '1' or 'line 1'. Returns None if unknown."""
        cleaned = " ".join(str(query or "").split())
        if not cleaned:
            return None
        if cleaned.isdigit():
            cleaned = f"Line {int(cleaned)}"
        lookup = {name.lower(): name for name in self.lines}
        return lookup.get(cleaned.lower())

    # ------------------------------------------------------------ updates
    def add_line(self, line_name, station_names, distances_m, bidirectional=True):
        """Add a new line through an ordered list of stations.

        Args:
            line_name: Name of the new line (must not exist yet).
            station_names: Ordered station names; unknown stations are created.
            distances_m: Distances in meters between consecutive stations.
            bidirectional: If True, add connections in both directions.

        Raises:
            ValueError: On duplicate line, too few stations, or bad distances.
        """
        line = clean_name(line_name)
        if line in self.lines:
            raise ValueError(f"line already exists: {line}")
        names = [clean_name(n) for n in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances_m) != len(names) - 1:
            raise ValueError("number of distances must equal number of stations minus one")
        distances = []
        for value in distances_m:
            distance = parse_distance(value)
            if distance <= 0:
                raise ValueError("distances must be positive")
            distances.append(distance)

        numbers = [self._register_station(n, [line]) for n in names]
        for i, distance in enumerate(distances):
            a, b = numbers[i], numbers[i + 1]
            self.graph.add_edge(Edge(a, b, distance, line))
            if bidirectional:
                self.graph.add_edge(Edge(b, a, distance, line))

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its served lines.

        Args:
            name: Existing station name (exact).
            new_name: Optional new name.
            lines: Optional replacement list of lines.
        """
        number = self.station_number(name)
        if lines is not None:
            new_lines = [clean_name(l) for l in lines]
            old_lines = list(self.graph.station_lines[name])
            for line in old_lines:
                if line not in new_lines and line in self.lines:
                    self.lines[line] = [s for s in self.lines[line] if s != name]
                    if not self.lines[line]:
                        del self.lines[line]
            self.graph.station_lines[name] = []
            for line in new_lines:
                self._attach_line(name, line)

        if new_name is not None:
            target = clean_name(new_name)
            if target != name:
                if target in self.station_to_number:
                    raise ValueError(f"station already exists: {target}")
                self.station_to_number[target] = self.station_to_number.pop(name)
                self.number_to_station[number] = target
                self._name_index.pop(name.lower(), None)
                self._name_index[target.lower()] = target
                self.graph.station_lines[target] = self.graph.station_lines.pop(name)
                for line in self.lines:
                    self.lines[line] = [target if s == name else s for s in self.lines[line]]

    def update_distance(self, source, dest, distance, both_directions=False) -> int:
        """Update the distance between two stations on their connection(s).

        Returns:
            Number of edges updated.

        Raises:
            KeyError: If no connection exists between the stations.
        """
        src = self.station_number(source)
        dst = self.station_number(dest)
        value = parse_distance(distance)
        if value <= 0:
            raise ValueError("distance must be positive")
        updated = 0
        for edge in self.graph.get_edges(src, dst):
            edge.distance = value
            updated += 1
        if both_directions:
            for edge in self.graph.get_edges(dst, src):
                edge.distance = value
                updated += 1
        if updated == 0:
            raise KeyError(f"no connection between {source} and {dest}")
        return updated

    # --------------------------------------------------------- integrity
    def check_integrity(self, expected_lines=EXPECTED_LINES,
                        representative_stations=REPRESENTATIVE_STATIONS) -> DataIntegrityReport:
        """Run data integrity checks (coverage, connections, distance accuracy)."""
        errors = []
        warnings = []

        # Station data coverage.
        for line in expected_lines:
            stations = self.lines.get(line, [])
            if not stations:
                warnings.append(f"Main line '{line}' has no stations in the data")
            elif len(stations) < 2:
                warnings.append(f"Main line '{line}' has fewer than two stations")
        for name in representative_stations:
            if name not in self.station_to_number:
                warnings.append(f"Representative station '{name}' is missing")

        # Connection integrity and distance accuracy.
        pairs = set()
        seen_keys = set()
        has_in = set()
        has_out = set()
        for edge in self.graph.edges():
            src_name = self.station_name(edge.source)
            dst_name = self.station_name(edge.dest)
            pairs.add((edge.source, edge.dest))
            has_out.add(edge.source)
            has_in.add(edge.dest)

            if edge.distance <= 0:
                errors.append(f"Non-positive distance {edge.distance} m on {src_name} -> {dst_name} ({edge.line})")
            elif edge.distance < MIN_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"Suspiciously short distance {edge.distance} m on {src_name} -> {dst_name}")
            elif edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"Suspiciously long distance {edge.distance} m on {src_name} -> {dst_name}")

            key = (edge.source, edge.dest, edge.line)
            if key in seen_keys:
                warnings.append(f"Duplicate connection {src_name} -> {dst_name} on {edge.line}")
            seen_keys.add(key)

            if edge.line not in self.graph.station_lines.get(src_name, []) or \
                    edge.line not in self.graph.station_lines.get(dst_name, []):
                warnings.append(f"Connection {src_name} -> {dst_name} line '{edge.line}' not served by both stations")

        for src, dst in pairs:
            if (dst, src) not in pairs:
                warnings.append(
                    f"No reverse connection {self.station_name(dst)} -> {self.station_name(src)}")

        for number in self.graph.vertices():
            if number not in has_in and number not in has_out:
                warnings.append(f"Station '{self.station_name(number)}' has no connections")

        return DataIntegrityReport(is_valid=not errors, errors=errors, warnings=warnings)
