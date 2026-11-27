"""Graph data structures used to model the subway network.

The network is a weighted undirected graph: vertices are station numbers
(assigned by the caller) and edges carry the inter-station distance in
meters as well as the subway line they belong to.
"""


class Edge:
    """An undirected weighted edge between two stations on a given line."""

    def __init__(self, source, dest, distance, line):
        if distance is None:
            raise ValueError("Edge distance must not be None")
        if distance < 0:
            raise ValueError("Edge distance must not be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        graph: dict mapping a station number to the list of incident edges
        station_lines: dict mapping a station name to the lines serving it
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edges = []

    # ----- vertices ---------------------------------------------------
    def add_vertex(self, vertex):
        self.graph.setdefault(vertex, [])

    def has_vertex(self, vertex):
        return vertex in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    # ----- station line info -----------------------------------------
    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def lines_of(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges ------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both endpoint adjacency lists)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the edges incident to ``vertex``."""
        return self.graph.get(vertex, [])

    def edges(self):
        return list(self._edges)

    def E(self):
        return len(self._edges)

    def __repr__(self):
        return f"Graph(V={self.V()}, E={self.E()})"
