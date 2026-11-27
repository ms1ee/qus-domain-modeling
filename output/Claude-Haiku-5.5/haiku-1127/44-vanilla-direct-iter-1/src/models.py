"""Core graph data structures for the subway network.

The ``Graph`` is a weighted undirected graph. Vertices are station numbers
(assigned by the caller, normally ``network.SubwayNetwork``), and each
``Edge`` carries the inter-station distance (in meters) and the line it
belongs to.
"""


class Edge:
    """An undirected, weighted connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line that operates this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
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
        raise ValueError(f"Vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: Mapping of station name to the list of line names that
            serve that station (used for transfer detection and validation).
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    # ------------------------------------------------------------------
    # Vertex management
    # ------------------------------------------------------------------
    def add_vertex(self, vertex):
        """Add ``vertex`` to the graph if it is not already present."""
        if vertex not in self._adjacency:
            self._adjacency[vertex] = []

    def has_vertex(self, vertex):
        """Return True if ``vertex`` exists in the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return a list of all vertices (station numbers)."""
        return list(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Set the lines serving ``station_name``, removing duplicates while
        keeping the original order."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge, registering both endpoints as vertices."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the list of edges incident to ``vertex`` (read-only use)."""
        return self._adjacency.get(vertex, [])

    def edges(self):
        """Return a list of all edges in the graph."""
        return list(self._edges)

    def find_edges(self, u, v):
        """Return all edges connecting vertices ``u`` and ``v``."""
        return [edge for edge in self.adj(u) if edge.other(u) == v]

    def update_distance(self, u, v, distance, line=None):
        """Update the distance of edges between ``u`` and ``v``.

        Args:
            u: First station number.
            v: Second station number.
            distance: New distance in meters.
            line: If given, only edges on this line are updated.

        Returns:
            int: Number of edges updated.
        """
        count = 0
        for edge in self.find_edges(u, v):
            if line is None or edge.line == line:
                edge.distance = distance
                count += 1
        return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    @property
    def num_vertices(self):
        """Number of stations in the graph."""
        return len(self._adjacency)

    @property
    def num_edges(self):
        """Number of connections in the graph."""
        return len(self._edges)
