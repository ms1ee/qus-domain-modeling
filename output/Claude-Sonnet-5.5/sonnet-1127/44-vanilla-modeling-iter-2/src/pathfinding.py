"""MinPQ and Dijkstra-based ShortestPath."""
import heapq
import itertools

MODE_SHORTEST = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"

TRANSFER_PENALTY = {MODE_SHORTEST: 0.0, MODE_LEAST_TRANSFER: 1e7, MODE_COMPREHENSIVE: 2000.0}


class PathfindingConfig:
    def __init__(self, mode=MODE_SHORTEST, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._info = {}  # state -> (cost, dist, transfers)
        self._prev = {}  # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0.0)
        limit = cfg.max_transfers
        start = (self.source, None, 0)
        self._info[start] = (0.0, 0, 0)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        best_cost = {}
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, _ = state
            _, dist, tr = self._info[state]
            if node not in best_cost or cost < best_cost[node]:
                best_cost[node] = cost
                self._best_state[node] = state
                self.dist_to[node] = dist
            for e in self.graph.neighbors(node):
                ntr = tr + (1 if line is not None and e.line != line else 0)
                if limit is not None and ntr > limit:
                    continue
                w = e.distance * (0.8 if e.line in cfg.preferred_lines else 1.0)
                ncost = cost + w + (penalty if ntr > tr else 0.0)
                nstate = (e.dest, e.line, ntr if limit is not None else 0)
                if nstate in done:
                    continue
                old = self._info.get(nstate)
                if old is None or ncost < old[0]:
                    self._info[nstate] = (ncost, dist + e.distance, ntr)
                    self._prev[nstate] = (state, e)
                    pq.push(ncost, nstate)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._prev:
            state, e = self._prev[state]
            edges.append(e)
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
