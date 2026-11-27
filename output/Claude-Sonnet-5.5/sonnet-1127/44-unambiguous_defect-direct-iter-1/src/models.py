"""Graph data structures."""


class Edge:
    """Edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}, {self.line})"


class Graph:
    """Weighted undirected graph; station numbers are chosen by the caller."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_node(self, n):
        self.adj.setdefault(n, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        self.adj[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def neighbors(self, n):
        return self.adj.get(n, [])

    def nodes(self):
        return list(self.adj.keys())

    def edge_count(self):
        return sum(len(v) for v in self.adj.values()) // 2
