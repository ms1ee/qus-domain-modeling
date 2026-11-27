"""Core data models: stations, lines, weighted edges and the undirected graph."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Station:
    """A subway station (one node of the network)."""

    id: int
    name: str
    is_transfer_station: bool = False


@dataclass(frozen=True)
class Line:
    """A subway line."""

    name: str
    code: str = ""


@dataclass(frozen=True)
class Transfer:
    """A line change at a transfer station."""

    station_name: str
    from_line: str
    to_line: str


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: actual distance between the stations in meters.
        line: name of the line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if source == dest:
            raise ValueError("an edge cannot connect a station to itself")
        if distance <= 0:
            raise ValueError(f"edge distance must be positive, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest path search (equals the distance in meters)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: if ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller; the graph only manages vertices
    (station numbers), edges, and the name -> lines mapping ``station_lines``.
    """

    def __init__(self) -> None:
        self._adj: dict[int, list[Edge]] = {}
        self._edges: list[Edge] = []
        # station name -> list of line names serving that station
        self.station_lines: dict[str, list[str]] = {}

    # ------------------------------------------------------------------ vertices
    def add_vertex(self, vertex: int) -> None:
        """Ensure ``vertex`` exists in the graph."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        """Return True if ``vertex`` is part of the graph."""
        return vertex in self._adj

    def vertices(self) -> list[int]:
        """Return all vertex (station number) identifiers."""
        return list(self._adj)

    @property
    def station_count(self) -> int:
        """Number of stations (vertices) in the graph."""
        return len(self._adj)

    # --------------------------------------------------------------- station data
    def set_station_lines(self, station_name: str, lines: list[str]) -> None:
        """Record the lines serving a station, removing duplicates while keeping order."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def get_station_lines(self, station_name: str) -> list[str]:
        """Return a copy of the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))

    # ---------------------------------------------------------------------- edges
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge to the graph (both endpoints reference it)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, vertex: int) -> list[Edge]:
        """Return the edges incident to ``vertex`` (read-only view by convention)."""
        return self._adj.get(vertex, [])

    def find_edges(self, a: int, b: int) -> list[Edge]:
        """Return all edges directly connecting stations ``a`` and ``b``."""
        return [edge for edge in self._adj.get(a, []) if edge.other(a) == b]

    def edges(self) -> list[Edge]:
        """Return a list of all edges, each listed once."""
        return list(self._edges)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self._edges)

    # --------------------------------------------------------------- diagnostics
    def memory_usage_mb(self) -> float:
        """Estimate the memory footprint of the graph structures in megabytes."""
        total = sys.getsizeof(self._adj) + sys.getsizeof(self._edges)
        for vertex, adj in self._adj.items():
            total += sys.getsizeof(vertex) + sys.getsizeof(adj)
        for edge in self._edges:
            total += sys.getsizeof(edge)
        for name, lines in self.station_lines.items():
            total += sys.getsizeof(name) + sys.getsizeof(lines)
        return total / (1024 * 1024)


def optional_name(value: Optional[str]) -> str:
    """Return ``value`` or an empty string when it is None (small helper for reports)."""
    return value if value is not None else ""
