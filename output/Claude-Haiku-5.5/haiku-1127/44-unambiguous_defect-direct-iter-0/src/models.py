"""Graph data structures used to model the subway network.

The graph is an undirected, weighted graph stored as adjacency lists.
Vertices are station numbers assigned by the caller (see
``subway_network.SubwayNetwork``); edges carry the inter-station distance
in meters as their weight and the line on which the connection runs.
"""


class Edge:
    """An undirected weighted edge between two stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: inter-station distance in meters (also exposed as ``weight``).
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
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
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
        adj: dict mapping station number -> list of incident Edge objects.
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self._edges = []

    # ----- vertex management -------------------------------------------
    def add_node(self, vertex):
        """Add a vertex if it does not exist yet."""
        if vertex not in self.adj:
            self.adj[vertex] = []

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self.adj

    def vertices(self):
        """Return the list of all vertices."""
        return list(self.adj.keys())

    # ----- station metadata --------------------------------------------
    def set_station_lines(self, station_name, lines):
        """Store the list of lines that serve a station (keyed by name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the line list for a station name."""
        return list(self.station_lines.get(station_name, []))

    # ----- edge management ---------------------------------------------
    def add_edge(self, edge):
        """Insert an undirected edge, creating missing endpoints."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        """Remove an edge object from the graph."""
        self.adj[edge.source].remove(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].remove(edge)
        self._edges.remove(edge)

    def adjacent(self, vertex):
        """Return a copy of the list of edges incident to ``vertex``."""
        return list(self.adj.get(vertex, []))

    def edges_between(self, u, v):
        """Return all edges joining vertices ``u`` and ``v``."""
        result = []
        for edge in self.adj.get(u, []):
            if (edge.source == u and edge.dest == v) or (edge.source == v and edge.dest == u):
                result.append(edge)
        return result

    def edges(self):
        """Return a copy of all edges (each undirected edge listed once)."""
        return list(self._edges)

    # ----- statistics --------------------------------------------------
    @property
    def num_vertices(self):
        return len(self.adj)

    @property
    def num_edges(self):
        return len(self._edges)
