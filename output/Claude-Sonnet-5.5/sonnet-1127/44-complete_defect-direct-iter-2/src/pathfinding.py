"""Dijkstra shortest path with a heap-based priority queue."""
import heapq

TRANSFER_PENALTY = 1000000   # least_transfer mode
COMPREHENSIVE_PENALTY = 1500  # meters-equivalent per transfer


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    def __init__(self):
        self._h = []
        self._c = 0

    def push(self, key, item):
        self._c += 1
        heapq.heappush(self._h, (key, self._c, item))

    def pop(self):
        k, _, item = heapq.heappop(self._h)
        return k, item

    def __len__(self):
        return len(self._h)


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._parent = {}   # state -> (prev_state, edge)
        self._run()

    def _run(self):
        cfg = self.config
        limit = cfg.max_transfers
        track = limit is not None
        if cfg.mode == "least_transfer":
            pen = TRANSFER_PENALTY
        elif cfg.mode == "comprehensive":
            pen = COMPREHENSIVE_PENALTY
        else:
            pen = 0
        pref = set(cfg.preferred_lines) if cfg.mode == "comprehensive" else set()
        start = (self.source, None, 0)
        cost = {start: 0.0}
        real = {start: 0}
        self._parent[start] = None
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        best_cost = {}
        while len(pq):
            c, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            node, line, tr = st
            if node not in best_cost:
                best_cost[node] = c
                self._best_state[node] = st
                self.dist_to[node] = real[st]
            for e in self.graph.adj(node):
                ntr = tr
                add = e.weight
                if line is not None and e.line != line:
                    ntr += 1
                    add += pen
                    if track and ntr > limit:
                        continue
                if e.line in pref:
                    add = add * 0.9
                key_tr = ntr if (track or pen) else 0
                ns = (e.dest, e.line, key_tr if track else (ntr if pen else 0))
                nc = c + add
                if ns not in cost or nc < cost[ns] - 1e-9:
                    cost[ns] = nc
                    real[ns] = real[st] + e.weight
                    self._parent[ns] = (st, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self.dist_to

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        st = self._best_state[target]
        edges = []
        while self._parent[st] is not None:
            prev, e = self._parent[st]
            edges.append(e)
            st = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        n = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                n += 1
        return n
