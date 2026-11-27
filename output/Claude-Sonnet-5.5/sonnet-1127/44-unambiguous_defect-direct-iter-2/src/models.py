"""Graph data structures."""


class Edge:
    """Undirected edge segment between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph using adjacency lists keyed by station number."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_node(self, n):
        self.adj.setdefault(n, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an edge in both directions."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        self.adj[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def neighbors(self, n):
        return self.adj.get(n, [])

    def remove_edges_between(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.adj[x] = [e for e in self.adj.get(x, [])
                           if not (e.dest == y and (line is None or e.line == line))]

    def update_distance(self, a, b, distance, line=None):
        """Update distance of existing edges; return number of directed edges changed."""
        n = 0
        for x, y in ((a, b), (b, a)):
            for e in self.adj.get(x, []):
                if e.dest == y and (line is None or e.line == line):
                    e.distance = distance
                    n += 1
        return n

    def nodes(self):
        return list(self.adj.keys())

    def V(self):
        return len(self.adj)

    def E(self):
        return sum(len(v) for v in self.adj.values()) // 2
