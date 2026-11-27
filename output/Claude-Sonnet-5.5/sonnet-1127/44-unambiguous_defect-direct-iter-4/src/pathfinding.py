"""MinPQ and Dijkstra-based ShortestPath."""
import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap priority queue."""

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
        self._best_state = {}
        self._parent = {}   # state -> (prev_state, edge)
        self._run()

    def _penalty(self):
        m = self.config.mode
        if m == "least_transfer":
            return 100000
        if m == "comprehensive":
            return 1500
        return 0

    def _run(self):
        cfg = self.config
        pen = self._penalty()
        limit = cfg.max_transfers
        prefs = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        cost = {start: 0.0}
        real = {start: 0}
        self._parent[start] = None
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        node_cost = {}
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, t = st
            if node not in node_cost or c < node_cost[node]:
                node_cost[node] = c
                self._best_state[node] = st
                self.dist_to[node] = real[st]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    extra = pen
                    if limit is not None:
                        nt = t + 1
                        if nt > limit:
                            continue
                w = e.distance * (0.9 if e.line in prefs else 1.0)
                ns = (e.dest, e.line, nt)
                nc = c + w + extra
                if ns not in done and nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    real[ns] = real[st] + e.distance
                    self._parent[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self.dist_to

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while self._parent[st] is not None:
            st, e = self._parent[st]
            edges.append(e)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
