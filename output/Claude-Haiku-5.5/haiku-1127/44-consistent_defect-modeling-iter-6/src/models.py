"""
Core graph data structures for the subway network.

The network is modelled as a weighted directed graph. Vertices are station
numbers (assigned by the caller), edges carry the inter-station distance in
meters and the name of the line they belong to.
"""

from typing import Dict, List, Optional


class Edge:
    """A directed connection between two stations.

    Attributes:
        source: Station number of the origin station.
        dest: Station number of the destination station.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def __repr__(self) -> str:
        return f"Edge({self.source}->{self.dest}, {self.distance}m, line={self.line!r})"


class Graph:
    """Weighted directed graph implemented with adjacency lists.

    Station numbers are assigned externally; the graph only stores them as
    vertices. Station names and their line affiliations are kept in
    ``station_lines`` keyed by station name.

    Attributes:
        station_lines: Mapping of station name to the list of lines serving it.
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex: int) -> None:
        """Add a vertex (station number) if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def vertices(self) -> List[int]:
        """Return all vertices in insertion order."""
        return list(self._adj.keys())

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Record the lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge, creating its endpoints when needed."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adjacent(self, vertex: int) -> List[Edge]:
        """Return the outgoing edges of a vertex."""
        return self._adj.get(vertex, [])

    def edges(self) -> List[Edge]:
        """Return every edge in the graph."""
        result: List[Edge] = []
        for edge_list in self._adj.values():
            result.extend(edge_list)
        return result

    def update_edge_distance(
        self, source: int, dest: int, distance: float, line: Optional[str] = None
    ) -> int:
        """Update the distance of matching edges.

        Args:
            source: Origin station number.
            dest: Destination station number.
            distance: New distance in meters.
            line: Optional line filter.

        Returns:
            Number of edges updated.
        """
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        count = 0
        for edge in self.adjacent(source):
            if edge.dest == dest and (line is None or edge.line == line):
                edge.distance = distance
                count += 1
        return count

    def remove_edges(self, source: int, dest: int, line: Optional[str] = None) -> int:
        """Remove matching edges and return how many were removed."""
        if source not in self._adj:
            return 0
        before = len(self._adj[source])
        self._adj[source] = [
            e for e in self._adj[source]
            if not (e.dest == dest and (line is None or e.line == line))
        ]
        return before - len(self._adj[source])

    # ----- statistics --------------------------------------------------------
    @property
    def vertex_count(self) -> int:
        """Number of vertices."""
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        """Number of directed edges."""
        return sum(len(edge_list) for edge_list in self._adj.values())
