"""MinPQ and Dijkstra-based ShortestPath."""
import heapq
import itertools


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


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


TRANSFER_PENALTY = {
    "shortest_distance": 0.001,   # only tie-breaker
    "least_transfer": 10_000_000.0,
    "comprehensive": 1500.0,      # meters-equivalent per transfer
}


class ShortestPath:
    """Dijkstra from a source station number; state = (station, line, transfers)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._parent = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0.001)
        use_pref = cfg.mode != "shortest_distance" and cfg.preferred_lines
        limit = cfg.max_transfers
        start = (self.source, None, 0)
        cost = {start: 0.0}
        real = {start: 0}
        self._parent[start] = None
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, t = st
            if node not in self.dist_to:
                self.dist_to[node] = real[st]
                self._best_state[node] = st
            for e in self.graph.neighbors(node):
                change = 1 if (line is not None and e.line != line) else 0
                nt_real = t + change
                if limit is not None and nt_real > limit:
                    continue
                nt = nt_real if limit is not None else 0
                w = e.weight
                if use_pref and e.line in cfg.preferred_lines:
                    w *= 0.9
                nst = (e.dest, e.line, nt)
                nc = c + w + change * penalty
                if nst not in cost or nc < cost[nst]:
                    cost[nst] = nc
                    real[nst] = real[st] + e.weight
                    self._parent[nst] = (st, e)
                    pq.push(nc, nst)

    def has_path_to(self, target):
        return target in self.dist_to

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        nodes, edges = [], []
        while st is not None:
            nodes.append(st[0])
            p = self._parent[st]
            if p is None:
                break
            edges.append(p[1])
            st = p[0]
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        n = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                n += 1
        return n
