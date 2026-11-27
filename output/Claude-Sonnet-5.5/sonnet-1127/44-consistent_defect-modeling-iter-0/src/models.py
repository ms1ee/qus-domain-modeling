"""Core data models: Edge, Graph, Station, Line."""


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


class Station:
    def __init__(self, name, station_id, is_transfer=False):
        self.name = name
        self.station_id = station_id
        self.is_transfer = is_transfer


class Line:
    def __init__(self, name, station_sequence=None):
        self.name = name
        self.station_sequence = list(station_sequence or [])


class Graph:
    """Weighted directed graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_node(self, node):
        self.adjacency.setdefault(node, [])

    def add_edge(self, edge):
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, [])

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        return list(self.adjacency.keys())
