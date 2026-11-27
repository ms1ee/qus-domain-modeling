"""
Dijkstra-based path finding on the subway graph.

The search runs over *states* ``(station, current line[, transfers])`` so
that line changes at interchange stations are detected and counted
correctly. Three modes are supported:

* ``shortest_distance`` - minimise total distance (ties: fewer transfers)
* ``least_transfer``    - minimise number of transfers (ties: distance)
* ``comprehensive``     - minimise distance + transfer penalty

Optional settings: maximum number of transfers, preferred lines (edges on
preferred lines are weighted lower).
"""

from models import MinPQ

MODES = ("shortest_distance", "least_transfer", "comprehensive")
# Equivalent distance cost of one transfer in comprehensive mode (meters).
TRANSFER_PENALTY_METERS = 3000
# Weight multiplier applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.7


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=TRANSFER_PENALTY_METERS):
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines)
        self.transfer_penalty = transfer_penalty

    def validate(self):
        if self.mode not in MODES:
            raise ValueError(f"Unknown mode '{self.mode}', expected one of {', '.join(MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int) \
                    or self.max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")


class ShortestPath:
    """Compute optimal paths from a source station using Dijkstra's algorithm.

    Attributes:
        dist_to: dict station number -> actual travel distance (meters) of the
                 optimal path found under the configured mode.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.dist_to = {}
        self._transfers = {}
        self._best_state = {}
        self._edge_to = {}
        self._run()

    # ------------------------------------------------------------------
    def _cost(self, eff, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, eff)
        if mode == "comprehensive":
            penalty = getattr(self.config, "transfer_penalty", TRANSFER_PENALTY_METERS) or 0
            return (eff + transfers * penalty, transfers)
        return (eff, transfers)

    def _run(self):
        max_t = self.config.max_transfers
        preferred = set(getattr(self.config, "preferred_lines", None) or [])
        start = (self.source, None, 0 if max_t is not None else None)
        # state -> (actual distance, transfers, effective weight)
        info = {start: (0, 0, 0)}
        best_cost = {start: self._cost(0, 0)}
        self._edge_to = {start: None}
        done = set()
        pq = MinPQ()
        counter = 0
        pq.insert((best_cost[start], counter, start))

        while not pq.is_empty():
            cost, _, state = pq.del_min()
            if state in done or cost != best_cost.get(state):
                continue
            done.add(state)
            v, line, _tk = state
            dist, trans, eff = info[state]

            # Record best state per station (first settled = best cost).
            if v not in self._best_state:
                self._best_state[v] = state
                self.dist_to[v] = dist
                self._transfers[v] = trans

            for e in self.graph.adj(v):
                new_trans = trans + (1 if line is not None and e.line != line else 0)
                if max_t is not None and new_trans > max_t:
                    continue
                w = e.weight
                if preferred and e.line in preferred:
                    w = w * PREFERRED_LINE_FACTOR
                new_eff = eff + w
                ns = (e.dest, e.line, new_trans if max_t is not None else None)
                if ns in done:
                    continue
                nc = self._cost(new_eff, new_trans)
                if ns not in best_cost or nc < best_cost[ns]:
                    best_cost[ns] = nc
                    info[ns] = (dist + e.distance, new_trans, new_eff)
                    self._edge_to[ns] = (state, e)
                    counter += 1
                    pq.insert((nc, counter, ns))

        if self.source not in self.dist_to:
            self.dist_to[self.source] = 0
            self._transfers[self.source] = 0
            self._best_state[self.source] = start

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        if not self.has_path_to(target):
            raise ValueError(f"No path to station {target}")
        return self.dist_to[target]

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) if the target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        edges = []
        state = self._best_state[target]
        while True:
            entry = self._edge_to.get(state)
            if entry is None:
                break
            prev, e = entry
            edges.append(e)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if not self.has_path_to(target):
            raise ValueError(f"No path to station {target}")
        return self._transfers[target]

    def transfer_points(self, target):
        """Return list of (station number, from_line, to_line) along the path."""
        _, edges = self.path_with_edges(target)
        result = []
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                result.append((cur.source, prev.line, cur.line))
        return result

    def lines_on_path(self, target):
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
