"""Core data models: Edge and Graph."""


class Edge:
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
        return f"Edge({self.source}->{self.dest}, {self.distance}, {self.line})"


class Graph:
    """Undirected weighted graph; add_edge stores both directions."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, n):
        self.adj.setdefault(n, [])

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        self.adj[edge.dest].append(edge.reversed())

    def neighbors(self, n):
        return self.adj.get(n, [])

    def nodes(self):
        return list(self.adj.keys())

    def edges(self):
        return [e for lst in self.adj.values() for e in lst]
