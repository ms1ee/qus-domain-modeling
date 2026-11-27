"""Dijkstra shortest path with transfer awareness."""
import heapq
import itertools

TRANSFER_PENALTY = {
    "shortest_distance": 0,
    "least_transfer": 1000000,
    "comprehensive": 2000,
}


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Heap-based min priority queue."""

    def __init__(self):
        self._h = []
        self._c = itertools.count()

    def push(self, key, item):
        heapq.heappush(self._h, (key, next(self._c), item))

    def pop(self):
        k, _, item = heapq.heappop(self._h)
        return k, item

    def is_empty(self):
        return not self._h


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._prev = {}  # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        best = {start: 0.0}
        real = {start: 0}
        settled = set()
        pq = MinPQ()
        pq.push(0.0, start)
        self._prev[start] = None
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in settled:
                continue
            settled.add(st)
            node, line, t = st
            if node not in self._best_state:
                self._best_state[node] = st
                self.dist_to[node] = real[st]
            for e in self.graph.edges_from(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    if limit is not None and t + 1 > limit:
                        continue
                    extra = penalty
                    if limit is not None:
                        nt = t + 1
                w = e.weight
                if pref and e.line in pref:
                    w = w * 0.9
                ns = (e.dest, e.line, nt)
                nc = cost + w + extra
                if ns not in settled and nc < best.get(ns, float("inf")):
                    best[ns] = nc
                    real[ns] = real[st] + e.weight
                    self._prev[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while self._prev.get(st) is not None:
            st, e = self._prev[st]
            edges.append(e)
        edges.reverse()
        return [self.source] + [e.dest for e in edges], edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        n = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                n += 1
        return n
