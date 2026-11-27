"""Dijkstra shortest path with priority queue."""
import heapq
import itertools

TRANSFER_PENALTY = 1000  # meters-equivalent used in comprehensive mode
PREFERENCE_FACTOR = 0.9


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

    def __len__(self):
        return len(self._h)

    def is_empty(self):
        return not self._h


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
        self._best = {}   # node -> state
        self._info = {}   # state -> (prev_state, edge, dist, transfers)
        self._run()

    def _edge_cost(self, edge, transferred):
        c = float(edge.distance)
        if edge.line in self.config.preferred_lines:
            c *= PREFERENCE_FACTOR
        if transferred:
            mode = self.config.mode
            if mode == "least_transfer":
                c += 1e7
            elif mode == "comprehensive":
                c += TRANSFER_PENALTY
        return c

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0)
        self._info[start] = (None, None, 0, 0)
        costs = {start: 0.0}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, _ = st
            _, _, dist, tr = self._info[st]
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = dist
            for e in self.graph.neighbors(node):
                transferred = line is not None and e.line != line
                ntr = tr + (1 if transferred else 0)
                if limit is not None and ntr > limit:
                    continue
                ns = (e.dest, e.line, ntr if limit is not None else 0)
                if ns in done:
                    continue
                nc = cost + self._edge_cost(e, transferred)
                if nc < costs.get(ns, float("inf")):
                    costs[ns] = nc
                    self._info[ns] = (st, e, dist + e.distance, ntr)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        nodes, edges = [], []
        st = self._best[target]
        while st is not None:
            prev, e, _, _ = self._info[st]
            nodes.append(st[0])
            if e is not None:
                edges.append(e)
            st = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for i in range(1, len(edges)) if edges[i].line != edges[i - 1].line)
