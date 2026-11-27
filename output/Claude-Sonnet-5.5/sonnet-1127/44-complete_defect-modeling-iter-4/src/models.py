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

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph with adjacency lists.
    Station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, node):
        self.adjacency.setdefault(node, [])

    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def has_node(self, node):
        return node in self.adjacency
