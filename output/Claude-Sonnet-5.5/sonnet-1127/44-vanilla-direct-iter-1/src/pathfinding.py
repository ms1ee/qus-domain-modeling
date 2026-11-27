"""Dijkstra shortest path with transfer awareness."""
from models import MinPQ

MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = 3000  # meters-equivalent per transfer (comprehensive)
PREFERRED_FACTOR = 0.9


class PathfindingConfig:
    def __init__(self):
        self.mode = "shortest_distance"
        self.max_transfers = None
        self.preferred_lines = []


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._transfers = {}
        self._best_state = {}
        self._info = {}  # state -> (cost, dist, transfers, parent, edge)
        self._run()

    def _step_cost(self, edge, transferred):
        mode = self.config.mode
        d = edge.distance
        if edge.line in self.config.preferred_lines:
            d_eff = d * PREFERRED_FACTOR
        else:
            d_eff = d
        t = 1 if transferred else 0
        if mode == "least_transfer":
            return t * 1e9 + d_eff
        if mode == "comprehensive":
            return d_eff + t * TRANSFER_PENALTY
        return d_eff

    def _run(self):
        maxt = self.config.max_transfers
        bounded = maxt is not None

        def key(node, line, t):
            return (node, line, t) if bounded else (node, line)

        start = (self.source, None, 0) if bounded else (self.source, None)
        self._info[start] = (0.0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, st = pq.pop()
            if st in done:
                continue
            done.add(st)
            _, dist, t, _, _ = self._info[st]
            node, line = st[0], st[1]
            for e in self.graph.adj(node):
                transferred = line is not None and e.line != line
                nt = t + (1 if transferred else 0)
                if bounded and nt > maxt:
                    continue
                nst = key(e.dest, e.line, nt)
                if nst in done:
                    continue
                ncost = cost + self._step_cost(e, transferred)
                old = self._info.get(nst)
                if old is None or ncost < old[0]:
                    self._info[nst] = (ncost, dist + e.distance, nt, st, e)
                    pq.push(ncost, nst)
        for st, (cost, dist, t, _, _) in self._info.items():
            node = st[0]
            cur = self._best_state.get(node)
            if cur is None or cost < self._info[cur][0]:
                self._best_state[node] = st
        for node, st in self._best_state.items():
            self.dist_to[node] = self._info[st][1]
            self._transfers[node] = self._info[st][2]

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        st = self._best_state.get(target)
        if st is None:
            return [], []
        nodes, edges = [], []
        while st is not None:
            _, _, _, parent, e = self._info[st]
            nodes.append(st[0])
            if e is not None:
                edges.append(e)
            st = parent
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        return self._transfers.get(target, 0)
