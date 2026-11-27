"""Dijkstra shortest path with priority queue."""
import heapq
import itertools

from models import Edge, Graph  # noqa: F401

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1500}


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Heap based minimum priority queue."""

    def __init__(self):
        self._h = []
        self._c = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._h, (priority, next(self._c), item))

    def pop(self):
        p, _, item = heapq.heappop(self._h)
        return p, item

    def is_empty(self):
        return not self._h

    def __len__(self):
        return len(self._h)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}    # node -> state key
        self._info = {}    # state key -> (real dist, transfers, parent key, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        pref = set(cfg.preferred_lines or [])
        track_t = cfg.max_transfers is not None
        start = (self.source, None, 0)
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
            node, line, _ = st
            d, t, _, _ = self._info[st]
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = d
            for e in self.graph.neighbors(node):
                nt = t + (1 if line is not None and e.line != line else 0)
                if track_t and nt > cfg.max_transfers:
                    continue
                key = (e.dest, e.line, nt if track_t else 0)
                if key in done:
                    continue
                w = e.distance * (0.95 if e.line in pref else 1.0)
                nc = c + w + (penalty if nt > t else 0)
                if nc < cost.get(key, float("inf")):
                    cost[key] = nc
                    self._info[key] = (d + e.distance, nt, st, e)
                    pq.push(nc, key)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
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

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best:
            return 0
        return self._info[self._best[target]][1]
