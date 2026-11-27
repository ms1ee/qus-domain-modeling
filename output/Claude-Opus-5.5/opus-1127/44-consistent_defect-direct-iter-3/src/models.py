"""Core graph data structures: Edge, Graph and MinPQ."""

import heapq
import itertools


class Edge:
    """A weighted, directed connection between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source!r} -> {self.dest!r}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self.edges = []

    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])
        self.edges.append(edge)

    def remove_edge(self, source, dest, line=None):
        """Remove edges source->dest (optionally only of a given line)."""
        removed = 0
        lst = self.adj.get(source, [])
        keep = []
        for e in lst:
            if e.dest == dest and (line is None or e.line == line):
                removed += 1
            else:
                keep.append(e)
        self.adj[source] = keep
        self.edges = [e for e in self.edges
                      if not (e.source == source and e.dest == dest and (line is None or e.line == line))]
        return removed

    def edges_from(self, v):
        return list(self.adj.get(v, []))

    def vertices(self):
        return list(self.adj.keys())

    @property
    def V(self):
        return len(self.adj)

    @property
    def E(self):
        return len(self.edges)


class MinPQ:
    """Heap-based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, key, item):
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def pop(self):
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
