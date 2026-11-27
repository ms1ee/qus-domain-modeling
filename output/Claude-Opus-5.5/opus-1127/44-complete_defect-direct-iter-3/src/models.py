"""Core data structures: Edge, Graph and MinPQ (heap based priority queue)."""

import heapq
import itertools


class Edge:
    """A weighted, line-labelled edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, v):
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller.  ``graph`` maps each station
    number to a list of outgoing :class:`Edge` objects; each undirected
    connection is stored as two oriented edges.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.E = 0

    @property
    def V(self):
        return len(self.graph)

    def add_vertex(self, v):
        if v not in self.graph:
            self.graph[v] = []

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self.E += 1

    def remove_edge(self, a, b, line=None):
        """Remove the connection(s) between a and b (optionally only for a line)."""
        removed = 0
        for u, w in ((a, b), (b, a)):
            if u in self.graph:
                before = len(self.graph[u])
                self.graph[u] = [e for e in self.graph[u]
                                 if not (e.dest == w and (line is None or e.line == line))]
                removed += before - len(self.graph[u])
        self.E -= removed // 2
        return removed > 0

    def adj(self, v):
        return self.graph.get(v, [])

    def vertices(self):
        return list(self.graph.keys())

    def edges(self):
        result = []
        for v, lst in self.graph.items():
            for e in lst:
                if e.source <= e.dest if isinstance(e.source, int) else True:
                    result.append(e)
        return result


class MinPQ:
    """Minimum priority queue based on a binary heap (heapq)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min(self):
        if not self._heap:
            raise IndexError("min from empty priority queue")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)
