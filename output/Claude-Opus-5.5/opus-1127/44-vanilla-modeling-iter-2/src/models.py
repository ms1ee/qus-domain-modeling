"""
Core data structures: graph, edges, priority queue and domain objects.
"""

import heapq
import itertools
from dataclasses import dataclass, field
from typing import List, Optional


class Edge:
    """A weighted undirected edge between two station numbers.

    :param source: station number of one endpoint
    :param dest: station number of the other endpoint
    :param distance: distance in meters (also exposed as ``weight``)
    :param line: name of the subway line this connection belongs to
    """

    def __init__(self, source, dest, distance, line=None):
        if distance is None or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.weight = distance
        self.line = line

    @property
    def distance(self):
        """Distance in meters (alias of ``weight``)."""
        return self.weight

    @distance.setter
    def distance(self, value):
        if value is None or value < 0:
            raise ValueError("Edge distance must be non-negative")
        self.weight = value

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.weight!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. The graph additionally keeps
    ``station_lines`` (station name -> list of lines) for transfer handling.
    """

    def __init__(self):
        self._adj = {}
        self._edges = []
        self.station_lines = {}
        self.station_names = {}

    # ------------------------------------------------------------------ nodes
    def add_vertex(self, vertex, name=None):
        """Register a vertex (station number); optionally attach a name."""
        self._adj.setdefault(vertex, [])
        if name is not None:
            self.station_names[vertex] = name

    def set_station_lines(self, station_name, lines):
        """Set the lines a station belongs to (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def is_transfer_station(self, station_name):
        """Return True if the station is served by more than one line."""
        return len(self.station_lines.get(station_name, [])) > 1

    def has_vertex(self, vertex):
        return vertex in self._adj

    def __contains__(self, vertex):
        return vertex in self._adj

    def vertices(self):
        return list(self._adj.keys())

    @property
    def vertex_count(self):
        return len(self._adj)

    def V(self):
        return len(self._adj)

    # ------------------------------------------------------------------ edges
    def add_edge(self, edge):
        """Add an undirected edge (stored once, referenced from both endpoints)."""
        self._adj.setdefault(edge.source, []).append(edge)
        if edge.dest != edge.source:
            self._adj.setdefault(edge.dest, []).append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        """Remove a previously added edge object."""
        if edge in self._edges:
            self._edges.remove(edge)
            for vertex in (edge.source, edge.dest):
                lst = self._adj.get(vertex, [])
                if edge in lst:
                    lst.remove(edge)

    def adj(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self._adj.get(vertex, [])

    def edges(self):
        return list(self._edges)

    @property
    def edge_count(self):
        return len(self._edges)

    def E(self):
        return len(self._edges)

    @property
    def adjacency_list(self):
        return self._adj

    def degree(self, vertex):
        return len(self._adj.get(vertex, []))


class MinPQ:
    """Heap based minimum priority queue used to optimise Dijkstra's algorithm.

    Items are inserted with a priority; ties are broken by insertion order so
    arbitrary (possibly non-comparable) items can be stored.
    """

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    push = insert

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self.heap:
            raise IndexError("del_min from empty priority queue")
        priority, _, item = heapq.heappop(self.heap)
        return priority, item

    pop = del_min

    def min(self):
        if not self.heap:
            raise IndexError("min of empty priority queue")
        priority, _, item = self.heap[0]
        return priority, item

    def is_empty(self):
        return not self.heap

    @property
    def size(self):
        return len(self.heap)

    def __len__(self):
        return len(self.heap)

    def __bool__(self):
        return bool(self.heap)


# ---------------------------------------------------------------- domain objects
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
class Connection:
    source: str
    dest: str
    distance: int
    line: Optional[str] = None
    bidirectional: bool = True


@dataclass
class Transfer:
    station: str
    from_line: Optional[str]
    to_line: Optional[str]
    transfer_time: float = 5.0
    transfer_distance: int = 0


@dataclass
class Segment:
    line: Optional[str]
    stations: List[str] = field(default_factory=list)
    distance: int = 0


@dataclass
class Route:
    start: str
    end: str
    station_sequence: List[str]
    total_distance: int
    transfer_count: int
    involved_lines: List[str]
    estimated_time: float
    fare: int
    transfers: List[Transfer] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    mode: str = "shortest_distance"

    @property
    def total_distance_km(self):
        return self.total_distance / 1000.0
