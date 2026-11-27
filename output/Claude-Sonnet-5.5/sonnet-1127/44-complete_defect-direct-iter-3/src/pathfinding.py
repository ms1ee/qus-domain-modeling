"""Dijkstra shortest path with a heap-based priority queue."""
import heapq
import itertools

TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 1000000, "comprehensive": 1500}
PREFERRED_FACTOR = 0.9


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap min priority queue."""

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
        self._paths = {}
        self._transfers = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        maxt = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        # state: (node, line, transfers); transfers only distinguishes when limited
        start = (self.source, None, 0)
        parent = {start: (None, None)}
        real = {start: 0}
        best = {start[:2] if maxt is None else start: 0.0}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            key = st[:2] if maxt is None else st
            if key in done:
                continue
            done.add(key)
            node = st[0]
            if node not in self.dist_to:
                edges = []
                s = st
                while parent[s][0] is not None:
                    ps, e = parent[s]
                    edges.append(e)
                    s = ps
                edges.reverse()
                self.dist_to[node] = real[st]
                self._paths[node] = edges
                self._transfers[node] = st[2]
            for e in self.graph.neighbors(node):
                t = st[2]
                if st[1] is not None and e.line != st[1]:
                    t += 1
                if maxt is not None and t > maxt:
                    continue
                w = e.weight * (PREFERRED_FACTOR if e.line in pref else 1.0)
                if t > st[2]:
                    w += penalty
                ns = (e.dest, e.line, t)
                nkey = ns[:2] if maxt is None else ns
                if nkey in done:
                    continue
                nc = cost + w
                if nc < best.get(nkey, float("inf")):
                    best[nkey] = nc
                    parent[ns] = (st, e)
                    real[ns] = real[st] + e.weight
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self.dist_to

    def path_with_edges(self, target):
        if target not in self.dist_to:
            return [], []
        edges = list(self._paths[target])
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._paths:
            return 0
        edges = self._paths[target]
        return sum(1 for i in range(1, len(edges)) if edges[i].line != edges[i - 1].line)
