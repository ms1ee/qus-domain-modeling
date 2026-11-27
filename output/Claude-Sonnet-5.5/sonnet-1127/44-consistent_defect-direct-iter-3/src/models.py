"""Graph data structures."""
import heapq


class Edge:
    """Directed weighted edge between station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted directed graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_node(self, n):
        self.adj.setdefault(n, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])

    def edges_from(self, n):
        return self.adj.get(n, [])

    def nodes(self):
        return list(self.adj.keys())


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self._h = []
        self._c = 0

    def push(self, priority, item):
        self._c += 1
        heapq.heappush(self._h, (priority, self._c, item))

    def pop(self):
        p, _, item = heapq.heappop(self._h)
        return p, item

    def __len__(self):
        return len(self._h)

    def is_empty(self):
        return not self._h
