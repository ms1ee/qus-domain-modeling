"""Core data models: Edge and Graph."""
from collections import defaultdict


class Edge:
    """Undirected weighted edge between station numbers."""

    def __init__(self, source, dest, distance, line=None):
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
    """Weighted undirected graph keyed by station numbers."""

    def __init__(self):
        self.adjacency = defaultdict(list)
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}

    def register_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an edge in both directions (duplicates are ignored)."""
        self._add_directed(edge)
        self._add_directed(Edge(edge.dest, edge.source, edge.distance, edge.line))

    def _add_directed(self, e):
        for x in self.adjacency[e.source]:
            if x.dest == e.dest and x.line == e.line and x.distance == e.distance:
                return
        self.adjacency[e.source].append(e)

    def remove_edges_between(self, a, b, line=None):
        for u, v in ((a, b), (b, a)):
            self.adjacency[u] = [e for e in self.adjacency[u]
                                 if not (e.dest == v and (line is None or e.line == line))]

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        s = set(self.adjacency.keys())
        s.update(self.number_to_station.keys())
        return s

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1
