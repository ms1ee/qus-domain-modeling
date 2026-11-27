"""Graph data structures for the subway network."""


class Edge:
    """A directed weighted edge between two station numbers."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return "Edge(%r -> %r, %r m, %r)" % (self.source, self.dest, self.weight, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))


class Graph:
    """Weighted directed graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self.adj = {}             # station number -> list[Edge]
        self.station_lines = {}   # station name -> list[str]
        self._edge_count = 0

    def add_vertex(self, v):
        if v not in self.adj:
            self.adj[v] = []

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        self._edge_count += 1

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    def out_edges(self, v):
        return self.adj.get(v, [])

    def vertices(self):
        return list(self.adj.keys())

    def edges(self):
        result = []
        for lst in self.adj.values():
            result.extend(lst)
        return result

    def V(self):
        return len(self.adj)

    def E(self):
        return self._edge_count

    def update_edge_distance(self, source, dest, distance, line=None):
        """Update the distance of matching edges. Returns number updated."""
        count = 0
        for e in self.adj.get(source, []):
            if e.dest == dest and (line is None or e.line == line):
                e.distance = distance
                e.weight = distance
                count += 1
        return count
