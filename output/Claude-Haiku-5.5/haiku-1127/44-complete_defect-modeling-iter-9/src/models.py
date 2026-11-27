"""Core graph and route data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


class Edge:
    """An undirected weighted connection between two stations.

    ``source`` and ``dest`` are station numbers, ``distance`` is in meters,
    and ``line`` is the name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers (vertices) are assigned by the caller. The graph also keeps
    a mapping from station name to the lines serving that station.
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}

    def add_vertex(self, vertex: int) -> None:
        """Register a vertex (station number) if it is not yet present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        return vertex in self._adj

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Record the list of lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge to the graph."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, vertex: int) -> List[Edge]:
        """Return the edges incident to ``vertex`` (read-only by convention)."""
        return self._adj.get(vertex, [])

    def vertices(self) -> List[int]:
        return list(self._adj.keys())

    def edges(self) -> List[Edge]:
        return list(self._edges)

    @property
    def vertex_count(self) -> int:
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        return len(self._edges)


@dataclass
class Query:
    """A passenger query: start station, end station, mode and time."""

    start_station: str
    end_station: str
    mode: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RouteSegment:
    """A continuous ride on one line between two stations."""

    line_name: str
    distance_meters: float
    sequence_number: int
    start_station: str
    end_station: str


@dataclass
class TransferInfo:
    """A line change at a transfer station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    """The result of a path query, including fare and summary figures."""

    stations: List[str]
    segments: List[RouteSegment]
    transfers: List[TransferInfo]
    total_distance_meters: float
    transfer_count: int
    estimated_time_minutes: float
    fare_yuan: int
    lines_involved: List[str]
    notes: Optional[str] = None
