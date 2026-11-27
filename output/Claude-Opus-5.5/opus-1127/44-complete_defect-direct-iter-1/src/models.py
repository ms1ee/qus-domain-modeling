"""
Core graph data structures: Edge, Graph and the MinPQ priority queue.
"""


class Edge:
    """A weighted, line-labelled connection between two stations.

    ``source`` and ``dest`` are station numbers; ``weight`` equals the
    distance in meters.
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

    def reversed(self):
        """Return the same connection in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def other(self, v):
        """Return the endpoint that is not ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, "
                f"{self.distance!r}, {self.line!r})")


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    ``graph`` is a dictionary mapping station number -> list of outgoing
    Edge objects. Each undirected connection is stored in both directions.
    Station numbers are assigned by the caller.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edges = []

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, v):
        self.graph.setdefault(v, [])

    def vertices(self):
        return list(self.graph.keys())

    @property
    def V(self):
        return len(self.graph)

    @property
    def E(self):
        return len(self._edges)

    # ---- station metadata ----------------------------------------------
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self._edges.append(edge)

    def adj(self, v):
        return self.graph.get(v, [])

    def edges(self):
        return list(self._edges)

    def remove_edge(self, a, b, line=None):
        """Remove the connection(s) between a and b (optionally on one line)."""
        def match(e, x, y):
            return e.source == x and e.dest == y and (line is None or e.line == line)

        removed = 0
        for v in (a, b):
            if v in self.graph:
                before = len(self.graph[v])
                self.graph[v] = [e for e in self.graph[v]
                                 if not (match(e, a, b) or match(e, b, a))]
                removed += before - len(self.graph[v])
        self._edges = [e for e in self._edges
                       if not (match(e, a, b) or match(e, b, a))]
        return removed > 0

    def update_edge_distance(self, a, b, distance, line=None):
        """Update the distance of connection(s) between a and b."""
        updated = False
        for v in (a, b):
            for e in self.graph.get(v, []):
                if {e.source, e.dest} == {a, b} and (line is None or e.line == line):
                    e.distance = distance
                    e.weight = distance
                    updated = True
        for e in self._edges:
            if {e.source, e.dest} == {a, b} and (line is None or e.line == line):
                e.distance = distance
                e.weight = distance
        return updated


class MinPQ:
    """Binary-heap minimum priority queue.

    Items are (key, value) pairs; ties are broken by insertion order so that
    values never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def __len__(self):
        return len(self._heap)

    def size(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def insert(self, key, value):
        self._heap.append((key, self._counter, value))
        self._counter += 1
        self._swim(len(self._heap) - 1)

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        key, _, value = self._heap[0]
        return key, value

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i, j):
        a, b = self._heap[i], self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._heap[k], self._heap[parent] = self._heap[parent], self._heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and self._less(right, left):
                child = right
            if self._less(child, k):
                self._heap[k], self._heap[child] = self._heap[child], self._heap[k]
                k = child
            else:
                break
