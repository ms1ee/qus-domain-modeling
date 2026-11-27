"""Core data models: Station, Line, Edge, Graph."""


class Station:
    def __init__(self, id, name, lines=None):
        self.id = id
        self.name = name
        self.lines = list(lines or [])

    @property
    def is_transfer(self):
        return len(self.lines) > 1


class Line:
    def __init__(self, name, station_sequence=None):
        self.name = name
        self.station_sequence = list(station_sequence or [])


class Edge:
    """Undirected connection between two station numbers (stored per direction)."""

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
    """Weighted undirected graph with adjacency lists keyed by station number."""

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
        self.adjacency.setdefault(edge.dest, []).append(
            Edge(edge.dest, edge.source, edge.distance, edge.line))

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def edges_between(self, a, b):
        return [e for e in self.adjacency.get(a, []) if e.dest == b]

    def nodes(self):
        return list(self.adjacency.keys())
