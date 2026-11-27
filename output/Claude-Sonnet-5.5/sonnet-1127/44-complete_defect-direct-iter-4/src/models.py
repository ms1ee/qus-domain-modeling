"""Graph data structures."""


class Edge:
    """Undirected weighted edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, node):
        return self.dest if node == self.source else self.source

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph with adjacency lists keyed by station number."""

    def __init__(self):
        self.graph = {}          # number -> list[Edge]
        self.adj = self.graph
        self.station_lines = {}  # station name -> list of lines
        self.edges = []

    def add_node(self, node):
        self.graph.setdefault(node, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(edge)
        self.edges.append(edge)

    def neighbors(self, node):
        return self.graph.get(node, [])

    def nodes(self):
        return list(self.graph.keys())
