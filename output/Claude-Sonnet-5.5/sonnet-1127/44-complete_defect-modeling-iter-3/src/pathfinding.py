"""Dijkstra shortest path with a heap-based priority queue."""
import heapq
import itertools

TRANSFER_PENALTY_LEAST = 1000000
TRANSFER_PENALTY_COMPREHENSIVE = 1000


class MinPQ:
    """Min priority queue on a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self._heap)
        return p, item

    @property
    def size(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class ShortestPath:
    """Single-source search; states are (station, line) to track transfers."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._labels = {}  # state -> (cost, dist, transfers, prev_state, edge)
        self._run()

    def _penalty(self):
        m = self.config.mode
        if m == "least_transfer":
            return TRANSFER_PENALTY_LEAST
        if m == "comprehensive":
            return TRANSFER_PENALTY_COMPREHENSIVE
        return 0

    def _preferred(self, line):
        for p in self.config.preferred_lines:
            if p and (p == line or p.casefold() in str(line).casefold()):
                return True
        return False

    def _edge_cost(self, edge):
        c = edge.weight
        if self.config.preferred_lines and self._preferred(edge.line):
            c *= 0.9
        return c

    def _run(self):
        start = (self.source, None)
        self._labels[start] = (0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(0, start)
        done = set()
        pen = self._penalty()
        maxt = self.config.max_transfers
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line = state
            _, dist, trans, _, _ = self._labels[state]
            for e in self.graph.neighbors(node):
                nt = trans
                add = self._edge_cost(e)
                if line is not None and e.line != line:
                    nt += 1
                    add += pen
                    if maxt is not None and nt > maxt:
                        continue
                ns = (e.dest, e.line)
                if ns in done:
                    continue
                nc = cost + add
                old = self._labels.get(ns)
                if old is None or nc < old[0]:
                    self._labels[ns] = (nc, dist + e.weight, nt, state, e)
                    pq.push(nc, ns)
        for state, lab in self._labels.items():
            n = state[0]
            b = self._best_state.get(n)
            if b is None or lab[0] < self._labels[b][0]:
                self._best_state[n] = state
        for n, st in self._best_state.items():
            self.dist_to[n] = self._labels[st][1]

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        st = self._best_state.get(target)
        if st is None:
            return [], []
        edges = []
        while st is not None:
            lab = self._labels[st]
            if lab[4] is not None:
                edges.append(lab[4])
            st = lab[3]
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
