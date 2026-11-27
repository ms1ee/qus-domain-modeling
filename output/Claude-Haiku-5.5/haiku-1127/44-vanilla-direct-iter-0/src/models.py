"""
Core graph data structures for the subway network.

Stations are identified by integer numbers that are assigned by the caller
(see ``subway_network.SubwayNetwork``). The graph is a weighted undirected
graph stored as adjacency lists.
"""


class Edge:
    """
    A weighted, undirected connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other_end(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """
    Weighted undirected graph implemented with adjacency lists.

    Station numbers are the vertices. ``station_lines`` maps official station
    names to the list of lines serving that station, which is used to detect
    multi-line transfer stations.
    """

    def __init__(self):
        self._adjacency = {}   # vertex -> list[Edge] (both directions stored)
        self._edges = []       # each undirected edge stored once
        self.station_lines = {}  # station name -> list[str]

    def add_vertex(self, vertex):
        """Add a vertex if it does not exist yet."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Record the lines that serve a station (duplicates removed, order kept)."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def add_edge(self, edge):
        """
        Add an undirected edge to the graph.

        Raises:
            ValueError: If the edge is a self-loop or has a negative distance.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not supported")
        if edge.distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(
            Edge(edge.dest, edge.source, edge.distance, edge.line)
        )
        self._edges.append(edge)

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex`` (oriented away from it)."""
        return self._adjacency.get(vertex, [])

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adjacency)

    def edges(self):
        """Return a list of all undirected edges (each stored once)."""
        return list(self._edges)

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adjacency)

    def num_edges(self):
        """Return the number of undirected edges."""
        return len(self._edges)
