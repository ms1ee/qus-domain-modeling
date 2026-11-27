"""Shortest-path computation using Dijkstra's algorithm with a binary heap.

The search runs over states (station number, arriving line). This allows
exact transfer counting, the least-transfer mode and the max-transfer limit.
Each state is settled at most once, and states are kept in a MinPQ, so the
running time is O((V + E) log V) for the expanded state graph.
"""

from min_pq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for each transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000
# Equivalent distance (meters) charged for each segment not on a preferred line.
PREFERENCE_PENALTY_M = 500


class PathfindingConfig:
    """Query configuration for path computation.

    Attributes:
        mode: one of "shortest_distance", "least_transfer", "comprehensive".
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: list of line names to prefer (empty means no preference).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self):
        """Raise ValueError/TypeError if the configuration is invalid."""
        if self.mode not in MODES:
            raise ValueError(f"unknown mode '{self.mode}'")
        if self.max_transfers is not None:
            if (isinstance(self.max_transfers, bool)
                    or not isinstance(self.max_transfers, int)
                    or self.max_transfers < 0):
                raise ValueError("max_transfers must be a non-negative integer or None")
        for line in self.preferred_lines:
            if not isinstance(line, str):
                raise TypeError("preferred lines must be strings")


class ShortestPath:
    """Single-source shortest path computation.

    Args:
        graph: the Graph to search.
        source: station number of the starting station.
        config: optional PathfindingConfig (defaults to shortest distance).

    Attributes:
        dist_to: dict station number -> actual travelled distance in meters
            of the best path found to that station (only reachable stations).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.dist_to = {}
        self._keys = {}       # state -> cost key used for ordering
        self._info = {}       # state -> (distance_m, transfers, preference_penalty)
        self._edge_to = {}    # state -> (previous state, edge used)
        self._best_state = {}  # station number -> best state reaching it
        self._run()

    # ------------------------------------------------------------------
    # Cost model
    # ------------------------------------------------------------------
    def _cost_key(self, dist, transfers, pref):
        """Return the comparable cost key of a state for the current mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, dist + pref)
        if mode == MODE_COMPREHENSIVE:
            return (dist + pref + TRANSFER_PENALTY_M * transfers,)
        return (dist + pref,)

    # ------------------------------------------------------------------
    # Dijkstra main loop
    # ------------------------------------------------------------------
    def _run(self):
        prefs = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        self._info[start] = (0, 0, 0)
        self._keys[start] = self._cost_key(0, 0, 0)

        pq = MinPQ()
        pq.insert(self._keys[start], start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled or key != self._keys[state]:
                continue  # stale heap entry
            settled.add(state)
            node, line = state
            dist, transfers, pref = self._info[state]

            for edge in self.graph.adjacent(node):
                nxt = edge.other(node)
                new_transfers = transfers + (1 if line is not None and line != edge.line else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_dist = dist + edge.distance
                new_pref = pref + (PREFERENCE_PENALTY_M
                                   if prefs and edge.line not in prefs else 0)
                next_state = (nxt, edge.line)
                if next_state in settled:
                    continue
                new_key = self._cost_key(new_dist, new_transfers, new_pref)
                old_key = self._keys.get(next_state)
                if old_key is None or new_key < old_key:
                    self._keys[next_state] = new_key
                    self._info[next_state] = (new_dist, new_transfers, new_pref)
                    self._edge_to[next_state] = (state, edge)
                    pq.insert(new_key, next_state)

        for state in settled:
            node = state[0]
            if node not in self._best_state or self._keys[state] < self._keys[self._best_state[node]]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._info[state][0]

    # ------------------------------------------------------------------
    # Public queries
    # ------------------------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the travelled distance in meters to ``target`` (KeyError if unreachable)."""
        return self.dist_to[target]

    def path_with_edges(self, target):
        """Return the station sequence and edge sequence from source to target.

        Returns:
            (list of station numbers, list of Edge). The edge list has one
            element fewer than the station list. Unreachable targets return
            ([], []).
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        chain_states = [state]
        chain_edges = []
        while state in self._edge_to:
            prev_state, edge = self._edge_to[state]
            chain_edges.append(edge)
            state = prev_state
            chain_states.append(state)
        chain_states.reverse()
        chain_edges.reverse()
        nodes = [s[0] for s in chain_states]
        return nodes, chain_edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``.

        Returns 0 if the target is unreachable.
        """
        if target not in self._best_state:
            return 0
        return self._info[self._best_state[target]][1]
