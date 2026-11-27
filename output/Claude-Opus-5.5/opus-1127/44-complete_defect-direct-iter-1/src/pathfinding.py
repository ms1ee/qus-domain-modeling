"""
Dijkstra-based path computation with transfer awareness.

The search runs over states (station, current line[, transfers]) so that
transfers at multi-line interchange stations are counted correctly, which
enables the ``least_transfer``/``comprehensive`` modes, the maximum transfer
limit and line preferences. With the default configuration the result is
the plain shortest-distance path.
"""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in meters equivalent) applied per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Edges on preferred lines are weighted by this factor during the search.
PREFERRED_LINE_FACTOR = 0.7

INF = float("inf")


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None,
                 preferred_lines=None, transfer_penalty=TRANSFER_PENALTY_METERS):
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise TypeError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty = transfer_penalty


class ShortestPath:
    """Single-source Dijkstra over the subway graph.

    Attributes:
        dist_to: station number -> travelled distance (meters) of the chosen
                 path; ``inf`` for unreachable stations.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._info = {}    # state -> (key, eff, dist, transfers, parent_state, edge)
        self._final = {}   # station -> best settled state
        self._preferred = {p.strip().lower() for p in self.config.preferred_lines
                           if p and p.strip()}
        self._run()

    # ------------------------------------------------------------------
    def _key(self, eff, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, eff)
        if mode == "comprehensive":
            return (eff + transfers * self.config.transfer_penalty, transfers)
        return (eff, transfers)

    def _edge_cost(self, edge):
        if self._preferred and str(edge.line).strip().lower() in self._preferred:
            return edge.weight * PREFERRED_LINE_FACTOR
        return edge.weight

    def _run(self):
        cfg = self.config
        track_t = cfg.max_transfers is not None
        start = (self.source, None, 0 if track_t else None)
        key0 = self._key(0, 0)
        self._info[start] = (key0, 0, 0, 0, None, None)
        pq = MinPQ()
        pq.insert(key0, start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled:
                continue
            rec = self._info[state]
            if key != rec[0]:
                continue
            settled.add(state)
            v, line, _ = state
            if v not in self._final:
                self._final[v] = state
                self.dist_to[v] = rec[2]

            for e in self.graph.adj(v):
                transfers = rec[3] + (1 if (line is not None and e.line != line) else 0)
                if track_t and transfers > cfg.max_transfers:
                    continue
                ns = (e.dest, e.line, transfers if track_t else None)
                if ns in settled:
                    continue
                eff = rec[1] + self._edge_cost(e)
                nk = self._key(eff, transfers)
                old = self._info.get(ns)
                if old is None or nk < old[0]:
                    self._info[ns] = (nk, eff, rec[2] + e.weight, transfers, state, e)
                    pq.insert(nk, ns)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._final

    def path_with_edges(self, target):
        """Return (stations, edges) from source to target; ([], []) if unreachable."""
        if target not in self._final:
            return [], []
        edges = []
        state = self._final[target]
        while True:
            rec = self._info[state]
            if rec[4] is None:
                break
            edges.append(rec[5])
            state = rec[4]
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the path to target (0 if unreachable)."""
        if target not in self._final:
            return 0
        return self._info[self._final[target]][3]
