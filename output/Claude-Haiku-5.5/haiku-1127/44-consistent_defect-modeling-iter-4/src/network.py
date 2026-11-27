"""Subway network model: station registry, graph construction and data updates.

``SubwayNetwork`` turns the raw dataset (see ``data_loader``) into a ``Graph``
with integer station numbers, and provides name resolution, line queries,
transfer-station detection and data update operations.
"""

import difflib
import re

from data_loader import DATA_FILE_PATH
from models import Edge, Graph

# Main lines that must be represented in the network (PRD section 4.1).
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

_SEPARATOR_PATTERN = re.compile(r"[\s\-_\u00b7\u2022]+")
_SUFFIX_PATTERN = re.compile(r"(\u7ad9|station)$")


class UnknownStationError(LookupError):
    """Raised when a station name cannot be resolved."""


class NetworkUpdateError(ValueError):
    """Raised when a data update request is invalid."""


def normalize_name(text):
    """Normalize a station or line name for loose comparison.

    Lowercases the text, removes separators (spaces, hyphens, underscores)
    and a trailing "station" / "站" suffix.
    """
    cleaned = _SEPARATOR_PATTERN.sub("", (text or "").strip().lower())
    return _SUFFIX_PATTERN.sub("", cleaned)


class SubwayNetwork:
    """The Beijing Subway network as a weighted directed graph.

    Attributes:
        graph: the ``Graph`` holding stations (as numbers) and directed edges.
        station_to_number: official station name -> station number.
        number_to_station: station number -> official station name.
        load_warnings: messages about connection records that were skipped.
    """

    def __init__(self, data=None, name="Beijing Subway", data_source=DATA_FILE_PATH,
                 version="1.0"):
        self.name = name
        self.data_source = data_source
        self.version = version
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.load_warnings = []
        self._station_index = {}   # normalized name -> official name
        self._line_names = []      # official line names, in first-seen order
        self._line_index = {}      # normalized line name -> official line name
        if data is not None:
            self.load(data)

    # ------------------------------------------------------------------
    # Loading and construction
    # ------------------------------------------------------------------
    def load(self, data):
        """Populate the network from a dataset dictionary."""
        for station in data.get("stations", []):
            self.add_station(station["name"], station.get("lines", []))
        for conn in data.get("connections", []):
            try:
                self.add_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])
            except ValueError as exc:
                self.load_warnings.append(
                    f"Skipped connection {conn.get('source')} -> {conn.get('dest')}: {exc}")

    def register_line(self, line):
        """Register a line name and return its official spelling."""
        clean = (line or "").strip()
        if not clean:
            raise ValueError("Line name must not be empty")
        key = normalize_name(clean)
        if key in self._line_index:
            return self._line_index[key]
        self._line_index[key] = clean
        self._line_names.append(clean)
        return clean

    def add_station(self, name, lines=()):
        """Add a station (or merge lines into an existing one).

        Returns:
            int: the station number.
        """
        clean = (name or "").strip()
        if not clean:
            raise ValueError("Station name must not be empty")
        if clean not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[clean] = number
            self.number_to_station[number] = clean
            self._station_index[normalize_name(clean)] = clean
            self.graph.add_node(number)
            self.graph.set_station_lines(clean, [])

        merged = self.graph.get_station_lines(clean)
        for line in lines:
            official = self.register_line(line)
            if official not in merged:
                merged.append(official)
        self.graph.set_station_lines(clean, merged)
        return self.station_to_number[clean]

    def add_connection(self, source, dest, distance, line, bidirectional=False):
        """Add a connection between two stations on a line.

        Args:
            source: origin station name.
            dest: destination station name.
            distance: distance in meters (non-negative).
            line: line name operating the connection.
            bidirectional: if True, also add the reverse direction.

        Returns:
            bool: True if a new forward edge was created.
        """
        if source == dest:
            raise ValueError("a station cannot be connected to itself")
        dist = float(distance)
        if dist < 0:
            raise ValueError("distance must be non-negative")
        official_line = self.register_line(line)
        src = self.add_station(source, [official_line])
        dst = self.add_station(dest, [official_line])
        created = self.graph.add_edge(Edge(src, dst, dist, official_line))
        if bidirectional:
            self.graph.add_edge(Edge(dst, src, dist, official_line))
        return created

    def add_line(self, line_name, station_names, distances):
        """Add a new line from an ordered station sequence (both directions).

        Args:
            line_name: name of the new line.
            station_names: ordered list of station names on the line.
            distances: distances in meters between consecutive stations.

        Returns:
            str: the official line name.
        """
        if len(station_names) < 2:
            raise NetworkUpdateError("a line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise NetworkUpdateError("one distance is required per consecutive station pair")
        official = self.register_line(line_name)
        for index, distance in enumerate(distances):
            self.add_connection(station_names[index], station_names[index + 1],
                                distance, official, bidirectional=True)
        return official

    # ------------------------------------------------------------------
    # Data updates
    # ------------------------------------------------------------------
    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its lines.

        Returns:
            str: the official name of the station after the modification.
        """
        current = self.get_station_name(self.get_station_number(name))
        if new_name is not None and new_name.strip() and new_name.strip() != current:
            target = new_name.strip()
            if target in self.station_to_number:
                raise NetworkUpdateError(f"Station '{target}' already exists")
            number = self.station_to_number.pop(current)
            self.station_to_number[target] = number
            self.number_to_station[number] = target
            self._station_index.pop(normalize_name(current), None)
            self._station_index[normalize_name(target)] = target
            self.graph.station_lines[target] = self.graph.station_lines.pop(current, [])
            current = target
        if lines is not None:
            registered = []
            for line in lines:
                official = self.register_line(line)
                if official not in registered:
                    registered.append(official)
            self.graph.set_station_lines(current, registered)
        return current

    def update_distance(self, source, dest, distance, both_directions=True):
        """Update the distance of the connection between two stations.

        Returns:
            int: number of edges updated.
        """
        src = self.get_station_number(source)
        dst = self.get_station_number(dest)
        dist = float(distance)
        if dist < 0:
            raise NetworkUpdateError("distance must be non-negative")
        count = 0
        for edge in self.graph.get_edges(src, dst):
            edge.distance = dist
            count += 1
        if both_directions:
            for edge in self.graph.get_edges(dst, src):
                edge.distance = dist
                count += 1
        if count == 0:
            raise NetworkUpdateError(f"No direct connection between '{source}' and '{dest}'")
        return count

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_station(self, name):
        """Return True if the official station name exists."""
        return name in self.station_to_number

    def get_station_number(self, name):
        """Return the station number of an official station name."""
        if name not in self.station_to_number:
            raise UnknownStationError(f"Station '{name}' does not exist")
        return self.station_to_number[name]

    def get_station_name(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all official station names, sorted alphabetically."""
        return sorted(self.station_to_number)

    def lines_of_station(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(name)

    def line_names(self):
        """Return all registered line names."""
        return list(self._line_names)

    def normalize_line(self, text):
        """Return the official line name matching ``text``, or None."""
        if not text:
            return None
        return self._line_index.get(normalize_name(text))

    def transfer_stations(self):
        """Return the names of stations served by more than one line."""
        return [name for name in self.station_names() if len(self.lines_of_station(name)) > 1]

    def resolve_station(self, query):
        """Resolve user input to an official station name.

        Exact and normalized matches are preferred; otherwise the nearest
        station name is returned.

        Returns:
            tuple: ``(official_name, exact_match)``.

        Raises:
            UnknownStationError: if no station is close enough to the input.
        """
        text = (query or "").strip()
        if not text:
            raise UnknownStationError("Station name must not be empty")
        if text in self.station_to_number:
            return text, True
        key = normalize_name(text)
        if key in self._station_index:
            return self._station_index[key], True
        close = difflib.get_close_matches(key, list(self._station_index), n=1, cutoff=0.5)
        if close:
            return self._station_index[close[0]], False
        raise UnknownStationError(f"Station '{text}' does not exist, please check the station name")
