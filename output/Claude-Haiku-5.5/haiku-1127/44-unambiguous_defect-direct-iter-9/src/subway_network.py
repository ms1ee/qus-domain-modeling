"""Subway network model: station registry, graph construction and data management.

This module owns the station-name <-> station-number mapping and builds the
:class:`models.Graph` from the dataset. It also provides the data update
operations (adding lines, modifying stations and updating distances) and the
station name standardisation used by the query parser.
"""

from models import Edge, Graph

_STATION_SUFFIXES = ("station", "站")


class StationNotFoundError(Exception):
    """Raised when a station name is not part of the network."""


def _normalize_station_key(name):
    """Build a comparison key: no whitespace, lower case, no 'station' suffix."""
    key = "".join(name.split()).lower()
    for suffix in _STATION_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            key = key[: -len(suffix)]
            break
    return key


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    return distance


class SubwayNetwork:
    """Container for the subway graph and its station/line bookkeeping.

    Attributes:
        graph: The weighted undirected :class:`models.Graph`.
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        line_stations: dict mapping line name -> set of station names.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.line_stations = {}

    # ----- construction ------------------------------------------------------
    @classmethod
    def from_data(cls, data):
        """Build a network from the dict returned by ``load_subway_data``."""
        network = cls()
        for station in data.get("stations", []):
            network.add_station(station["name"], station.get("lines", []))
        for connection in data.get("connections", []):
            network.add_connection(
                connection["source"],
                connection["dest"],
                connection["distance"],
                connection["line"],
            )
        return network

    # ----- station management ------------------------------------------------
    def add_station(self, name, lines=()):
        """Add a station (or merge lines into an existing one). Returns its number."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("station name must be a non-empty string")
        name = " ".join(name.split())
        if name in self.station_to_number:
            number = self.station_to_number[name]
            merged = list(self.graph.station_lines.get(name, []))
        else:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            merged = []
        for line in lines:
            if line not in merged:
                merged.append(line)
        self.graph.set_station_lines(name, merged)
        for line in merged:
            self.line_stations.setdefault(line, set()).add(name)
        return number

    def has_station(self, name):
        return name in self.station_to_number

    def get_number(self, name):
        """Return the station number for an exact station name.

        Raises:
            StationNotFoundError: If the station is unknown.
        """
        if name not in self.station_to_number:
            raise StationNotFoundError(f"station {name!r} does not exist")
        return self.station_to_number[name]

    def resolve_station_name(self, raw):
        """Standardise user input to an official station name.

        Matching ignores case, whitespace and a trailing 'Station'/'站' word.

        Returns:
            str or None: The official name, or None if nothing matches.
        """
        if not isinstance(raw, str):
            return None
        collapsed = " ".join(raw.split())
        if not collapsed:
            return None
        if collapsed in self.station_to_number:
            return collapsed
        key = _normalize_station_key(collapsed)
        for name in self.station_to_number:
            if _normalize_station_key(name) == key:
                return name
        return None

    def station_names(self):
        """Return all station names, sorted alphabetically."""
        return sorted(self.station_to_number)

    def lines(self):
        """Return all line names, sorted alphabetically."""
        return sorted(self.line_stations)

    def stations_on_line(self, line):
        """Return the sorted station names served by ``line``."""
        return sorted(self.line_stations.get(line, set()))

    def transfer_stations(self):
        """Return ``{station name: sorted lines}`` for multi-line interchanges."""
        result = {}
        for name in self.station_names():
            lines = self.graph.station_lines.get(name, [])
            if len(lines) > 1:
                result[name] = sorted(lines)
        return result

    # ----- connections -------------------------------------------------------
    def add_connection(self, source, dest, distance, line):
        """Add a direct connection between two stations served by ``line``.

        Unknown stations are created automatically and both endpoints are
        registered as serving ``line``.
        """
        if not isinstance(line, str) or not line.strip():
            raise ValueError("line name must be a non-empty string")
        _validate_distance(distance)
        src = self.add_station(source, [line])
        dst = self.add_station(dest, [line])
        edge = Edge(src, dst, distance, line)
        self.graph.add_edge(edge)
        return edge

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Returns:
            int: Number of edges updated.

        Raises:
            StationNotFoundError: If a station is unknown.
            ValueError: If no matching connection exists or distance is invalid.
        """
        _validate_distance(distance)
        a = self.get_number(station_a)
        b = self.get_number(station_b)
        edges = [
            edge for edge in self.graph.find_edges(a, b)
            if line is None or edge.line == line
        ]
        if not edges:
            raise ValueError(f"no connection between {station_a!r} and {station_b!r}")
        for edge in edges:
            edge.distance = distance
        return len(edges)

    # ----- line management ---------------------------------------------------
    def add_new_line(self, line, stations, distances):
        """Add a new line through an ordered list of stations.

        Args:
            line: Name of the new line (must not already exist).
            stations: Ordered list of station names (at least two).
            distances: Either one distance (meters) used for every segment, or a
                list with ``len(stations) - 1`` distances.

        Raises:
            ValueError: If the line exists or the inputs are invalid.
        """
        if not isinstance(line, str) or not line.strip():
            raise ValueError("line name must be a non-empty string")
        if line in self.line_stations:
            raise ValueError(f"line {line!r} already exists")
        stations = list(stations)
        if len(stations) < 2:
            raise ValueError("a new line needs at least two stations")
        segments = len(stations) - 1
        if isinstance(distances, (int, float)) and not isinstance(distances, bool):
            distances = [distances] * segments
        distances = list(distances)
        if len(distances) != segments:
            raise ValueError("number of distances must equal number of segments")
        for value in distances:
            _validate_distance(value)
        for index in range(segments):
            self.add_connection(stations[index], stations[index + 1], distances[index], line)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line affiliations.

        Returns:
            str: The station's (possibly new) name.
        """
        if old_name not in self.station_to_number:
            raise StationNotFoundError(f"station {old_name!r} does not exist")
        current = old_name
        if new_name and new_name != old_name:
            if new_name in self.station_to_number:
                raise ValueError(f"station {new_name!r} already exists")
            number = self.station_to_number.pop(old_name)
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            old_lines = self.graph.station_lines.pop(old_name, [])
            for line in old_lines:
                members = self.line_stations.get(line, set())
                members.discard(old_name)
                members.add(new_name)
            self.graph.set_station_lines(new_name, old_lines)
            current = new_name
        if lines is not None:
            new_lines = list(dict.fromkeys(lines))
            for line in self.graph.station_lines.get(current, []):
                if line not in new_lines:
                    self.line_stations.get(line, set()).discard(current)
            for line in new_lines:
                self.line_stations.setdefault(line, set()).add(current)
            self.graph.set_station_lines(current, new_lines)
        return current
