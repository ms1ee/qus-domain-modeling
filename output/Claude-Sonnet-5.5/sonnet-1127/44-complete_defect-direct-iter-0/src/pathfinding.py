"""Dijkstra shortest path with a heap based priority queue."""
import heapq
import itertools


class MinPQ:
    """Minimum priority queue backed by a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    MODES = ("shortest_distance", "least_transfer", "comprehensive")

    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class ShortestPath:
    """Single-source shortest paths; state is (station, line, transfers)."""

    TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 1000000, "comprehensive": 1500}

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._prev = {}      # state -> (prev_state, edge)
        self._info = {}      # state -> (actual distance, transfers)
        self._run()

    def _run(self):
        cfg = self.config
        limited = cfg.max_transfers is not None
        penalty = self.TRANSFER_PENALTY.get(cfg.mode, 0)
        preferred = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        cost = {start: 0.0}
        self._info[start] = (0, 0)
        self._prev[start] = None
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, _ = state
            actual, trans = self._info[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = actual
            for e in self.graph.neighbors(node):
                nt = trans
                if line is not None and e.line != line:
                    nt += 1
                if limited and nt > cfg.max_transfers:
                    continue
                w = float(e.distance)
                if e.line in preferred:
                    w *= 0.9
                if nt > trans:
                    w += penalty
                key = (e.dest, e.line, nt if limited else 0)
                nc = c + w
                if nc < cost.get(key, float("inf")):
                    cost[key] = nc
                    self._info[key] = (actual + e.distance, nt)
                    self._prev[key] = (state, e)
                    pq.push(nc, key)

    def has_path_to(self, target):
        return target in self.dist_to

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes, edges = [], []
        while state is not None:
            nodes.append(state[0])
            p = self._prev[state]
            if p is None:
                break
            edges.append(p[1])
            state = p[0]
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        if target not in self._best_state:
            return 0
        return self._info[self._best_state[target]][1]
