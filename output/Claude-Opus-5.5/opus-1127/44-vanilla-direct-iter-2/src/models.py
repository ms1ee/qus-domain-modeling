"""
Core data structures: Edge, Graph (weighted undirected graph) and MinPQ
(binary-heap priority queue used by Dijkstra's algorithm).
"""

import numbers


class Edge:
    """A weighted undirected edge between two station numbers on one line."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, vertex):
        """Return the endpoint of the edge different from ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (vertex,))

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. ``adj`` maps a station number
    to the list of incident edges. ``station_lines`` maps station names to the
    lines that serve them (used for transfer station detection).
    """

    def __init__(self):
        self.adj = {}
        self.station_lines = {}
        self._edges = []

    def add_vertex(self, v):
        if v not in self.adj:
            self.adj[v] = []

    def has_vertex(self, v):
        return v in self.adj

    def set_station_lines(self, station_name, lines):
        seen = []
        for line in lines or []:
            if line not in seen:
                seen.append(line)
        self.station_lines[station_name] = seen

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, source, dest, line=None):
        """Remove edges between source and dest (optionally only on ``line``)."""
        removed = 0
        keep = []
        for e in self._edges:
            match = {e.source, e.dest} == {source, dest} and (line is None or e.line == line)
            if match:
                removed += 1
                for v in (e.source, e.dest):
                    if v in self.adj and e in self.adj[v]:
                        self.adj[v].remove(e)
            else:
                keep.append(e)
        self._edges = keep
        return removed

    def neighbors(self, v):
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
    """Binary min-heap priority queue.

    Items are stored with a comparable key; ties are broken by insertion
    order so that the items themselves never need to be compared.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def insert(self, key, item=None):
        entry = (key, self._counter, item)
        self._counter += 1
        self._heap.append(entry)
        self._swim(len(self._heap) - 1)

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        key, _, item = self._heap[0]
        return key, item

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def _less(self, i, j):
        a, b = self._heap[i], self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                heap[k], heap[parent] = heap[parent], heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        heap = self._heap
        n = len(heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and self._less(right, left):
                child = right
            if self._less(child, k):
                heap[k], heap[child] = heap[child], heap[k]
                k = child
            else:
                break
