"""Core graph data structures for the subway network.

Station numbers (vertices) are integers assigned by the caller; the Graph
class only stores them. The graph is an undirected weighted graph stored as
adjacency lists.
"""

from typing import Dict, Hashable, List


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    def __init__(self, source: int, dest: int, distance: int, line: str) -> None:
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> int:
        """Edge weight used by shortest path algorithms (equal to distance)."""
        return self.distance

    def either(self) -> int:
        """Return one endpoint of the edge."""
        return self.source

    def other(self, vertex: int) -> int:
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with station metadata.

    Attributes:
        graph: Adjacency lists, mapping station number -> list of incident Edges.
        station_lines: Mapping station name -> list of line names serving it.
    """

    def __init__(self) -> None:
        self.graph: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self._edges: List[Edge] = []

    def add_vertex(self, v: Hashable) -> None:
        """Add a station vertex if it does not already exist."""
        self.graph.setdefault(v, [])

    def has_vertex(self, v: Hashable) -> bool:
        """Return True if the vertex exists in the graph."""
        return v in self.graph

    def vertices(self) -> List[Hashable]:
        """Return all vertices in insertion order."""
        return list(self.graph.keys())

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, registering both endpoints as vertices."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, v: Hashable) -> List[Edge]:
        """Return the edges incident to vertex ``v``."""
        return self.graph.get(v, [])

    def edges(self) -> List[Edge]:
        """Return all edges of the graph (each counted once)."""
        return list(self._edges)

    @property
    def num_vertices(self) -> int:
        """Number of vertices (stations)."""
        return len(self.graph)

    @property
    def num_edges(self) -> int:
        """Number of edges (connections)."""
        return len(self._edges)

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Record the lines serving a station (by station name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return the lines serving a station, or an empty list if unknown."""
        return list(self.station_lines.get(station_name, []))
