"""Dijkstra-based path computation on the subway graph.

The search runs over *states* ``(station, current line[, transfers])`` rather
than plain stations.  This makes transfers at interchange stations explicit:
moving onto an edge of a different line than the one used to arrive counts
as a transfer.  Using a priority queue keeps the complexity at
O((V+E) log V) in the number of states.

Modes:
    shortest_distance  - minimise distance (ties: fewer transfers)
    least_transfer     - minimise transfers (ties: shorter distance)
    comprehensive      - minimise distance + a penalty per transfer
"""

from models import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for one transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Weight multiplier for edges on preferred lines (preference modes).
PREFERRED_LINE_FACTOR = 0.7


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines)

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Single-source path computation using Dijkstra's algorithm.

    Attributes:
        source:  source station number
        dist_to: ``{station number: distance in meters}`` of the best route
                 (according to the configured mode) to every reachable station
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._validate_config()
        self._preferred = set(self.config.preferred_lines or [])
        self._limited = self.config.max_transfers is not None

        self.dist_to = {}
        self._best_state = {}   # station -> settled best state
        self._values = {}       # state -> (distance, transfers, adjusted distance)
        self._parent = {}       # state -> (previous state, edge)
        self._run()

    # ------------------------------------------------------------------
    def _validate_config(self):
        mode = self.config.mode
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown path mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}")
        mt = self.config.max_transfers
        if mt is not None:
            if isinstance(mt, bool) or not isinstance(mt, int):
                raise TypeError("max_transfers must be an integer")
            if mt < 0:
                raise ValueError("max_transfers must be non-negative")
        if isinstance(self.config.preferred_lines, str):
            self.config.preferred_lines = [self.config.preferred_lines]

    def _cost(self, distance, transfers, adjusted):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, adjusted, distance)
        if mode == MODE_COMPREHENSIVE:
            return (adjusted + TRANSFER_PENALTY_METERS * transfers, transfers, distance)
        # shortest distance: preference is only a tie-breaker
        return (distance, transfers, adjusted)

    def _edge_adjusted_weight(self, edge):
        if edge.line in self._preferred:
            if self.config.mode == MODE_SHORTEST_DISTANCE:
                return 0  # tie-breaker: count only non-preferred distance
            return edge.weight * PREFERRED_LINE_FACTOR
        return edge.weight

    def _run(self):
        start = (self.source, None, 0 if self._limited else None)
        self._values[start] = (0, 0, 0)
        best_cost = {start: self._cost(0, 0, 0)}
        settled = set()
        pq = MinPQ()
        pq.push(start, best_cost[start])
        max_t = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.pop()
            if state in settled:
                continue
            settled.add(state)
            station, line, _ = state
            distance, transfers, adjusted = self._values[state]
            if station not in self._best_state:
                self._best_state[station] = state
                self.dist_to[station] = distance

            for edge in self.graph.adj(station):
                new_t = transfers + (1 if line is not None and edge.line != line else 0)
                if self._limited and new_t > max_t:
                    continue
                new_d = distance + edge.weight
                new_adj = adjusted + self._edge_adjusted_weight(edge)
                new_state = (edge.dest, edge.line, new_t if self._limited else None)
                if new_state in settled:
                    continue
                new_cost = self._cost(new_d, new_t, new_adj)
                if new_state not in best_cost or new_cost < best_cost[new_state]:
                    best_cost[new_state] = new_cost
                    self._values[new_state] = (new_d, new_t, new_adj)
                    self._parent[new_state] = (state, edge)
                    pq.push(new_state, new_cost)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return ``(station numbers, edges)`` from source to ``target``.

        Both lists are empty when ``target`` is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = [state[0]]
        edges = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            stations.append(prev[0])
            state = prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of transfers on the route to ``target`` (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        return self._values[self._best_state[target]][1]
