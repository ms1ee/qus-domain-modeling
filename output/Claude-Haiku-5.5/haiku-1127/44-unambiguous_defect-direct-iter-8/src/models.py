"""Graph data structures for the weighted undirected subway network."""

from typing import Dict, List


class Edge:
    """A weighted undirected edge between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance in meters (also used as the edge weight).
        line: Name of the subway line that this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equals distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}-{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller (see network.SubwayNetwork).
    The graph also keeps a mapping from station name to the lines serving it.
    """

    def __init__(self):
        self._adj: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}

    # ----- vertices -------------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex (station number) if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def __contains__(self, vertex):
        return vertex in self._adj

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self._adj.keys())

    def V(self):
        """Return the number of vertices."""
        return len(self._adj)

    def E(self):
        """Return the number of undirected edges."""
        return len(self._edges)

    def set_station_lines(self, station_name, lines):
        """Record the lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    # ----- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge; both endpoints are created if necessary."""
        if edge.source == edge.dest:
            raise ValueError("self-loops are not allowed")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the adjacency list (edges incident to ``vertex``).

        The returned list is the internal list and must not be modified.
        """
        return self._adj.get(vertex, [])

    def edges(self):
        """Return a copy of the list of all edges (each listed once)."""
        return list(self._edges)

    def remove_edge(self, source, dest, line=None):
        """Remove edges between two vertices (optionally only on ``line``).

        Returns:
            int: Number of removed edges.
        """
        matches = [
            e for e in self._edges
            if {e.source, e.dest} == {source, dest} and (line is None or e.line == line)
        ]
        for edge in matches:
            self._edges.remove(edge)
            self._adj[edge.source].remove(edge)
            self._adj[edge.dest].remove(edge)
        return len(matches)

    def set_edge_distance(self, source, dest, distance, line=None):
        """Update the distance of edges between two vertices.

        Returns:
            int: Number of updated edges.
        """
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        count = 0
        for edge in self._edges:
            if {edge.source, edge.dest} == {source, dest} and (line is None or edge.line == line):
                edge.distance = distance
                count += 1
        return count
