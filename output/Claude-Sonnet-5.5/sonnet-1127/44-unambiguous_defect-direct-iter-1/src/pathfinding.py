"""Dijkstra shortest path with priority queue."""
import heapq
import itertools

MODE_SHORTEST = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"

TRANSFER_PENALTY = {MODE_SHORTEST: 0, MODE_LEAST_TRANSFER: 10000, MODE_COMPREHENSIVE: 1500}


class PathfindingConfig:
    def __init__(self):
        self.mode = MODE_SHORTEST
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap based min priority queue."""

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

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        prefs = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        cost = {start: 0.0}
        dist = {start: 0}
        settled = set()
        pq = MinPQ()
        pq.push(0.0, start)
        while not pq.is_empty():
            c, st = pq.pop()
            if st in settled:
                continue
            settled.add(st)
            node, line, t = st
            if node not in self._best_state:
                self._best_state[node] = st
                self.dist_to[node] = dist[st]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    extra = penalty
                    if limit is not None:
                        nt = t + 1
                        if nt > limit:
                            continue
                w = e.weight * (0.9 if e.line in prefs else 1.0)
                ns = (e.dest, e.line, nt)
                if ns in settled:
                    continue
                nc = c + w + extra
                if nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    dist[ns] = dist[st] + e.weight
                    self._parent[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        nodes = [st[0]]
        edges = []
        while st in self._parent:
            st, e = self._parent[st]
            nodes.append(st[0])
            edges.append(e)
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
