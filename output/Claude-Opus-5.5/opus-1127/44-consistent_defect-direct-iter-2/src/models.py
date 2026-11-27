"""Graph data structures: Edge, Graph and a heap-based MinPQ."""

import heapq
import itertools


class Edge:
    """A weighted connection between two stations (by station number)."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.weight, self.line)


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller. Every added edge can be
    travelled in both directions.
    """

    def __init__(self):
        self.adj = {}
        self.graph = self.adj  # adjacency-list dictionary alias
        self.station_lines = {}
        self.number_to_station = {}
        self._edges = []

    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._edges.append(edge)
        self.adj[edge.source].append(edge)
        if edge.source != edge.dest:
            self.adj[edge.dest].append(edge.reversed())

    def adjacent(self, v):
        return self.adj.get(v, [])

    def vertices(self):
        return list(self.adj.keys())

    def edges(self):
        return list(self._edges)

    def V(self):
        return len(self.adj)

    def E(self):
        return len(self._edges)


class MinPQ:
    """Min priority queue backed by a binary heap (heapq)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
