"""
Path calculation based on Dijkstra's algorithm.

The search runs on an expanded state space ``(station, current_line)`` (plus
the transfer count when a maximum transfer limit is configured) so that
transfers at multi-line interchange stations are handled exactly. Priorities
are tuples of non-negative accumulated quantities, so Dijkstra remains
correct for every query mode:

* ``shortest_distance`` - minimise distance (ties: preferred lines, transfers)
* ``least_transfer``    - minimise transfers, then (preference weighted) distance
* ``comprehensive``     - minimise a composite score: distance plus a penalty
                          per transfer equivalent to the transfer time
"""

from fare_calculator import MINUTES_PER_KM, MINUTES_PER_TRANSFER
from models import Edge, Graph, MinPQ  # noqa: F401  (re-exported for convenience)

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

#: Distance (meters) equivalent of one transfer, derived from the time model
#: (5 minutes per transfer at 1.5 minutes per kilometer ~= 3333 meters).
TRANSFER_PENALTY_METERS = MINUTES_PER_TRANSFER / MINUTES_PER_KM * 1000.0

#: Extra weight factor applied to distance travelled on non-preferred lines.
NON_PREFERRED_LINE_FACTOR = 0.5


class PathfindingConfig:
    """Configuration of a path query.

    :param mode: one of :data:`VALID_MODES`
    :param max_transfers: maximum allowed number of transfers (None = no limit)
    :param preferred_lines: list of preferred line names
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])
        self.validate()

    def validate(self):
        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{self.mode}', expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if self.preferred_lines is None:
            self.preferred_lines = []

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class PathCalculationError(Exception):
    """Raised when a path cannot be calculated."""


class ShortestPath:
    """Dijkstra shortest path tree from a single source station number.

    Attributes:
        dist_to:  station number -> distance (meters) of the best path found
        edge_to:  station number -> last :class:`Edge` on the best path
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        if not graph.has_vertex(source):
            raise PathCalculationError(f"Source station number {source!r} is not in the graph")
        self.dist_to = {}
        self.edge_to = {}
        self._transfers = {}
        self._best_state = {}
        self._parent = {}
        self._run()

    # ---------------------------------------------------------------- search
    def _priority(self, acc):
        dist, nonpref, transfers = acc
        mode = self.config.mode
        if mode == "shortest_distance":
            return (dist, nonpref, transfers)
        if mode == "least_transfer":
            return (transfers, dist + NON_PREFERRED_LINE_FACTOR * nonpref, dist)
        # comprehensive
        score = dist + NON_PREFERRED_LINE_FACTOR * nonpref + TRANSFER_PENALTY_METERS * transfers
        return (score, transfers, dist)

    def _run(self):
        cfg = self.config
        preferred = set(cfg.preferred_lines)
        use_pref = bool(preferred)
        limit = cfg.max_transfers
        track = limit is not None

        start = (self.source, None, 0) if track else (self.source, None)
        acc = {start: (0, 0, 0)}
        pq = MinPQ()
        pq.insert(self._priority(acc[start]), start)
        settled = set()

        while pq:
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state[0], state[1]
            dist, nonpref, transfers = acc[state]

            if node not in self.dist_to:
                self.dist_to[node] = dist
                self._transfers[node] = transfers
                self._best_state[node] = state
                parent = self._parent.get(state)
                if parent is not None:
                    self.edge_to[node] = parent[1]

            for edge in self.graph.adj(node):
                nxt = edge.other(node)
                new_transfers = transfers + (1 if (line is not None and edge.line != line) else 0)
                if track and new_transfers > limit:
                    continue
                new_state = (nxt, edge.line, new_transfers) if track else (nxt, edge.line)
                if new_state in settled:
                    continue
                extra_np = edge.weight if (use_pref and edge.line not in preferred) else 0
                cand = (dist + edge.weight, nonpref + extra_np, new_transfers)
                old = acc.get(new_state)
                if old is None or self._priority(cand) < self._priority(old):
                    acc[new_state] = cand
                    self._parent[new_state] = (state, edge)
                    pq.insert(self._priority(cand), new_state)

    # --------------------------------------------------------------- queries
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        """Distance in meters to ``target`` (``float('inf')`` if unreachable)."""
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return ``(station numbers, edges)`` of the best path to ``target``.

        Returns ``([], [])`` if the target is unreachable (under the current
        configuration, e.g. the maximum transfer limit).
        """
        if target not in self._best_state:
            return [], []
        nodes = [target]
        edges = []
        state = self._best_state[target]
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            nodes.append(prev[0])
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        """Return the list of station numbers on the best path to ``target``."""
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of transfers on the best path to ``target`` (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        return self._transfers[target]

    def get_transfer_points(self, target):
        """List of ``(station number, from_line, to_line)`` along the best path."""
        nodes, edges = self.path_with_edges(target)
        points = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                points.append((nodes[i], edges[i - 1].line, edges[i].line))
        return points
