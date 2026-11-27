"""Dijkstra shortest path with MinPQ, transfer-aware."""
import heapq
import itertools

TRANSFER_PENALTY = 1000.0      # meters-equivalent per transfer (comprehensive)
LEAST_TRANSFER_WEIGHT = 1e7
PREFERRED_FACTOR = 0.9


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self.edge_to = {}
        self._best_state = {}
        self._run()

    def _step_cost(self, edge, transferred):
        cfg = self.config
        d = float(edge.distance)
        if edge.line in cfg.preferred_lines:
            d *= PREFERRED_FACTOR
        if cfg.mode == "least_transfer":
            return d + (LEAST_TRANSFER_WEIGHT if transferred else 0.0)
        if cfg.mode == "comprehensive":
            return d + (TRANSFER_PENALTY if transferred else 0.0)
        return d

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0)
        cost = {start: 0.0}
        dist = {start: 0}
        prev = {start: (None, None)}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, t = st
            for e in self.graph.neighbors(node):
                transferred = line is not None and e.line != line
                nt = t + (1 if transferred else 0)
                if limit is not None and nt > limit:
                    continue
                ns = (e.dest, e.line, nt if limit is not None else 0)
                if ns in done:
                    continue
                nc = c + self._step_cost(e, transferred)
                if nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    dist[ns] = dist[st] + e.distance
                    prev[ns] = (st, e)
                    pq.push(nc, ns)
        best = {}
        for st, c in cost.items():
            n = st[0]
            if n not in best or c < cost[best[n]]:
                best[n] = st
        self._prev = prev
        self._best_state = best
        for n, st in best.items():
            self.dist_to[n] = dist[st]

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        nodes, edges = [], []
        while st is not None:
            nodes.append(st[0])
            p, e = self._prev[st]
            if e is not None:
                edges.append(e)
            st = p
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
