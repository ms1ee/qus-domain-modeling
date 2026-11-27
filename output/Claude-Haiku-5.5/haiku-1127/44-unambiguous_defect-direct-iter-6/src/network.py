"""Subway network management.

``SubwayNetwork`` wraps the graph model and owns the mapping between official
station names and integer station numbers. It also supports data updates:
adding lines, modifying stations, and updating distances.
"""

import re

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

_SPACE_RE = re.compile(r"\s+")
_SEPARATOR_CHARS_RE = re.compile(r"[\s\-'\u2019\u00b7]")


def _clean(text):
    """Collapse whitespace and strip a station or line name."""
    if not isinstance(text, str):
        raise TypeError("Names must be strings")
    return _SPACE_RE.sub(" ", text).strip()


def _normalize_key(text):
    """Build a lookup key that ignores case, spacing, punctuation and suffixes."""
    key = _SEPARATOR_CHARS_RE.sub("", text.casefold())
    if key.endswith("station"):
        key = key[:-len("station")]
    if key.endswith("\u7ad9"):  # Chinese suffix for "station"
        key = key[:-1]
    return key


class SubwayNetwork:
    """Subway network model built from the dataset.

    Attributes:
        graph: The weighted undirected ``Graph`` of the network.
        station_to_number: Mapping from official station name to station number.
        number_to_station: Mapping from station number to station name.
    """

    def __init__(self, data=None, path=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(path)
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._build(data)

    # ----- construction ------------------------------------------------------

    def _build(self, data):
        """Populate the network from a dataset dictionary."""
        for item in data.get("stations", []):
            name = self._register_station(item["name"])
            current = self.graph.station_lines[name]
            for line in item.get("lines", []):
                line = _clean(str(line))
                if line and line not in current:
                    current.append(line)

        for conn in data.get("connections", []):
            source = self._register_station(conn["source"])
            dest = self._register_station(conn["dest"])
            line = _clean(str(conn["line"]))
            distance = int(conn["distance"])
            self.graph.add_edge(Edge(self.station_to_number[source],
                                     self.station_to_number[dest],
                                     distance, line))

    def _register_station(self, name):
        """Register a station if unknown and return its cleaned name."""
        clean = _clean(name)
        if not clean:
            raise ValueError("Station name cannot be empty")
        if clean not in self.station_to_number:
            number = max(self.number_to_station, default=0) + 1
            self.station_to_number[clean] = number
            self.number_to_station[number] = clean
            self.graph.add_vertex(number)
            self.graph.set_station_lines(clean, [])
        return clean

    # ----- queries -----------------------------------------------------------

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def has_station(self, name):
        """Return True if the exact station name exists."""
        return _clean(name) in self.station_to_number

    def standardize_station_name(self, name):
        """Map user input to the official station name.

        Returns:
            The official name, or None if no station matches.
        """
        clean = _clean(name)
        if clean in self.station_to_number:
            return clean
        key = _normalize_key(clean)
        if not key:
            return None
        for candidate in self.station_to_number:
            if _normalize_key(candidate) == key:
                return candidate
        return None

    def number_of(self, name):
        """Return the station number of an official station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return the line names a station belongs to."""
        return list(self.graph.station_lines.get(name, []))

    def all_lines(self):
        """Return every line name present in the network, sorted."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines)

    def stations_on_line(self, line):
        """Return the names of stations served by a line, sorted by name."""
        numbers = set()
        for edge in self.graph.edges():
            if edge.line == line:
                numbers.add(edge.source)
                numbers.add(edge.dest)
        return sorted(self.number_to_station[n] for n in numbers)

    # ----- updates -----------------------------------------------------------

    def _require_station(self, name):
        canonical = self.standardize_station_name(name)
        if canonical is None:
            raise ValueError(f"Station '{name}' does not exist")
        return canonical

    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError("Distance must be a number of meters")
        if distance <= 0:
            raise ValueError("Distance must be a positive number of meters")

    def add_connection(self, source, dest, distance, line):
        """Add a connection between two existing stations on a line."""
        src = self._require_station(source)
        dst = self._require_station(dest)
        if src == dst:
            raise ValueError("A station cannot connect to itself")
        line = _clean(line)
        if not line:
            raise ValueError("Line name cannot be empty")
        self._validate_distance(distance)
        self.graph.add_edge(Edge(self.number_of(src), self.number_of(dst),
                                 int(round(distance)), line))

    def add_line(self, line, station_names, distances):
        """Add a new line through an ordered list of stations.

        Args:
            line: New line name.
            station_names: Ordered station names along the line. Unknown
                stations are created.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the line already exists or the input is invalid.
        """
        line = _clean(line)
        if not line:
            raise ValueError("Line name cannot be empty")
        if line in self.all_lines():
            raise ValueError(f"Line '{line}' already exists")
        names = [_clean(s) for s in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise ValueError("Exactly one distance is required between consecutive stations")
        for distance in distances:
            self._validate_distance(distance)

        for name in names:
            registered = self._register_station(name)
            station_lines = self.graph.station_lines[registered]
            if line not in station_lines:
                station_lines.append(line)
        for a, b, distance in zip(names, names[1:], distances):
            self.add_connection(a, b, distance, line)

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of existing connection(s) between two stations.

        Returns:
            The number of connections updated.
        """
        src = self._require_station(source)
        dst = self._require_station(dest)
        self._validate_distance(distance)
        edges = self.graph.find_edges(self.number_of(src), self.number_of(dst),
                                      _clean(line) if line else None)
        if not edges:
            raise ValueError(f"No connection between '{src}' and '{dst}'")
        for edge in edges:
            edge.distance = int(round(distance))
        return len(edges)

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line affiliations.

        Returns:
            The station's name after the modification.
        """
        current = self._require_station(name)
        target = current
        if new_name is not None:
            target = _clean(new_name)
            if not target:
                raise ValueError("New station name cannot be empty")
            if target != current and self.standardize_station_name(target) is not None:
                raise ValueError(f"Station '{target}' already exists")
        if target != current:
            number = self.station_to_number.pop(current)
            self.station_to_number[target] = number
            self.number_to_station[number] = target
            self.graph.station_lines[target] = self.graph.station_lines.pop(current)
        if lines is not None:
            cleaned = []
            for line in lines:
                line = _clean(line)
                if line and line not in cleaned:
                    cleaned.append(line)
            self.graph.set_station_lines(target, cleaned)
        return target

    # ----- serialization -----------------------------------------------------

    def to_dict(self):
        """Export the current network in the dataset format."""
        stations = []
        for number in sorted(self.number_to_station):
            name = self.number_to_station[number]
            stations.append({"name": name, "lines": list(self.graph.station_lines.get(name, []))})
        connections = []
        for edge in self.graph.edges():
            connections.append({
                "source": self.number_to_station[edge.source],
                "dest": self.number_to_station[edge.dest],
                "distance": edge.distance,
                "line": edge.line,
            })
        return {"stations": stations, "connections": connections}

    def save(self, path=DATA_FILE_PATH):
        """Persist the current network to a JSON dataset file."""
        save_subway_data(self.to_dict(), path)
