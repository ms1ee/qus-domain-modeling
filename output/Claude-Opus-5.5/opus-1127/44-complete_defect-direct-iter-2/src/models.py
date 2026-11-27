"""Graph data structures for the subway network model."""


class Edge:
    """A weighted, line-labelled connection between two station numbers."""

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("distance must be a number")
        if distance < 0:
            raise ValueError("distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, vertex):
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("vertex is not an endpoint of this edge")

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def set_distance(self, distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
            raise ValueError("distance must be a non-negative number")
        self.distance = distance
        self.weight = distance

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller. ``graph`` maps a station
    number to the list of outgoing ``Edge`` objects (each undirected edge is
    stored once per direction so that ``edge.source`` is always the vertex
    whose adjacency list contains it).
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.station_names = {}
        self._edges = []

    # ----- stations -----
    def add_station(self, number, name=None):
        self.graph.setdefault(number, [])
        if name is not None:
            self.station_names[number] = name

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def has_station(self, number):
        return number in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    # ----- edges -----
    def add_edge(self, edge):
        self.graph.setdefault(edge.source, []).append(edge)
        self.graph.setdefault(edge.dest, []).append(edge.reversed())
        self._edges.append(edge)

    def adj(self, vertex):
        return self.graph.get(vertex, [])

    def edges(self):
        return list(self._edges)

    def E(self):
        return len(self._edges)

    def update_edge_distance(self, a, b, distance, line=None):
        """Update the distance of edge(s) between a and b. Returns count updated."""
        updated = 0
        for v, w in ((a, b), (b, a)):
            for e in self.graph.get(v, []):
                if e.dest == w and (line is None or e.line == line):
                    e.set_distance(distance)
        for e in self._edges:
            if {e.source, e.dest} == {a, b} and (line is None or e.line == line):
                e.set_distance(distance)
                updated += 1
        return updated

    def remove_edge(self, a, b, line=None):
        for v, w in ((a, b), (b, a)):
            if v in self.graph:
                self.graph[v] = [e for e in self.graph[v] if not (e.dest == w and (line is None or e.line == line))]
        before = len(self._edges)
        self._edges = [
            e for e in self._edges if not ({e.source, e.dest} == {a, b} and (line is None or e.line == line))
        ]
        return before - len(self._edges)
