"""
Path calculation using Dijkstra's algorithm with a heap priority queue.

The search is performed over states (station, current line[, transfers]),
which allows correct handling of transfer stations, transfer counting,
maximum transfer limits and line preferences.
"""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    """Configuration for path queries.

    mode: 'shortest_distance' | 'least_transfer' | 'comprehensive'
    max_transfers: maximum allowed number of transfers (None = unlimited)
    preferred_lines: list of preferred line names
    transfer_penalty: equivalent distance (meters) of one transfer, used in
        comprehensive mode (models transfer walking time/distance)
    preference_factor: weight multiplier applied to edges on preferred lines
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=3000, preference_factor=0.8):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', must be one of {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor


class ShortestPath:
    """Dijkstra shortest path from a source station number."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}        # station number -> actual distance (meters)
        self.edge_to = {}        # station number -> last Edge on best path
        self._best_state = {}    # station number -> best state
        self._parent = {}        # state -> (prev_state, edge)
        self._info = {}          # state -> (weighted_dist, actual_dist, transfers)
        self._run()

    # ------------------------------------------------------------------
    def _cost(self, wdist, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, wdist)
        if mode == "comprehensive":
            return (wdist + self.config.transfer_penalty * transfers, transfers)
        return (wdist, transfers)

    def _run(self):
        cfg = self.config
        track_transfers = cfg.max_transfers is not None
        preferred = set(cfg.preferred_lines)

        start = (self.source, None, 0 if track_transfers else None)
        self._info[start] = (0, 0, 0)
        best_cost = {start: self._cost(0, 0)}
        pq = MinPQ()
        pq.push(best_cost[start], start)
        settled = set()

        while not pq.is_empty():
            cost, state = pq.pop()
            if state in settled or best_cost.get(state) != cost:
                continue
            settled.add(state)
            station, line, _ = state
            wdist, adist, transfers = self._info[state]
            if station not in self._best_state:
                self._best_state[station] = state
                self.dist_to[station] = adist
                parent = self._parent.get(state)
                if parent is not None:
                    self.edge_to[station] = parent[1]

            for edge in self.graph.adj(station):
                new_transfers = transfers
                if line is not None and edge.line is not None and edge.line != line:
                    new_transfers += 1
                if track_transfers and new_transfers > cfg.max_transfers:
                    continue
                factor = cfg.preference_factor if (preferred and edge.line in preferred) else 1
                nw = wdist + edge.weight * factor
                na = adist + edge.weight
                new_line = edge.line if edge.line is not None else line
                nstate = (edge.dest, new_line, new_transfers if track_transfers else None)
                if nstate in settled:
                    continue
                ncost = self._cost(nw, new_transfers)
                if nstate not in best_cost or ncost < best_cost[nstate]:
                    best_cost[nstate] = ncost
                    self._info[nstate] = (nw, na, new_transfers)
                    self._parent[nstate] = (state, edge)
                    pq.push(ncost, nstate)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return (list of station numbers from source to target, list of Edge).

        Returns ([], []) if target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
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
        """Number of transfers on the best path to target (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        return self._info[self._best_state[target]][2]
