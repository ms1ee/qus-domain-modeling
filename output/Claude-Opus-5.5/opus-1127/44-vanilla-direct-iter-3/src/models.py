"""Core data structures: Edge, Graph (weighted undirected) and MinPQ."""

import heapq
import itertools
import math


class Edge:
    """A weighted edge between two stations (identified by numbers)."""

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if math.isnan(distance) or distance < 0:
            raise ValueError("Edge distance must be non-negative")
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
        raise ValueError("Vertex is not an endpoint of this edge")

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r -> %r, %r m, %r)" % (self.source, self.dest, self.weight, self.line)


class Graph:
    """Weighted undirected graph using adjacency lists.

    ``graph`` maps a station number to the list of outgoing :class:`Edge`
    objects. Every undirected connection is stored in both directions.
    Station numbers are assigned by the caller.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self._edges = []

    # ---- stations -------------------------------------------------------
    def add_station(self, station_name, number, lines=None):
        self.station_to_number[station_name] = number
        self.number_to_station[number] = station_name
        self.graph.setdefault(number, [])
        if lines is not None:
            self.set_station_lines(station_name, lines)

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines or [])

    def add_vertex(self, v):
        self.graph.setdefault(v, [])

    def is_transfer_station(self, station_name):
        return len(set(self.station_lines.get(station_name, []))) > 1

    def transfer_stations(self):
        return [n for n in self.station_lines if self.is_transfer_station(n)]

    def get_station_name(self, number):
        return self.number_to_station.get(number, str(number))

    def get_station_number(self, name):
        return self.station_to_number.get(name)

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        self.graph.setdefault(edge.source, []).append(edge)
        if edge.source != edge.dest:
            self.graph.setdefault(edge.dest, []).append(edge.reversed())
        self._edges.append(edge)

    def adj(self, v):
        return list(self.graph.get(v, []))

    def edges(self):
        return list(self._edges)

    def vertices(self):
        return list(self.graph.keys())

    @property
    def V(self):
        return len(self.graph)

    @property
    def E(self):
        return len(self._edges)

    def __contains__(self, v):
        return v in self.graph


class MinPQ:
    """Heap-based minimum priority queue (stable for equal priorities)."""

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
