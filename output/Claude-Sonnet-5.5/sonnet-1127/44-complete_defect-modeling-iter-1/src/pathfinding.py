"""Dijkstra shortest path with a heap based priority queue."""
import heapq
import itertools


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    def __init__(self):
        self.heap = []
        self._c = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._c), item))

    def pop(self):
        p, _, item = heapq.heappop(self.heap)
        return p, item

    def is_empty(self):
        return not self.heap


TRANSFER_PENALTY = {"shortest_distance": 0, "least_transfer": 100000, "comprehensive": 1000}


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}
        self._info = {}  # state -> (cost, dist, prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        pen = TRANSFER_PENALTY.get(cfg.mode, 0)
        maxt = cfg.max_transfers
        pref = set(cfg.preferred_lines or [])
        start = (self.source, None, 0)
        self._info[start] = (0.0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, t = st
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = self._info[st][1]
            dist = self._info[st][1]
            for e in self.graph.neighbors(node):
                nt = t
                extra = 0
                if line is not None and e.line != line:
                    nt = t + 1
                    extra = pen
                if maxt is not None and nt > maxt:
                    continue
                w = e.weight * (0.9 if e.line in pref else 1.0)
                ns = (e.dest, e.line, nt if maxt is not None else 0)
                nc = cost + w + extra
                if ns in done:
                    continue
                if ns not in self._info or nc < self._info[ns][0]:
                    self._info[ns] = (nc, dist + e.weight, st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        st = self._best[target]
        nodes, edges = [], []
        while st is not None:
            _, _, prev, e = self._info[st]
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
