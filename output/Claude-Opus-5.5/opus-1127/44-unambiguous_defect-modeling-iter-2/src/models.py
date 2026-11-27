"""Core graph data structures: Edge, Graph, Station and Route."""

from dataclasses import dataclass, field
from typing import List, Optional


class Edge:
    """A weighted, line-labelled connection between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, v):
        """Return the endpoint of the edge that is not ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (v,))

    def reversed(self):
        """Return a copy of the edge with the direction reversed."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller.  ``graph`` maps a station
    number to the list of outgoing edges (each undirected edge is stored
    once in each direction).
    """

    def __init__(self):
        self.graph = {}                 # station number -> list[Edge]
        self.station_lines = {}         # station name -> list[str]
        self.station_to_number = {}     # station name -> station number
        self.number_to_station = {}     # station number -> station name
        self._edge_count = 0

    # ----- vertices / stations -------------------------------------------------
    def add_vertex(self, v):
        self.graph.setdefault(v, [])

    def add_station(self, name, number, lines=None):
        """Register a station name with its caller-assigned number."""
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.add_vertex(number)
        if lines is not None:
            self.set_station_lines(name, lines)
        else:
            self.station_lines.setdefault(name, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines is not None else []

    def get_station_name(self, number):
        return self.number_to_station.get(number, str(number))

    def get_station_number(self, name):
        return self.station_to_number.get(name)

    def is_transfer_station(self, station_name):
        return len(set(self.station_lines.get(station_name, []))) > 1

    # ----- edges -------------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        if edge.weight is None or edge.weight < 0:
            raise ValueError("Edge distance must be non-negative: %r" % (edge,))
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed: %r" % (edge,))
        self.graph.setdefault(edge.source, []).append(edge)
        self.graph.setdefault(edge.dest, []).append(edge.reversed())
        self._edge_count += 1

    def adj(self, v):
        return self.graph.get(v, [])

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    def E(self):
        return self._edge_count

    @property
    def vertex_count(self):
        return self.V()

    @property
    def edge_count(self):
        return self.E()

    def edges(self):
        """Return every undirected edge once."""
        seen = set()
        result = []
        for v, lst in self.graph.items():
            for e in lst:
                key = (min(e.source, e.dest, key=str), max(e.source, e.dest, key=str), e.line, e.distance)
                if key in seen:
                    continue
                seen.add(key)
                result.append(e)
        return result

    def lines_between(self, u, v):
        return [e.line for e in self.adj(u) if e.dest == v]


@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(set(self.lines)) > 1


@dataclass
class Route:
    """Result of a path query."""
    start: str
    end: str
    mode: str
    stations: List[str]
    edge_lines: List[str]
    edge_distances: List[float]
    total_distance: float
    transfer_count: int
    transfer_stations: List[str]
    lines: List[str]
    segments: List[dict]
    fare: int
    estimated_time: float
    max_transfers: Optional[int] = None
    line_preference: List[str] = field(default_factory=list)
