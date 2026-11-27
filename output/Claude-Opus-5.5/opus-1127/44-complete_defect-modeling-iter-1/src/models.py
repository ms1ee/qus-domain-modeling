"""
Core data structures: Edge, Graph (weighted undirected graph using
adjacency lists) and MinPQ (binary-heap based priority queue).
"""


class Edge:
    """A weighted, directed edge between two station numbers on a line."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def reversed(self):
        """Return the edge in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def other(self, v):
        """Return the endpoint different from ``v``."""
        return self.dest if v == self.source else self.source

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))

    def __repr__(self):
        return f"Edge({self.source!r}->{self.dest!r}, {self.weight}m, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller.  Adding an edge stores it in
    both directions.  ``graph`` maps station number -> list of outgoing Edges.
    ``station_lines`` maps station name -> list of line names.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.edge_count = 0

    # ------------------------------------------------------------------ nodes
    @property
    def vertex_count(self):
        return len(self.graph)

    def add_vertex(self, v):
        if v not in self.graph:
            self.graph[v] = []

    def vertices(self):
        return list(self.graph.keys())

    def set_station_lines(self, station_name, lines):
        """Record which lines serve a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ------------------------------------------------------------------ edges
    def _find(self, u, v, line):
        for e in self.graph.get(u, []):
            if e.dest == v and e.line == line:
                return e
        return None

    def add_edge(self, edge):
        """Add an undirected edge. Returns False if an identical edge
        (same endpoints and line) already exists, in which case its weight
        is updated."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        existing = self._find(edge.source, edge.dest, edge.line)
        if existing is not None:
            self.update_edge_weight(edge.source, edge.dest, edge.weight, edge.line)
            return False
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self.edge_count += 1
        return True

    def update_edge_weight(self, u, v, distance, line=None):
        """Update the weight of edge(s) between u and v (optionally only on
        a given line). Returns number of undirected edges updated."""
        count = 0
        for a, b in ((u, v), (v, u)):
            for e in self.graph.get(a, []):
                if e.dest == b and (line is None or e.line == line):
                    e.weight = distance
                    e.distance = distance
                    if a == u:
                        count += 1
        return count

    def remove_edge(self, u, v, line=None):
        removed = 0
        for a, b in ((u, v), (v, u)):
            if a not in self.graph:
                continue
            before = len(self.graph[a])
            self.graph[a] = [e for e in self.graph[a]
                             if not (e.dest == b and (line is None or e.line == line))]
            if a == u:
                removed = before - len(self.graph[a])
        self.edge_count -= removed
        return removed

    def adjacent(self, v):
        return self.graph.get(v, [])

    def edges(self):
        """Return each undirected edge once."""
        seen = set()
        result = []
        for u, lst in self.graph.items():
            for e in lst:
                key = (min(repr(e.source), repr(e.dest)), max(repr(e.source), repr(e.dest)), e.line)
                if key in seen:
                    continue
                seen.add(key)
                result.append(e)
        return result


class MinPQ:
    """Minimum priority queue implemented as a binary heap.

    Items are inserted with a comparable key; ties are broken by insertion
    order so that items themselves never need to be comparable.
    """

    def __init__(self):
        self.heap = []
        self._counter = 0

    @property
    def size(self):
        return len(self.heap)

    def __len__(self):
        return len(self.heap)

    def is_empty(self):
        return not self.heap

    def insert(self, key, item):
        self.heap.append((key, self._counter, item))
        self._counter += 1
        self._swim(len(self.heap) - 1)

    push = insert

    def min(self):
        if not self.heap:
            raise IndexError("priority queue is empty")
        key, _, item = self.heap[0]
        return key, item

    def del_min(self):
        if not self.heap:
            raise IndexError("priority queue is empty")
        top = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self._sink(0)
        return top[0], top[2]

    pop = del_min

    def _less(self, i, j):
        return self.heap[i][:2] < self.heap[j][:2]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self.heap[k], self.heap[parent] = self.heap[parent], self.heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self.heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            if left + 1 < n and self._less(left + 1, left):
                child = left + 1
            if self._less(child, k):
                self.heap[k], self.heap[child] = self.heap[child], self.heap[k]
                k = child
            else:
                break
