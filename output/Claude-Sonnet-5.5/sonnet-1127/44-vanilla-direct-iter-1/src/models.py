"""Graph data structures."""
import heapq
import itertools


class Edge:
    """Undirected edge between station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class MinPQ:
    """Heap based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


class Graph:
    """Weighted undirected graph (adjacency lists keyed by station number)."""

    def __init__(self):
        self.graph = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}

    def add_station(self, name, number=None):
        if name in self.station_to_number:
            return self.station_to_number[name]
        if number is None:
            number = len(self.station_to_number)
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.setdefault(number, [])
        return number

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        self.graph.setdefault(edge.source, []).append(edge)
        self.graph.setdefault(edge.dest, []).append(edge.reversed())

    def adj(self, node):
        return self.graph.get(node, [])

    def set_distance(self, a, b, distance, line=None):
        """Update distance of edges between a and b; returns True if found."""
        found = False
        for u, v in ((a, b), (b, a)):
            for e in self.graph.get(u, []):
                if e.dest == v and (line is None or e.line == line):
                    e.distance = distance
                    e.weight = distance
                    found = True
        return found

    def is_transfer_station(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def V(self):
        return len(self.graph)

    def E(self):
        return sum(len(v) for v in self.graph.values()) // 2
