"""Core domain models for the Beijing Subway network and route results.

This module contains the weighted undirected graph used by the path
calculation module, along with the lightweight data classes describing
queries and computed routes.
"""

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """A weighted, undirected connection between two adjacent stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: str, dest: str, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest path algorithms (equals the distance)."""
        return self.distance

    def other_endpoint(self, node: str) -> str:
        """Return the endpoint of this edge that is not ``node``.

        Raises:
            ValueError: If ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"Node '{node}' is not an endpoint of {self!r}")

    def __repr__(self) -> str:
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations using adjacency lists.

    Station numbers are assigned by the caller (see ``SubwayNetwork``); the
    graph only manages vertices and edges. The ``station_lines`` dictionary
    maps official station names to the lines serving them.

    Attributes:
        station_lines: Mapping of station name to the list of line names.
    """

    def __init__(self) -> None:
        self._adjacency: Dict[str, List[Edge]] = {}
        self._edge_count: int = 0
        self.station_lines: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Properties and statistics
    # ------------------------------------------------------------------
    @property
    def vertex_count(self) -> int:
        """Number of stations (vertices) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """Number of undirected connections (edges) in the graph."""
        return self._edge_count

    @property
    def memory_usage_mb(self) -> float:
        """Approximate memory footprint of the graph data structure in MB."""
        total = sys.getsizeof(self._adjacency)
        for key, edges in self._adjacency.items():
            total += sys.getsizeof(key) + sys.getsizeof(edges)
        for edge in self.edges():
            total += sys.getsizeof(edge) + sys.getsizeof(edge.distance)
        for name, lines in self.station_lines.items():
            total += sys.getsizeof(name) + sys.getsizeof(lines)
        return total / (1024.0 * 1024.0)

    # ------------------------------------------------------------------
    # Vertex management
    # ------------------------------------------------------------------
    def add_vertex(self, number: str) -> None:
        """Add a station vertex identified by ``number`` if it is not present."""
        self._adjacency.setdefault(number, [])

    def has_vertex(self, number: str) -> bool:
        """Return True if the station number exists in the graph."""
        return number in self._adjacency

    def vertices(self) -> List[str]:
        """Return all station numbers in insertion order."""
        return list(self._adjacency.keys())

    # ------------------------------------------------------------------
    # Station line information
    # ------------------------------------------------------------------
    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the list of lines serving a station (keyed by station name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return a copy of the lines serving a station, or an empty list."""
        return list(self.station_lines.get(station_name, []))

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, creating its endpoints when necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edge_count += 1

    def adjacent(self, number: str) -> List[Edge]:
        """Return the edges incident to a station (read-only use recommended)."""
        return self._adjacency.get(number, [])

    def edges(self) -> List[Edge]:
        """Return every unique edge in the graph exactly once."""
        seen = set()
        result: List[Edge] = []
        for edges in self._adjacency.values():
            for edge in edges:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def find_edges(self, number_a: str, number_b: str) -> List[Edge]:
        """Return all edges connecting two stations (in either direction)."""
        pair = {number_a, number_b}
        return [
            edge
            for edge in self._adjacency.get(number_a, [])
            if {edge.source, edge.dest} == pair
        ]

    def lines_at(self, number: str) -> List[str]:
        """Return the sorted unique line names of edges incident to a station."""
        return sorted({edge.line for edge in self._adjacency.get(number, [])})


@dataclass
class Query:
    """A passenger query: origin, destination and calculation options."""

    start_station: str
    end_station: str
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class RouteSegment:
    """A continuous ride on one subway line between two stations."""

    line_name: str
    start_station: str
    end_station: str
    distance_meters: float
    hop_count: int


@dataclass
class TransferPoint:
    """A transfer between two lines at an interchange station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    """The complete result of a path calculation, including fare and summary."""

    stations: List[str] = field(default_factory=list)
    segments: List[RouteSegment] = field(default_factory=list)
    transfers: List[TransferPoint] = field(default_factory=list)
    total_distance_meters: float = 0.0
    transfer_count: int = 0
    estimated_time_minutes: float = 0.0
    fare_yuan: int = 0
    lines_involved: List[str] = field(default_factory=list)

    @property
    def total_distance_km(self) -> float:
        """Total travel distance converted from meters to kilometers."""
        return self.total_distance_meters / 1000.0
