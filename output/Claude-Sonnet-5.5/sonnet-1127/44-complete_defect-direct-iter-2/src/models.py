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
    """Weighted undirected graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.graph = {}          # number -> list[Edge]
        self.station_lines = {}  # name -> list[str]

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, n):
        self.graph.setdefault(n, [])

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def adj(self, n):
        return self.graph.get(n, [])

    def nodes(self):
        return list(self.graph.keys())
