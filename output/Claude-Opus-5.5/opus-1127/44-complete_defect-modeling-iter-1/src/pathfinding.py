"""
Shortest path computation (Dijkstra with a binary-heap priority queue).

The search runs over states ``(station, current line, transfers)`` so that
transfers at multi-line interchange stations are handled correctly and so
that maximum-transfer limits, line preferences and different query modes
can be supported.  Complexity is O((V+E) log V) in the state space.
"""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Cost in meters assigned to one transfer in "comprehensive" mode.
TRANSFER_PENALTY_METERS = 3000
# Effective weight multiplier for preferred lines in "comprehensive" mode.
PREFERRED_LINE_DISCOUNT = 0.8


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        if isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Dijkstra single-source shortest paths from ``source`` (station number)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self.edge_to = {}
        self._labels = {}
        self._parent = {}
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------ cost
    def _cost(self, label):
        dist, transfers, nonpref, eff = label
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, dist, nonpref)
        if mode == "comprehensive":
            return (eff + transfers * TRANSFER_PENALTY_METERS, transfers, dist)
        return (dist, transfers, nonpref)

    def _run(self):
        mode = getattr(self.config, "mode", "shortest_distance")
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'")
        max_t = getattr(self.config, "max_transfers", None)
        preferred = set(getattr(self.config, "preferred_lines", None) or [])
        track_t = max_t is not None

        start = (self.source, None, 0)
        self._labels[start] = (0, 0, 0, 0.0)
        pq = MinPQ()
        pq.insert(self._cost(self._labels[start]), start)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            station, line, _t = state
            label = self._labels[state]
            if station not in self._best_state:
                self._best_state[station] = state
                self.dist_to[station] = label[0]
                if state in self._parent:
                    self.edge_to[station] = self._parent[state][1]

            for e in self.graph.adjacent(station):
                is_transfer = line is not None and e.line != line
                nt = label[1] + (1 if is_transfer else 0)
                if track_t and nt > max_t:
                    continue
                ns = (e.dest, e.line, nt if track_t else 0)
                if ns in done:
                    continue
                w = e.weight
                pref = e.line in preferred
                new_label = (label[0] + w, nt,
                             label[2] + (0 if pref else w),
                             label[3] + (w * PREFERRED_LINE_DISCOUNT if pref else w))
                new_cost = self._cost(new_label)
                if ns not in self._labels or new_cost < self._cost(self._labels[ns]):
                    self._labels[ns] = new_label
                    self._parent[ns] = (state, e)
                    pq.insert(new_cost, ns)

    # --------------------------------------------------------------- queries
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edges) from source to
        target. Both lists are empty if target is unreachable."""
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while state in self._parent:
            prev, e = self._parent[state]
            edges.append(e)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to target (0 if none/unreachable)."""
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                count += 1
        return count

    def get_lines(self, target):
        """Lines used along the path, in order of first use."""
        _, edges = self.path_with_edges(target)
        return list(dict.fromkeys(e.line for e in edges))
