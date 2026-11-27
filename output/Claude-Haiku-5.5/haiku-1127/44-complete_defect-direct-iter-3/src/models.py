"""
Graph data structures for the subway network.

The graph is a weighted undirected graph stored as adjacency lists. Station
numbers (integers) are assigned by the caller; the graph itself only stores
edges, vertices and the mapping from station names to their lines.
"""


class Edge:
    """
    A weighted connection between two stations on a single line.

    Attributes:
        source: Station number of the starting end of the edge.
        dest: Station number of the other end of the edge.
        distance: Physical distance in meters (also used as the edge weight).
        line: Name of the subway line the edge belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to the distance in meters)."""
        return self.distance

    def reversed(self):
        """Return a copy of this edge pointing in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """
    Weighted undirected graph represented with adjacency lists.

    Attributes:
        station_lines: Dictionary mapping station names to the list of lines serving them.
    """

    def __init__(self):
        self._adj = {}          # station number -> list[Edge]
        self._edge_count = 0
        self.station_lines = {}  # station name -> list[str]

    def set_station_lines(self, station_name, lines):
        """Record the lines that serve a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def lines_of(self, station_name):
        """Return a copy of the list of lines serving the given station name."""
        return list(self.station_lines.get(station_name, []))

    def add_vertex(self, vertex):
        """Ensure a station number exists as a vertex of the graph."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the station number is part of the graph."""
        return vertex in self._adj

    def add_edge(self, edge):
        """
        Add an undirected edge. Both directions are stored in the adjacency lists.

        Args:
            edge: An Edge instance.
        """
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.source != edge.dest:
            self._adj[edge.dest].append(edge.reversed())
        self._edge_count += 1

    def adj(self, vertex):
        """Return the list of edges leaving the given vertex (empty if unknown)."""
        return self._adj.get(vertex, [])

    def vertices(self):
        """Return the list of all station numbers in the graph."""
        return list(self._adj.keys())

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adj)

    def num_edges(self):
        """Return the number of undirected edges that were added."""
        return self._edge_count
