"""Core data models: Edge, Graph, Station, Line, PathQuery, Route."""


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
        return "Edge(%r,%r,%r,%r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph; station numbers are assigned by the caller."""

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
        self.adjacency.setdefault(edge.source, [])
        self.adjacency.setdefault(edge.dest, [])
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge.reversed())

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def remove_edges_between(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.adjacency[x] = [e for e in self.adjacency.get(x, [])
                                 if not (e.dest == y and (line is None or e.line == line))]

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1


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


class PathQuery:
    def __init__(self, start, end, mode="shortest_distance", max_transfers=None, line_preference=None):
        self.start = start
        self.end = end
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference


class Route:
    def __init__(self, stations, edges, total_distance, transfer_count, lines, transfer_stations=None):
        self.stations = stations
        self.edges = edges
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.lines = lines
        self.transfer_stations = transfer_stations or []
