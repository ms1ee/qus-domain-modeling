"""MinPQ and ShortestPath (Dijkstra over (station, line) states)."""
import heapq
import itertools

MODE_SHORTEST = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"

TRANSFER_PENALTY = {
    MODE_SHORTEST: 0,
    MODE_LEAST_TRANSFER: 1000000,
    MODE_COMPREHENSIVE: 1500,
}


class PathfindingConfig:
    def __init__(self):
        self.mode = MODE_SHORTEST
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Heap based min priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self._heap)
        return p, item

    def is_empty(self):
        return not self._heap


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._prev = {}   # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        track = cfg.max_transfers is not None
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
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = real[state]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    extra = penalty
                    if track:
                        nt = t + 1
                        if nt > cfg.max_transfers:
                            continue
                w = e.weight
                if e.line in cfg.preferred_lines:
                    w *= 0.9
                ns = (e.dest, e.line, nt if track else 0)
                nc = c + w + extra
                if ns not in done and nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    real[ns] = real[state] + e.distance
                    self._prev[ns] = (state, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._prev:
            state, e = self._prev[state]
            edges.append(e)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
