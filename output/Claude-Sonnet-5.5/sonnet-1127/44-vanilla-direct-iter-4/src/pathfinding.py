"""Dijkstra-based path finding with several query modes."""
import heapq
import itertools

INF = float("inf")
TRANSFER_PENALTY = 1000  # metres-equivalent per transfer in comprehensive mode
PREFERENCE_FACTOR = 0.9


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

    def push(self, key, item):
        heapq.heappush(self._h, (key, next(self._c), item))

    def pop(self):
        key, _, item = heapq.heappop(self._h)
        return key, item

    def is_empty(self):
        return not self._h

    def __len__(self):
        return len(self._h)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {v: INF for v in graph.nodes()}
        self.dist_to[source] = 0
        self._best = {}   # node -> state
        self._info = {}   # state -> (dist, transfers, prev_state, edge)
        self._run()

    def _key(self, dist, transfers, score):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, dist)
        if mode == "comprehensive":
            return (score, dist)
        return (dist,)

    def _run(self):
        cfg = self.config
        maxt = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None)
        self._info[start] = (0, 0, None, None)
        pq = MinPQ()
        pq.push(self._key(0, 0, 0), (start, 0, 0, 0))
        done = set()
        while not pq.is_empty():
            _, (state, dist, tr, score) = pq.pop()
            if state in done:
                continue
            done.add(state)
            v, line = state
            if v not in self._best:
                self._best[v] = state
                self.dist_to[v] = dist
            for e in self.graph.neighbors(v):
                w = e.other(v)
                ntr = tr
                if line is not None and e.line != line:
                    ntr += 1
                if maxt is not None and ntr > maxt:
                    continue
                nstate = (w, e.line)
                if nstate in done:
                    continue
                nd = dist + e.weight
                factor = PREFERENCE_FACTOR if e.line in pref else 1.0
                nscore = score + e.weight * factor + (ntr - tr) * TRANSFER_PENALTY
                key = self._key(nd, ntr, nscore)
                old = self._info.get(nstate)
                if old is not None and old[4] <= key:
                    continue
                self._info[nstate] = (nd, ntr, state, e, key)
                pq.push(key, (nstate, nd, ntr, nscore))

    def has_path_to(self, target):
        return target in self._best

    def _states(self, target):
        st = self._best.get(target)
        out = []
        while st is not None:
            out.append(st)
            st = self._info[st][2]
        out.reverse()
        return out

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        states = self._states(target)
        nodes = [s[0] for s in states]
        edges = [self._info[s][3] for s in states[1:]]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
