"""Graph data structures."""


class Edge:
    """Directed weighted edge between station numbers."""

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

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, number):
        self.adj.setdefault(number, [])

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])

    def edges_from(self, number):
        return self.adj.get(number, [])

    def nodes(self):
        return list(self.adj.keys())

    def edge_count(self):
        return sum(len(v) for v in self.adj.values())
