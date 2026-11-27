"""Core data models: Station, Line, Edge, Graph, MinPQ."""
import heapq


class Station:
    def __init__(self, name, station_id, is_transfer=False):
        self.name = name
        self.station_id = station_id
        self.is_transfer = is_transfer


class Line:
    def __init__(self, name, station_sequence=None):
        self.name = name
        self.station_sequence = list(station_sequence or [])


class Edge:
    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def __repr__(self):
        return "Edge(%r,%r,%r,%r)" % (self.source, self.dest, self.distance, self.line)


Connection = Edge


class MinPQ:
    """Heap based min priority queue of (priority, item)."""

    def __init__(self):
        self.heap = []
        self._n = 0

    def push(self, priority, item):
        self._n += 1
        heapq.heappush(self.heap, (priority, self._n, item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class Graph:
    """Weighted directed graph; station numbers are given by the caller."""

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.adjacency = {}
        self.station_lines = {}

    @property
    def graph(self):
        return self.adjacency

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, [])

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1
