"""Dijkstra-based path finding with transfer awareness.

The search runs over states ``(station, current line, transfers)`` so that
transfers at multi-line interchange stations are counted correctly and
transfer limits / line preferences can be honoured.
"""

from models import MinPQ

INF = float("inf")

MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance cost (meters) of one transfer in comprehensive mode
# (about 5 minutes of walking/waiting ~ 3.3 km of riding at 1.5 min/km).
TRANSFER_PENALTY_METERS = 3000
# Weight multiplier applied to edges on preferred lines.
PREFERENCE_FACTOR = 0.7


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None,
                 preferred_lines=None, transfer_penalty=TRANSFER_PENALTY_METERS,
                 preference_factor=PREFERENCE_FACTOR):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def validate(self):
        if self.mode not in MODES:
            raise ValueError("Unknown mode '%s', expected one of %s" % (self.mode, ", ".join(MODES)))
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if self.preferred_lines is None:
            self.preferred_lines = []


class ShortestPath:
    """Single-source optimal paths from ``source`` (a station number)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self._preferred = set(self.config.preferred_lines or [])
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._info = {}      # state -> (cost, distance, transfers, adjusted)
        self._parent = {}    # state -> (prev_state, edge)
        self._best = {}      # station -> best state
        self._run()

    # ------------------------------------------------------------------
    def _factor(self, line):
        if self._preferred and line in self._preferred:
            return self.config.preference_factor
        return 1.0

    def _cost(self, adjusted, transfers, distance):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, adjusted, distance)
        if mode == "comprehensive":
            return (adjusted + transfers * self.config.transfer_penalty, transfers, distance)
        return (adjusted, transfers, distance)

    def _run(self):
        max_t = self.config.max_transfers
        pq = MinPQ()
        start = (self.source, None, 0)
        start_cost = self._cost(0, 0, 0)
        self._info[start] = (start_cost, 0, 0, 0)
        pq.insert(start_cost, start)
        done = set()
        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in done:
                continue
            info = self._info[state]
            if cost > info[0]:
                continue
            done.add(state)
            v, line, _ = state
            _, d, t, a = info
            for e in self.graph.graph.get(v, []):
                nt = t + (1 if line is not None and e.line != line else 0)
                if max_t is not None and nt > max_t:
                    continue
                nd = d + e.weight
                na = a + e.weight * self._factor(e.line)
                ncost = self._cost(na, nt, nd)
                ns = (e.dest, e.line, nt if max_t is not None else 0)
                if ns in done:
                    continue
                old = self._info.get(ns)
                if old is None or ncost < old[0]:
                    self._info[ns] = (ncost, nd, nt, na)
                    self._parent[ns] = (state, e)
                    pq.insert(ncost, ns)

        for state, info in self._info.items():
            v = state[0]
            cur = self._best.get(v)
            if cur is None or info[0] < self._info[cur][0]:
                self._best[v] = state
        for v, state in self._best.items():
            self.dist_to[v] = self._info[state][1]

    # ------------------------------------------------------------------
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
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best:
            return -1
        return self._info[self._best[target]][2]

    def get_transfer_stations(self, target):
        _, edges = self.path_with_edges(target)
        result = []
        for prev, nxt in zip(edges, edges[1:]):
            if prev.line != nxt.line:
                result.append(prev.dest)
        return result

    def get_lines(self, target):
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
