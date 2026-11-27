"""Dijkstra-based path finding with transfer awareness."""
import heapq
import itertools

SHORTEST = "shortest_distance"
LEAST_TRANSFER = "least_transfer"
COMPREHENSIVE = "comprehensive"

TRANSFER_PENALTY = 1500   # meters-equivalent per transfer (comprehensive mode)
PREFERENCE_FACTOR = 0.9   # cost factor on preferred lines
DEFAULT_TRANSFER_CAP = 15


class PathfindingConfig:
    def __init__(self, mode=SHORTEST, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary-heap based min priority queue."""

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
    """Dijkstra over states (station, last line, transfers)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._prev = {}
        self._run()

    def _edge_cost(self, edge, transferred):
        mode = self.config.mode
        d = float(edge.distance)
        if mode == COMPREHENSIVE and edge.line in self.config.preferred_lines:
            d *= PREFERENCE_FACTOR
        if mode == LEAST_TRANSFER:
            return d + (1e7 if transferred else 0)
        if mode == COMPREHENSIVE:
            return d + (TRANSFER_PENALTY if transferred else 0)
        return d

    def _run(self):
        cap = self.config.max_transfers
        if cap is None:
            cap = DEFAULT_TRANSFER_CAP
        start = (self.source, None, 0)
        costs = {start: 0.0}
        dists = {start: 0}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        self._best_state[self.source] = start
        self.dist_to[self.source] = 0
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, tr = st
            if node not in self._best_state:
                self._best_state[node] = st
                self.dist_to[node] = dists[st]
            for e in self.graph.neighbors(node):
                transferred = line is not None and e.line != line
                ntr = tr + (1 if transferred else 0)
                if ntr > cap:
                    continue
                ns = (e.dest, e.line, ntr)
                if ns in done:
                    continue
                if self.config.mode == SHORTEST:
                    nc = c + e.distance + (0.001 if transferred else 0)
                else:
                    nc = c + self._edge_cost(e, transferred)
                if nc < costs.get(ns, float("inf")):
                    costs[ns] = nc
                    dists[ns] = dists[st] + e.distance
                    self._prev[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        st = self._best_state.get(target)
        if st is None:
            return [], []
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
        st = self._best_state.get(target)
        return st[2] if st else 0
