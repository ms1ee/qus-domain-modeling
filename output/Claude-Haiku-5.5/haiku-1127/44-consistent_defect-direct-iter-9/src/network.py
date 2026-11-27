"""Subway network model: station registry, adjacency data and update operations.

Station names are mapped to integer numbers, and the directed graph of
connections is built on those numbers. Connections listed in the dataset are
stored in their listed direction; when the reverse direction is not listed,
it is added as well so that the network behaves as a bidirectional subway.
"""

import difflib
import re

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


class StationNotFoundError(LookupError):
    """Raised when a station cannot be found or matched."""


class NetworkUpdateError(ValueError):
    """Raised when a data update request is invalid."""


def _normalize_name(name):
    """Normalize a station name for loose matching (case, spaces, suffixes)."""
    text = re.sub(r"\s+", "", str(name)).lower()
    for suffix in ("station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text


class SubwayNetwork:
    """Holds the station registry and the weighted graph of the subway network.

    Attributes:
        graph: ``models.Graph`` keyed by station numbers.
        station_to_number: Mapping station name -> station number.
        number_to_station: Mapping station number -> station name.
        raw_connections: Connection records as listed in the dataset.
    """

    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.raw_connections = []
        self._norm_index = {}
        self._next_number = 0
        self._build(data)

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Create a network from the subway dataset file."""
        return cls(load_subway_data(path))

    # ----- construction ------------------------------------------------------
    def _build(self, data):
        for station in data.get("stations", []):
            self._ensure_station(station["name"], station.get("lines", []))

        for conn in data.get("connections", []):
            self.raw_connections.append({
                "source": str(conn["source"]).strip(),
                "dest": str(conn["dest"]).strip(),
                "distance": int(conn["distance"]),
                "line": str(conn["line"]).strip(),
            })

        listed = {(c["source"], c["dest"]) for c in self.raw_connections}
        for conn in self.raw_connections:
            src, dst = conn["source"], conn["dest"]
            self._ensure_station(src)
            self._ensure_station(dst)
            self._add_directed(self.station_to_number[src], self.station_to_number[dst],
                               conn["distance"], conn["line"])
            if (dst, src) not in listed:
                self._add_directed(self.station_to_number[dst], self.station_to_number[src],
                                   conn["distance"], conn["line"])

    def _ensure_station(self, name, lines=()):
        """Register a station (if new) and merge in the given lines. Returns its number."""
        name = str(name).strip()
        if name not in self.station_to_number:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
            self._norm_index[_normalize_name(name)] = name
        current = self.graph.get_station_lines(name)
        for line in lines:
            line = str(line).strip()
            if line and line not in current:
                current.append(line)
        self.graph.set_station_lines(name, current)
        return self.station_to_number[name]

    def _add_directed(self, source, dest, distance, line):
        """Add a directed edge, or update the distance if the same line already links them."""
        for edge in self.graph.edges_between(source, dest):
            if edge.line == line:
                edge.distance = distance
                return
        self.graph.add_edge(Edge(source, dest, distance, line))

    def _rebuild_norm_index(self):
        self._norm_index = {_normalize_name(n): n for n in self.station_to_number}

    # ----- queries -----------------------------------------------------------
    @property
    def station_count(self):
        """Number of stations in the network."""
        return len(self.station_to_number)

    def station_names(self):
        """Return a sorted list of station names."""
        return sorted(self.station_to_number)

    def has_station(self, name):
        """Return True if the exact station name exists."""
        return str(name).strip() in self.station_to_number

    def number_of(self, name):
        """Return the station number for an exact station name."""
        name = str(name).strip()
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Unknown station '{name}'")
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def get_lines(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(name)

    def line_names(self):
        """Return a sorted list of all line names in the network."""
        lines = set()
        for names in self.graph.station_lines.values():
            lines.update(names)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines)

    def stations_on_line(self, line):
        """Return a sorted list of station names that have edges on the given line."""
        result = set()
        for edge in self.graph.edges():
            if edge.line == line:
                result.add(self.name_of(edge.source))
                result.add(self.name_of(edge.dest))
        return sorted(result)

    def adjacency(self, name):
        """Return ``{neighbor name: distance in meters}`` for a station."""
        number = self.number_of(name)
        return {self.name_of(e.dest): e.distance for e in self.graph.adj(number)}

    def resolve_station(self, name):
        """Resolve user input to an official station name.

        Returns:
            tuple: ``(official_name, exact)`` where ``exact`` is False if the
            input was matched to the nearest station by fuzzy matching.

        Raises:
            StationNotFoundError: If no station is close enough to the input.
        """
        text = str(name).strip()
        if text in self.station_to_number:
            return text, True
        key = _normalize_name(text)
        if not key:
            raise StationNotFoundError(f"Station '{text}' does not exist")
        if key in self._norm_index:
            return self._norm_index[key], True
        matches = difflib.get_close_matches(key, list(self._norm_index), n=1, cutoff=0.5)
        if matches:
            return self._norm_index[matches[0]], False
        raise StationNotFoundError(f"Station '{text}' does not exist")

    # ----- data updates ------------------------------------------------------
    def add_station(self, name, lines=None):
        """Add a new station (or merge lines into an existing one). Returns its number."""
        name = str(name).strip()
        if not name:
            raise NetworkUpdateError("Station name must not be empty")
        number = self._ensure_station(name, lines or [])
        self._rebuild_norm_index()
        return number

    def add_line(self, line_name, station_names, distances, bidirectional=True):
        """Add a new line described by an ordered station list and consecutive distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations.
            bidirectional: If True, the reverse direction is also added.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise NetworkUpdateError("Line name must not be empty")
        names = [str(n).strip() for n in station_names]
        if len(names) < 2:
            raise NetworkUpdateError("A line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise NetworkUpdateError("Number of distances must equal stations minus one")
        for d in distances:
            if int(d) <= 0:
                raise NetworkUpdateError("Distances must be positive")

        for name in names:
            self._ensure_station(name, [line_name])
        self._rebuild_norm_index()

        for i, distance in enumerate(distances):
            a = self.number_of(names[i])
            b = self.number_of(names[i + 1])
            self._add_directed(a, b, int(distance), line_name)
            if bidirectional:
                self._add_directed(b, a, int(distance), line_name)

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its lines.

        Args:
            name: Current official station name.
            new_name: New name (optional).
            lines: Replacement list of lines (optional).
        """
        name = str(name).strip()
        number = self.number_of(name)
        if lines is not None:
            self.graph.set_station_lines(name, [str(l).strip() for l in lines])
        if new_name is not None:
            new_name = str(new_name).strip()
            if not new_name:
                raise NetworkUpdateError("New station name must not be empty")
            if new_name != name:
                if new_name in self.station_to_number:
                    raise NetworkUpdateError(f"Station '{new_name}' already exists")
                del self.station_to_number[name]
                self.station_to_number[new_name] = number
                self.number_to_station[number] = new_name
                self.graph.station_lines[new_name] = self.graph.station_lines.pop(name, [])
                self._rebuild_norm_index()

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two adjacent stations in both directions.

        Returns:
            int: Number of edges updated.
        """
        distance = int(distance)
        if distance <= 0:
            raise NetworkUpdateError("Distance must be positive")
        a = self.number_of(name_a)
        b = self.number_of(name_b)
        updated = 0
        for u, v in ((a, b), (b, a)):
            for edge in self.graph.edges_between(u, v):
                if line is None or edge.line == line:
                    edge.distance = distance
                    updated += 1
        if updated == 0:
            raise NetworkUpdateError(
                f"No connection between '{name_a}' and '{name_b}'"
                + (f" on line '{line}'" if line else "")
            )
        return updated
