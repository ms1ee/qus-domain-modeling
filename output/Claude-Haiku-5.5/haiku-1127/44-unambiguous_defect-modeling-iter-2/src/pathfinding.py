"""Shortest path computation on the subway graph using Dijkstra's algorithm.

The search runs over states ``(station_number, line)``: the line is the line
used to arrive at the station. This allows the algorithm to count transfers
(line changes) exactly and to support the different query modes:

* ``shortest_distance``  - minimise the total distance in meters.
* ``least_transfer``     - minimise the number of transfers, then the distance.
* ``comprehensive``      - minimise distance plus a penalty per transfer.

Lines that are not in the preference list receive a penalty in every mode, so
routes on preferred lines are favoured when reasonable.
"""

try:
    from .min_pq import MinPQ
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from min_pq import MinPQ


MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 800.0
# Equivalent distance (meters) added per edge that is not on a preferred line.
PREFERENCE_PENALTY_METERS = 1500.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of line names the passenger prefers.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Dijkstra-based single-source shortest path search.

    Attributes:
        dist_to: Dictionary mapping a reachable station number to the actual
            distance in meters of the best path found to it.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._transfers_to = {}
        self._best_state = {}
        self._edge_to = {}
        self._search()

    # ------------------------------------------------------------------
    # Cost model
    # ------------------------------------------------------------------
    def _cost_key(self, meters, transfers, penalty):
        """Build a comparable cost key for a partial path according to the mode."""
        effective = meters + penalty
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, effective)
        if mode == MODE_COMPREHENSIVE:
            return (effective + transfers * TRANSFER_PENALTY_METERS, meters)
        return (effective, transfers)

    # ------------------------------------------------------------------
    # Dijkstra search over (station, line) states
    # ------------------------------------------------------------------
    def _search(self):
        start = (self.source, None)
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        state_meters = {start: 0.0}
        state_transfers = {start: 0}
        state_penalty = {start: 0.0}
        state_key = {start: self._cost_key(0.0, 0, 0.0)}

        pq = MinPQ()
        pq.insert(start, state_key[start])
        settled = set()

        while not pq.is_empty():
            state = pq.del_min()
            settled.add(state)
            station, line = state
            for other, edge in self.graph.neighbors(station):
                changed_line = line is not None and line != edge.line
                transfers = state_transfers[state] + (1 if changed_line else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue

                new_state = (other, edge.line)
                if new_state in settled:
                    continue

                meters = state_meters[state] + edge.weight
                penalty = state_penalty[state]
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_METERS
                key = self._cost_key(meters, transfers, penalty)

                old_key = state_key.get(new_state)
                if old_key is None or key < old_key:
                    state_key[new_state] = key
                    state_meters[new_state] = meters
                    state_transfers[new_state] = transfers
                    state_penalty[new_state] = penalty
                    self._edge_to[new_state] = (state, edge)
                    if pq.contains(new_state):
                        pq.decrease_key(new_state, key)
                    else:
                        pq.insert(new_state, key)

        # Choose, for every station, the best state (line) that reaches it.
        best = {}
        for state, key in state_key.items():
            station = state[0]
            if station not in best or key < state_key[best[station]]:
                best[station] = state
        for station, state in best.items():
            self._best_state[station] = state
            self.dist_to[station] = state_meters[state]
            self._transfers_to[station] = state_transfers[state]

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------
    def has_path(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the path to ``target`` as ``(station_numbers, edges)``.

        ``station_numbers`` starts with the source and ends with the target;
        ``edges`` contains the connections traversed between consecutive
        stations. Unreachable targets yield ``([], [])``.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while True:
            stations.append(state[0])
            if state not in self._edge_to:
                break
            previous, edge = self._edge_to[state]
            edges.append(edge)
            state = previous
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target`` (0 if unreachable)."""
        return self._transfers_to.get(target, 0)
