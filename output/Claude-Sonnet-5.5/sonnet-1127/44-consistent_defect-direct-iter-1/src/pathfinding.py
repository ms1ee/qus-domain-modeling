"""Dijkstra shortest path with transfer awareness."""
from min_pq import MinPQ

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
        self._node_state = {}
        self._parent = {}
        self._run()

    def _penalty(self):
        m = self.config.mode
        if m == "least_transfer":
            return 1e7
        if m == "comprehensive":
            return 1500.0
        return 0.0

    def _run(self):
        cfg = self.config
        limit = cfg.max_transfers
        pen = self._penalty()
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        best = {start: 0.0}
        real = {start: 0}
        self._parent[start] = (None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done or cost > best.get(st, float("inf")):
                continue
            done.add(st)
            node, line, tr = st
            if node not in self._node_state:
                self._node_state[node] = st
                self.dist_to[node] = real[st]
            for e in self.graph.neighbors(node):
                is_tr = line is not None and e.line != line
                ntr = tr + (1 if is_tr else 0)
                if limit is not None and ntr > limit:
                    continue
                c = cost + e.weight * (0.9 if e.line in pref else 1.0) + (pen if is_tr else 0.0)
                ns = (e.dest, e.line, ntr if limit is not None else 0)
                if c < best.get(ns, float("inf")):
                    best[ns] = c
                    real[ns] = real[st] + e.distance
                    self._parent[ns] = (st, e)
                    pq.push(c, ns)

    def has_path_to(self, target):
        return target in self._node_state

    def path_with_edges(self, target):
        st = self._node_state.get(target)
        if st is None:
            return [], []
        nodes, edges = [], []
        while st is not None:
            nodes.append(st[0])
            p, e = self._parent[st]
            if e is not None:
                edges.append(e)
            st = p
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
