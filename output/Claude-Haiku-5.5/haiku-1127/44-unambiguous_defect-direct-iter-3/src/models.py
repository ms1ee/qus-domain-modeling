"""Graph data structures used to model the subway network.

The graph is a weighted, undirected multigraph. Vertices are station numbers
(integers assigned by the caller, e.g. ``SubwayNetwork``), and every edge
stores the inter-station distance in metres as its weight.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class Edge:
    """An undirected, weighted connection between two stations on a line."""

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: int, line: str) -> None:
        if source == dest:
            raise ValueError("an edge cannot connect a station to itself")
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> int:
        """Edge weight used by path algorithms (equal to the distance in metres)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return (
            f"Edge({self.source}, {self.dest}, distance={self.distance}, "
            f"line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. The graph additionally keeps
    ``station_lines``, mapping each station name to the lines serving it.
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------ vertices
    def add_vertex(self, vertex: int) -> None:
        """Add a vertex if it does not exist yet."""
        if vertex not in self._adj:
            self._adj[vertex] = []

    def has_vertex(self, vertex: int) -> bool:
        return vertex in self._adj

    def vertices(self) -> List[int]:
        return list(self._adj)

    @property
    def num_vertices(self) -> int:
        return len(self._adj)

    # --------------------------------------------------------------------- edges
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, creating its endpoints when necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, vertex: int) -> List[Edge]:
        """Edges incident to ``vertex`` (treat the returned list as read-only)."""
        return self._adj.get(vertex, [])

    def edges(self) -> List[Edge]:
        """A copy of the list of all edges, each listed once."""
        return list(self._edges)

    @property
    def num_edges(self) -> int:
        return len(self._edges)

    def edges_between(
        self, a: int, b: int, line: Optional[str] = None
    ) -> List[Edge]:
        """Return edges joining ``a`` and ``b`` (optionally restricted to a line)."""
        return [
            e
            for e in self._adj.get(a, [])
            if e.other(a) == b and (line is None or e.line == line)
        ]

    def remove_edges(self, a: int, b: int, line: Optional[str] = None) -> int:
        """Remove edges between ``a`` and ``b``; return how many were removed."""
        removed = self.edges_between(a, b, line)
        if not removed:
            return 0
        removed_ids = {id(e) for e in removed}
        self._edges = [e for e in self._edges if id(e) not in removed_ids]
        for vertex in (a, b):
            self._adj[vertex] = [
                e for e in self._adj[vertex] if id(e) not in removed_ids
            ]
        return len(removed)

    # ------------------------------------------------------------ station lines
    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the list of lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        return list(self.station_lines.get(station_name, []))
