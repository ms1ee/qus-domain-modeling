"""Graph data structures for the subway network."""


class Edge:
    """A weighted edge between two stations (by number) on a given line."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, v):
        """Return the endpoint different from ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller. ``graph`` is a dictionary
    mapping a station number to the list of outgoing edges; each undirected
    connection is stored once in each direction.
    """

    def __init__(self):
        self.graph = {}          # station number -> list[Edge]
        self.station_lines = {}  # station name -> list[str]
        self._edge_count = 0

    # ---- vertex management -------------------------------------------
    def add_vertex(self, v):
        if v not in self.graph:
            self.graph[v] = []

    def has_vertex(self, v):
        return v in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    def E(self):
        return self._edge_count

    # ---- station information -----------------------------------------
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(set(self.station_lines.get(station_name, []))) > 1

    # ---- edge management ---------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(edge.reversed())
        self._edge_count += 1

    def adj(self, v):
        return self.graph.get(v, [])

    def edges(self):
        """Return each undirected edge once."""
        result = []
        seen = set()
        for v, edges in self.graph.items():
            for e in edges:
                key = (min(e.source, e.dest), max(e.source, e.dest), e.distance, e.line)
                if key in seen:
                    continue
                seen.add(key)
                result.append(e)
        return result

    def __repr__(self):
        return f"Graph(V={self.V()}, E={self.E()})"
