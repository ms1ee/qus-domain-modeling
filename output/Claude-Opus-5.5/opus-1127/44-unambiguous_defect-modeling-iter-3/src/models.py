"""Core data structures: edges, the weighted undirected graph and a
heap-based minimum priority queue."""

import heapq
import itertools
import math


class Edge:
    """A weighted, line-labelled connection between two station numbers.

    Attributes:
        source:   station number the edge starts from
        dest:     station number the edge leads to
        distance: distance in meters
        weight:   same as distance (used by the path algorithms)
        line:     name of the subway line operating this connection
    """

    def __init__(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if math.isnan(distance) or distance < 0:
            raise ValueError("Edge distance must be a non-negative number")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of this edge")

    def reversed(self):
        """Return a new edge going in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def _key(self):
        return (self.source, self.dest, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller.  ``graph`` is the adjacency
    dictionary ``{station number: [Edge, ...]}``; each undirected connection is
    stored as two directed ``Edge`` objects so every edge in a vertex's list
    has ``edge.source == vertex``.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edge_count = 0

    # ----- vertices / stations -------------------------------------------
    def add_vertex(self, vertex):
        self.graph.setdefault(vertex, [])

    def set_station_lines(self, station_name, lines):
        """Record the lines serving ``station_name`` (duplicates removed)."""
        if lines is None:
            lines = []
        if isinstance(lines, str):
            lines = [lines]
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def is_transfer_station(self, station_name):
        """A station served by more than one line is a transfer station."""
        return len(self.station_lines.get(station_name, [])) > 1

    @property
    def vertices(self):
        return list(self.graph.keys())

    @property
    def vertex_count(self):
        return len(self.graph)

    @property
    def edge_count(self):
        return self._edge_count

    # ----- edges ------------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.graph.setdefault(edge.source, []).append(edge)
        if edge.source != edge.dest:
            self.graph.setdefault(edge.dest, []).append(edge.reversed())
        self._edge_count += 1

    def adj(self, vertex):
        """Edges leaving ``vertex``."""
        return self.graph.get(vertex, [])

    def edges(self):
        """Each undirected edge exactly once."""
        result = []
        seen = set()
        for vertex, edges in self.graph.items():
            for edge in edges:
                key = (frozenset((edge.source, edge.dest)), edge.line, edge.distance)
                if key in seen:
                    continue
                seen.add(key)
                result.append(edge)
        return result

    def get_edge(self, source, dest, line=None):
        for edge in self.adj(source):
            if edge.dest == dest and (line is None or edge.line == line):
                return edge
        return None

    def __repr__(self):
        return f"Graph(vertices={self.vertex_count}, edges={self.edge_count})"


class MinPQ:
    """Minimum priority queue backed by a binary heap.

    Items with equal priority are returned in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, item, priority):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    insert = push

    def pop(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("pop from an empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def peek(self):
        if not self._heap:
            raise IndexError("peek at an empty priority queue")
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
