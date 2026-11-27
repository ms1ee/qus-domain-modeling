"""
Graph data structures for the Beijing Subway network.

The network is modelled as a weighted undirected graph stored as adjacency
lists. Station numbers (graph vertices) are assigned by the caller; the Graph
class only stores and connects them. Edge weights are physical distances in
meters.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass


def normalize_text(text: str) -> str:
    """Return a case-insensitive form of ``text`` with normalised whitespace."""
    return " ".join(str(text).split()).lower()


@dataclass
class Edge:
    """A connection between two stations operated by a single subway line.

    Attributes:
        source: Station number of the origin vertex.
        dest: Station number of the destination vertex.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating the connection.
    """

    source: int
    dest: int
    distance: float
    line: str

    @property
    def weight(self) -> float:
        """The edge weight used by shortest path algorithms (equal to the distance)."""
        return self.distance

    def reversed_copy(self) -> "Edge":
        """Return a copy of this edge with source and destination swapped."""
        return Edge(self.dest, self.source, self.distance, self.line)


class Graph:
    """Weighted undirected graph implemented with adjacency lists.

    Each undirected edge is stored twice (once per direction) so that
    ``adjacent`` can be answered in time proportional to the degree of a vertex.

    Attributes:
        station_lines: Mapping from station name to the list of line names serving it.
    """

    def __init__(self) -> None:
        self._adj: dict[int, list[Edge]] = {}
        self._edge_count = 0
        self.station_lines: dict[str, list[str]] = {}

    def add_vertex(self, number: int) -> None:
        """Register a station number as a vertex of the graph (no-op if present)."""
        self._adj.setdefault(number, [])

    def has_vertex(self, number: int) -> bool:
        """Return True if the station number is a vertex of the graph."""
        return number in self._adj

    def set_station_lines(self, station_name: str, lines) -> None:
        """Record the lines serving a station, keyed by station name."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge between two stations.

        Raises:
            ValueError: If the edge distance is negative.
        """
        if edge.distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge.reversed_copy())
        self._edge_count += 1

    def adjacent(self, number: int) -> list[Edge]:
        """Return the outgoing edges of a vertex (empty list for unknown vertices)."""
        return self._adj.get(number, [])

    def vertices(self) -> list[int]:
        """Return all station numbers in the graph."""
        return list(self._adj)

    @property
    def node_count(self) -> int:
        """Number of vertices (stations) in the graph."""
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        """Number of undirected edges (connections) in the graph."""
        return self._edge_count

    def memory_usage_mb(self) -> float:
        """Estimate the memory used by the adjacency structure, in megabytes."""
        total = sys.getsizeof(self._adj)
        for vertex, edges in self._adj.items():
            total += sys.getsizeof(vertex) + sys.getsizeof(edges)
            for edge in edges:
                total += sys.getsizeof(edge) + sys.getsizeof(edge.__dict__)
        return total / (1024 * 1024)
