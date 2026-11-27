"""
Path calculation: priority queue (MinPQ) and Dijkstra's shortest path
(ShortestPath) with support for several query modes, maximum transfer limits
and line preferences.

The search runs over states (station, current line[, transfers used]) so that
transfers at multi-line interchange stations are modeled explicitly.
Complexity is O((V+E) log V) in the number of states/edges.
"""

import itertools
import math

try:
    from models import Edge, Graph  # noqa: F401
except ImportError:  # pragma: no cover - package-style import
    from .models import Edge, Graph  # noqa: F401

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

#: Transfer cost (in equivalent meters) used by the comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
#: Weight multiplier applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.8


class MinPQ:
    """Binary-heap based minimum priority queue of (key, item) pairs."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        self._heap.append((key, next(self._counter), item))
        self._swim(len(self._heap) - 1)

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def min(self):
        if not self._heap:
            raise IndexError("min from empty priority queue")
        return self._heap[0][0], self._heap[0][2]

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    # ---- heap helpers ---------------------------------------------------
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


class PathfindingConfig:
    """
    Configuration of a path query.

    Attributes:
        mode:            'shortest_distance', 'least_transfer' or 'comprehensive'
        max_transfers:   maximum number of transfers allowed (None = unlimited)
        preferred_lines: list of line names to favour
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=TRANSFER_PENALTY_METERS, preference_factor=PREFERRED_LINE_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [p for p in preferred_lines if p]
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """
    Dijkstra's algorithm from a single source station.

    Attributes:
        source:       source station number
        dist_to:      dict station number -> distance (meters) of the chosen
                      route (math.inf when unreachable)
        edge_to:      dict station number -> last Edge on the chosen route
        transfers_to: dict station number -> number of transfers on that route
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: math.inf for v in graph.vertices}
        self.dist_to[source] = 0
        self.edge_to = {}
        self.transfers_to = {source: 0}
        self._best_state = {}
        self._parent = {}
        self._preferred = set(self.config.preferred_lines)
        self._run()

    # ---- key according to mode -------------------------------------------
    def _key(self, eff, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, eff)
        if mode == "comprehensive":
            return (eff + transfers * self.config.transfer_penalty, transfers)
        return (eff, transfers)

    def _run(self):
        max_t = self.config.max_transfers
        use_t = max_t is not None
        factor = self.config.preference_factor

        start = (self.source, None, 0) if use_t else (self.source, None)
        labels = {start: (0.0, 0, 0)}  # state -> (effective cost, real distance, transfers)
        self._parent[start] = None
        settled = set()
        pq = MinPQ()
        pq.insert(self._key(0.0, 0), start)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            v, cur_line = state[0], state[1]
            eff, real, t = labels[state]

            if v not in self._best_state:
                self._best_state[v] = state
                self.dist_to[v] = real
                self.transfers_to[v] = t
                parent = self._parent[state]
                if parent is not None:
                    self.edge_to[v] = parent[1]

            for e in self.graph.adj(v):
                nt = t + (1 if cur_line is not None and e.line != cur_line else 0)
                if use_t and nt > max_t:
                    continue
                ns = (e.dest, e.line, nt) if use_t else (e.dest, e.line)
                if ns in settled:
                    continue
                w = e.weight * (factor if e.line in self._preferred else 1.0)
                neff = eff + w
                nk = self._key(neff, nt)
                old = labels.get(ns)
                if old is None or nk < self._key(old[0], old[2]):
                    labels[ns] = (neff, real + e.weight, nt)
                    self._parent[ns] = (state, e)
                    pq.insert(nk, ns)

        if self.source not in self._best_state:
            self._best_state[self.source] = start

    # ---- queries ---------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """
        Return (list of station numbers, list of Edge) from source to target.
        Both lists are empty when target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while True:
            parent = self._parent.get(state)
            if parent is None:
                break
            state, edge = parent
            edges.append(edge)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the chosen path to ``target``."""
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if cur.line != prev.line:
                count += 1
        return count
