"""Dijkstra-based path computation with transfer-aware modes."""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class MinPQ:
    """Heap-based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)

    def size(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=5000, preference_factor=0.8):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', must be one of {VALID_MODES}")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty = transfer_penalty      # meters-equivalent per transfer
        self.preference_factor = preference_factor


class ShortestPath:
    """Dijkstra's algorithm over (station, current line) states."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {v: float("inf") for v in graph.vertices()}
        self.dist_to[source] = 0
        self._best_state = {}
        self._edge_to = {}
        self._real = {}
        self._transfers = {}
        self._run()

    def _cost(self, wdist, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, wdist)
        if mode == "comprehensive":
            return (wdist + transfers * self.config.transfer_penalty, transfers)
        return (wdist, transfers)

    def _run(self):
        cfg = self.config
        preferred = set(cfg.preferred_lines)
        start = (self.source, None)
        best = {start: self._cost(0, 0)}
        wdist = {start: 0}
        self._real[start] = 0
        self._transfers[start] = 0
        self._edge_to[start] = None
        pq = MinPQ()
        pq.push(best[start], start)
        done = set()
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done or cost != best.get(state):
                continue
            done.add(state)
            v, line = state
            for e in self.graph.adj(v):
                t = self._transfers[state] + (1 if line is not None and e.line != line else 0)
                if cfg.max_transfers is not None and t > cfg.max_transfers:
                    continue
                w = e.weight
                if preferred and e.line not in preferred:
                    w = e.weight / cfg.preference_factor if cfg.preference_factor > 0 else e.weight
                nwd = wdist[state] + w
                nstate = (e.dest, e.line)
                ncost = self._cost(nwd, t)
                if nstate not in best or ncost < best[nstate]:
                    best[nstate] = ncost
                    wdist[nstate] = nwd
                    self._real[nstate] = self._real[state] + e.weight
                    self._transfers[nstate] = t
                    self._edge_to[nstate] = (state, e)
                    pq.push(ncost, nstate)

        for state, cost in best.items():
            v = state[0]
            cur = self._best_state.get(v)
            if cur is None or cost < best[cur]:
                self._best_state[v] = state
        self._best_state[self.source] = start
        for v, state in self._best_state.items():
            self.dist_to[v] = self._real[state]

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while self._edge_to.get(state) is not None:
            prev, e = self._edge_to[state]
            edges.append(e)
            state = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best_state:
            return 0
        return self._transfers[self._best_state[target]]
