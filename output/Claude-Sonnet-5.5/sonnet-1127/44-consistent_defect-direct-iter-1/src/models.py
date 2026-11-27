"""Graph data structures."""


class Edge:
    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted directed graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self.edges = []

    def add_node(self, n):
        self.adj.setdefault(n, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])
        self.edges.append(edge)

    def neighbors(self, n):
        return self.adj.get(n, [])

    def nodes(self):
        return list(self.adj.keys())
