"""Core graph data structures: edges and a weighted directed graph.

Station numbers (integers) are assigned by the caller (see ``network.py``);
the graph itself only stores numbers and the per-station line information
keyed by station name.
"""


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: Station number where the connection starts.
        dest: Station number where the connection ends.
        line: Name of the subway line this connection belongs to.

    Properties:
        distance: Actual distance between the stations in meters.
        weight: Edge weight used by path search (equal to ``distance``).
    """

    __slots__ = ("source", "dest", "_distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self._distance = distance
        self.line = line

    @property
    def distance(self):
        """Distance between the two stations in meters."""
        return self._distance

    @distance.setter
    def distance(self, value):
        if value < 0:
            raise ValueError("Edge distance must be non-negative")
        self._distance = value

    @property
    def weight(self):
        """Edge weight used by Dijkstra's algorithm (equal to distance)."""
        return self._distance

    def __repr__(self):
        return (f"Edge(source={self.source}, dest={self.dest}, "
                f"distance={self._distance}, line={self.line!r})")


class Graph:
    """Weighted directed graph stored as adjacency lists.

    Each connection is usable only in its listed direction. Station numbers
    are supplied by the caller.

    Attributes:
        station_lines: Mapping of station name to the list of lines serving it.
    """

    def __init__(self):
        # Adjacency lists: station number -> list of outgoing Edge objects.
        self._adj = {}
        self.station_lines = {}

    # ----- node management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a station number as a node if it is not already present."""
        if vertex not in self._adj:
            self._adj[vertex] = []

    def has_vertex(self, vertex) -> bool:
        """Return True if the station number is a node of the graph."""
        return vertex in self._adj

    def vertices(self) -> list:
        """Return all station numbers in the graph."""
        return list(self._adj.keys())

    def num_vertices(self) -> int:
        """Return the number of nodes."""
        return len(self._adj)

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (replacing any previous value)."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management -------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes if necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adj(self, vertex) -> list:
        """Return the outgoing edges of a station number."""
        return self._adj[vertex]

    def get_edges_between(self, source, dest) -> list:
        """Return all edges going from ``source`` to ``dest``."""
        if source not in self._adj:
            return []
        return [e for e in self._adj[source] if e.dest == dest]

    def edges(self) -> list:
        """Return every edge in the graph."""
        result = []
        for edge_list in self._adj.values():
            result.extend(edge_list)
        return result

    def num_edges(self) -> int:
        """Return the number of directed edges."""
        return sum(len(edge_list) for edge_list in self._adj.values())
