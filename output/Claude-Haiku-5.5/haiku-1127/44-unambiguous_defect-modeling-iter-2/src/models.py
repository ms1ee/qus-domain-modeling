"""Graph data structures used to model the subway network.

Stations are identified by integer numbers that are assigned by the caller
(see ``network.SubwayNetwork``). ``Graph`` stores an undirected adjacency list
in which every ``Edge`` object is shared by both of its endpoints.
"""

try:
    from .min_pq import MinPQ  # noqa: F401  (re-exported for convenience)
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from min_pq import MinPQ  # noqa: F401


def validate_distance(distance):
    """Validate a distance value in meters.

    Args:
        distance: Numeric distance.

    Returns:
        The validated distance unchanged.

    Raises:
        TypeError: If the value is not an int or float.
        ValueError: If the value is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number, got {type(distance).__name__}")
    if distance != distance or distance < 0:
        raise ValueError(f"Distance must be a non-negative number, got {distance}")
    return distance


class Edge:
    """An undirected, weighted connection between two adjacent stations on a line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if source == dest:
            raise ValueError("An edge must connect two different stations")
        self.source = source
        self.dest = dest
        self.distance = validate_distance(distance)
        self.line = str(line)

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def set_distance(self, distance):
        """Update the distance of this connection after validation."""
        self.distance = validate_distance(distance)

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    The graph also keeps ``station_lines``, mapping each station name to the
    list of lines serving it, which is used to detect interchange stations.
    """

    def __init__(self):
        self._adj = {}
        self._edge_count = 0
        self.station_lines = {}

    @property
    def vertex_count(self):
        """Number of vertices in the graph."""
        return len(self._adj)

    @property
    def edge_count(self):
        """Number of undirected edges in the graph."""
        return self._edge_count

    @property
    def is_undirected(self):
        """The subway graph is always undirected."""
        return True

    def add_vertex(self, vertex):
        """Add a vertex (station number) if it does not already exist."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists."""
        return vertex in self._adj

    def vertices(self):
        """Return the list of all vertices."""
        return list(self._adj)

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        if vertex not in self._adj:
            raise KeyError(f"Unknown vertex: {vertex}")
        return list(self._adj[vertex])

    def neighbors(self, vertex):
        """Return a list of ``(neighbor_vertex, edge)`` tuples for ``vertex``."""
        return [(edge.other(vertex), edge) for edge in self._adj.get(vertex, [])]

    def add_edge(self, edge):
        """Add an undirected edge to the graph.

        Raises:
            ValueError: If an edge with the same endpoints and line already exists.
        """
        if self.find_edge(edge.source, edge.dest, edge.line) is not None:
            raise ValueError(
                f"Duplicate connection between {edge.source} and {edge.dest} on {edge.line}"
            )
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edge_count += 1

    def find_edge(self, a, b, line=None):
        """Return the edge between ``a`` and ``b`` (optionally on ``line``) or None."""
        for edge in self._adj.get(a, []):
            if edge.other(a) == b and (line is None or edge.line == line):
                return edge
        return None

    def edges(self):
        """Yield every undirected edge exactly once."""
        for vertex, incident in self._adj.items():
            for edge in incident:
                if edge.source == vertex:
                    yield edge

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
