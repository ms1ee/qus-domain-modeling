"""Core data structures: Edge, Graph, MinPQ."""
import heapq
import itertools


class Edge:
    """Directed view of a connection between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph; station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge (both directions)."""
        for e in (edge, edge.reversed()):
            lst = self.adjacency.setdefault(e.source, [])
            if not any(x.dest == e.dest and x.line == e.line for x in lst):
                lst.append(e)
            self.adjacency.setdefault(e.dest, [])

    def remove_edges(self, a, b, line=None):
        for x, y in ((a, b), (b, a)):
            self.adjacency[x] = [e for e in self.adjacency.get(x, [])
                                 if not (e.dest == y and (line is None or e.line == line))]

    def neighbors(self, node):
        return self.adjacency.get(node, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1


class MinPQ:
    """Heap based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self._heap)
        return p, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
