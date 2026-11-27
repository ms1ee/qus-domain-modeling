"""
Core data structures: Edge, Graph (weighted, undirected adjacency lists)
and MinPQ (binary-heap priority queue).
"""

import heapq
import itertools


class Edge:
    """A weighted edge between two station numbers on a given line."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, vertex):
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return a new edge going in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller. Each added edge is usable
    in both directions (a reverse edge is stored in the destination's
    adjacency list).
    """

    def __init__(self):
        self.graph = {}          # station number -> list[Edge] (adjacency lists)
        self.edges = []          # original edges, as added
        self.station_lines = {}  # station name -> list of line names

    # --- node management -------------------------------------------------
    def add_vertex(self, v):
        if v not in self.graph:
            self.graph[v] = []

    def has_vertex(self, v):
        return v in self.graph

    def vertices(self):
        return list(self.graph.keys())

    @property
    def vertex_count(self):
        return len(self.graph)

    @property
    def edge_count(self):
        return len(self.edges)

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # --- edge management -------------------------------------------------
    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.edges.append(edge)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())

    def remove_edges_between(self, a, b, line=None):
        """Remove edges between a and b (optionally only those on `line`)."""
        def match(e):
            return ({e.source, e.dest} == {a, b}) and (line is None or e.line == line)
        removed = [e for e in self.edges if match(e)]
        self.edges = [e for e in self.edges if not match(e)]
        for v in (a, b):
            if v in self.graph:
                self.graph[v] = [e for e in self.graph[v] if not match(e)]
        return len(removed)

    def adj(self, v):
        return self.graph.get(v, [])

    def __repr__(self):
        return f"Graph(V={self.vertex_count}, E={self.edge_count})"


class MinPQ:
    """Minimum priority queue backed by a binary heap (heapq)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        """Remove and return (priority, item) with the smallest priority."""
        if not self._heap:
            raise IndexError("pop from empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)
