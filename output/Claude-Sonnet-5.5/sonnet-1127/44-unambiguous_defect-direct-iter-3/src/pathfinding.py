"""Dijkstra shortest path with priority queue."""
import heapq
import itertools

from models import Graph  # noqa: F401

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap minimum priority queue."""

    def __init__(self):
        self._h = []
        self._c = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._h, (priority, next(self._c), item))

    def pop(self):
        p, _, item = heapq.heappop(self._h)
        return p, item

    def is_empty(self):
        return not self._h

    def __len__(self):
        return len(self._h)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}   # node -> state
        self._info = {}   # state -> (cost, dist, prev_state, edge, transfers)
        self._run()

    def _penalty(self):
        mode = self.config.mode
        if mode == "least_transfer":
            return 100000.0
        if mode == "comprehensive":
            return 1000.0
        return 0.0

    def _run(self):
        pen = self._penalty()
        limit = self.config.max_transfers
        prefs = set(self.config.preferred_lines or [])

        def key(node, line, t):
            return (node, line, t if limit is not None else 0)

        start = key(self.source, None, 0)
        self._info[start] = (0.0, 0, None, None, 0)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, _ = st
            _, d, _, _, t = self._info[st]
            cur = self._best.get(node)
            if cur is None or (cost, d) < (self._info[cur][0], self._info[cur][1]):
                self._best[node] = st
                self.dist_to[node] = d
            for e in self.graph.adj(node):
                nt = t + (1 if line is not None and e.line != line else 0)
                if limit is not None and nt > limit:
                    continue
                w = e.weight * (0.9 if e.line in prefs else 1.0)
                ncost = cost + w + (pen if nt > t else 0)
                ns = key(e.dest, e.line, nt)
                if ns in done:
                    continue
                old = self._info.get(ns)
                if old is None or ncost < old[0]:
                    self._info[ns] = (ncost, d + e.distance, st, e, nt)
                    pq.push(ncost, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        st = self._best.get(target)
        if st is None:
            return [], []
        edges = []
        while st is not None:
            _, _, prev, e, _ = self._info[st]
            if e is not None:
                edges.append(e)
            st = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
