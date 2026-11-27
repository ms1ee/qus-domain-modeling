"""
Shortest path computation (Dijkstra's algorithm with a heap-based priority queue).

The search runs over states ``(station, current_line[, transfers])`` so that
line changes at interchange stations are counted correctly, which allows
transfer-aware modes, maximum transfer limits and line preferences.
"""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in meters) applied per transfer in comprehensive mode
TRANSFER_PENALTY_METERS = 3000
# Extra weight factor for distance travelled on non-preferred lines (comprehensive mode)
NON_PREFERRED_FACTOR = 0.5


class MinPQ:
    """Heap-based minimum priority queue (lazy deletion friendly)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    push = insert

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    pop = del_min

    def min(self):
        if not self._heap:
            raise IndexError("min from empty priority queue")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Single-source shortest paths from ``source`` (a station number)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        mode = self.config.mode or "shortest_distance"
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown path query mode: {mode!r}")
        self.mode = mode
        max_t = self.config.max_transfers
        if max_t is not None:
            max_t = int(max_t)
            if max_t < 0:
                raise ValueError("max_transfers must be non-negative")
        self.max_transfers = max_t
        self.preferred_lines = set(self.config.preferred_lines or [])

        self.dist_to = {}
        self._transfers_to = {}
        self._best_state = {}
        self._edge_to = {}
        self._run()

    # ------------------------------------------------------------------
    def _key(self, d, t, np_dist):
        if self.mode == "least_transfer":
            return (t, d, np_dist)
        if self.mode == "comprehensive":
            return (d + TRANSFER_PENALTY_METERS * t + NON_PREFERRED_FACTOR * np_dist, d, t)
        return (d, np_dist, t)

    def _run(self):
        limited = self.max_transfers is not None
        prefs = self.preferred_lines
        start = (self.source, None, 0)
        comps = {start: (0, 0, 0)}
        done = set()
        pq = MinPQ()
        pq.insert(self._key(0, 0, 0), start)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            node, line, _ = state
            d, t, np_dist = comps[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = d
                self._transfers_to[node] = t
            for e in self.graph.adj(node):
                inc = 1 if (line is not None and e.line != line) else 0
                nt = t + inc
                if limited and nt > self.max_transfers:
                    continue
                nd = d + e.weight
                nnp = np_dist + (e.weight if prefs and e.line not in prefs else 0)
                ns = (e.dest, e.line, nt if limited else 0)
                if ns in done:
                    continue
                nk = self._key(nd, nt, nnp)
                old = comps.get(ns)
                if old is None or nk < self._key(*old):
                    comps[ns] = (nd, nt, nnp)
                    self._edge_to[ns] = (state, e)
                    pq.insert(nk, ns)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to target.

        Returns ``([], [])`` if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while state in self._edge_to:
            prev, e = self._edge_to[state]
            edges.append(e)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to ``target`` (0 if unreachable)."""
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
