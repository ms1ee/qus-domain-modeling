"""
Core data structures: weighted undirected graph and a heap-based min
priority queue.

Station numbers are assigned by the caller; the :class:`Graph` simply stores
whatever integer identifiers it is given.
"""


class Edge:
    """A weighted connection between two stations on a specific line.

    :param source: station number of one endpoint
    :param dest:   station number of the other endpoint
    :param distance: distance in meters (non-negative)
    :param line:   name of the line this connection belongs to
    """

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
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
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return a copy of this edge with swapped direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        adjacency:     dict station number -> list of outgoing :class:`Edge`
        station_lines: dict station name -> list of line names
        station_names: dict station number -> station name (optional info)
    """

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}
        self.station_names = {}
        self._edges = []

    # -- node management ------------------------------------------------
    def add_station(self, number, name=None, lines=None):
        self.adjacency.setdefault(number, [])
        if name is not None:
            self.station_names[number] = name
            if lines is not None:
                self.set_station_lines(name, lines)

    def set_station_lines(self, station_name, lines):
        unique = []
        for line in lines or []:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # -- edge management ------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both endpoints' adjacency lists)."""
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, []).append(edge.reversed())
        self._edges.append(edge)

    def update_edge_distance(self, u, v, distance, line=None):
        """Update the distance of edge(s) between u and v. Returns number updated."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
            raise ValueError("Distance must be a non-negative number")
        count = 0
        for vertex in (u, v):
            for e in self.adjacency.get(vertex, []):
                if {e.source, e.dest} == {u, v} and (line is None or e.line == line):
                    e.distance = distance
                    e.weight = distance
        for e in self._edges:
            if {e.source, e.dest} == {u, v} and (line is None or e.line == line):
                e.distance = distance
                e.weight = distance
                count += 1
        return count

    def adj(self, vertex):
        return list(self.adjacency.get(vertex, []))

    def vertices(self):
        return list(self.adjacency.keys())

    def edges(self):
        return list(self._edges)

    def has_station(self, number):
        return number in self.adjacency

    def V(self):
        return len(self.adjacency)

    def E(self):
        return len(self._edges)

    @property
    def vertex_count(self):
        return self.V()

    @property
    def edge_count(self):
        return self.E()


class MinPQ:
    """Binary-heap based minimum priority queue.

    Items must be mutually comparable (tuples are typically used).
    """

    def __init__(self):
        self._heap = []

    def insert(self, item):
        self._heap.append(item)
        self._swim(len(self._heap) - 1)

    push = insert

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._heap[0]

    peek = min

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top

    pop = del_min

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)

    # -- heap helpers ---------------------------------------------------
    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k] < heap[parent]:
                heap[k], heap[parent] = heap[parent], heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        heap = self._heap
        n = len(heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            smallest = left
            right = left + 1
            if right < n and heap[right] < heap[left]:
                smallest = right
            if heap[smallest] < heap[k]:
                heap[k], heap[smallest] = heap[smallest], heap[k]
                k = smallest
            else:
                break
