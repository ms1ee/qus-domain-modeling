"""Core data models: Edge and Graph."""


class Edge:
    """Undirected connection between two station numbers."""

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
        """Add an undirected edge (stored in both directions)."""
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, []).append(edge.reversed())

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def remove_edges_between(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.adjacency[x] = [e for e in self.adjacency.get(x, [])
                                 if not (e.dest == y and (line is None or e.line == line))]

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1

    @property
    def num_stations(self):
        return len(self.station_to_number)
