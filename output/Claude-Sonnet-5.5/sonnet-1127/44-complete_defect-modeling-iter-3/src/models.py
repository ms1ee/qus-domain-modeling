"""Core data models: Edge and Graph."""


class Edge:
    """Undirected-edge record; source/dest are station numbers."""

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
    """Weighted undirected graph with adjacency lists."""

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}
        self.station_lines = {}

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.graph.setdefault(edge.source, []).append(edge)
        self.graph.setdefault(edge.dest, []).append(edge.reversed())

    def neighbors(self, number):
        return self.graph.get(number, [])

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def node_count(self):
        return len(self.graph)
