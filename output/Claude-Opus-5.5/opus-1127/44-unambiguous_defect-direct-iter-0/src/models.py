"""Core graph data structures for the Beijing Subway network.

The network is modelled as a weighted undirected graph:

* vertices are station numbers (integers assigned by the caller);
* every edge stores the distance between two adjacent stations (meters)
  and the name of the subway line serving that connection.

Undirected edges are stored as two directed half-edges, one in each
adjacency list, so that edges returned by path searches are always
oriented in the direction of travel.
"""


class Edge:
    """A connection between two adjacent stations on a given line."""

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Weight used by the shortest-path algorithm (= distance in meters)."""
        return self.distance

    @weight.setter
    def weight(self, value):
        self.distance = value

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (vertex,))

    def reversed(self):
        """Return a new edge with source and destination swapped."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        graph: dict mapping station number -> list of outgoing ``Edge``.
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edges = []

    # ----------------------------------------------------------- vertices
    def add_vertex(self, vertex):
        if vertex not in self.graph:
            self.graph[vertex] = []

    def has_vertex(self, vertex):
        return vertex in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    # -------------------------------------------------------------- lines
    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        """A station served by more than one line is a transfer station."""
        return len(self.station_lines.get(station_name, [])) > 1

    def all_lines(self):
        lines = set()
        for line_list in self.station_lines.values():
            lines.update(line_list)
        for edge in self._edges:
            lines.add(edge.line)
        return sorted(lines)

    # -------------------------------------------------------------- edges
    def add_edge(self, edge):
        """Add an undirected edge (stored as two oriented half-edges)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self._edges.append(edge)

    def adj(self, vertex):
        """Edges leaving ``vertex`` (oriented away from it)."""
        return self.graph.get(vertex, [])

    def edges(self):
        return list(self._edges)

    def E(self):
        return len(self._edges)

    def degree(self, vertex):
        return len(self.graph.get(vertex, []))

    def __repr__(self):
        return "Graph(V=%d, E=%d)" % (self.V(), self.E())
