"""Graph data structures used to model the subway network.

Station numbers (vertices) are assigned by the caller (see ``network.py``);
the graph itself only stores adjacency information and per-station line
affiliations keyed by station name.
"""


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: number of the first station.
        dest: number of the second station.
        distance: physical distance in meters (also used as the edge weight).
        line: name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: if ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex {} is not an endpoint of {!r}".format(vertex, self))

    def __repr__(self):
        return "Edge({!r}, {!r}, {!r}, {!r})".format(self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Vertices are station numbers (integers). ``station_lines`` maps official
    station names to the list of line names serving that station.
    """

    def __init__(self):
        self._adjacency = {}   # station number -> list[Edge]
        self._edges = []       # every edge exactly once
        self.station_lines = {}  # station name -> list[str]

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex if it does not already exist."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex is present in the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adjacency.keys())

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station (replaces any previous value)."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge; both endpoints are created if missing."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the list of edges incident to ``vertex`` (treat as read-only)."""
        return self._adjacency.get(vertex, [])

    def edges(self):
        """Return a list of all edges (each undirected edge appears once)."""
        return list(self._edges)

    def num_edges(self):
        """Return the number of undirected edges."""
        return len(self._edges)

    def find_edge(self, u, v, line=None):
        """Find an edge between ``u`` and ``v``, optionally restricted to a line.

        Returns:
            The matching Edge, or None if no such edge exists.
        """
        for edge in self._adjacency.get(u, []):
            if edge.other(u) == v and (line is None or edge.line == line):
                return edge
        return None
