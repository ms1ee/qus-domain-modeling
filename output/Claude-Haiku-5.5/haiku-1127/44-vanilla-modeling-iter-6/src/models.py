"""Core data models: edges, graph-related helpers, routes, transfers and fare tiers."""

from dataclasses import dataclass, field
import math


class Edge:
    """A weighted, line-tagged connection between two adjacent stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters (also used as the edge weight).
        line: name of the subway line that serves this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path computations (meters)."""
        return self.distance

    def other(self, node):
        """Return the endpoint opposite to ``node``.

        Raises:
            ValueError: if ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"Node {node} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, "
                f"{self.distance!r}, {self.line!r})")


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (or through ``allocate_number``
    when the caller is a loader/manager). The graph keeps:
      * ``station_to_number``: station name -> station number
      * ``number_to_station``: station number -> station name
      * ``station_lines``: station name -> list of line names serving it
      * an adjacency list of ``Edge`` objects keyed by station number.
    """

    def __init__(self):
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self._adjacency = {}
        self._edge_index = {}
        self._next_number = 1

    # ------------------------------------------------------------------ #
    # Station management
    # ------------------------------------------------------------------ #
    def allocate_number(self):
        """Return a fresh, unused station number as a zero-padded string."""
        while True:
            number = f"{self._next_number:04d}"
            self._next_number += 1
            if number not in self.number_to_station:
                return number

    def add_station(self, name, number, lines=None):
        """Register a new station.

        Raises:
            ValueError: if the name or number is already registered, or the
                name is empty.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Station name must be a non-empty string")
        if name in self.station_to_number:
            raise ValueError(f"Station already exists: {name}")
        if number in self.number_to_station:
            raise ValueError(f"Station number already in use: {number}")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.station_lines[name] = []
        self._adjacency[number] = []
        for line in lines or []:
            self.add_line_to_station(name, line)

    def has_station(self, name):
        """Return True if a station with this exact name is registered."""
        return name in self.station_to_number

    def lookup_number(self, name):
        """Return the station number for ``name`` or None if unknown."""
        return self.station_to_number.get(name)

    def number_of(self, name):
        """Return the station number for ``name``; raises KeyError if unknown."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for ``number``; raises KeyError if unknown."""
        return self.number_to_station[number]

    def station_names(self):
        """Return a sorted list of all station names."""
        return sorted(self.station_to_number.keys())

    def rename_station(self, old_name, new_name):
        """Rename a station while keeping its number and edges intact."""
        if old_name not in self.station_to_number:
            raise ValueError(f"Unknown station: {old_name}")
        if new_name in self.station_to_number:
            raise ValueError(f"Station already exists: {new_name}")
        number = self.station_to_number.pop(old_name)
        self.station_to_number[new_name] = number
        self.number_to_station[number] = new_name
        self.station_lines[new_name] = self.station_lines.pop(old_name, [])

    @property
    def station_count(self):
        """Number of registered stations."""
        return len(self.station_to_number)

    # ------------------------------------------------------------------ #
    # Line management
    # ------------------------------------------------------------------ #
    def set_station_lines(self, station_name, lines):
        """Replace the list of lines serving a station (duplicates removed)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_line_to_station(self, name, line):
        """Add a line to a station's line list if it is not already present."""
        if name not in self.station_to_number:
            raise ValueError(f"Unknown station: {name}")
        lines = self.station_lines.setdefault(name, [])
        if line not in lines:
            lines.append(line)

    def lines_of(self, name):
        """Return the list of line names serving the station."""
        return list(self.station_lines.get(name, []))

    def all_lines(self):
        """Return a sorted list of every line name known to the graph."""
        lines = set()
        for station_line_list in self.station_lines.values():
            lines.update(station_line_list)
        for edge in self._edge_index.values():
            lines.add(edge.line)
        return sorted(lines)

    # ------------------------------------------------------------------ #
    # Edge management
    # ------------------------------------------------------------------ #
    def add_edge(self, edge):
        """Add an undirected edge. An existing edge between the same two
        stations is replaced (this is how distances are updated).

        Raises:
            ValueError: for unknown endpoints, self loops or non-positive
                distances.
        """
        src, dst = edge.source, edge.dest
        if src not in self.number_to_station or dst not in self.number_to_station:
            raise ValueError(f"Edge references unknown station: {src}, {dst}")
        if src == dst:
            raise ValueError(f"Self loops are not allowed: {src}")
        if not isinstance(edge.distance, (int, float)) or isinstance(edge.distance, bool):
            raise ValueError("Edge distance must be a number")
        if not math.isfinite(edge.distance) or edge.distance <= 0:
            raise ValueError("Edge distance must be a positive number")

        key = frozenset((src, dst))
        old = self._edge_index.get(key)
        if old is not None:
            self._detach(old)
        self._edge_index[key] = edge
        self._adjacency[src].append(edge)
        self._adjacency[dst].append(edge)

    def _detach(self, edge):
        """Remove an edge object from both adjacency lists and the index."""
        for node in (edge.source, edge.dest):
            adj = self._adjacency.get(node, [])
            self._adjacency[node] = [e for e in adj if e is not edge]
        self._edge_index.pop(frozenset((edge.source, edge.dest)), None)

    def remove_edge(self, a, b):
        """Remove the edge between station numbers ``a`` and ``b`` if present."""
        edge = self._edge_index.get(frozenset((a, b)))
        if edge is not None:
            self._detach(edge)

    def edge_between(self, a, b):
        """Return the edge between two station numbers, or None."""
        return self._edge_index.get(frozenset((a, b)))

    def get_edges(self, number):
        """Return the list of edges incident to station ``number``."""
        return self._adjacency.get(number, [])

    def iter_edges(self):
        """Iterate over each undirected edge exactly once."""
        return iter(list(self._edge_index.values()))

    @property
    def edge_count(self):
        """Number of undirected edges."""
        return len(self._edge_index)


@dataclass
class Transfer:
    """A line change at a station during a route."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    """The result of a path query."""

    start_station: str
    end_station: str
    mode: str
    station_names: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    total_distance_meters: float = 0.0
    transfer_count: int = 0
    estimated_time_minutes: float = 0.0
    fare_yuan: int = 0
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)

    @property
    def total_distance_km(self):
        """Total distance expressed in kilometers."""
        return self.total_distance_meters / 1000.0


@dataclass(frozen=True)
class FareTier:
    """One distance band of the Beijing Subway fare table.

    The band is left-closed and right-open: [min_distance_km, max_distance_km).
    For extended bands, ``extension_interval_km`` gives the step after which
    the price increases by one yuan.
    """

    min_distance_km: float
    max_distance_km: float
    price: int
    extension_interval_km: float = 0.0
