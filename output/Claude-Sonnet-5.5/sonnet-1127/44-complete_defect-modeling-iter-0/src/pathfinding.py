"""MinPQ and Dijkstra-based ShortestPath."""
import heapq
import itertools


class MinPQ:
    """Binary-heap based min priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self.heap)
        return priority, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1500}
PREFERENCE_FACTOR = 0.9


class ShortestPath:
    """Dijkstra from source over (station, line, transfers) states."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._parent = {}
        self._run()

    def _run(self):
        cfg = self.config
        limit = cfg.max_transfers
        track = cfg.mode != "shortest_distance" or limit is not None
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0)
        preferred = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        cost = {start: 0.0}
        dist = {start: 0}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            c, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, t = state
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = dist[state]
            for e in self.graph.neighbors(node):
                changed = line is not None and e.line != line
                nt = t + (1 if changed else 0)
                if limit is not None and nt > limit:
                    continue
                step = e.distance * (PREFERENCE_FACTOR if e.line in preferred else 1)
                if changed:
                    step += penalty
                ns = (e.dest, e.line if track else None, nt if limit is not None else 0)
                nc = c + step
                if ns not in done and nc < cost.get(ns, float("inf")):
                    cost[ns] = nc
                    dist[ns] = dist[state] + e.distance
                    self._parent[ns] = (state, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._parent:
            state, e = self._parent[state]
            edges.append(e)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
