"""Core data structures: Edge, Graph (weighted undirected) and MinPQ."""


class Edge:
    """A weighted, line-labelled edge between two station numbers."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        return self.source

    def other(self, v):
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (v,))

    def reversed(self):
        """Return the same connection travelled in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == \
               (other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.weight, self.line)


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller.  ``adj`` (also exposed as
    ``graph``) maps a station number to the list of outgoing edges.
    """

    def __init__(self):
        self.adj = {}
        self.graph = self.adj
        self.station_lines = {}
        self.station_names = {}   # number -> name (optional, set by caller)
        self._edges = []

    # ---- nodes -------------------------------------------------------
    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def add_station(self, number, name, lines=None):
        self.add_vertex(number)
        self.station_names[number] = name
        if lines is not None:
            self.set_station_lines(name, lines)

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def lines_of(self, number):
        name = self.station_names.get(number)
        return list(self.station_lines.get(name, [])) if name is not None else []

    def vertices(self):
        return list(self.adj.keys())

    def V(self):
        return len(self.adj)

    def has_vertex(self, v):
        return v in self.adj

    # ---- edges -------------------------------------------------------
    def add_edge(self, edge):
        if edge.weight is None or edge.weight < 0:
            raise ValueError("Edge distance must be a non-negative number")
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, []).append(edge.reversed())
        self._edges.append(edge)

    def adjacent(self, v):
        return self.adj.get(v, [])

    def edges(self):
        return list(self._edges)

    def E(self):
        return len(self._edges)


class MinPQ:
    """Binary-heap based min priority queue of (key, value) pairs.

    Ties on key are broken by insertion order so values never need to be
    comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def push(self, key, value):
        self._heap.append((key, self._counter, value))
        self._counter += 1
        self._swim(len(self._heap) - 1)

    insert = push

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty priority queue")
        key, _, value = self._heap[0]
        return key, value

    def pop(self):
        if not self._heap:
            raise IndexError("pop from empty priority queue")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top[0], top[2]

    del_min = pop

    def _less(self, i, j):
        a, b = self._heap[i], self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
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
            child = left
            if left + 1 < n and self._less(left + 1, left):
                child = left + 1
            if self._less(child, k):
                heap[k], heap[child] = heap[child], heap[k]
                k = child
            else:
                break
