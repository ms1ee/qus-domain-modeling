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
    """Undirected-edge half; source/dest are station numbers."""

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
    """Weighted undirected graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}  # number -> list[Edge]
        self.station_lines = {}  # name -> list[str]

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an edge in both directions."""
        self.graph.setdefault(edge.source, []).append(edge)
        self.graph.setdefault(edge.dest, []).append(edge.reversed())

    def neighbors(self, number):
        return self.graph.get(number, [])

    def remove_edges_between(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.graph[x] = [e for e in self.graph.get(x, [])
                             if not (e.dest == y and (line is None or e.line == line))]

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1
