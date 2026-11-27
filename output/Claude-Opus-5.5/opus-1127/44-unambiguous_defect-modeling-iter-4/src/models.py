"""
Core data structures: weighted edges, an undirected weighted graph and a
heap-based minimum priority queue.
"""

import heapq
import itertools


class Edge:
    """A weighted, undirected edge between two station numbers.

    Attributes:
        source:   station number of one endpoint
        dest:     station number of the other endpoint
        distance: distance in meters
        weight:   same as distance (used by the shortest path algorithm)
        line:     name of the subway line this connection belongs to
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line=None):
        if distance is None:
            raise ValueError("Edge distance cannot be None")
        if distance < 0:
            raise ValueError(f"Edge distance cannot be negative: {distance}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, vertex):
        """Return the endpoint of the edge different from ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, "
                f"{self.distance!r}, {self.line!r})")


class Graph:
    """Weighted undirected graph represented with adjacency lists.

    Station numbers are assigned by the caller; the graph only stores
    whatever vertex identifiers appear in the added edges.

    Attributes:
        graph:         dict[vertex, list[Edge]] adjacency lists
        station_lines: dict[station name, list[str]] line affiliation
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edges = []

    # ----------------------------------------------------------- vertices
    def add_vertex(self, v):
        """Ensure the vertex exists (possibly without edges)."""
        if v not in self.graph:
            self.graph[v] = []

    def has_vertex(self, v):
        return v in self.graph

    def vertices(self):
        return list(self.graph.keys())

    @property
    def vertex_count(self):
        return len(self.graph)

    def V(self):
        return self.vertex_count

    # -------------------------------------------------------------- edges
    def add_edge(self, edge):
        """Add an undirected edge (stored in both endpoint adjacency lists)."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, v):
        """Edges incident to vertex ``v``."""
        return self.graph.get(v, [])

    def edges(self):
        return list(self._edges)

    @property
    def edge_count(self):
        return len(self._edges)

    def E(self):
        return self.edge_count

    def degree(self, v):
        return len(self.graph.get(v, []))

    # ----------------------------------------------------- station lines
    def set_station_lines(self, station_name, lines):
        """Record which lines a station belongs to."""
        self.station_lines[station_name] = list(lines or [])

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(set(self.station_lines.get(station_name, []))) > 1

    def __repr__(self):
        return f"Graph(V={self.vertex_count}, E={self.edge_count})"


class MinPQ:
    """Minimum priority queue backed by a binary heap (``heapq``).

    Items with equal priority are returned in insertion order; items
    themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    push = insert

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    pop = del_min

    def min(self):
        if not self._heap:
            raise IndexError("min of empty priority queue")
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
