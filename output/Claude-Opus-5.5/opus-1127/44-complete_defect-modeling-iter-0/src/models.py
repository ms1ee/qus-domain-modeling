"""
Core data structures: Edge, Graph and simple domain value objects.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """A weighted, line-labelled edge between two station numbers."""

    def __init__(self, source, dest, distance, line=None):
        if distance is None or isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def reversed(self):
        """Return the same connection in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def other(self, vertex):
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.weight!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller; the graph just stores them.
    """

    def __init__(self):
        self.adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self._edges: List[Edge] = []

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def add_station(self, name, number, lines=None):
        """Register a named station with a caller-assigned number."""
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.add_vertex(number)
        if lines is not None:
            self.set_station_lines(name, lines)

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    def vertices(self):
        return list(self.adj.keys())

    @property
    def V(self):
        return len(self.adj)

    @property
    def vertex_count(self):
        return self.V

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both adjacency lists)."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.adj.setdefault(edge.source, []).append(edge)
        if edge.source != edge.dest:
            self.adj.setdefault(edge.dest, []).append(edge.reversed())
        self._edges.append(edge)

    def adjacent(self, v):
        return self.adj.get(v, [])

    def edges(self):
        return list(self._edges)

    @property
    def E(self):
        return len(self._edges)

    @property
    def edge_count(self):
        return self.E

    def __repr__(self):
        return f"Graph(V={self.V}, E={self.E})"


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
    from_line: Optional[str]
    to_line: Optional[str]


@dataclass
class Route:
    start: str
    end: str
    station_sequence: List[str]
    total_distance_meters: int
    transfer_count: int
    estimated_time: float
    involved_lines: List[str]
    transfers: List[Transfer] = field(default_factory=list)
    segments: List[dict] = field(default_factory=list)
    fare: int = 0
    mode: str = "shortest_distance"


@dataclass
class PathSummary:
    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time: float

    @classmethod
    def from_route(cls, route):
        return cls(
            total_distance_km=round(route.total_distance_meters / 1000.0, 2),
            total_fare=route.fare,
            transfer_count=route.transfer_count,
            estimated_time=round(route.estimated_time, 1),
        )
