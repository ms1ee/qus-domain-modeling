"""Core graph data structures for the subway network.

Station numbers (integers) are assigned by the caller (see ``network.py``);
``Graph`` only manages adjacency and per-station line information.
"""

from typing import Dict, Iterator, List


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: actual distance between the stations in meters.
        line: name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: int, line: str) -> None:
        if distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = int(distance)
        self.line = line

    @property
    def weight(self) -> int:
        """Edge weight used by shortest-path algorithms (equals the distance)."""
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
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph represented with adjacency lists.

    Attributes:
        adj: mapping from station number to the list of incident edges.
        station_lines: mapping from station name to the list of line names
            the station belongs to.
    """

    def __init__(self) -> None:
        self.adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ----- station line management -------------------------------------
    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set (replace) the line affiliations of a station, removing duplicates."""
        unique_lines = list(dict.fromkeys(lines))
        self.station_lines[station_name] = unique_lines

    # ----- vertex / edge management ------------------------------------
    def add_vertex(self, vertex: int) -> None:
        """Ensure that ``vertex`` exists in the adjacency structure."""
        self.adj.setdefault(vertex, [])

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, registering it in both endpoints' lists."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)

    def remove_edges_between(self, a: int, b: int) -> int:
        """Remove every edge joining vertices ``a`` and ``b``.

        Returns:
            The number of removed edges.
        """
        removed = 0
        for vertex, other_vertex in ((a, b), (b, a)):
            incident = self.adj.get(vertex, [])
            kept = [e for e in incident if e.other(vertex) != other_vertex]
            removed += len(incident) - len(kept)
            self.adj[vertex] = kept
        # Each removed undirected edge was counted once per endpoint.
        return removed // 2 if a != b else removed

    def neighbors(self, vertex: int) -> List[Edge]:
        """Return the list of edges incident to ``vertex`` (do not mutate)."""
        return self.adj.get(vertex, [])

    def vertices(self) -> List[int]:
        """Return all vertex (station number) identifiers."""
        return list(self.adj.keys())

    def edges(self) -> Iterator[Edge]:
        """Yield every undirected edge exactly once."""
        for vertex, incident in self.adj.items():
            for edge in incident:
                if edge.source == vertex:
                    yield edge

    def edge_count(self) -> int:
        """Return the number of undirected edges."""
        return sum(1 for _ in self.edges())

    def __len__(self) -> int:
        return len(self.adj)
