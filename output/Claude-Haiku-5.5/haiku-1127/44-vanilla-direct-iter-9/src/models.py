"""Graph data structures for the Beijing Subway network.

Stations are identified by integer numbers assigned by the caller (see
``subway_network.SubwayNetwork``). The graph is an undirected weighted graph
whose adjacency lists hold shared ``Edge`` objects.
"""

from typing import Dict, Hashable, List, Optional


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: Hashable, dest: Hashable, distance: float, line: str):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    @weight.setter
    def weight(self, value: float) -> None:
        if value < 0:
            raise ValueError("Edge weight must be non-negative")
        self.distance = value

    def other(self, vertex: Hashable) -> Hashable:
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Also keeps ``station_lines``, a mapping from station name to the list of
    lines serving that station, which is used for transfer-station handling.
    """

    def __init__(self) -> None:
        self._adj: Dict[Hashable, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ----- node management -------------------------------------------------
    def add_node(self, vertex: Hashable) -> None:
        """Add a vertex if it does not already exist."""
        self._adj.setdefault(vertex, [])

    def has_node(self, vertex: Hashable) -> bool:
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def nodes(self) -> List[Hashable]:
        """Return all vertices as a list."""
        return list(self._adj.keys())

    @property
    def num_nodes(self) -> int:
        """Number of vertices."""
        return len(self._adj)

    def adj(self, vertex: Hashable) -> List[Edge]:
        """Return the adjacency list of ``vertex``. Callers must not mutate it.

        Raises:
            KeyError: If the vertex does not exist.
        """
        if vertex not in self._adj:
            raise KeyError(f"Vertex {vertex!r} is not in the graph")
        return self._adj[vertex]

    # ----- edge management -------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Insert an undirected edge into the adjacency lists of both endpoints."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)

    def find_edges(self, u: Hashable, v: Hashable, line: Optional[str] = None) -> List[Edge]:
        """Return all edges between ``u`` and ``v``, optionally filtered by line."""
        result: List[Edge] = []
        for edge in self._adj.get(u, []):
            if edge.other(u) == v and (line is None or edge.line == line):
                result.append(edge)
        return result

    def remove_edge(self, u: Hashable, v: Hashable, line: Optional[str] = None) -> int:
        """Remove edges between ``u`` and ``v`` (optionally on one line).

        Returns:
            The number of edges removed.
        """
        targets = self.find_edges(u, v, line)
        for edge in targets:
            for node in (edge.source, edge.dest):
                self._adj[node] = [e for e in self._adj[node] if e is not edge]
        return len(targets)

    def edges(self) -> List[Edge]:
        """Return every distinct edge exactly once."""
        seen = set()
        result: List[Edge] = []
        for edge_list in self._adj.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    @property
    def num_edges(self) -> int:
        """Number of distinct edges."""
        return len(self.edges())

    # ----- station line information ----------------------------------------
    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the list of lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return a copy of the lines serving a station (empty if unknown)."""
        return list(self.station_lines.get(station_name, []))
