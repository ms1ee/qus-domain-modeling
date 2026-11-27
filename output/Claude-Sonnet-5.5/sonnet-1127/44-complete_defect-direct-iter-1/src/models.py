"""Graph data structures for the subway network."""


class Edge:
    """Undirected edge between two station numbers."""

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
    """Weighted undirected graph using adjacency lists."""

    def __init__(self):
        self.graph = {}
        self.station_lines = {}

    def add_node(self, node):
        self.graph.setdefault(node, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(edge.reversed())

    def neighbors(self, node):
        return self.graph.get(node, [])

    def nodes(self):
        return list(self.graph.keys())

    def edge_count(self):
        return sum(len(v) for v in self.graph.values()) // 2
