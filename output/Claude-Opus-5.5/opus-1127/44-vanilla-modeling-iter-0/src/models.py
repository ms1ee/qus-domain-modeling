"""
Core data structures: weighted undirected graph (``Graph``), its edges
(``Edge``) and a heap based priority queue (``MinPQ``).
"""

import heapq
import itertools


class Edge:
    """A weighted, undirected connection between two stations on one line.

    ``source`` and ``dest`` are station numbers. ``weight`` always equals
    ``distance`` (meters).
    """

    def __init__(self, source, dest, distance, line):
        if distance is None or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Weight of the edge (equal to its distance in meters)."""
        return self.distance

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, v):
        """Return the endpoint of the edge that is not ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v!r} is not an endpoint of {self!r}")

    def connects(self, a, b):
        """Whether this edge joins ``a`` and ``b`` (in any direction)."""
        return (self.source == a and self.dest == b) or (self.source == b and self.dest == a)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller; the graph simply stores
    whatever vertex identifiers appear in the edges it receives.
    """

    def __init__(self):
        self.adj = {}             # station number -> list[Edge]
        self.edges = []           # every edge once
        self.station_lines = {}   # station name -> list of line names

    # ----- vertices -------------------------------------------------
    def add_vertex(self, v):
        """Register a vertex (no-op if it already exists)."""
        self.adj.setdefault(v, [])

    def vertices(self):
        return list(self.adj.keys())

    @property
    def vertex_count(self):
        return len(self.adj)

    @property
    def edge_count(self):
        return len(self.edges)

    # ----- station metadata -----------------------------------------
    def set_station_lines(self, station_name, lines):
        """Set the lines a station belongs to (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        """A station served by more than one line is a transfer station."""
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges ------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in the adjacency of both endpoints)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)
        self.edges.append(edge)

    def adjacent(self, v):
        """Edges incident to ``v``."""
        return list(self.adj.get(v, []))

    def degree(self, v):
        return len(self.adj.get(v, []))

    def find_edges(self, a, b, line=None):
        """All edges between ``a`` and ``b`` (optionally restricted to a line)."""
        return [e for e in self.adj.get(a, [])
                if e.connects(a, b) and (line is None or e.line == line)]

    def remove_edges_between(self, a, b, line=None):
        """Remove edges between ``a`` and ``b``; return number removed."""
        doomed = self.find_edges(a, b, line)
        for e in doomed:
            for v in (e.source, e.dest):
                lst = self.adj.get(v, [])
                if e in lst:
                    lst.remove(e)
            if e in self.edges:
                self.edges.remove(e)
        return len(doomed)

    def __repr__(self):
        return f"Graph(V={self.vertex_count}, E={self.edge_count})"


class MinPQ:
    """Binary-heap based minimum priority queue.

    Items with equal priority are returned in insertion order, and items
    themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    insert = push

    def pop(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("pop from an empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    del_min = pop

    def peek(self):
        if not self._heap:
            raise IndexError("peek from an empty priority queue")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self):
        return not self._heap

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)
