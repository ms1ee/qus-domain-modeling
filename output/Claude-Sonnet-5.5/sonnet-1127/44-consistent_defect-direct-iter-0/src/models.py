"""Graph data structures: Edge, Graph, MinPQ."""
import heapq
import itertools


class Edge:
    """Directed weighted edge between station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return "Edge(%r->%r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted directed graph; station numbers assigned by the caller."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def add_node(self, number):
        self.adj.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])

    def edges_from(self, number):
        return self.adj.get(number, [])

    def nodes(self):
        return list(self.adj.keys())

    def edge_count(self):
        return sum(len(v) for v in self.adj.values())


class MinPQ:
    """Heap based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self._heap)
        return p, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
