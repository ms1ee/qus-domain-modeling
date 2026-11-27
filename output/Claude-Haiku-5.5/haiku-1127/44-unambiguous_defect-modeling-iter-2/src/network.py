"""Subway network model: stations, lines, connections and data management.

``SubwayNetwork`` owns the ``Graph`` and the name/number mappings. Station
numbers are assigned here (the caller of ``Graph``), in the order stations are
first registered. The class also offers name standardisation and the data
update operations required by the PRD (adding lines, modifying stations and
updating distances).
"""

import re
import unicodedata

try:
    from .models import Graph, Edge
    from .data_loader import load_subway_data, DATA_FILE_PATH
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from models import Graph, Edge
    from data_loader import load_subway_data, DATA_FILE_PATH


class NetworkError(Exception):
    """Base class for network model errors."""


class StationNotFoundError(NetworkError):
    """Raised when a station name cannot be resolved."""


class LineNotFoundError(NetworkError):
    """Raised when a line name cannot be resolved."""


class DuplicateConnectionError(NetworkError):
    """Raised when a connection already exists between two stations on a line."""


_STATION_NOISE_RE = re.compile(r"[\s_\-·•'’\.]+")
_LINE_NOISE_RE = re.compile(r"[\s_\-]+")


def normalize_station_name(text):
    """Return a canonical lookup key for a station name.

    The key ignores case, whitespace, punctuation, Unicode width and the
    optional "station"/"站" suffix, so "Xizhimen", "xizhimen station" and
    "西直门站" can be matched against the same official name.
    """
    value = unicodedata.normalize("NFKC", str(text)).strip().lower()
    value = _STATION_NOISE_RE.sub("", value)
    for suffix in ("station", "站"):
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
            break
    return value


def normalize_line_name(text):
    """Return a canonical lookup key for a line name.

    "Line 1", "1号线", "line1" and "1" all map to the key ``"1"``;
    "Changping Line" and "昌平线" both map to ``"changping"``.
    """
    value = unicodedata.normalize("NFKC", str(text)).strip().lower()
    value = _LINE_NOISE_RE.sub("", value)
    for token in ("line", "号线", "线"):
        value = value.replace(token, "")
    return value


