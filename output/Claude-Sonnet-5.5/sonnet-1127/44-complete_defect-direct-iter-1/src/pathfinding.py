"""Dijkstra shortest path with priority queue."""
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


TRANSFER_PENALTY = {
    "shortest_distance": 0.0,
    "least_transfer": 10_000_000.0,
    "comprehensive": 1500.0,
}


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}
        self._info = {}
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0.0)
        limit = cfg.max_transfers
        prefs = set(cfg.preferred_lines or [])

        def key_of(node, line, tr):
            return (node, line, tr) if limit is not None else (node, line)

        start = key_of(self.source, None, 0)
        # info: key -> (cost, dist, transfers, prev_key, edge)
        info = {start: (0.0, 0, 0, None, None)}
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, key = pq.pop()
            if key in done:
                continue
            done.add(key)
            _, dist, tr, _, _ = info[key]
            node, line = key[0], key[1]
            for e in self.graph.neighbors(node):
                ntr = tr
                c = e.weight * (0.9 if e.line in prefs else 1.0)
                if line is not None and e.line != line:
                    ntr += 1
                    c += penalty
                if limit is not None and ntr > limit:
                    continue
                nkey = key_of(e.dest, e.line, ntr)
                ncost = cost + c
                if nkey not in info or ncost < info[nkey][0]:
                    info[nkey] = (ncost, dist + e.weight, ntr, key, e)
                    pq.push(ncost, nkey)
        self._info = info
        best = {}
        for key, val in info.items():
            n = key[0]
            if n not in best or val[0] < info[best[n]][0]:
                best[n] = key
        best[self.source] = start
        self._best = best
        self.dist_to = {n: info[k][1] for n, k in best.items()}

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        key = self._best[target]
        nodes = [target]
        edges = []
        while True:
            _, _, _, prev, edge = self._info[key]
            if prev is None:
                break
            edges.append(edge)
            nodes.append(prev[0])
            key = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
