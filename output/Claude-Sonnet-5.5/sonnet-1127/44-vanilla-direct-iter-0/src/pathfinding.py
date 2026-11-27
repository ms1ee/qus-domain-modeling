"""Dijkstra shortest path with a heap based priority queue."""
import heapq
import itertools

TRANSFER_PENALTY = 1000.0
PREFERENCE_FACTOR = 0.8


class MinPQ:
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
        self._transfers = {}
        self._final = {}
        self._parent = {}
        self._run()

    def _cost(self, eff, dist, tr):
        mode = self.config.mode
        if mode == "least_transfer":
            return (tr, dist)
        if mode == "comprehensive":
            return (eff + tr * TRANSFER_PENALTY,)
        return (dist,)

    def _run(self):
        cfg = self.config
        limit = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        best = {start: self._cost(0, 0, 0)}
        self._parent[start] = (None, None)
        pq = MinPQ()
        pq.push(best[start], (start, 0.0, 0))
        done = set()
        while not pq.is_empty():
            cost, (state, eff, dist) = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, tr = state
            if node not in self._final:
                self._final[node] = state
                self.dist_to[node] = dist
                self._transfers[node] = tr
            for e in self.graph.neighbors(node):
                ntr = tr + (1 if line is not None and e.line != line else 0)
                if limit is not None and ntr > limit:
                    continue
                w = e.weight * (PREFERENCE_FACTOR if e.line in pref else 1.0)
                neff = eff + w
                ndist = dist + e.weight
                if limit is not None:
                    ns = (e.dest, e.line, ntr)
                else:
                    ns = (e.dest, e.line, 0)
                    ntr_key = ntr
                c = self._cost(neff, ndist, ntr)
                if ns in done:
                    continue
                if ns not in best or c < best[ns]:
                    best[ns] = c
                    self._parent[ns] = (state, e)
                    pq.push(c, (ns, neff, ndist))
        # with no transfer limit, state transfers are not tracked in key;
        # recompute transfers along reconstructed paths
        self._recompute = limit is None

    def has_path_to(self, target):
        return target in self._final

    def path_with_edges(self, target):
        if target not in self._final:
            return [], []
        state = self._final[target]
        edges = []
        while state is not None:
            parent, e = self._parent[state]
            if e is not None:
                edges.append(e)
            state = parent
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
