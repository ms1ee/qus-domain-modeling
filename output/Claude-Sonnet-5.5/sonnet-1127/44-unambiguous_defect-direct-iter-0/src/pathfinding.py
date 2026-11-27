"""Dijkstra-based path finding with transfer awareness."""
import heapq
import itertools


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap based minimum priority queue."""

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
    TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1500}

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}      # station -> state key
        self._label = {}     # state key -> (dist, transfers, prev key, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = self.TRANSFER_PENALTY.get(cfg.mode, 0)
        limit = cfg.max_transfers
        prefs = set(cfg.preferred_lines or [])
        use_pref = cfg.mode != "shortest_distance" or False
        start = (self.source, None, 0)
        self._label[start] = (0, 0, None, None)
        cost_of = {start: 0}
        pq = MinPQ()
        pq.push(0, start)
        done = set()
        while not pq.is_empty():
            cost, key = pq.pop()
            if key in done:
                continue
            done.add(key)
            st, line, _t = key
            dist, trans, _, _ = self._label[key]
            if st not in self._best:
                self._best[st] = key
                self.dist_to[st] = dist
            for e in self.graph.neighbors(st):
                nt = trans + (1 if line is not None and e.line != line else 0)
                if limit is not None and nt > limit:
                    continue
                nkey = (e.dest, e.line, nt if limit is not None else 0)
                if nkey in done:
                    continue
                w = e.weight
                if use_pref and prefs and e.line in prefs:
                    w = w * 0.9
                ncost = cost + w + (penalty if nt > trans else 0)
                if ncost < cost_of.get(nkey, float("inf")):
                    cost_of[nkey] = ncost
                    self._label[nkey] = (dist + e.weight, nt, key, e)
                    pq.push(ncost, nkey)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        key = self._best[target]
        nodes, edges = [], []
        while key is not None:
            _, _, prev, e = self._label[key]
            nodes.append(key[0])
            if e is not None:
                edges.append(e)
            key = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for i in range(1, len(edges)) if edges[i].line != edges[i - 1].line)
