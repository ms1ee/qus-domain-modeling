"""Core graph data structures for the subway network.

Stations are identified by integer numbers that are assigned by the caller
(see network.SubwayNetwork). The graph is an undirected weighted graph whose
edge weight is the physical distance in meters.
"""


class Edge:
    """An undirected weighted edge between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
        weight: Edge weight used by path algorithms (equal to distance).
        line: Name of the subway line this connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        adj: dict mapping station number -> list of incident Edge objects.
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Register a station number as a vertex (no-op if already present)."""
        self.adj.setdefault(vertex, [])

    def add_edge(self, edge):
        """Add an undirected edge, registering both endpoints as vertices."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)

    def remove_edge(self, edge):
        """Remove an edge from both endpoint adjacency lists."""
        for vertex in {edge.source, edge.dest}:
            self.adj[vertex] = [e for e in self.adj.get(vertex, []) if e is not edge]

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self.adj.get(vertex, [])

    def vertices(self):
        """Return the list of all station numbers in the graph."""
        return list(self.adj.keys())

    def edges(self):
        """Return every distinct edge exactly once."""
        seen = set()
        result = []
        for edge_list in self.adj.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self.adj)

    def edge_count(self):
        """Return the number of distinct edges."""
        return len(self.edges())

    def set_station_lines(self, station_name, lines):
        """Record the list of lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the list of lines serving a station (by name)."""
        return list(self.station_lines.get(station_name, []))
