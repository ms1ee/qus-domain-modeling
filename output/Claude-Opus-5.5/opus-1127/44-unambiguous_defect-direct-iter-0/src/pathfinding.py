"""Shortest path computation (Dijkstra with a binary-heap priority queue).

The search runs over states ``(station, current_line[, transfers])`` so
that transfers at multi-line interchange stations are handled exactly.
Each query mode defines a lexicographic cost key:

* shortest_distance: (distance, transfers, non-preferred distance)
* least_transfer:    (transfers, weighted distance, distance)
* comprehensive:     (distance + transfer penalty + preference penalty, ...)

All key components are non-negative and additive, so Dijkstra's algorithm
remains correct.  Complexity: O((V + E) log V) on the state graph.
"""

import heapq
import itertools
import math

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY_METERS = 4000
NON_PREFERRED_PENALTY_RATIO = 0.3


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode %r, expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def __repr__(self):
        return "PathfindingConfig(mode=%r, max_transfers=%r, preferred_lines=%r)" % (
            self.mode, self.max_transfers, self.preferred_lines)


class MinPQ:
    """Minimum priority queue backed by a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min(self):
        if not self._heap:
            raise IndexError("min of empty priority queue")
        key, _, item = self._heap[0]
        return key, item

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Single-source shortest paths from ``source`` (a station number)."""

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError("Source station %r is not in the graph" % (source,))
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._preferred = set(self.config.preferred_lines)
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self._best_state = {}
        self._parent = {}
        self._costs = {}
        self._run()

    # ---------------------------------------------------------------- core
    def _key(self, dist, transfers, nonpref):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, dist + nonpref * NON_PREFERRED_PENALTY_RATIO, dist)
        if mode == "comprehensive":
            score = dist + transfers * TRANSFER_PENALTY_METERS + nonpref * NON_PREFERRED_PENALTY_RATIO
            return (score, transfers, dist)
        return (dist, transfers, nonpref)

    def _run(self):
        max_t = self.config.max_transfers
        track = max_t is not None
        start = (self.source, None, 0)
        best_key = {start: self._key(0, 0, 0)}
        self._costs[start] = (0, 0, 0)
        pq = MinPQ()
        pq.insert(best_key[start], start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled or key > best_key[state]:
                continue
            settled.add(state)
            vertex, line, _ = state
            dist, transfers, nonpref = self._costs[state]
            if vertex not in self._best_state:
                self._best_state[vertex] = state
                self.dist_to[vertex] = dist

            for edge in self.graph.adj(vertex):
                new_transfers = transfers + (1 if line is not None and edge.line != line else 0)
                if track and new_transfers > max_t:
                    continue
                new_state = (edge.dest, edge.line, new_transfers if track else 0)
                if new_state in settled:
                    continue
                new_dist = dist + edge.weight
                new_nonpref = nonpref
                if self._preferred and edge.line not in self._preferred:
                    new_nonpref += edge.weight
                new_key = self._key(new_dist, new_transfers, new_nonpref)
                old = best_key.get(new_state)
                if old is None or new_key < old:
                    best_key[new_state] = new_key
                    self._costs[new_state] = (new_dist, new_transfers, new_nonpref)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

    # ------------------------------------------------------------- queries
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) when the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                count += 1
        return count

    def get_lines(self, target):
        """Ordered list of distinct lines used along the path."""
        _, edges = self.path_with_edges(target)
        lines = []
        for edge in edges:
            if not lines or lines[-1] != edge.line:
                if edge.line not in lines:
                    lines.append(edge.line)
        return lines
