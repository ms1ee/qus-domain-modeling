"""Dijkstra shortest path over (station, line) states."""
from models import MinPQ

TRANSFER_PENALTY = 1000
LEAST_TRANSFER_WEIGHT = 1000000
PREFERRED_FACTOR = 0.9


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
        self._cost = {}      # state -> cost
        self._real = {}      # state -> (distance, transfers)
        self._prev = {}      # state -> (prev_state, edge)
        self._best = {}      # node -> state
        self._run()

    def _edge_cost(self, edge, transfer):
        c = self.config
        d = edge.distance
        if edge.line in c.preferred_lines:
            d = d * PREFERRED_FACTOR
        if c.mode == "least_transfer":
            return d + (LEAST_TRANSFER_WEIGHT if transfer else 0)
        if c.mode == "comprehensive":
            return d + (TRANSFER_PENALTY if transfer else 0)
        return d

    def _run(self):
        start = (self.source, None)
        self._cost[start] = 0
        self._real[start] = (0, 0)
        pq = MinPQ()
        pq.push(0, start)
        done = set()
        mt = self.config.max_transfers
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line = st
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = self._real[st][0]
            dist, tr = self._real[st]
            for e in self.graph.neighbors(node):
                transfer = line is not None and e.line != line
                ntr = tr + (1 if transfer else 0)
                if mt is not None and ntr > mt:
                    continue
                ns = (e.dest, e.line)
                nc = cost + self._edge_cost(e, transfer)
                if ns not in done and nc < self._cost.get(ns, float("inf")):
                    self._cost[ns] = nc
                    self._real[ns] = (dist + e.distance, ntr)
                    self._prev[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        st = self._best.get(target)
        if st is None:
            return [], []
        edges = []
        while st in self._prev:
            st, e = self._prev[st]
            edges.append(e)
        edges.reverse()
        return [self.source] + [e.dest for e in edges], edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        st = self._best.get(target)
        return self._real[st][1] if st else 0
