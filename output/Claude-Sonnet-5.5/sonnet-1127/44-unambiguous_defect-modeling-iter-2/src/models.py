"""Core data structures: Edge, Graph, MinPQ."""
import heapq
import itertools


class Edge:
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
        return f"Edge({self.source}->{self.dest}, {self.distance}, {self.line})"


class Graph:
    """Weighted undirected graph with adjacency lists (station numbers)."""

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def add_node(self, n):
        self.adjacency.setdefault(n, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge.reversed())

    def edges_from(self, n):
        return self.adjacency.get(n, [])

    def nodes(self):
        return list(self.adjacency.keys())

    def node_count(self):
        return len(self.adjacency)

    def edge_count(self):
        return sum(len(v) for v in self.adjacency.values()) // 2


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)
