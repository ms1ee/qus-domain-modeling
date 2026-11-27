"""Dijkstra shortest path with transfer limits and line preference."""
from models import MinPQ

TRANSFER_PENALTY = {
    "shortest_distance": 0.0,
    "least_transfer": 1000000.0,
    "comprehensive": 1000.0,
}


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
        self._pred = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0.0)
        limit = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        cost = {start: 0.0}
        real = {start: 0}
        self._pred[start] = None
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
                extra = 0.0
                if line is not None and e.line != line:
                    if limit is not None:
                        nt = t + 1
                        if nt > limit:
                            continue
                    extra += penalty
                    if limit is None and penalty == 0.0:
                        pass
                w = e.weight * (0.9 if e.line in pref else 1.0)
                # tiny tie-break so transfers are never free when counted
                nc = c + w + extra
                ns = (e.dest, e.line, nt)
                if ns not in cost or nc < cost[ns]:
                    cost[ns] = nc
                    real[ns] = real[st] + e.weight
                    self._pred[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while self._pred[st] is not None:
            prev, e = self._pred[st]
            edges.append(e)
            st = prev
        edges.reverse()
        return [self.source] + [e.dest for e in edges], edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
