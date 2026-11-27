"""Core graph data structures used to model the subway network.

Station numbers (vertices) are plain hashable values assigned by the caller
(see ``subway_network.SubwayNetwork``). ``Graph`` only manages vertices,
undirected weighted edges and the per-station line affiliation table.
"""


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations, in meters.
        line: Name of the subway line that operates this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("edge distance must be a number of meters")
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equals the distance)."""
        return self.distance

    def other_endpoint(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex!r} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex if it is not already present."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if ``vertex`` is part of the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Record the line names a station belongs to."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Insert an undirected edge, creating its endpoints if needed.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loops are not supported")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        """Remove an edge from the graph.

        Raises:
            ValueError: If the edge is not part of the graph.
        """
        if not any(existing is edge for existing in self._edges):
            raise ValueError("edge is not part of the graph")
        self._edges = [existing for existing in self._edges if existing is not edge]
        self._adjacency[edge.source] = [
            existing for existing in self._adjacency[edge.source] if existing is not edge
        ]
        self._adjacency[edge.dest] = [
            existing for existing in self._adjacency[edge.dest] if existing is not edge
        ]

    def adjacent_edges(self, vertex):
        """Return the list of edges incident to ``vertex`` (do not mutate)."""
        if vertex not in self._adjacency:
            raise KeyError(f"vertex {vertex!r} is not in the graph")
        return self._adjacency[vertex]

    def neighbors(self, vertex):
        """Yield ``(edge, neighbor_vertex)`` pairs for ``vertex``."""
        for edge in self.adjacent_edges(vertex):
            yield edge, edge.other_endpoint(vertex)

    def find_edges(self, u, v):
        """Return all edges directly connecting ``u`` and ``v``."""
        if u not in self._adjacency:
            return []
        return [edge for edge in self._adjacency[u] if edge.other_endpoint(u) == v]

    def edges(self):
        """Return a list of all edges."""
        return list(self._edges)

    @property
    def num_vertices(self):
        return len(self._adjacency)

    @property
    def num_edges(self):
        return len(self._edges)
