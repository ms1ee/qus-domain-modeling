"""Dijkstra shortest path with a heap-based priority queue."""
import heapq
import itertools


class MinPQ:
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


TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1500}


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._parent = {}  # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        pref = set(cfg.preferred_lines)
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
            if node not in self._best_state:
                self._best_state[node] = st
                self.dist_to[node] = real[st]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    if limit is not None and t + 1 > limit:
                        continue
                    nt = t + 1 if limit is not None else 0
                    extra = penalty
                w = e.weight * (0.9 if e.line in pref else 1.0)
                ns = (e.dest, e.line, nt)
                nc = c + w + extra
                if ns not in cost or nc < cost[ns] - 1e-12:
                    cost[ns] = nc
                    real[ns] = real[st] + e.weight
                    self._parent[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while self._parent[st] is not None:
            prev, e = self._parent[st]
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
