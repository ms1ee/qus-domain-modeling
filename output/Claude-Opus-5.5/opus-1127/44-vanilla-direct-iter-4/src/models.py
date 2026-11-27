"""Graph data structures for the subway network.

The network is modelled as a weighted undirected graph. Vertices are station
numbers (assigned by the caller), edges carry the distance in meters and the
name of the line they belong to.
"""


class Edge:
    """A weighted undirected edge between two stations."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line=None):
        if distance is None or distance < 0:
            raise ValueError("Edge distance must be a non-negative number")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, v):
        """Return the endpoint of the edge that is not ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, "
                f"{self.distance!r}, {self.line!r})")


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller, not by Graph.
    """

    def __init__(self):
        # adjacency lists: station number -> list[Edge]
        self.graph = {}
        # station name -> list of line names
        self.station_lines = {}
        self._edges = []

    # ----- vertex management -------------------------------------------
    def add_vertex(self, v):
        if v not in self.graph:
            self.graph[v] = []

    def has_vertex(self, v):
        return v in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    # ----- edge management ---------------------------------------------
    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        for v in (edge.source, edge.dest):
            lst = self.graph.get(v, [])
            if edge in lst:
                lst.remove(edge)
        if edge in self._edges:
            self._edges.remove(edge)

    def adj(self, v):
        return self.graph.get(v, [])

    def edges(self):
        return list(self._edges)

    def find_edges(self, u, v):
        return [e for e in self.adj(u) if e.other(u) == v]

    @property
    def num_vertices(self):
        return len(self.graph)

    @property
    def num_edges(self):
        return len(self._edges)

    def __repr__(self):
        return f"Graph(V={self.num_vertices}, E={self.num_edges})"
