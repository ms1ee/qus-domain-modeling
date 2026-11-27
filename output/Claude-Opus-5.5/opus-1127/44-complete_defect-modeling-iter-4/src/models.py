"""
Core data structures: Edge, Graph and simple domain records.
"""

from dataclasses import dataclass, field
from typing import List


class Edge:
    """A directed view of a connection between two stations.

    Attributes:
        source: station number of the start of the edge
        dest: station number of the end of the edge
        distance: distance in meters
        weight: same as distance (used by the shortest path algorithm)
        line: name of the line this connection belongs to
    """

    def __init__(self, source, dest, distance, line):
        if distance is None or distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    @property
    def from_(self):
        return self.source

    @property
    def to(self):
        return self.dest

    def other(self, v):
        """Return the endpoint that is not ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def reversed(self):
        """Return a new edge in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller. ``adj`` (alias ``graph``)
    maps a station number to the list of outgoing :class:`Edge` objects.
    """

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self._edges = []

    @property
    def graph(self):
        return self.adj

    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def has_vertex(self, v):
        return v in self.adj

    def set_station_lines(self, station_name, lines):
        """Record the lines a station belongs to (duplicates removed)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.source != edge.dest:
            self.adj[edge.dest].append(edge.reversed())
        self._edges.append(edge)

    def adjacent(self, v):
        return self.adj.get(v, [])

    neighbors = adjacent

    def vertices(self):
        return list(self.adj.keys())

    def edges(self):
        """Return each undirected edge once (as originally added)."""
        return list(self._edges)

    @property
    def vertex_count(self):
        return len(self.adj)

    @property
    def edge_count(self):
        return len(self._edges)

    V = vertex_count
    E = edge_count


@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    name: str
    station_sequence: List[str] = field(default_factory=list)
    transfer_info: str = ""


@dataclass
class Transfer:
    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    station_sequence: List[str]
    total_distance: int
    transfer_count: int
    estimated_time: float
    involved_lines: List[str]
    segments: list = field(default_factory=list)
    transfers: List[Transfer] = field(default_factory=list)
