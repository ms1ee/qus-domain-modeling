"""Graph data structures."""


class Edge:
    """Undirected weighted edge between two station numbers."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, v):
        return self.dest if v == self.source else self.source

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph with adjacency lists keyed by station number."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self.edge_count = 0

    def add_node(self, v):
        self.adj.setdefault(v, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)
        self.edge_count += 1

    def neighbors(self, v):
        return self.adj.get(v, [])

    def nodes(self):
        return list(self.adj.keys())

    def edges(self):
        seen = set()
        for lst in self.adj.values():
            for e in lst:
                if id(e) not in seen:
                    seen.add(id(e))
                    yield e

    def V(self):
        return len(self.adj)

    def E(self):
        return self.edge_count
