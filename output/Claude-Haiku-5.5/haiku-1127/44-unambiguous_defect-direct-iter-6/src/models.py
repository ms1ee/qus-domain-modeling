"""Core graph data structures for the subway network.

Stations are identified by integer numbers in the graph. The mapping from
station names to numbers is maintained by the caller (see ``network.py``).
The graph is a weighted undirected graph stored as adjacency lists.
"""


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (the distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
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
    """Weighted undirected graph implemented with adjacency lists.

    Vertices are station numbers (integers). Each edge is stored in the
    adjacency list of both of its endpoints.

    Attributes:
        station_lines: Mapping from station name to the list of line names
            the station belongs to.
    """

    def __init__(self):
        self._adj = {}
        self.station_lines = {}

    # ----- vertex management -------------------------------------------------

    def add_vertex(self, vertex):
        """Add a vertex if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adj.keys())

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self._adj)

    def set_station_lines(self, station_name, lines):
        """Record the line names a station belongs to."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management ---------------------------------------------------

    def add_edge(self, edge):
        """Insert an undirected edge.

        If an edge between the same pair of stations on the same line already
        exists, it is replaced.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        for old in self.find_edges(edge.source, edge.dest, edge.line):
            self._remove_edge_object(old)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)

    def find_edges(self, u, v, line=None):
        """Return all edges between ``u`` and ``v`` (optionally on one line)."""
        if u not in self._adj:
            return []
        result = []
        for edge in self._adj[u]:
            if edge.other(u) == v and (line is None or edge.line == line):
                result.append(edge)
        return result

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self._adj.get(vertex, [])

    def edges(self):
        """Return every edge exactly once."""
        result = []
        for vertex, incident in self._adj.items():
            for edge in incident:
                if edge.source == vertex:
                    result.append(edge)
        return result

    def edge_count(self):
        """Return the number of undirected edges."""
        return len(self.edges())

    def _remove_edge_object(self, edge):
        """Remove an edge object from both endpoint adjacency lists."""
        self._adj[edge.source].remove(edge)
        self._adj[edge.dest].remove(edge)
