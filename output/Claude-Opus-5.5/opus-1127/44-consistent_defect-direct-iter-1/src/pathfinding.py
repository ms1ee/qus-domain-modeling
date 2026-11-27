"""Dijkstra-based path computation over the subway graph."""

import heapq
import itertools

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty (meters) for one transfer in comprehensive mode.
TRANSFER_PENALTY = 3000
# Weight multiplier applied to edges on non-preferred lines when preferences exist.
NON_PREFERRED_FACTOR = 1.3


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode: %r" % (mode,))
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Dijkstra shortest paths from a single source station number.

    The search runs over states (station, current line, [transfers]) so that
    transfers at interchange stations are tracked correctly.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._transfers = {source: 0}
        self._best_state = {}
        self._parent = {}
        self._run()

    def _edge_weight(self, edge):
        w = edge.weight
        prefs = self.config.preferred_lines
        if prefs and edge.line not in prefs:
            w = w * NON_PREFERRED_FACTOR
        return w

    def _cost(self, adj_dist, transfers):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, adj_dist)
        if mode == MODE_COMPREHENSIVE:
            return (adj_dist + transfers * TRANSFER_PENALTY, transfers)
        return (adj_dist, transfers)

    def _run(self):
        max_tr = self.config.max_transfers
        limited = max_tr is not None
        start = (self.source, None, 0)
        info = {start: (0, 0, 0)}  # state -> (adjusted dist, actual dist, transfers)
        visited = set()
        pq = MinPQ()
        pq.insert(self._cost(0, 0), start)
        while not pq.is_empty():
            _, state = pq.del_min()
            if state in visited:
                continue
            visited.add(state)
            node, line, _ = state
            adj, actual, tr = info[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = actual
                self._transfers[node] = tr
            for e in self.graph.out_edges(node):
                ntr = tr + (1 if (line is not None and e.line != line) else 0)
                if limited and ntr > max_tr:
                    continue
                nstate = (e.dest, e.line, ntr if limited else 0)
                if nstate in visited:
                    continue
                nadj = adj + self._edge_weight(e)
                nact = actual + e.weight
                ncost = self._cost(nadj, ntr)
                old = info.get(nstate)
                if old is None or ncost < self._cost(old[0], old[2]):
                    info[nstate] = (nadj, nact, ntr)
                    self._parent[nstate] = (state, e)
                    pq.insert(ncost, nstate)

    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target."""
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._parent:
            prev, e = self._parent[state]
            edges.append(e)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best_state:
            return 0
        return self._transfers.get(target, 0)
