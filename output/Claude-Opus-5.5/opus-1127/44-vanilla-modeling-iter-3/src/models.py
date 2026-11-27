"""Core data structures: stations, lines, connections, edges and the graph."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Station:
    """A subway station."""
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self) -> bool:
        return len(self.lines) > 1


@dataclass
class Line:
    """A subway line with its ordered station sequence."""
    name: str
    stations: List[str] = field(default_factory=list)


@dataclass
class Connection:
    """A bidirectional connection between two adjacent stations."""
    source: str
    dest: str
    distance: int
    line: str
    bidirectional: bool = True


@dataclass
class TransferDetail:
    """A transfer made at a station between two lines."""
    station_name: str
    from_line: str
    to_line: str


class Edge:
    """A weighted edge between two station numbers on a given line."""

    def __init__(self, source, dest, distance, line):
        if distance is None or distance < 0:
            raise ValueError("Edge distance must be a non-negative number")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, vertex):
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex is not an endpoint of this edge")

    def reversed(self):
        """Return the same connection traversed in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))

    def __repr__(self):
        return "Edge({!r}, {!r}, {!r}, {!r})".format(
            self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller. Every undirected edge is
    stored once in each endpoint's adjacency list, oriented away from that
    endpoint (so ``edge.source`` is always the current vertex).
    """

    def __init__(self):
        self.adj = {}             # station number -> list[Edge]
        self.station_lines = {}   # station name -> list[str]
        self._edges = []

    # ----- vertices -------------------------------------------------------
    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def vertices(self):
        return list(self.adj.keys())

    @property
    def V(self):
        return len(self.adj)

    vertex_count = V

    # ----- station info ---------------------------------------------------
    def set_station_lines(self, station_name, lines):
        unique = []
        for line in lines or []:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges ----------------------------------------------------------
    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.source != edge.dest:
            self.adj[edge.dest].append(edge.reversed())
        self._edges.append(edge)

    def adjacent(self, v):
        return list(self.adj.get(v, []))

    def edges(self):
        return list(self._edges)

    @property
    def E(self):
        return len(self._edges)

    edge_count = E

    @property
    def graph(self):
        """The adjacency-list dictionary representation."""
        return self.adj

    def __repr__(self):
        return "Graph(V={}, E={})".format(self.V, self.E)
