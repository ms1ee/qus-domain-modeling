"""Dijkstra based path finding."""
import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 10 ** 7, "comprehensive": 1000}


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Heap based min priority queue."""

    def __init__(self):
        self.heap = []
        self._c = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._c), item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self.edge_to = {}
        self._node_state = {}
        self._prev = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        track = cfg.max_transfers is not None
        start = (self.source, None, 0)
        best = {start: 0.0}
        dist = {start: 0}
        self._prev[start] = (None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, t = st
            if node not in self._node_state:
                self._node_state[node] = st
                self.dist_to[node] = dist[st]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    nt = t + 1
                    extra = penalty
                if track and nt > cfg.max_transfers:
                    continue
                w = e.weight
                if cfg.preferred_lines and e.line in cfg.preferred_lines:
                    w = w * 0.8
                ns = (e.dest, e.line, nt if track else 0)
                nc = cost + w + extra
                if ns not in done and nc < best.get(ns, float("inf")):
                    best[ns] = nc
                    dist[ns] = dist[st] + e.weight
                    self._prev[ns] = (st, e)
                    pq.push(nc, ns)
        for n, st in self._node_state.items():
            if self._prev[st][1] is not None:
                self.edge_to[n] = self._prev[st][1]

    def has_path_to(self, target):
        return target in self._node_state

    def path_with_edges(self, target):
        if target not in self._node_state:
            return [], []
        st = self._node_state[target]
        edges = []
        while True:
            prev, e = self._prev[st]
            if prev is None:
                break
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
