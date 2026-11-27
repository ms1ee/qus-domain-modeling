"""Core data models: graph structures, routes, segments, transfers, fares, reports."""

import sys
from dataclasses import dataclass, field
from typing import Optional


class Edge:
    """An undirected weighted edge between two station numbers on a given line.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters (also used as the edge weight).
        line: name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str):
        if distance is None or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest-path algorithms (the distance in meters)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller (see ``SubwayNetwork``); the graph
    only manages nodes and edges. ``station_lines`` maps station names to the
    lines they belong to.
    """

    def __init__(self):
        self._adj: dict[int, list[Edge]] = {}
        self._edges: list[Edge] = []
        self.station_lines: dict[str, list[str]] = {}

    # ----- size information -------------------------------------------------
    @property
    def node_count(self) -> int:
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # ----- node management --------------------------------------------------
    def add_node(self, vertex: int) -> None:
        """Ensure ``vertex`` exists in the graph."""
        self._adj.setdefault(vertex, [])

    def has_node(self, vertex: int) -> bool:
        return vertex in self._adj

    def nodes(self) -> list[int]:
        return list(self._adj.keys())

    def set_station_lines(self, station_name: str, lines: list[str]) -> None:
        """Record the line affiliation of a station (by name)."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management --------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Insert an undirected edge into the adjacency lists."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge: Edge) -> None:
        """Remove an edge previously added with ``add_edge``."""
        self._edges.remove(edge)
        self._adj[edge.source].remove(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].remove(edge)

    def adjacent(self, vertex: int) -> list[Edge]:
        """Edges incident to ``vertex`` (read-only use expected)."""
        return self._adj.get(vertex, [])

    def edges(self) -> list[Edge]:
        """All undirected edges, each listed exactly once."""
        return list(self._edges)

    def find_edges(self, u: int, v: int) -> list[Edge]:
        """All edges directly connecting stations ``u`` and ``v``."""
        return [e for e in self._adj.get(u, []) if e.other(u) == v]

    # ----- diagnostics ------------------------------------------------------
    def memory_usage_mb(self) -> float:
        """Rough estimate of the memory used by the graph structures, in MB."""
        total = sys.getsizeof(self._adj) + sys.getsizeof(self._edges)
        for adj_list in self._adj.values():
            total += sys.getsizeof(adj_list)
        for edge in self._edges:
            total += sys.getsizeof(edge)
        for name, lines in self.station_lines.items():
            total += sys.getsizeof(name) + sys.getsizeof(lines)
        return total / (1024 * 1024)


@dataclass
class PathSegment:
    """A maximal run of consecutive stations travelled on one line."""

    line_name: str
    start_station: str
    end_station: str
    distance: float
    station_count: int


@dataclass
class Transfer:
    """A line change at a station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class FareResult:
    """Fare amount charged for a route."""

    amount: int
    currency: str = "yuan"


@dataclass
class Route:
    """A computed passenger route with all derived information."""

    start: str
    end: str
    mode: str
    stations: list[str]
    edges: list[Edge]
    total_distance: float
    transfer_count: int
    estimated_time: float
    fare: FareResult
    segments: list[PathSegment] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class PathReport:
    """A rendered report of a route."""

    format: str
    content: str
    output_file: Optional[str] = None
