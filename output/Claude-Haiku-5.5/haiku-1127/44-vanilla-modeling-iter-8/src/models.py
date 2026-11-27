"""Core graph data structures for the subway network.

The graph is a weighted undirected graph. Station numbers (integers) are assigned
by the caller (see ``subway_network.SubwayNetwork``); the graph itself only stores
station numbers, edges and the lines that serve each station (keyed by name).
"""


class Edge:
    """A railway connection between two stations.

    Attributes:
        source: Station number of the origin of this directed view of the edge.
        dest: Station number of the destination.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative, got %r" % (distance,))
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (vertex,))

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph implemented with adjacency lists.

    Every edge added with :meth:`add_edge` is stored in both adjacency lists, so
    traversal algorithms can use :meth:`adjacent` directly.

    Attributes:
        station_lines: dict mapping station name -> list of line names serving it.
    """

    def __init__(self):
        self._adj = {}          # station number -> list[Edge] (directed views)
        self._edges = []        # original undirected edges, in insertion order
        self.station_lines = {}  # station name -> list[str]

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a station number to the graph if it is not present yet."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the station number exists in the graph."""
        return vertex in self._adj

    def vertices(self):
        """Return the list of station numbers in the graph."""
        return list(self._adj.keys())

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (replaces any previous value)."""
        self.station_lines[station_name] = list(lines)

    def lines_of(self, station_name):
        """Return the list of lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge. Both endpoints are created if necessary."""
        if edge.weight < 0:
            raise ValueError("Edge weight must be non-negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))
        self._edges.append(edge)

    def adjacent(self, vertex):
        """Return the list of edges leaving ``vertex`` (as directed Edge objects)."""
        return self._adj.get(vertex, [])

    def edges(self):
        """Return the list of undirected edges as originally added."""
        return list(self._edges)

    # ----- statistics --------------------------------------------------------
    @property
    def num_vertices(self):
        return len(self._adj)

    @property
    def num_edges(self):
        return len(self._edges)

    def __repr__(self):
        return "Graph(vertices=%d, edges=%d)" % (self.num_vertices, self.num_edges)
