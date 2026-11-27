"""Core data models: Station, Line, Edge, Graph."""


class Station:
    def __init__(self, id, name, is_transfer=False):
        self.id = id
        self.name = name
        self.is_transfer = is_transfer


class Line:
    def __init__(self, name, station_sequence=None):
        self.name = name
        self.station_sequence = list(station_sequence or [])


class Edge:
    """Directed weighted connection between station numbers."""

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


Connection = Edge


class Graph:
    """Weighted directed graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}

    def add_station(self, number, name):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, [])

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def edges(self):
        for lst in self.adjacency.values():
            for e in lst:
                yield e

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1
