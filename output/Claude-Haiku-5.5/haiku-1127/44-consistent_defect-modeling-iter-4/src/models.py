"""Core graph data structures for the subway network.

The network is a weighted *directed* graph: every ``Edge`` can only be
traversed in the direction it was declared. Station numbers are assigned by
the caller (see ``network.SubwayNetwork``), not by ``Graph``.
"""


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: station number of the origin station.
        dest: station number of the destination station.
        distance: actual inter-station distance in meters (the base weight).
        line: name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Base weight of the edge (equal to its distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance} m, {self.line!r})"


class Graph:
    """Weighted directed graph stored as adjacency lists.

    Nodes are station numbers. ``station_lines`` maps station names to the
    list of lines serving them, which is needed for transfer detection.
    """

    def __init__(self):
        self._adjacency = {}      # node -> list[Edge] (outgoing edges)
        self._edge_count = 0
        self.station_lines = {}   # station name -> list[str]

    # ------------------------------------------------------------------
    # Size information
    # ------------------------------------------------------------------
    @property
    def node_count(self):
        """Number of nodes (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of directed edges in the graph."""
        return self._edge_count

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------
    def add_node(self, node):
        """Add a node if it is not already present."""
        self._adjacency.setdefault(node, [])

    def has_node(self, node):
        """Return True if the node exists in the graph."""
        return node in self._adjacency

    def nodes(self):
        """Return the list of node identifiers."""
        return list(self._adjacency.keys())

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving a station."""
        return list(self.station_lines.get(station_name, []))

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge, creating its nodes if necessary.

        If an edge with the same source, destination and line already exists,
        its distance is overwritten instead of creating a duplicate.

        Returns:
            bool: True if a new edge was created, False if an existing one was updated.
        """
        self.add_node(edge.source)
        self.add_node(edge.dest)
        for existing in self._adjacency[edge.source]:
            if existing.dest == edge.dest and existing.line == edge.line:
                existing.distance = edge.distance
                return False
        self._adjacency[edge.source].append(edge)
        self._edge_count += 1
        return True

    def adj(self, node):
        """Return the outgoing edges of a node (internal list, do not modify)."""
        return self._adjacency.get(node, [])

    def get_edges(self, source, dest):
        """Return all edges going from ``source`` to ``dest``."""
        return [edge for edge in self._adjacency.get(source, []) if edge.dest == dest]

    def edges(self):
        """Yield every edge in the graph."""
        for node_edges in self._adjacency.values():
            for edge in node_edges:
                yield edge
