"""Dijkstra-based path finding over the subway graph.

The search runs over states ``(station, line of arrival[, transfers])`` so
that transfers between lines can be counted exactly, which enables the
three query modes:

* ``shortest_distance`` - minimise total distance (ties: fewer transfers)
* ``least_transfer``    - minimise number of transfers (ties: distance)
* ``comprehensive``     - minimise distance + transfers * penalty

Optional constraints: a maximum number of transfers and a list of
preferred lines (edges on preferred lines are cheaper during the search).
Reported distances are always the real distances in meters.
"""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance (meters) charged per transfer in comprehensive mode;
# models the walking distance and time spent at an interchange.
TRANSFER_PENALTY_METERS = 3000
# Search-cost multiplier applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.8

INF = float("inf")


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    """Single-source Dijkstra shortest paths with a priority queue.

    :param graph: ``models.Graph``
    :param source: station number of the starting station
    :param config: ``PathfindingConfig`` (defaults to shortest distance)
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        if self.config.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{self.config.mode}'")
        self._preferred = set(self.config.preferred_lines or [])
        self._track_transfers = self.config.max_transfers is not None

        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._info = {}        # state -> (cost, weighted_dist, dist, transfers)
        self._edge_to = {}     # state -> (previous state, edge)
        self._best_state = {}  # station -> best settled state
        self._run()

    # ----- helpers -----
    def _key(self, node, line, transfers):
        if self._track_transfers:
            return (node, line, transfers)
        return (node, line)

    def _weight(self, edge):
        if self._preferred and edge.line in self._preferred:
            return edge.distance * PREFERRED_LINE_FACTOR
        return edge.distance

    def _cost(self, wdist, transfers, dist):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, wdist, dist)
        if mode == "comprehensive":
            return (wdist + transfers * TRANSFER_PENALTY_METERS, transfers, dist)
        return (wdist, transfers, dist)

    # ----- Dijkstra -----
    def _run(self):
        pq = MinPQ()
        start = self._key(self.source, None, 0)
        start_cost = self._cost(0, 0, 0)
        self._info[start] = (start_cost, 0, 0, 0)
        pq.insert(start_cost, start)
        settled = set()
        max_t = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled or cost != self._info[state][0]:
                continue
            settled.add(state)
            node, line = state[0], state[1]
            _, wdist, dist, transfers = self._info[state]
            if node not in self._best_state:
                self._best_state[node] = state

            for edge in self.graph.adj(node):
                nxt = edge.other(node)
                n_t = transfers + (1 if line is not None and edge.line != line else 0)
                if max_t is not None and n_t > max_t:
                    continue
                key = self._key(nxt, edge.line, n_t)
                if key in settled:
                    continue
                n_wd = wdist + self._weight(edge)
                n_d = dist + edge.distance
                n_cost = self._cost(n_wd, n_t, n_d)
                old = self._info.get(key)
                if old is None or n_cost < old[0]:
                    self._info[key] = (n_cost, n_wd, n_d, n_t)
                    self._edge_to[key] = (state, edge)
                    pq.insert(n_cost, key)

        for node, state in self._best_state.items():
            self.dist_to[node] = self._info[state][2]

    # ----- queries -----
    @property
    def edge_to(self):
        """Map station -> edge used to reach it on the best path."""
        result = {}
        for node, state in self._best_state.items():
            if state in self._edge_to:
                result[node] = self._edge_to[state][1]
        return result

    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` of the best path to ``target``.

        Both lists are empty when the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while state in self._edge_to:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        stations = [self.source]
        for edge in edges:
            stations.append(edge.other(stations[-1]))
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                count += 1
        return count
