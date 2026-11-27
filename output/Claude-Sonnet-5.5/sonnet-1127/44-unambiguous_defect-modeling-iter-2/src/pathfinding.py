"""Dijkstra shortest path with transfer-aware states."""
from models import MinPQ

SHORTEST_DISTANCE = "shortest_distance"
LEAST_TRANSFER = "least_transfer"
COMPREHENSIVE = "comprehensive"
MODES = (SHORTEST_DISTANCE, LEAST_TRANSFER, COMPREHENSIVE)

TRANSFER_PENALTY = {SHORTEST_DISTANCE: 0, LEAST_TRANSFER: 100000, COMPREHENSIVE: 1500}


class PathfindingConfig:
    def __init__(self, mode=SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
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
        self._info = {}   # state -> (real_dist, transfers, parent_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        start = (self.source, None)
        cost = {start: 0.0}
        self._info[start] = (0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, last = st
            if node not in self._best:
                self._best[node] = st
            real, tr, _, _ = self._info[st]
            for e in self.graph.edges_from(node):
                t = tr
                extra = 0
                if last is not None and e.line != last:
                    t += 1
                    extra = penalty
                if cfg.max_transfers is not None and t > cfg.max_transfers:
                    continue
                w = e.weight
                if e.line in cfg.preferred_lines:
                    w *= 0.9
                nc = c + w + extra
                ns = (e.dest, e.line)
                if ns in done:
                    continue
                if nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    self._info[ns] = (real + e.weight, t, st, e)
                    pq.push(nc, ns)
        for n, st in self._best.items():
            self.dist_to[n] = self._info[st][0]

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            raise ValueError("No path to target")
        nodes, edges = [], []
        st = self._best[target]
        while st is not None:
            _, _, parent, e = self._info[st]
            nodes.append(st[0])
            if e is not None:
                edges.append(e)
            st = parent
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
