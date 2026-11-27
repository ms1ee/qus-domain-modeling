"""Dijkstra shortest path with priority queue, transfer-aware."""
import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 5000, "comprehensive": 1500}


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Heap-based minimum priority queue."""

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
        self._prev = {}
        self._best_state = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        track = limit is not None
        start = (self.source, None, 0)
        cost = {start: 0.0}
        dist = {start: 0}
        best = {self.source: (0.0, start)}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, tr = st
            for e in self.graph.neighbors(node):
                ntr = tr
                extra = 0
                if line is not None and e.line != line:
                    ntr += 1
                    extra = penalty
                    if track and ntr > limit:
                        continue
                w = e.weight
                if e.line in self.config.preferred_lines:
                    w *= 0.9
                nst = (e.dest, e.line, ntr if track else 0)
                nc = c + w + extra
                if nc < cost.get(nst, float("inf")):
                    cost[nst] = nc
                    dist[nst] = dist[st] + e.weight
                    self._prev[nst] = (st, e)
                    pq.push(nc, nst)
                    if nc < best.get(e.dest, (float("inf"), None))[0]:
                        best[e.dest] = (nc, nst)
        for node, (c, st) in best.items():
            self._best_state[node] = st
            self.dist_to[node] = dist[st]

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while st in self._prev:
            st, e = self._prev[st]
            edges.append(e)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
