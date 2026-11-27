"""Dijkstra shortest path with transfer awareness."""
from models import MinPQ

TRANSFER_PENALTY = 1500  # meters-equivalent penalty per transfer (comprehensive)
BIG = 10 ** 7


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
        self._best = {}    # node -> state
        self._info = {}    # state -> (cost, dist, transfers, prev_state, edge)
        self._run()

    def _step_cost(self, edge, transfer):
        mode = self.config.mode
        w = float(edge.weight)
        if edge.line in self.config.preferred_lines:
            w *= 0.9
        if mode == "least_transfer":
            return w / 1000.0 + (BIG if transfer else 0)
        if mode == "comprehensive":
            return w + (TRANSFER_PENALTY if transfer else 0)
        return w

    def _run(self):
        maxt = self.config.max_transfers
        start = (self.source, None)
        self._info[start] = (0.0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(0.0, start)
        done = set()
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line = state
            _, dist, tr, _, _ = self._info[state]
            if node not in self._best:
                self._best[node] = state
                self.dist_to[node] = dist
            for e in self.graph.edges_from(node):
                transfer = line is not None and e.line != line
                nt = tr + (1 if transfer else 0)
                if maxt is not None and nt > maxt:
                    continue
                ns = (e.dest, e.line)
                if ns in done:
                    continue
                nc = cost + self._step_cost(e, transfer)
                old = self._info.get(ns)
                if old is None or nc < old[0]:
                    self._info[ns] = (nc, dist + e.weight, nt, state, e)
                    pq.push(nc, ns)

    def has_path_to(self, target):
        return target in self._best

    def path_with_edges(self, target):
        if target not in self._best:
            return [], []
        state = self._best[target]
        nodes, edges = [], []
        while state is not None:
            nodes.append(state[0])
            _, _, _, prev, e = self._info[state]
            if e is not None:
                edges.append(e)
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best:
            return 0
        return self._info[self._best[target]][2]
