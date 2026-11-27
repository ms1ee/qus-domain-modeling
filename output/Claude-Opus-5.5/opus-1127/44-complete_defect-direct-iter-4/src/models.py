"""
Graph data structures for subway network modeling.

Stations are vertices identified by integer numbers assigned by the caller.
Connections are undirected weighted edges (weight = distance in meters),
each tagged with the subway line it belongs to.
"""


class Edge:
    """A weighted, line-tagged connection between two stations."""

    def __init__(self, source, dest, distance, line):
        if distance is None or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight, equal to the distance in meters."""
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
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return a new edge with the direction reversed."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    ``graph`` maps a station number to a list of outgoing ``Edge`` objects.
    Every undirected connection is stored as two directed edges.
    """

    def __init__(self):
        self.graph = {}            # station number -> list[Edge]
        self.station_lines = {}    # station name -> list[str]
        self.station_names = {}    # station number -> station name
        self.edges = []            # original (undirected) edges as added

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, number, name=None):
        self.graph.setdefault(number, [])
        if name is not None:
            self.station_names[number] = name

    def vertices(self):
        return list(self.graph.keys())

    @property
    def V(self):
        return len(self.graph)

    @property
    def E(self):
        return len(self.edges)

    # ---- station lines -------------------------------------------------
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ---- edges -----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self.edges.append(edge)

    def adj(self, vertex):
        return self.graph.get(vertex, [])

    def update_edge_distance(self, u, v, distance, line=None):
        """Update the distance of all edges between u and v (optionally on a line).

        Returns the number of undirected connections updated.
        """
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        count = 0
        for e in self.edges:
            if {e.source, e.dest} == {u, v} and (line is None or e.line == line):
                e.distance = distance
                count += 1
        for vertex in (u, v):
            for e in self.graph.get(vertex, []):
                if {e.source, e.dest} == {u, v} and (line is None or e.line == line):
                    e.distance = distance
        return count

    def __repr__(self):
        return f"Graph(V={self.V}, E={self.E})"
