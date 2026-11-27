"""Priority queue and Dijkstra-based shortest path with transfer awareness."""
import heapq
import itertools

MODE_SHORTEST = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"

TRANSFER_PENALTY_COMPREHENSIVE = 1500  # meters-equivalent per transfer
TRANSFER_PENALTY_LEAST = 10_000_000


class MinPQ:
    """Heap-based minimum priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        heapq.heappush(self.heap, (key, next(self._counter), item))

    def del_min(self):
        key, _, item = heapq.heappop(self.heap)
        return key, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class PathfindingConfig:
    def __init__(self, mode=MODE_SHORTEST, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Dijkstra over (station, current line) states."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}
        self._parent = {}
        self._trans = {}
        self._run()

    def _penalty(self):
        if self.config.mode == MODE_LEAST_TRANSFER:
            return TRANSFER_PENALTY_LEAST
        if self.config.mode == MODE_COMPREHENSIVE:
            return TRANSFER_PENALTY_COMPREHENSIVE
        return 0

    def _run(self):
        cfg = self.config
        penalty = self._penalty()
        start = (self.source, None)
        cost = {start: 0.0}
        dist = {start: 0}
        trans = {start: 0}
        self._parent[start] = None
        done = set()
        pq = MinPQ()
        pq.insert(0.0, start)
        best_cost = {}
        while not pq.is_empty():
            c, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            node, line = state
            if node not in best_cost or c < best_cost[node]:
                best_cost[node] = c
                self._best[node] = state
                self.dist_to[node] = dist[state]
            for e in self.graph.neighbors(node):
                nt = trans[state] + (1 if line is not None and e.line != line else 0)
                if cfg.max_transfers is not None and nt > cfg.max_transfers:
                    continue
                step = float(e.distance)
                if e.line in cfg.preferred_lines:
                    step *= 0.95
                nc = c + step + (penalty if nt > trans[state] else 0)
                ns = (e.dest, e.line)
                if ns in done:
                    continue
                if ns not in cost or nc < cost[ns]:
                    cost[ns] = nc
                    dist[ns] = dist[state] + e.distance
                    trans[ns] = nt
                    self._parent[ns] = (state, e)
                    pq.insert(nc, ns)
        self._trans = trans

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        state = self._best[target]
        nodes = [state[0]]
        edges = []
        while self._parent[state] is not None:
            prev, e = self._parent[state]
            edges.append(e)
            nodes.append(prev[0])
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best:
            return 0
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
