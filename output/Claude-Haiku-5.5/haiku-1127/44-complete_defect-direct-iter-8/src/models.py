"""Graph data structures for the subway network.

Station numbers (vertex identifiers) are assigned by the caller, not by Graph.
"""


class Edge:
    """A weighted, undirected connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            raise ValueError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path search (equals the distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint of this edge that is not `vertex`.

        Raises:
            ValueError: If `vertex` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, "
                f"distance={self.distance!r}, line={self.line!r})")


class Graph:
    """Weighted undirected graph represented with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names serving it.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex (station number) if it is not already present."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return a sorted list of all vertex identifiers."""
        return sorted(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (replaces any previous value)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the list of lines serving a station (empty if unknown)."""
        return list(self.station_lines.get(station_name, []))

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge, registering both endpoints as vertices."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        """Remove an edge from the graph.

        Raises:
            ValueError: If the edge is not part of the graph.
        """
        if edge not in self._edges:
            raise ValueError("Edge is not part of this graph")
        self._edges.remove(edge)
        self._adjacency[edge.source].remove(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].remove(edge)

    def adjacent(self, vertex):
        """Return a tuple of edges incident to `vertex`."""
        return tuple(self._adjacency.get(vertex, ()))

    def edges_between(self, u, v):
        """Return all edges joining vertices u and v (in either direction)."""
        return [edge for edge in self._adjacency.get(u, ()) if edge.other(u) == v]

    def edges(self):
        """Return a list of all edges in the graph."""
        return list(self._edges)

    @property
    def num_vertices(self):
        """Number of vertices in the graph."""
        return len(self._adjacency)

    @property
    def num_edges(self):
        """Number of edges in the graph."""
        return len(self._edges)
