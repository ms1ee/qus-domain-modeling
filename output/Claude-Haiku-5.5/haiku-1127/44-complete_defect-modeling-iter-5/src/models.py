"""Core graph data structures used by the subway network.

Station nodes are identified by integer station numbers that are assigned by
the caller (see ``network.SubwayNetwork``). ``Graph`` keeps the adjacency lists
and the line affiliation of every station name.
"""


class Edge:
    """A weighted, undirected connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other(self, node):
        """Return the endpoint of this edge that is opposite to ``node``.

        Raises:
            ValueError: If ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"Node {node} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return (
            f"Edge(source={self.source!r}, dest={self.dest!r}, "
            f"distance={self.distance!r}, line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        adjacency: dict mapping station number -> list of incident ``Edge`` objects.
        station_lines: dict mapping station name -> list of line names it belongs to.
    """

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def add_node(self, node):
        """Register a station number as a node of the graph (no-op if present)."""
        self.adjacency.setdefault(node, [])

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) list of lines of a station."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge):
        """Add an undirected edge to the graph.

        Raises:
            TypeError: If ``edge`` is not an ``Edge``.
            ValueError: If the edge is a self-loop or has a non-positive distance.
        """
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        if edge.distance <= 0:
            raise ValueError("Edge distance must be positive")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge)

    def neighbors(self, node):
        """Return the list of edges incident to ``node`` (empty if unknown)."""
        return self.adjacency.get(node, [])

    def nodes(self):
        """Return the list of all station numbers in the graph."""
        return list(self.adjacency)

    def edges(self):
        """Yield every edge of the graph exactly once."""
        for node, incident in self.adjacency.items():
            for edge in incident:
                if edge.source == node:
                    yield edge

    def num_nodes(self):
        """Return the number of stations in the graph."""
        return len(self.adjacency)

    def num_edges(self):
        """Return the number of connections in the graph."""
        return sum(1 for _ in self.edges())

    def has_edge(self, a, b, line=None):
        """Return True if a connection between ``a`` and ``b`` exists (optionally on ``line``)."""
        for edge in self.neighbors(a):
            if edge.other(a) == b and (line is None or edge.line == line):
                return True
        return False

    def update_edge_distance(self, a, b, distance, line=None):
        """Update the distance of all connections between ``a`` and ``b``.

        Returns:
            int: Number of edges that were updated.
        """
        count = 0
        for edge in self.neighbors(a):
            if edge.other(a) == b and (line is None or edge.line == line):
                edge.distance = distance
                count += 1
        return count
