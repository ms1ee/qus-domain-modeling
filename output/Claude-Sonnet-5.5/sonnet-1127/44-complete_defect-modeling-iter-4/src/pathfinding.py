"""MinPQ and Dijkstra-based ShortestPath."""
import heapq
import itertools


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class MinPQ:
    """Binary-heap based min priority queue."""

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


TRANSFER_PENALTY = {"shortest_distance": 0.0, "least_transfer": 1e7, "comprehensive": 1500.0}
PREFERRED_FACTOR = 0.9


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best = {}      # node -> state
        self._info = {}      # state -> (cost, dist, prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        penalty = TRANSFER_PENALTY.get(cfg.mode, 0.0)
        limit = cfg.max_transfers
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
                if line is not None and e.line != line:
                    nt += 1
                if limit is not None and nt > limit:
                    continue
                if limit is None:
                    nt_key = 0
                    if penalty == 0.0:
                        nt_key = 0
                else:
                    nt_key = nt
                w = e.weight * (PREFERRED_FACTOR if e.line in pref else 1.0)
                c = cost + w + (penalty if nt != t else 0.0)
                nst = (e.dest, e.line, nt_key)
                if nst in done:
                    continue
                old = self._info.get(nst)
                if old is None or c < old[0]:
                    self._info[nst] = (c, dist + e.distance, st, e)
                    pq.push(c, nst)

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

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
