"""Core graph data structures: Edge and Graph.

The graph is a weighted undirected graph whose nodes are station numbers
(assigned by the caller) and whose edges carry the inter-station distance in
meters together with the subway line the edge belongs to.
"""


class Edge:
    """A weighted, undirected connection between two stations on one line.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters (also exposed as ``weight``).
        line: name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
        return self.distance

    @weight.setter
    def weight(self, value):
        self.distance = float(value)

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: if ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("vertex {} is not an endpoint of this edge".format(vertex))

    def __repr__(self):
        return "Edge({}, {}, {}, {!r})".format(
            self.source, self.dest, self.distance, self.line
        )


class Graph:
    """Weighted undirected graph represented with adjacency lists.

    Station numbers are supplied by the caller. The graph also keeps a
    ``station_lines`` mapping from station name to the lines serving it, which
    is used to identify transfer stations.
    """

    def __init__(self):
        self._adjacency = {}      # node -> list[Edge]
        self._edge_count = 0
        self.station_lines = {}   # station name -> list[str]

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def node_count(self):
        """Number of nodes (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of edges added to the graph."""
        return self._edge_count

    @property
    def is_weighted(self):
        """The graph always carries distance weights."""
        return True

    @property
    def is_undirected(self):
        """The graph is always undirected."""
        return True

    # ------------------------------------------------------------------ #
    # Node management
    # ------------------------------------------------------------------ #
    def add_node(self, node):
        """Register a node if it is not already present."""
        self._adjacency.setdefault(node, [])

    def has_node(self, node):
        """Return True if ``node`` exists in the graph."""
        return node in self._adjacency

    def nodes(self):
        """Return the list of node identifiers."""
        return list(self._adjacency)

    # ------------------------------------------------------------------ #
    # Edge management
    # ------------------------------------------------------------------ #
    def add_edge(self, edge):
        """Add an undirected edge, registering both endpoints as needed.

        Raises:
            ValueError: for self-loops or negative distances.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loops are not allowed: {}".format(edge.source))
        if edge.distance < 0:
            raise ValueError("edge distance must not be negative")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edge_count += 1

    def adjacent(self, node):
        """Return the list of edges incident to ``node`` (empty if unknown)."""
        return self._adjacency.get(node, [])

    def edges_between(self, node_a, node_b):
        """Return all edges directly connecting two nodes."""
        return [edge for edge in self.adjacent(node_a) if edge.other(node_a) == node_b]

    def edges(self):
        """Return every distinct edge in the graph exactly once."""
        seen = set()
        result = []
        for edge_list in self._adjacency.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    # ------------------------------------------------------------------ #
    # Station line information
    # ------------------------------------------------------------------ #
    def set_station_lines(self, station_name, lines):
        """Store the list of lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving a station."""
        return list(self.station_lines.get(station_name, []))
