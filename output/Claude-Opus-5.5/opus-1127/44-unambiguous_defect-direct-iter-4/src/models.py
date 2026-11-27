"""Graph data structures used to model the subway network.

The network is modelled as a weighted undirected graph. Vertices are station
numbers (assigned by the caller); edges carry the inter-station distance in
meters as their weight, plus the name of the line they belong to.
"""

import numbers


class Edge:
    """A weighted connection between two stations on a given line."""

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
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
        raise ValueError("Vertex %r is not an endpoint of this edge" % (vertex,))

    def reversed(self):
        """Return a new edge with source and destination swapped."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        graph: dict mapping station number -> list of outgoing :class:`Edge`.
            Every undirected connection appears in both endpoints' lists, each
            oriented away from the owning vertex.
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edges = []

    # ----- nodes ---------------------------------------------------------
    def add_node(self, vertex):
        """Ensure ``vertex`` exists in the graph."""
        self.graph.setdefault(vertex, [])

    def has_node(self, vertex):
        return vertex in self.graph

    def __contains__(self, vertex):
        return vertex in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    def __len__(self):
        return len(self.graph)

    # ----- station metadata ----------------------------------------------
    def set_station_lines(self, station_name, lines):
        """Record which lines serve ``station_name`` (duplicates removed)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges -----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(edge.reversed())
        self._edges.append(edge)

    def remove_edge(self, source, dest, line=None):
        """Remove the undirected edge(s) between two stations.

        Returns the number of undirected edges removed.
        """
        def match(e, a, b):
            return e.source == a and e.dest == b and (line is None or e.line == line)

        removed = 0
        kept = []
        for e in self._edges:
            if match(e, source, dest) or match(e, dest, source):
                removed += 1
            else:
                kept.append(e)
        self._edges = kept
        for a, b in ((source, dest), (dest, source)):
            if a in self.graph:
                self.graph[a] = [e for e in self.graph[a] if not match(e, a, b)]
        return removed

    def adjacent(self, vertex):
        return list(self.graph.get(vertex, []))

    def edges(self):
        """Return every undirected edge once."""
        return list(self._edges)

    def E(self):
        return len(self._edges)

    def __repr__(self):
        return "Graph(V=%d, E=%d)" % (self.V(), self.E())
