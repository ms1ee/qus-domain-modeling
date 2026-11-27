"""MinPQ, PathfindingConfig and ShortestPath (Dijkstra)."""
import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = 3000


class MinPQ:
    """Heap based min priority queue."""

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

    def __len__(self):
        return len(self.heap)


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}
        self._rec = {}
        self._run()

    def _edge_cost(self, edge, transfer):
        mode = self.config.mode
        d = edge.distance
        pref = edge.line in self.config.preferred_lines
        if mode == "least_transfer":
            return (1000000 if transfer else 0) + d * (0.95 if pref else 1)
        if mode == "comprehensive":
            return (TRANSFER_PENALTY if transfer else 0) + d * (0.9 if pref else 1)
        return d

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0)
        self._rec[start] = (0, 0, 0, None, None)  # cost, dist, transfers, prev, edge
        pq = MinPQ()
        pq.push(0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, _ = st
            _, dist, tr, _, _ = self._rec[st]
            for e in self.graph.neighbors(node):
                transfer = line is not None and e.line != line
                ntr = tr + (1 if transfer else 0)
                if limit is not None and ntr > limit:
                    continue
                nst = (e.dest, e.line, ntr if limit is not None else 0)
                ncost = cost + self._edge_cost(e, transfer)
                old = self._rec.get(nst)
                if old is None or ncost < old[0]:
                    self._rec[nst] = (ncost, dist + e.distance, ntr, st, e)
                    pq.push(ncost, nst)
        for st, rec in self._rec.items():
            n = st[0]
            if n not in self._best or rec[0] < self._rec[self._best[n]][0]:
                self._best[n] = st
        self.dist_to = {n: self._rec[s][1] for n, s in self._best.items()}

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        st = self._best[target]
        nodes, edges = [], []
        while st is not None:
            rec = self._rec[st]
            nodes.append(st[0])
            if rec[4] is not None:
                edges.append(rec[4])
            st = rec[3]
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
