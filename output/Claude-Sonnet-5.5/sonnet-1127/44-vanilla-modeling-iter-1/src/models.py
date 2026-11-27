"""Core data models: Edge and Graph."""


class Edge:
    """Undirected connection between two station numbers on one line."""

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
    """Weighted undirected graph keyed by station numbers."""

    def __init__(self):
        self.adjacency = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, []).append(edge.reversed())

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def update_distance(self, a, b, distance, line=None):
        """Update distance between station numbers a and b; return count of edges changed."""
        n = 0
        for u, v in ((a, b), (b, a)):
            for i, e in enumerate(self.adjacency.get(u, [])):
                if e.dest == v and (line is None or e.line == line):
                    self.adjacency[u][i] = Edge(u, v, distance, e.line)
                    n += 1
        return n

    def remove_edges_between(self, a, b):
        self.adjacency[a] = [e for e in self.adjacency.get(a, []) if e.dest != b]
        self.adjacency[b] = [e for e in self.adjacency.get(b, []) if e.dest != a]
