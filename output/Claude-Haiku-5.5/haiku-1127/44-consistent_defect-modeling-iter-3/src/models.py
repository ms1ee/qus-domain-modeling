"""Core data models used across the subway fare system."""

from dataclasses import dataclass, field
from datetime import datetime


class Edge:
    """A directed, weighted connection between two stations on one line.

    Attributes:
        source: Station number of the origin station.
        dest: Station number of the destination station.
        distance: Distance in meters (also used as the edge weight).
        line: Name of the subway line that operates this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = int(distance)
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def __repr__(self):
        return (f"Edge(source={self.source!r}, dest={self.dest!r}, "
                f"distance={self.distance!r}, line={self.line!r})")


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller (see network.SubwayNetwork);
    the graph only stores numeric vertices and edges. Station-to-line
    membership is kept by station name in ``station_lines``.
    """

    def __init__(self):
        self._adjacency = {}      # station number -> list[Edge]
        self._edge_count = 0
        self.station_lines = {}   # station name -> list[str]

    def add_vertex(self, vertex):
        """Register a vertex (station number) if it is not yet present."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station (by station name)."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add a directed edge, registering both endpoints as vertices."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, vertex):
        """Return the outgoing edges of a vertex (empty list if unknown)."""
        return self._adjacency.get(vertex, [])

    def vertices(self):
        """Return all vertex numbers in ascending order."""
        return sorted(self._adjacency)

    def edges(self):
        """Yield every edge in the graph."""
        for vertex in sorted(self._adjacency):
            for edge in self._adjacency[vertex]:
                yield edge

    def get_edges(self, source, dest):
        """Return all edges going from ``source`` to ``dest``."""
        return [edge for edge in self.adj(source) if edge.dest == dest]

    @property
    def vertex_count(self):
        """Number of vertices in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of edges in the graph."""
        return self._edge_count


@dataclass
class Station:
    """A subway station."""

    number: int
    name: str
    lines: list = field(default_factory=list)

    @property
    def is_transfer(self):
        """A station served by two or more lines is a transfer station."""
        return len(self.lines) >= 2


@dataclass
class TransferPoint:
    """A place where the journey changes from one line to another."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    """A computed journey.

    Attributes:
        stations: Station names ordered from the start station to the end station.
        edges: Edges traversed, in travel order.
        total_distance_m: Total distance in meters.
        transfer_count: Number of line changes.
        involved_lines: Unique line names used, in order of first use.
        transfers: Transfer points along the route.
    """

    stations: list
    edges: list
    total_distance_m: int
    transfer_count: int
    involved_lines: list
    transfers: list = field(default_factory=list)


@dataclass
class Query:
    """A passenger query and its configuration."""

    start_name: str
    end_name: str
    mode: str
    max_transfers: object = None
    line_preference: object = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataIntegrityReport:
    """Result of a data integrity check."""

    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
