"""
Core data structures: stations, lines, edges and the weighted undirected graph.
"""


class Station:
    """A subway station."""

    def __init__(self, name, number, lines=None):
        self.name = name
        self.number = number
        self.lines = list(lines or [])

    @property
    def is_transfer_station(self):
        """True if the station is served by more than one line."""
        return len(self.lines) > 1

    def __repr__(self):
        return f"Station({self.name!r}, {self.number}, {self.lines!r})"


class Line:
    """A subway line with its ordered station sequence."""

    def __init__(self, name, station_sequence=None, transfer_info=None):
        self.name = name
        self.station_sequence = list(station_sequence or [])
        # transfer_info: dict station name -> list of other lines
        self.transfer_info = dict(transfer_info or {})

    def __repr__(self):
        return f"Line({self.name!r}, {len(self.station_sequence)} stations)"


class Edge:
    """A weighted edge between two station numbers on a given line."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return the same edge pointing the other way."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))

    def __repr__(self):
        return f"Edge({self.source} -> {self.dest}, {self.weight}m, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller. Each added edge is stored in
    both endpoints' adjacency lists (the reverse direction as a mirrored Edge).
    """

    def __init__(self):
        self.adj = {}             # station number -> list[Edge] (outgoing)
        self.edges = []           # list of undirected edges as added
        self.station_lines = {}   # station name -> list[str]
        self.station_names = {}   # station number -> station name (optional)

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def add_station(self, number, name, lines=None):
        """Convenience: register a station number with its name and lines."""
        self.add_vertex(number)
        self.station_names[number] = name
        if lines is not None:
            self.set_station_lines(name, lines)

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge."""
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, []).append(edge.reversed())
        self.edges.append(edge)

    def neighbors(self, v):
        """Outgoing edges of ``v`` (each with ``source == v``)."""
        return self.adj.get(v, [])

    adj_of = neighbors

    def vertices(self):
        return list(self.adj.keys())

    @property
    def V(self):
        return len(self.adj)

    @property
    def E(self):
        return len(self.edges)

    vertex_count = V
    edge_count = E

    def __contains__(self, v):
        return v in self.adj

    def __repr__(self):
        return f"Graph(V={self.V}, E={self.E})"
