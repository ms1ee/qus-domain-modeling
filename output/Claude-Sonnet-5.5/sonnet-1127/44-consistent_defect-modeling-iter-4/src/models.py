"""Core data models: Edge and Graph (weighted directed graph)."""


class Edge:
    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted directed graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, number):
        self.adjacency.setdefault(number, [])

    def add_edge(self, edge):
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, [])

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def nodes(self):
        return list(self.adjacency.keys())
