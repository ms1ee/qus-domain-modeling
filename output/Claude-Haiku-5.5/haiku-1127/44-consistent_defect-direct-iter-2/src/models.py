"""Graph data model for the subway network.

The graph is a weighted, directed graph. Each connection is stored as an Edge
that can only be traversed in its listed direction. Station numbers (graph
nodes) are assigned by the caller; the Graph itself only stores them.
"""


class Edge:
    """A directed, weighted connection between two stations on one line."""

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        """
        Args:
            source: station number the edge starts from.
            dest: station number the edge leads to.
            distance: actual distance between the stations in meters.
            line: name of the subway line this connection belongs to.
        """
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Base weight of the edge used by path search (distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph keyed by station numbers, with station line data."""

    def __init__(self):
        # station number -> list of outgoing Edge objects
        self._adj = {}
        # station name -> list of line names the station belongs to
        self.station_lines = {}

    # ----- node management -----
    def add_node(self, node):
        """Add a node (station number) if it does not already exist."""
        if node not in self._adj:
            self._adj[node] = []

    def has_node(self, node):
        """Return True if the node exists in the graph."""
        return node in self._adj

    def nodes(self):
        """Return a list of all node numbers."""
        return list(self._adj.keys())

    @property
    def num_nodes(self):
        """Number of nodes in the graph."""
        return len(self._adj)

    # ----- edge management -----
    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes if needed.

        Raises:
            TypeError: if edge is not an Edge.
            ValueError: if the distance is negative.
        """
        if not isinstance(edge, Edge):
            raise TypeError("edge must be an Edge instance")
        if edge.distance < 0:
            raise ValueError(f"edge distance must be non-negative: {edge!r}")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adj[edge.source].append(edge)

    def edges_from(self, node):
        """Return the outgoing edges of a node (do not mutate the returned list)."""
        return self._adj.get(node, [])

    def edges(self):
        """Yield every directed edge in the graph."""
        for outgoing in self._adj.values():
            for edge in outgoing:
                yield edge

    def find_edges(self, source, dest):
        """Return all edges from source to dest (any line)."""
        return [edge for edge in self._adj.get(source, []) if edge.dest == dest]

    @property
    def num_edges(self):
        """Number of directed edges in the graph."""
        return sum(len(outgoing) for outgoing in self._adj.values())

    # ----- station line data -----
    def set_station_lines(self, station_name, lines):
        """Set the line list of a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def get_station_lines(self, station_name):
        """Return a copy of the line list of a station (empty if unknown)."""
        return list(self.station_lines.get(station_name, []))
