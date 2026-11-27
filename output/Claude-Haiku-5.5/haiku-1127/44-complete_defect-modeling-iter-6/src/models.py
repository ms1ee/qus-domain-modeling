"""Domain models: graph primitives and dataclasses describing the subway domain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
        weight: Edge weight used by path algorithms (equal to ``distance``).
        line: Name of the subway line this connection belongs to.
    """

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if source == dest:
            raise ValueError("self-loops are not allowed in the subway graph")
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, vertex: int) -> int:
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """A weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller; the graph only manages vertices
    (station numbers) and edges. Station-to-line information is kept in
    ``station_lines`` keyed by station name.
    """

    def __init__(self) -> None:
        self._adjacency: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}

    @property
    def vertex_count(self) -> int:
        """Number of vertices (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """Number of undirected edges (connections) in the graph."""
        return len(self._edges)

    @property
    def is_weighted(self) -> bool:
        """The subway graph is always weighted by distance."""
        return True

    def add_vertex(self, vertex: int) -> None:
        """Add a vertex if it does not already exist."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        """Return True if the vertex exists."""
        return vertex in self._adjacency

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, registering both endpoints as vertices."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, vertex: int) -> List[Edge]:
        """Return the incident edges of a vertex (treat the list as read-only)."""
        return self._adjacency.get(vertex, [])

    def vertices(self) -> List[int]:
        """Return all vertex numbers."""
        return list(self._adjacency.keys())

    def edges(self) -> List[Edge]:
        """Return all edges."""
        return list(self._edges)

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Record the lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))


@dataclass
class Station:
    """A subway station."""

    station_id: int
    name: str
    is_transfer: bool = False


@dataclass
class Line:
    """A subway line."""

    name: str
    line_code: str = ""


@dataclass
class Connection:
    """A direct connection between two adjacent stations on one line."""

    distance: float
    line_name: str


@dataclass
class Query:
    """A user query and its normalized parameters."""

    raw_input: str
    origin_station: str
    destination_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]


@dataclass
class Route:
    """A computed route with its derived metrics.

    ``segments`` is a list of ``(line_name, station_names)`` tuples in travel order.
    Consecutive segments share the station at which a transfer happens.
    """

    station_sequence: List[str]
    total_distance: float
    transfer_count: int
    estimated_time: float
    fare: int
    involved_lines: List[str]
    segments: List[Tuple[str, List[str]]] = field(default_factory=list)
