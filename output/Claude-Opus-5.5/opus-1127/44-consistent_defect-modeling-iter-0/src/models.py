"""
Core data structures: Edge, Graph, MinPQ and simple domain records.
"""

import heapq
import itertools
from dataclasses import dataclass, field
from typing import List, Optional


class Edge:
    """A weighted directed edge between two station numbers."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source!r} -> {self.dest!r}, {self.distance}m, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted directed graph keyed by caller-assigned station numbers.

    Each edge is usable only in the direction it was added.
    """

    def __init__(self):
        self.adj = {}             # station number -> list[Edge]
        self.station_lines = {}   # station name -> list[str]
        self.edge_count = 0

    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])
        self.edge_count += 1

    def edges_from(self, v):
        return self.adj.get(v, [])

    def adj_of(self, v):
        return self.edges_from(v)

    def edges(self):
        for lst in self.adj.values():
            for e in lst:
                yield e

    @property
    def vertices(self):
        return list(self.adj.keys())

    @property
    def vertex_count(self):
        return len(self.adj)

    def V(self):
        return self.vertex_count

    def E(self):
        return self.edge_count

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1


class MinPQ:
    """Binary-heap based minimum priority queue (stable for equal keys)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        heapq.heappush(self._heap, (key, next(self._counter), item))

    push = insert

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    pop = del_min

    def is_empty(self):
        return not self._heap

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    name: str
    station_sequence: List[str] = field(default_factory=list)


@dataclass
class TransferDetail:
    station_name: str
    from_line: Optional[str]
    to_line: Optional[str]


@dataclass
class FareResult:
    fare: int
    distance: int


@dataclass
class Route:
    start: str
    end: str
    station_sequence: List[str]
    total_distance: int
    transfer_count: int
    estimated_time: float
    involved_lines: List[str]
    transfers: List[TransferDetail]
    segments: List[dict]
    fare: int
    mode: str = "shortest_distance"
