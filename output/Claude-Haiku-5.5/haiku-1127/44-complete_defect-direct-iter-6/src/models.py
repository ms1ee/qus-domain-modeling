"""Core graph data structures for the Beijing Subway network.

Station numbers are assigned by the caller (see network.py); Graph only
stores adjacency information keyed by those numbers. The graph is
undirected: adding an edge stores it in both endpoints' adjacency lists.
"""

from __future__ import annotations

from typing import Dict, Iterable, List


class Edge:
    """A line-labelled connection between two stations.

    Attributes:
        source: station number where the edge starts.
        dest: station number where the edge ends.
        distance: track distance between the stations in meters.
        weight: edge weight used by shortest path search (equal to distance).
        line: name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source: int, dest: int, distance: int, line: str) -> None:
        if distance < 0:
            raise ValueError(f"edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def reversed(self) -> "Edge":
        """Return the same connection traversed in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self) -> str:
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: mapping from station name to the lines serving it.
    """

    def __init__(self) -> None:
        self._adjacency: Dict[int, List[Edge]] = {}
        self._edge_count = 0
        self.station_lines: Dict[str, List[str]] = {}

    def add_station(self, number: int) -> None:
        """Register a station node (no-op if it already exists)."""
        self._adjacency.setdefault(number, [])

    def has_station(self, number: int) -> bool:
        """Return True if the station number is a node of the graph."""
        return number in self._adjacency

    def set_station_lines(self, station_name: str, lines: Iterable[str]) -> None:
        """Record the (de-duplicated, order-preserving) lines of a station."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge between two existing or new station nodes.

        Raises:
            ValueError: if the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loops are not supported")
        self.add_station(edge.source)
        self.add_station(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge.reversed())
        self._edge_count += 1

    def adjacent(self, number: int) -> List[Edge]:
        """Return the edges leaving a station, oriented away from it."""
        return self._adjacency.get(number, [])

    def vertices(self) -> List[int]:
        """Return all station numbers in the graph."""
        return list(self._adjacency.keys())

    def vertex_count(self) -> int:
        """Number of station nodes."""
        return len(self._adjacency)

    def edge_count(self) -> int:
        """Number of undirected edges added."""
        return self._edge_count
