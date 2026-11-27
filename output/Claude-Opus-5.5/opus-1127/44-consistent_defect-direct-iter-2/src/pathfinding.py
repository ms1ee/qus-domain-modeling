"""Dijkstra-based shortest path computation with multiple query modes."""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY = 3000      # meters-equivalent cost of one transfer (comprehensive mode)
PREFERENCE_FACTOR = 0.8      # weight multiplier for preferred lines
INF = float("inf")


def _norm_line(name):
    return "".join(str(name).lower().split())


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode '%s'; expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Computes optimal paths from a source station using Dijkstra's algorithm.

    The search runs over states (station, current line[, transfers]) so that
    transfers at interchange stations are handled correctly.
    """

    def __init__(self, graph, source, config=None):
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._best_state = {}
        self._edge_to = {}
        self._info = {}
        self._pref = {_norm_line(l) for l in self.config.preferred_lines}
        self._run()

    def _key(self, adj, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, adj)
        if mode == "comprehensive":
            return (adj + transfers * TRANSFER_PENALTY, transfers)
        return (adj, transfers)

    def _run(self):
        track = self.config.max_transfers is not None
        maxt = self.config.max_transfers
        start = (self.source, None, 0) if track else (self.source, None)
        self._info[start] = (0.0, 0, 0)  # adjusted cost, real distance, transfers
        pq = MinPQ()
        pq.push(self._key(0.0, 0), start)
        best_key = {start: self._key(0.0, 0)}
        settled = set()
        while not pq.is_empty():
            key, state = pq.pop()
            if state in settled:
                continue
            settled.add(state)
            node, line = state[0], state[1]
            adj, real, t = self._info[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = real
            for e in self._graph.adjacent(node):
                nt = t + (1 if (line is not None and e.line != line) else 0)
                if track and nt > maxt:
                    continue
                w = e.weight
                if self._pref and _norm_line(e.line) in self._pref:
                    w = w * PREFERENCE_FACTOR
                nadj = adj + w
                nreal = real + e.weight
                ns = (e.dest, e.line, nt) if track else (e.dest, e.line)
                if ns in settled:
                    continue
                nkey = self._key(nadj, nt)
                if ns not in best_key or nkey < best_key[ns]:
                    best_key[ns] = nkey
                    self._info[ns] = (nadj, nreal, nt)
                    self._edge_to[ns] = (state, e)
                    pq.push(nkey, ns)

    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target."""
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._edge_to:
            prev, e = self._edge_to[state]
            edges.append(e)
            state = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
