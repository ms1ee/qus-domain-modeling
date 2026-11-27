"""Subway network model: station mapping, graph construction and data management.

The network is built from the dictionary returned by
``data_loader.load_subway_data``. Station numbers are assigned here, in the
order in which stations are first encountered, and are used as vertices of
the ``Graph``.
"""

from .data_loader import load_subway_data
from .models import Edge, Graph

# Main lines that must be covered by the dataset (used by the coverage check).
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
MIN_STATIONS_PER_LINE = 2
# Adjacent stations in Beijing Subway are rarely more than a few kilometers apart.
MAX_REASONABLE_DISTANCE_M = 5000


class StationNotFoundError(Exception):
    """Raised when a station name does not match any official station."""


def _normalize_key(name):
    """Normalise a station name for lenient matching (case and spaces ignored)."""
    return "".join(name.split()).casefold()


def _clean(value):
    """Return a stripped string, or an empty string for non-string values."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _parse_distance(value):
    """Convert a distance value from the dataset to a positive-or-zero integer."""
    if isinstance(value, bool):
        raise ValueError(f"invalid distance {value!r}")
    try:
        return int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid distance {value!r}") from exc


class SubwayNetwork:
    """Subway network with station mapping, weighted graph and line data.

    Attributes:
        station_to_number: dict mapping station name -> station number.
        number_to_station: list mapping station number -> station name.
        graph: ``Graph`` instance holding the adjacency lists.
        line_stations: dict mapping line name -> ordered list of station names.
    """

    def __init__(self, data=None):
        """Build the network.

        Args:
            data: Parsed dataset dict. If None, ``subway_data.json`` is loaded.
        """
        if data is None:
            data = load_subway_data()
        self.station_to_number = {}
        self.number_to_station = []
        self.graph = Graph()
        self.line_stations = {}
        self.load(data)

    # ----------------------------------------------------------------- loading
    def load(self, data):
        """(Re)build the network from a dataset dict.

        Raises:
            ValueError: If the dataset contains malformed station or connection data.
        """
        self.station_to_number = {}
        self.number_to_station = []
        self.graph = Graph()
        self.line_stations = {}

        for item in data.get("stations", []):
            name = _clean(item.get("name"))
            if not name:
                raise ValueError("station entry without a valid name")
            lines = [_clean(line) for line in item.get("lines", []) if _clean(line)]
            self._add_station(name, lines)

        for conn in data.get("connections", []):
            source = _clean(conn.get("source"))
            dest = _clean(conn.get("dest"))
            line = _clean(conn.get("line"))
            if not source or not dest or not line:
                raise ValueError(f"connection with missing fields: {conn!r}")
            distance = _parse_distance(conn.get("distance"))
            src_num = self._ensure_station(source)
            dst_num = self._ensure_station(dest)
            self.graph.add_edge(Edge(src_num, dst_num, distance, line))
            self._register_line(line, [source, dest])

        # Make sure every declared station-line affiliation appears in line_stations.
        for name in self.number_to_station:
            for line in self.graph.station_lines.get(name, []):
                self._register_line(line, [name])

    def _ensure_station(self, name):
        """Return the number of ``name``, creating the station if needed."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_station)
        self.station_to_number[name] = number
        self.number_to_station.append(name)
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, [])
        return number

    def _add_station(self, name, lines=()):
        """Create a station if needed and merge the given lines into its affiliation."""
        number = self._ensure_station(name)
        if lines:
            existing = self.graph.station_lines.get(name, [])
            self.graph.set_station_lines(name, existing + list(lines))
        return number

    def _register_line(self, line, names):
        """Record that ``names`` are served by ``line`` (keeps insertion order)."""
        stations = self.line_stations.setdefault(line, [])
        for name in names:
            if name not in stations:
                stations.append(name)

    # ---------------------------------------------------------------- queries
    def has_station(self, name):
        """Return True if an exact station name exists in the network."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for an exact station name.

        Raises:
            StationNotFoundError: If the station does not exist.
        """
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise StationNotFoundError(name) from exc

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all official station names, sorted alphabetically."""
        return sorted(self.station_to_number)

    def lines(self):
        """Return all line names, sorted alphabetically."""
        return sorted(self.line_stations)

    def get_lines(self, name):
        """Return the line names serving a station."""
        return list(self.graph.station_lines.get(self.standardize(name), []))

    def standardize(self, name):
        """Map a user-entered station name to the official station name.

        Matching ignores surrounding whitespace, inner spaces, and letter case.

        Raises:
            StationNotFoundError: If no unique official station matches.
        """
        if not isinstance(name, str) or not name.strip():
            raise StationNotFoundError(str(name))
        cleaned = name.strip()
        if cleaned in self.station_to_number:
            return cleaned
        key = _normalize_key(cleaned)
        matches = [official for official in self.station_to_number if _normalize_key(official) == key]
        if len(matches) == 1:
            return matches[0]
        raise StationNotFoundError(cleaned)

    # ------------------------------------------------------------ data update
    def add_line(self, line_name, station_names, distances):
        """Add a new line as a chain of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered list of station names on the line. Unknown
                stations are created.
            distances: Distances in meters between consecutive stations
                (length ``len(station_names) - 1``).

        Raises:
            ValueError: If the input is inconsistent.
        """
        line = _clean(line_name)
        if not line:
            raise ValueError("line name must not be empty")
        if line in self.line_stations:
            raise ValueError(f"line '{line}' already exists")
        names = [_clean(name) for name in station_names]
        if len(names) < 2 or any(not name for name in names):
            raise ValueError("a line needs at least two valid station names")
        if len(set(names)) != len(names):
            raise ValueError("a station may appear only once per line")
        if len(distances) != len(names) - 1:
            raise ValueError("distances must contain one value per pair of consecutive stations")
        parsed = [_parse_distance(value) for value in distances]
        if any(value <= 0 for value in parsed):
            raise ValueError("distances must be positive")

        numbers = [self._ensure_station(name) for name in names]
        for name in names:
            existing = self.graph.station_lines.get(name, [])
            self.graph.set_station_lines(name, existing + [line])
        for index, distance in enumerate(parsed):
            self.graph.add_edge(Edge(numbers[index], numbers[index + 1], distance, line))
        self._register_line(line, names)
        return len(names)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or change its line affiliation.

        Args:
            old_name: Current official station name.
            new_name: New name, or None to keep the current one.
            lines: New list of line names, or None to keep the current lines.

        Returns:
            str: The station name after modification.

        Raises:
            StationNotFoundError: If ``old_name`` does not exist.
            ValueError: If ``new_name`` is already used by another station.
        """
        old = self.standardize(old_name)
        number = self.station_to_number[old]
        new = new_name.strip() if new_name and new_name.strip() else old
        if new != old and new in self.station_to_number:
            raise ValueError(f"station '{new}' already exists")

        if new != old:
            del self.station_to_number[old]
            self.station_to_number[new] = number
            self.number_to_station[number] = new
            self.graph.station_lines[new] = self.graph.station_lines.pop(old, [])
            for line in list(self.line_stations):
                self.line_stations[line] = [new if name == old else name
                                            for name in self.line_stations[line]]

        if lines is not None:
            new_lines = list(dict.fromkeys(_clean(line) for line in lines if _clean(line)))
            self.graph.set_station_lines(new, new_lines)
            for line in list(self.line_stations):
                names = self.line_stations[line]
                if line not in new_lines and new in names:
                    self.line_stations[line] = [name for name in names if name != new]
            for line in new_lines:
                self._register_line(line, [new])
        return new

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two directly connected stations.

        Args:
            name_a: First station name.
            name_b: Second station name.
            distance: New distance in meters (positive integer).
            line: If given, only update connections on this line.

        Returns:
            int: Number of directed edges updated (2 for a normal connection).

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: If the distance is invalid or no connection exists.
        """
        a = self.standardize(name_a)
        b = self.standardize(name_b)
        value = _parse_distance(distance)
        if value <= 0:
            raise ValueError("distance must be positive")
        na = self.station_to_number[a]
        nb = self.station_to_number[b]
        changed = 0
        for edge in self.graph.adj(na):
            if edge.dest == nb and (line is None or edge.line == line):
                edge.distance = value
                changed += 1
        for edge in self.graph.adj(nb):
            if edge.dest == na and (line is None or edge.line == line):
                edge.distance = value
                changed += 1
        if changed == 0:
            raise ValueError(f"no connection between '{a}' and '{b}'")
        return changed

    # --------------------------------------------------------- integrity check
    def check_integrity(self):
        """Run data integrity checks.

        Checks performed:
            * Coverage: every required main line has stations in the dataset.
            * Stations: every station has line information and connections.
            * Connectivity: the network is a single connected component.
            * Connections: edges are symmetric, lines agree with station
              affiliations, and distances are positive and plausible.

        Returns:
            list[str]: Human-readable issue descriptions (empty if all checks pass).
        """
        issues = []

        def add(message):
            if message not in issues:
                issues.append(message)

        # Coverage of main lines.
        for line in REQUIRED_LINES:
            count = len(self.line_stations.get(line, []))
            if count < MIN_STATIONS_PER_LINE:
                add(f"Coverage: main line '{line}' is missing or has fewer than "
                    f"{MIN_STATIONS_PER_LINE} stations (found {count})")

        # Station-level checks.
        for name in self.number_to_station:
            number = self.station_to_number[name]
            if not self.graph.station_lines.get(name):
                add(f"Station data: station '{name}' has no line information")
            if not self.graph.adj(number):
                add(f"Connectivity: station '{name}' has no connections")

        # Connection-level checks.
        for number in self.graph.vertices():
            source_name = self.number_to_station[number]
            for edge in self.graph.adj(number):
                dest_name = self.number_to_station[edge.dest]
                if edge.distance <= 0:
                    add(f"Accuracy: connection '{source_name}'-'{dest_name}' has non-positive distance {edge.distance}")
                elif edge.distance > MAX_REASONABLE_DISTANCE_M:
                    add(f"Accuracy: connection '{source_name}'-'{dest_name}' on '{edge.line}' has "
                        f"suspicious distance {edge.distance} m")
                reverse = [back for back in self.graph.adj(edge.dest)
                           if back.dest == number and back.line == edge.line
                           and back.distance == edge.distance]
                if not reverse:
                    add(f"Connection integrity: connection '{source_name}'-'{dest_name}' "
                        f"is not bidirectional")
                for endpoint in (source_name, dest_name):
                    if edge.line not in self.graph.station_lines.get(endpoint, []):
                        add(f"Consistency: station '{endpoint}' is connected on '{edge.line}' "
                            f"but does not list that line")

        # Connectivity: count connected components.
        visited = set()
        components = 0
        for number in self.graph.vertices():
            if number in visited:
                continue
            components += 1
            stack = [number]
            visited.add(number)
            while stack:
                current = stack.pop()
                for edge in self.graph.adj(current):
                    if edge.dest not in visited:
                        visited.add(edge.dest)
                        stack.append(edge.dest)
        if components > 1:
            add(f"Connectivity: the network consists of {components} disconnected components")

        return issues