class SubwayNetwork:
    """Beijing Subway network model.

    Attributes:
        name: Human readable network name.
        data_source: Path or description of the data source.
        version: Dataset version string.
        graph: The weighted undirected ``Graph``.
        station_to_number: Mapping of official station name to station number.
        number_to_name: Mapping of station number to official station name.
        line_names: Ordered list of official line names.
        line_stations: Mapping of line name to the list of station names it serves.
        load_warnings: Messages produced while loading inconsistent data.
    """

    def __init__(self, name="Beijing Subway", data_source=DATA_FILE_PATH, version="1.0"):
        self.name = name
        self.data_source = str(data_source)
        self.version = version
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = {}
        self.line_names = []
        self.line_stations = {}
        self.load_warnings = []
        self._station_index = {}
        self._line_index = {}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Build a network from the JSON dataset file."""
        data = load_subway_data(path)
        network = cls(data_source=str(path))
        network.load_data(data)
        return network

    def load_data(self, data):
        """Populate the network from a dataset dictionary."""
        for item in data.get("stations", []):
            self.add_station(item["name"], item.get("lines", []))
        for conn in data.get("connections", []):
            try:
                self.add_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])
            except NetworkError as exc:
                self.load_warnings.append(str(exc))

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------
    def _register_line(self, line):
        """Register a line name and return its canonical spelling."""
        name = str(line).strip()
        if not name:
            raise ValueError("Line name cannot be empty")
        key = normalize_line_name(name)
        if key in self._line_index:
            return self._line_index[key]
        self._line_index[key] = name
        self.line_names.append(name)
        self.line_stations.setdefault(name, [])
        return name

    def add_station(self, name, lines=()):
        """Add a station (if new) and merge the given lines into its line list.

        Returns:
            str: The canonical station name.
        """
        canonical = str(name).strip()
        if not canonical:
            raise ValueError("Station name cannot be empty")
        if canonical not in self.station_to_number:
            number = len(self.number_to_name)
            self.station_to_number[canonical] = number
            self.number_to_name[number] = canonical
            self.graph.add_vertex(number)
            self._station_index[normalize_station_name(canonical)] = canonical

        merged = self.graph.get_station_lines(canonical)
        for line in lines:
            line_name = self._register_line(line)
            if line_name not in merged:
                merged.append(line_name)
        self.graph.set_station_lines(canonical, merged)
        for line_name in merged:
            members = self.line_stations.setdefault(line_name, [])
            if canonical not in members:
                members.append(canonical)
        return canonical

    def add_connection(self, source, dest, distance, line):
        """Add a direct connection between two adjacent stations on a line.

        Returns:
            Edge: The created edge.

        Raises:
            DuplicateConnectionError: If the same connection already exists.
        """
        line_name = self._register_line(line)
        src = self.add_station(source, [line_name])
        dst = self.add_station(dest, [line_name])
        a = self.station_to_number[src]
        b = self.station_to_number[dst]
        if self.graph.find_edge(a, b, line_name) is not None:
            raise DuplicateConnectionError(
                f"Duplicate connection between '{src}' and '{dst}' on {line_name}"
            )
        edge = Edge(a, b, distance, line_name)
        self.graph.add_edge(edge)
        return edge

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def resolve_station(self, text):
        """Return the official station name matching user input.

        Raises:
            StationNotFoundError: If no station matches.
        """
        raw = str(text).strip()
        if raw in self.station_to_number:
            return raw
        key = normalize_station_name(raw)
        if key and key in self._station_index:
            return self._station_index[key]
        raise StationNotFoundError(f"Station '{raw}' does not exist")

    def resolve_line(self, text):
        """Return the official line name matching user input.

        Raises:
            LineNotFoundError: If no line matches.
        """
        raw = str(text).strip()
        key = normalize_line_name(raw)
        if key and key in self._line_index:
            return self._line_index[key]
        raise LineNotFoundError(f"Line '{raw}' does not exist")

    def number_of(self, name):
        """Return the station number of a station name (resolved leniently)."""
        return self.station_to_number[self.resolve_station(name)]

    def name_of(self, number):
        """Return the official station name for a station number."""
        return self.number_to_name[number]

    def lines_of(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(self.resolve_station(name))

    def is_transfer_station(self, name):
        """Return True if more than one line serves the station."""
        return len(self.lines_of(name)) > 1

    def stations(self):
        """Return all official station names."""
        return list(self.station_to_number)

    # ------------------------------------------------------------------
    # Data update operations
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line from an ordered list of stations and inter-station distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names (at least two).
            distances: Distances in meters between consecutive stations.

        Raises:
            NetworkError: If the line already exists.
            ValueError: If the inputs are inconsistent.
        """
        if normalize_line_name(line_name) in self._line_index:
            raise NetworkError(f"Line '{line_name}' already exists")
        names = [str(s).strip() for s in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        line = self._register_line(line_name)
        for index in range(len(names) - 1):
            self.add_connection(names[index], names[index + 1], distances[index], line)
        return line

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace the lines serving it.

        Returns:
            str: The (possibly new) official station name.
        """
        old = self.resolve_station(name)
        number = self.station_to_number[old]
        target = old
        if new_name is not None and str(new_name).strip() and str(new_name).strip() != old:
            new = str(new_name).strip()
            if new in self.station_to_number or normalize_station_name(new) in self._station_index:
                raise NetworkError(f"Station '{new}' already exists")
            del self.station_to_number[old]
            self.station_to_number[new] = number
            self.number_to_name[number] = new
            self._station_index.pop(normalize_station_name(old), None)
            self._station_index[normalize_station_name(new)] = new
            self.graph.station_lines[new] = self.graph.station_lines.pop(old, [])
            target = new
            self._rebuild_line_stations()
        if lines is not None:
            unique = []
            for line in lines:
                line_name = self._register_line(line)
                if line_name not in unique:
                    unique.append(line_name)
            self.graph.set_station_lines(target, unique)
            self._rebuild_line_stations()
        return target

    def update_distance(self, a, b, distance, line=None):
        """Update the distance of an existing connection.

        Raises:
            NetworkError: If no matching connection exists.
        """
        na = self.number_of(a)
        nb = self.number_of(b)
        line_name = self.resolve_line(line) if line else None
        edge = self.graph.find_edge(na, nb, line_name)
        if edge is None:
            raise NetworkError(f"No connection between '{a}' and '{b}'")
        edge.set_distance(distance)
        return edge

    def _rebuild_line_stations(self):
        """Recompute ``line_stations`` from the station-to-line mapping."""
        self.line_stations = {line: [] for line in self.line_names}
        for name in self.station_to_number:
            for line in self.graph.get_station_lines(name):
                self.line_stations.setdefault(line, []).append(name)

    def to_data(self):
        """Export the network to the dataset dictionary format."""
        stations = [
            {"name": name, "lines": self.graph.get_station_lines(name)}
            for name in self.station_to_number
        ]
        connections = [
            {
                "source": self.name_of(edge.source),
                "dest": self.name_of(edge.dest),
                "distance": edge.distance,
                "line": edge.line,
            }
            for edge in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}
