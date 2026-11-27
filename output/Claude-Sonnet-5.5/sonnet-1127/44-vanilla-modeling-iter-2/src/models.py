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

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}, {self.line})"


class Graph:
    """Weighted undirected graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}  # number -> list[Edge]
        self.station_lines = {}  # name -> list[str]

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.setdefault(number, [])
        self.station_lines.setdefault(name, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def has_station(self, name):
        return name in self.station_to_number

    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.graph.setdefault(edge.source, [])
        self.graph.setdefault(edge.dest, [])
        self.graph[edge.source] = [e for e in self.graph[edge.source]
                                   if not (e.dest == edge.dest and e.line == edge.line)]
        self.graph[edge.dest] = [e for e in self.graph[edge.dest]
                                 if not (e.dest == edge.source and e.line == edge.line)]
        self.graph[edge.source].append(edge)
        self.graph[edge.dest].append(edge.reversed())

    def neighbors(self, number):
        return self.graph.get(number, [])

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def station_count(self):
        return len(self.station_to_number)
