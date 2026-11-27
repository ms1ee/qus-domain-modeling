"""Dijkstra-based path finding with several query modes.

Modes:
  * shortest_distance - minimise total distance
  * least_transfer    - minimise transfers, then distance
  * comprehensive     - minimise distance + transfers * TRANSFER_PENALTY
Optional constraints: maximum number of transfers and preferred lines.
"""

from models import MinPQ

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) of one transfer in comprehensive mode;
# models walking distance/time spent changing lines.
TRANSFER_PENALTY = 3000
# Cost multiplier applied to edges on non-preferred lines.
NON_PREFERRED_FACTOR = 1.3


class PathfindingConfig:
    """Configuration for a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None, transfer_penalty=TRANSFER_PENALTY,
                 non_preferred_factor=NON_PREFERRED_FACTOR):
        if mode not in MODES:
            raise ValueError("Unknown mode %r, expected one of %s" % (mode, ", ".join(MODES)))
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty = transfer_penalty
        self.non_preferred_factor = non_preferred_factor


def count_transfers(edges):
    """Number of line changes along a sequence of edges."""
    count = 0
    for prev, cur in zip(edges, edges[1:]):
        if prev.line != cur.line:
            count += 1
    return count


class ShortestPath:
    """Single-source path computation using Dijkstra with a MinPQ."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._edge_to = {}        # plain mode: node -> Edge
        self._final_state = {}    # state mode: node -> state
        self._prev = {}           # state mode: state -> (prev_state, Edge)
        cfg = self.config
        self._state_mode = not (cfg.mode == MODE_SHORTEST_DISTANCE
                                and cfg.max_transfers is None
                                and not cfg.preferred_lines)
        if self._state_mode:
            self._run_state_dijkstra()
        else:
            self._run_plain_dijkstra()

    # ------------------------------------------------------------------
    def _run_plain_dijkstra(self):
        dist = self.dist_to
        pq = MinPQ()
        pq.push(0, self.source)
        while not pq.is_empty():
            d, v = pq.pop()
            if d > dist.get(v, INF):
                continue
            for e in self.graph.adjacent(v):
                nd = d + e.weight
                if nd < dist.get(e.dest, INF):
                    dist[e.dest] = nd
                    self._edge_to[e.dest] = e
                    pq.push(nd, e.dest)

    def _edge_factor(self, line):
        prefs = self.config.preferred_lines
        if prefs and line not in prefs:
            return self.config.non_preferred_factor
        return 1.0

    def _cost(self, weighted, transfers):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, weighted)
        if mode == MODE_COMPREHENSIVE:
            return (weighted + transfers * self.config.transfer_penalty, transfers)
        return (weighted, transfers)

    def _run_state_dijkstra(self):
        cfg = self.config
        track = cfg.max_transfers is not None
        start = (self.source, None, 0) if track else (self.source, None)
        best = {start: self._cost(0, 0)}
        real_dist = {start: 0}
        weighted = {start: 0.0}
        transfers = {start: 0}
        self._prev[start] = (None, None)
        settled = set()
        pq = MinPQ()
        pq.push(best[start], start)
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in settled or cost != best.get(state):
                continue
            settled.add(state)
            v, line = state[0], state[1]
            d, w, tr = real_dist[state], weighted[state], transfers[state]
            if v not in self._final_state:
                self._final_state[v] = state
                self.dist_to[v] = d
            for e in self.graph.adjacent(v):
                ntr = tr + (1 if line is not None and e.line != line else 0)
                if track and ntr > cfg.max_transfers:
                    continue
                nw = w + e.weight * self._edge_factor(e.line)
                ncost = self._cost(nw, ntr)
                nstate = (e.dest, e.line, ntr) if track else (e.dest, e.line)
                if nstate in settled:
                    continue
                old = best.get(nstate)
                if old is None or ncost < old:
                    best[nstate] = ncost
                    real_dist[nstate] = d + e.weight
                    weighted[nstate] = nw
                    transfers[nstate] = ntr
                    self._prev[nstate] = (state, e)
                    pq.push(ncost, nstate)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return self.dist_to.get(target, INF) < INF

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (station numbers from source to target, edges travelled).

        Returns ([], []) when the target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        if target == self.source:
            return [self.source], []
        edges = []
        if self._state_mode:
            state = self._final_state[target]
            while True:
                prev_state, e = self._prev[state]
                if e is None:
                    break
                edges.append(e)
                state = prev_state
        else:
            v = target
            while v != self.source:
                e = self._edge_to[v]
                edges.append(e)
                v = e.source
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)
