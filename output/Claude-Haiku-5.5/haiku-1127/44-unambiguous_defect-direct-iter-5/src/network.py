"""Subway network modeling: builds the graph from the raw dataset.

This module owns the station-number mapping (``station_to_number``), the
graph itself, station-name standardization and line-level queries.
"""

import difflib
import re
import unicodedata
from collections import deque

from errors import DataError, StationNotFoundError
from models import Edge, Graph

_CHINESE_STATION_SUFFIX = "站"


def normalize_station_name(name):
    """Return a canonical lookup key for a station name.

    The key is NFKC-normalized, lower-cased, has all whitespace removed and
    ignores a trailing "站" (station) suffix, so "西直门站", "西直门" and
    " 西直门 " all map to the same key.
    """
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    text = re.sub(r"\s+", "", text)
    if len(text) > 1 and text.endswith(_CHINESE_STATION_SUFFIX):
        text = text[: -len(_CHINESE_STATION_SUFFIX)]
    return text


def natural_sort_key(text):
    """Sort key that orders embedded numbers numerically ("Line 2" < "Line 10")."""
    parts = re.split(r"(\d+)", str(text))
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _coerce_distance(value):
    """Convert a distance value from the dataset to a positive-compatible int (meters)."""
    if isinstance(value, bool):
        raise DataError(f"distance must be a number of meters, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise DataError(f"distance must be an integer number of meters, got {value!r}")


class SubwayNetwork:
    """Weighted undirected model of the subway network.

    Attributes:
        graph: The Graph instance holding adjacency lists and station lines.
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._connections = []   # list of (source_name, dest_name, distance, line)
        self._name_index = None  # lazily built lookup for standardized names

    # ----- construction -------------------------------------------------

    def add_station(self, name, lines=None):
        """Register a station (if new) and merge in the given lines.

        Returns:
            int: The station number assigned to the station.

        Raises:
            DataError: If the station name is empty or not a string.
        """
        if not isinstance(name, str) or not name.strip():
            raise DataError("station name must be a non-empty string")
        name = name.strip()
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
            self._name_index = None
        if lines:
            merged = self.graph.get_station_lines(name)
            for line in lines:
                if isinstance(line, str) and line.strip() and line.strip() not in merged:
                    merged.append(line.strip())
            self.graph.set_station_lines(name, merged)
        return self.station_to_number[name]

    def add_connection(self, source, dest, distance, line):
        """Add a track segment between two stations on a given line.

        Unknown stations are registered automatically.

        Returns:
            Edge: The created edge.

        Raises:
            DataError: If the distance is invalid or the line name is empty.
        """
        if not isinstance(line, str) or not line.strip():
            raise DataError("connection line must be a non-empty string")
        line = line.strip()
        distance = _coerce_distance(distance)
        if distance <= 0:
            raise DataError(f"distance between '{source}' and '{dest}' must be positive")
        u = self.add_station(source, [line])
        v = self.add_station(dest, [line])
        if u == v:
            raise DataError(f"connection from '{source}' to itself is not allowed")
        edge = Edge(u, v, distance, line)
        self.graph.add_edge(edge)
        self._connections.append(
            (self.number_to_station[u], self.number_to_station[v], distance, line)
        )
        return edge

    # ----- queries ------------------------------------------------------

    def station_name(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_number(self, name):
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def all_station_names(self):
        """Return all station names sorted naturally."""
        return sorted(self.station_to_number, key=natural_sort_key)

    def station_lines(self, name):
        """Return the list of lines serving a station."""
        return self.graph.get_station_lines(name)

    def is_transfer_station(self, name):
        """Return True if the station is an interchange of several lines."""
        return self.graph.is_transfer_station(name)

    def connections(self):
        """Return a copy of all connections as (source, dest, distance, line) tuples."""
        return list(self._connections)

    def line_names(self):
        """Return all line names known to the network, naturally sorted."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        for _src, _dst, _dist, line in self._connections:
            names.add(line)
        return sorted(names, key=natural_sort_key)

    def line_stations(self, line):
        """Return the station names of a line in travel order.

        The order is produced by a breadth-first walk starting from an
        end-point of the line (a station with the fewest neighbours).
        """
        adjacency = {}
        for src, dst, _dist, ln in self._connections:
            if ln != line:
                continue
            adjacency.setdefault(src, set()).add(dst)
            adjacency.setdefault(dst, set()).add(src)
        if not adjacency:
            return []
        start = min(adjacency, key=lambda n: (len(adjacency[n]), natural_sort_key(n)))
        order = []
        seen = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbour in sorted(adjacency[node], key=natural_sort_key):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return order

    # ----- station name standardization --------------------------------

    def _build_index(self):
        index = {}
        for name in self.station_to_number:
            index.setdefault(normalize_station_name(name), name)
        self._name_index = index

    def resolve_station(self, text, role="Station"):
        """Map user input to the official station name.

        Args:
            text: The name typed by the user.
            role: Label used in error messages, e.g. "Starting station".

        Returns:
            str: The official station name.

        Raises:
            StationNotFoundError: If no station matches the input. The error
                carries close-match suggestions.
        """
        cleaned = "" if text is None else str(text).strip()
        if not cleaned:
            raise StationNotFoundError(cleaned, role)
        if cleaned in self.station_to_number:
            return cleaned
        if self._name_index is None:
            self._build_index()
        key = normalize_station_name(cleaned)
        if key in self._name_index:
            return self._name_index[key]
        suggestions = difflib.get_close_matches(
            cleaned, list(self.station_to_number), n=3, cutoff=0.6
        )
        raise StationNotFoundError(cleaned, role, suggestions)


def build_network(data):
    """Build a SubwayNetwork from the dataset dictionary.

    Args:
        data: dict with "stations" (list of {"name", "lines"}) and
            "connections" (list of {"source", "dest", "distance", "line"}).

    Returns:
        SubwayNetwork: The constructed network.

    Raises:
        DataError: If the structure of the dataset is invalid.
    """
    if not isinstance(data, dict):
        raise DataError("subway data must be a dictionary")
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise DataError("'stations' must be a list")
    if not isinstance(connections, list):
        raise DataError("'connections' must be a list")

    network = SubwayNetwork()
    for index, item in enumerate(stations):
        if not isinstance(item, dict) or "name" not in item:
            raise DataError(f"station entry #{index} is malformed")
        lines = item.get("lines", [])
        if not isinstance(lines, list):
            raise DataError(f"lines of station '{item['name']}' must be a list")
        network.add_station(item["name"], lines)

    for index, item in enumerate(connections):
        if not isinstance(item, dict):
            raise DataError(f"connection entry #{index} is malformed")
        missing = [key for key in ("source", "dest", "distance", "line") if key not in item]
        if missing:
            raise DataError(f"connection entry #{index} misses fields: {', '.join(missing)}")
        network.add_connection(item["source"], item["dest"], item["distance"], item["line"])

    return network
