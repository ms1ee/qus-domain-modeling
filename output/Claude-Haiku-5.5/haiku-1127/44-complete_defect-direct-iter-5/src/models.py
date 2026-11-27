"""Graph data structures used to model the subway network.

Stations are identified by integer station numbers assigned by the caller
(see ``subway_network.SubwayNetwork``). The graph is an undirected weighted
graph stored as adjacency lists; each undirected edge is stored once in each
endpoint's adjacency list so that traversal is direction-aware.
"""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional


class Edge:
    """A weighted connection between two stations.

    Attributes:
        source: Station number of the origin endpoint.
        dest: Station number of the destination endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def __repr__(self) -> str:
        return (
            f"Edge(source={self.source}, dest={self.dest}, "
            f"distance={self.distance}, line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: Mapping from station name to the list of line names
            the station belongs to (transfer stations have several lines).
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Vertex management
    # ------------------------------------------------------------------
    def add_vertex(self, v: int) -> None:
        """Add a vertex if it is not already present."""
        self._adj.setdefault(v, [])

    def has_vertex(self, v: int) -> bool:
        """Return True if the vertex exists in the graph."""
        return v in self._adj

    def vertices(self) -> List[int]:
        """Return all vertex identifiers."""
        return list(self._adj.keys())

    def num_vertices(self) -> int:
        """Return the number of vertices."""
        return len(self._adj)

    def adj(self, v: int) -> List[Edge]:
        """Return the outgoing adjacency list of vertex ``v``.

        Raises:
            KeyError: If the vertex does not exist.
        """
        if v not in self._adj:
            raise KeyError(f"Unknown vertex: {v}")
        return self._adj[v]

    def set_station_lines(self, station_name: str, lines: Iterable[str]) -> None:
        """Set the line affiliations of a station, removing duplicates while keeping order."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def get_edge(self, a: int, b: int) -> Optional[Edge]:
        """Return the edge from ``a`` to ``b`` if it exists, otherwise None."""
        for edge in self._adj.get(a, []):
            if edge.dest == b:
                return edge
        return None

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge. If the pair is already connected, the
        existing connection is updated with the new distance and line.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)

        existing = self.get_edge(edge.source, edge.dest)
        if existing is not None:
            existing.distance = edge.distance
            existing.line = edge.line
            reverse = self.get_edge(edge.dest, edge.source)
            if reverse is not None:
                reverse.distance = edge.distance
                reverse.line = edge.line
            return

        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def set_edge_distance(self, a: int, b: int, distance: float) -> bool:
        """Update the distance of the connection between ``a`` and ``b``.

        Returns:
            True if the connection existed and was updated, False otherwise.

        Raises:
            ValueError: If the distance is negative.
        """
        if distance < 0:
            raise ValueError("Distance cannot be negative")
        forward = self.get_edge(a, b)
        if forward is None:
            return False
        forward.distance = distance
        backward = self.get_edge(b, a)
        if backward is not None:
            backward.distance = distance
        return True

    def edges(self) -> Iterator[Edge]:
        """Yield each undirected edge exactly once (oriented from lower to higher id)."""
        for lst in self._adj.values():
            for edge in lst:
                if edge.source < edge.dest:
                    yield edge

    def num_edges(self) -> int:
        """Return the number of undirected edges."""
        return sum(1 for _ in self.edges())
