"""MinPQ and Dijkstra-based ShortestPath with transfer-aware modes."""
import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1500}


class MinPQ:
    """Binary-heap priority queue."""

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


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}   # node -> state
        self._prev = {}   # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        track = penalty > 0 or limit is not None
        pref = set(cfg.preferred_lines)
        start = (self.source, None, 0)
        cost = {start: 0.0}
        real = {start: 0}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, t = state
            if node not in self._best:
                self._best[node] = state
                self.dist_to[node] = real[state]
            for e in self.graph.neighbors(node):
                nt = t
                if track and line is not None and e.line != line:
                    nt = t + 1
                    if limit is not None and nt > limit:
                        continue
                w = e.distance * (0.9 if e.line in pref else 1.0)
                if track and line is not None and e.line != line:
                    w += penalty
                nline = e.line if track else None
                ns = (e.dest, nline, nt)
                nc = c + w
                if ns not in done and nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    real[ns] = real[state] + e.distance
                    self._prev[ns] = (state, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        state = self._best[target]
        edges = []
        nodes = [state[0]]
        while state in self._prev:
            state, e = self._prev[state]
            edges.append(e)
            nodes.append(state[0])
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
