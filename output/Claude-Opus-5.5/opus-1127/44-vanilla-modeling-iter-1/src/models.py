"""Core data structures: stations, lines, edges, the subway graph and a
heap-based minimum priority queue."""

import heapq
import itertools
from dataclasses import dataclass, field
from typing import List


@dataclass
class Station:
    """A subway station."""

    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    """A subway line with its ordered station sequence."""

    name: str
    stations: List[str] = field(default_factory=list)


@dataclass
class Connection:
    """A raw connection between two adjacent stations (in meters)."""

    source: str
    dest: str
    distance: int
    line: str
    bidirectional: bool = True


class Edge:
    """A weighted undirected edge between two station numbers on one line."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight: the actual inter-station distance in meters."""
        return self.distance

    def either(self):
        return self.source

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller; the graph simply stores
    them. ``graph`` is the adjacency dictionary ``{number: [Edge, ...]}``.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.station_names = {}
        self._edge_count = 0

    # ----- vertices -----
    def add_vertex(self, vertex):
        if vertex not in self.graph:
            self.graph[vertex] = []

    def vertices(self):
        return list(self.graph.keys())

    def V(self):
        return len(self.graph)

    def E(self):
        return self._edge_count

    @property
    def vertex_count(self):
        return self.V()

    @property
    def edge_count(self):
        return self.E()

    # ----- station metadata -----
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def set_station_name(self, number, name):
        self.station_names[number] = name

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges -----
    def add_edge(self, edge):
        """Add an undirected edge (stored in both endpoint adjacency lists)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edge_count += 1

    def adj(self, vertex):
        return self.graph.get(vertex, [])

    def edges(self):
        seen = set()
        result = []
        for edge_list in self.graph.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def get_edges_between(self, u, v, line=None):
        return [
            e for e in self.adj(u)
            if (e.source == v or e.dest == v) and (line is None or e.line == line)
        ]

    def update_edge_distance(self, u, v, distance, line=None):
        """Update distance of edges between u and v; return number updated."""
        edges = self.get_edges_between(u, v, line)
        for e in edges:
            e.distance = distance
        return len(edges)


class MinPQ:
    """Minimum priority queue backed by a binary heap (``heapq``).

    Items with equal keys are returned in insertion order; items themselves
    never need to be comparable.
    """

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        heapq.heappush(self.heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key."""
        if not self.heap:
            raise IndexError("del_min from empty priority queue")
        key, _, item = heapq.heappop(self.heap)
        return key, item

    def min(self):
        if not self.heap:
            raise IndexError("min of empty priority queue")
        key, _, item = self.heap[0]
        return key, item

    def is_empty(self):
        return not self.heap

    @property
    def size(self):
        return len(self.heap)

    def __len__(self):
        return len(self.heap)
