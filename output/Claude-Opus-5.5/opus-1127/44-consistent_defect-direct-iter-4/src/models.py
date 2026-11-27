"""Graph data structures for the subway network."""


class Edge:
    """A directed, weighted edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self._adj = {}            # station number -> list[Edge]
        self.station_lines = {}   # station name -> list[str]
        self._edge_count = 0

    def add_vertex(self, v):
        if v not in self._adj:
            self._adj[v] = []

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, v):
        return list(self._adj.get(v, []))

    def vertices(self):
        return list(self._adj.keys())

    def edges(self):
        result = []
        for lst in self._adj.values():
            result.extend(lst)
        return result

    def find_edge(self, source, dest, line=None):
        for e in self._adj.get(source, []):
            if e.dest == dest and (line is None or e.line == line):
                return e
        return None

    @property
    def V(self):
        return len(self._adj)

    @property
    def E(self):
        return self._edge_count
