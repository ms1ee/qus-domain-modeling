"""Dijkstra based path finding with transfer awareness."""
from models import MinPQ

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._parent = {}   # state -> (prev_state, edge)
        self._run()

    def _penalty(self):
        mode = self.config.mode
        if mode == "least_transfer":
            return 10_000_000.0
        if mode == "comprehensive":
            return 1500.0
        return 0.0

    def _run(self):
        cfg = self.config
        penalty = self._penalty()
        limit = cfg.max_transfers
        prefs = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        best = {start: 0.0}
        real = {start: 0}
        self._parent[start] = None
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        node_cost = {}
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, tr = state
            if node not in node_cost or cost < node_cost[node]:
                node_cost[node] = cost
                self._best_state[node] = state
                self.dist_to[node] = real[state]
            for e in self.graph.neighbors(node):
                ntr = tr
                step = float(e.weight)
                if line is not None and e.line != line:
                    ntr = tr + 1
                    if limit is not None and ntr > limit:
                        continue
                    step += penalty
                if e.line in prefs:
                    step *= 0.9
                key_tr = ntr if limit is not None else 0
                ns = (e.dest, e.line, key_tr)
                nc = cost + step
                if nc < best.get(ns, float("inf")):
                    best[ns] = nc
                    real[ns] = real[state] + e.distance
                    self._parent[ns] = (state, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while self._parent[state] is not None:
            prev, e = self._parent[state]
            edges.append(e)
            state = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
