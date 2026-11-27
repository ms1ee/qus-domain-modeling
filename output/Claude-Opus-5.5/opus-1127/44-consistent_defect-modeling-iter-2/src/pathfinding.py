"""Dijkstra-based path finding with transfer awareness."""

import heapq
import itertools

TRANSFER_PENALTY_METERS = 3000      # composite score penalty per transfer
PREFERRED_LINE_FACTOR = 0.7         # weight multiplier for preferred lines

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode or "shortest_distance"
        self.max_transfers = max_transfers
        if isinstance(preferred_lines, str):
            preferred_lines = [p.strip() for p in preferred_lines.split(",") if p.strip()]
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, key, item):
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def pop(self):
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)

    @property
    def size(self):
        return len(self._heap)


class _DistDict(dict):
    """dict returning infinity for unreachable stations."""

    def __missing__(self, key):
        return float("inf")


class ShortestPath:
    """Single-source path computation over a :class:`models.Graph`.

    The search runs over states (station, line of arrival[, transfers]) so
    transfers can be counted and limited correctly.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        if self.config.mode not in MODES:
            raise ValueError(f"Unknown mode: {self.config.mode}")
        self.dist_to = _DistDict()
        self.transfers_to = {}
        self._best_state = {}
        self._parent = {}
        self._run()

    def _key(self, weighted, transfers, actual):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, weighted, actual)
        if mode == "comprehensive":
            return (weighted + transfers * TRANSFER_PENALTY_METERS, transfers, actual)
        return (weighted, transfers, actual)

    def _run(self):
        cfg = self.config
        track = cfg.max_transfers is not None
        preferred = set(cfg.preferred_lines)
        start = (self.source, None, 0 if track else None)
        info = {start: (0, 0.0, 0)}  # state -> (actual, weighted, transfers)
        best_key = {start: self._key(0.0, 0, 0)}
        self._parent[start] = (None, None)
        pq = MinPQ()
        pq.push(best_key[start], start)
        settled = set()
        while not pq.is_empty():
            key, state = pq.pop()
            if state in settled or key != best_key.get(state):
                continue
            settled.add(state)
            node, line, _ = state
            actual, weighted, transfers = info[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = actual
                self.transfers_to[node] = transfers
            for e in self.graph.adj(node):
                nt = transfers + (1 if line is not None and e.line != line else 0)
                if track and nt > cfg.max_transfers:
                    continue
                factor = PREFERRED_LINE_FACTOR if (preferred and e.line in preferred) else 1.0
                nw = weighted + e.weight * factor
                na = actual + e.weight
                nstate = (e.dest, e.line, nt if track else None)
                if nstate in settled:
                    continue
                nkey = self._key(nw, nt, na)
                if nstate not in best_key or nkey < best_key[nstate]:
                    best_key[nstate] = nkey
                    info[nstate] = (na, nw, nt)
                    self._parent[nstate] = (state, e)
                    pq.push(nkey, nstate)

    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to[target]

    def path_with_edges(self, target):
        """Return (station numbers from source to target, edges used)."""
        if target not in self._best_state:
            return [], []
        nodes, edges = [], []
        state = self._best_state[target]
        while state is not None:
            nodes.append(state[0])
            prev, edge = self._parent[state]
            if edge is not None:
                edges.append(edge)
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
