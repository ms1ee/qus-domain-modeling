"""Core data models: Edge and Graph."""


class Edge:
    """Weighted connection between two station numbers on a line."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Undirected weighted graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def add_node(self, number):
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge.reversed())

    def remove_edge(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.adjacency[x] = [e for e in self.adjacency.get(x, [])
                                 if not (e.dest == y and (line is None or e.line == line))]

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def edge_count(self):
        return sum(len(v) for v in self.adjacency.values()) // 2
