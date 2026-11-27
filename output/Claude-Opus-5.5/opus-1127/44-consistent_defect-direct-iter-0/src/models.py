"""Graph data structures for the subway network."""


class Edge:
    """A directed weighted edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.weight}, {self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists keyed by station number."""

    def __init__(self):
        self.graph = {}            # station number -> list[Edge]
        self.station_lines = {}    # station name -> list[str]
        self._edge_count = 0

    def add_vertex(self, v):
        self.graph.setdefault(v, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, v):
        return self.graph.get(v, [])

    def vertices(self):
        return list(self.graph.keys())

    def edges(self):
        for lst in self.graph.values():
            for e in lst:
                yield e

    @property
    def V(self):
        return len(self.graph)

    @property
    def E(self):
        return self._edge_count

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1
