"""Dijkstra shortest path with transfer awareness."""
from models import MinPQ

TRANSFER_PENALTY = {"shortest_distance": 0, "comprehensive": 3000, "least_transfer": 1000000}


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
        self._best = {}   # node -> state key
        self._info = {}   # key -> (cost, dist, transfers, prev_key, edge)
        self._run()

    def _run(self):
        cfg = self.config
        pen = TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        best_cost = {start: 0.0}
        self._info[start] = (0.0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, key = pq.pop()
            if key in done:
                continue
            done.add(key)
            node, line, _ = key
            _, d, t, _, _ = self._info[key]
            if node not in self._best:
                self._best[node] = key
                self.dist_to[node] = d
            for e in self.graph.edges_from(node):
                nt = t + (1 if line is not None and e.line != line else 0)
                if limit is not None and nt > limit:
                    continue
                w = e.weight
                if pref and e.line in pref:
                    w = w * 0.9
                ncost = cost + w + (pen if nt > t else 0)
                nkey = (e.dest, e.line, nt if limit is not None else 0)
                if ncost < best_cost.get(nkey, float("inf")):
                    best_cost[nkey] = ncost
                    self._info[nkey] = (ncost, d + e.distance, nt, key, e)
                    pq.push(ncost, nkey)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        key = self._best.get(target)
        if key is None:
            return [], []
        nodes, edges = [], []
        while key is not None:
            _, _, _, prev, e = self._info[key]
            nodes.append(key[0])
            if e is not None:
                edges.append(e)
            key = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        key = self._best.get(target)
        if key is None:
            return 0
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
