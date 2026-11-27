"""Dijkstra-based path finding with priority queue."""
import heapq
import itertools

TRANSFER_PENALTY = 1500  # meters-equivalent per transfer (comprehensive)


class MinPQ:
    """Heap-based minimum priority queue."""

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
    """Single-source best path on state space (station, line, transfers)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}   # node -> state
        self._info = {}   # state -> (cost, dist, transfers, prev_state, edge)
        self._run()

    def _edge_cost(self, e, transfer):
        c = float(e.weight)
        if e.line in self.config.preferred_lines:
            c *= 0.9
        mode = self.config.mode
        if transfer:
            if mode == "least_transfer":
                c += 1e7
            elif mode == "comprehensive":
                c += TRANSFER_PENALTY
            else:
                c += 0.001
        return c

    def _run(self):
        mt = self.config.max_transfers
        start = (self.source, None, 0)
        self._info[start] = (0.0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, _ = st
            _, d, t, _, _ = self._info[st]
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = d
            for e in self.graph.neighbors(node):
                tr = line is not None and e.line != line
                nt = t + (1 if tr else 0)
                if mt is not None and nt > mt:
                    continue
                ns = (e.dest, e.line, nt if mt is not None else 0)
                if ns in done:
                    continue
                nc = cost + self._edge_cost(e, tr)
                old = self._info.get(ns)
                if old is None or nc < old[0]:
                    self._info[ns] = (nc, d + e.weight, nt, st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        st = self._best.get(target)
        if st is None:
            return [], []
        nodes, edges = [], []
        while st is not None:
            _, _, _, prev, e = self._info[st]
            nodes.append(st[0])
            if e is not None:
                edges.append(e)
            st = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
