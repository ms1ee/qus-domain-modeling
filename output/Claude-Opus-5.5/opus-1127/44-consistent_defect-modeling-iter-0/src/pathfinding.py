"""
Dijkstra-based shortest path computation over a subway Graph.

The search runs over (station, arriving line) states so transfers can be
counted and limited correctly at multi-line interchange stations.
"""

try:
    from models import MinPQ
except ImportError:  # pragma: no cover
    from .models import MinPQ

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Penalty (meters equivalent) per transfer in comprehensive mode:
# 5 minutes per transfer ~ 3.33 km at 1.5 minutes per km.
TRANSFER_PENALTY = 3333
# Weight factor applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.7


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode is None:
            mode = MODE_SHORTEST_DISTANCE
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [p.strip() for p in preferred_lines.split(",") if p.strip()]
        self.preferred_lines = list(preferred_lines)


class ShortestPath:
    """Dijkstra single-source shortest path using a heap priority queue."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices}
        self.dist_to[source] = 0
        self._key = {}        # state -> cost key
        self._dist = {}       # state -> real distance
        self._transfers = {}  # state -> transfers
        self._prev = {}       # state -> (prev_state, edge)
        self._best = {}       # vertex -> best state
        self._run()

    # ---- internals -------------------------------------------------
    def _make_key(self, wdist, transfers):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, wdist)
        if mode == MODE_COMPREHENSIVE:
            return (wdist + transfers * TRANSFER_PENALTY, transfers)
        return (wdist, transfers)

    def _edge_weight(self, edge):
        w = edge.weight
        if self.config.preferred_lines and edge.line in self.config.preferred_lines:
            return w * PREFERRED_LINE_FACTOR
        return w

    def _run(self):
        start = (self.source, None)
        wdist = {start: 0}
        self._key[start] = self._make_key(0, 0)
        self._dist[start] = 0
        self._transfers[start] = 0
        self._prev[start] = None
        pq = MinPQ()
        pq.insert(self._key[start], start)
        done = set()
        max_t = self.config.max_transfers
        while not pq.is_empty():
            key, state = pq.del_min()
            if state in done or key != self._key.get(state):
                continue
            done.add(state)
            v, line = state
            t = self._transfers[state]
            for e in self.graph.edges_from(v):
                if e.line is None or line is None:
                    new_line = e.line if e.line is not None else line
                    new_t = t
                else:
                    new_line = e.line
                    new_t = t + (1 if e.line != line else 0)
                if max_t is not None and new_t > max_t:
                    continue
                nstate = (e.dest, new_line)
                if nstate in done:
                    continue
                nw = wdist[state] + self._edge_weight(e)
                nkey = self._make_key(nw, new_t)
                old = self._key.get(nstate)
                if old is None or nkey < old:
                    self._key[nstate] = nkey
                    wdist[nstate] = nw
                    self._dist[nstate] = self._dist[state] + e.weight
                    self._transfers[nstate] = new_t
                    self._prev[nstate] = (state, e)
                    pq.insert(nkey, nstate)
        for state, key in self._key.items():
            v = state[0]
            cur = self._best.get(v)
            if cur is None or key < self._key[cur]:
                self._best[v] = state
        self._best[self.source] = start
        for v, state in self._best.items():
            self.dist_to[v] = self._dist[state]

    # ---- public API ------------------------------------------------
    def has_path_to(self, target):
        return target in self._best

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target."""
        if target not in self._best:
            return [], []
        edges = []
        state = self._best[target]
        while self._prev.get(state) is not None:
            prev_state, e = self._prev[state]
            edges.append(e)
            state = prev_state
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the path to target (-1 if unreachable)."""
        if target not in self._best:
            return -1
        return self._transfers[self._best[target]]
