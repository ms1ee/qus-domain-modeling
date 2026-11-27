"""Graph data structures."""


class Edge:
    """Undirected-edge record between two station numbers."""

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
    """Weighted undirected graph with adjacency lists keyed by station number."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_node(self, node):
        self.adj.setdefault(node, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        self.adj[edge.dest].append(edge.reversed())

    def neighbors(self, node):
        return self.adj.get(node, [])

    def nodes(self):
        return list(self.adj.keys())

    def edge_count(self):
        return sum(len(v) for v in self.adj.values()) // 2

    def update_distance(self, a, b, distance, line=None):
        """Update distance of edges between a and b (optionally for one line)."""
        found = False
        for u, v in ((a, b), (b, a)):
            for e in self.adj.get(u, []):
                if e.dest == v and (line is None or e.line == line):
                    e.distance = distance
                    found = True
        return found
