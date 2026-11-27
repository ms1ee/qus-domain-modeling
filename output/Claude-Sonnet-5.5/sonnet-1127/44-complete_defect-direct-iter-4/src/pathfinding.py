"""Dijkstra shortest path with priority queue, transfer limits and line preference."""
import heapq
import itertools


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        p, _, item = heapq.heappop(self._heap)
        return p, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}   # node -> state key
        self._info = {}   # state -> (cost, dist, prev_state, edge)
        self._run()

    def _transfer_penalty(self):
        mode = self.config.mode
        if mode == "least_transfer":
            return 10_000_000.0
        if mode == "comprehensive":
            return 1000.0
        return 0.001

    def _run(self):
        limit = self.config.max_transfers
        pref = set(self.config.preferred_lines or [])
        pen = self._transfer_penalty()
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
            node, last, t = st
            if node not in self._best:
                self._best[node] = st
                self.dist_to[node] = self._info[st][1]
            dist = self._info[st][1]
            for e in self.graph.neighbors(node):
                nt = t
                c = e.weight * (0.9 if e.line in pref else 1.0)
                if last is not None and e.line != last:
                    nt += 1
                    c += pen
                if limit is not None and nt > limit:
                    continue
                ns = (e.other(node), e.line, nt if limit is not None else 0)
                if ns in done:
                    continue
                ncost = cost + c
                old = self._info.get(ns)
                if old is None or ncost < old[0]:
                    self._info[ns] = (ncost, dist + e.weight, st, e)
                    pq.push(ncost, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        nodes, edges = [], []
        st = self._best[target]
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
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
