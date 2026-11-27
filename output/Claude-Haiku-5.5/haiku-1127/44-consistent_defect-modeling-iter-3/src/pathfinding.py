"""Shortest path computation (Dijkstra's algorithm with a heap-based priority queue).

Path search runs over states ``(station number, line used to arrive)`` so that
line changes (transfers) can be counted and constrained. Three optimisation
modes are supported:

* ``shortest_distance``: minimise total distance (meters).
* ``least_transfer``: minimise the number of transfers, then distance.
* ``comprehensive``: minimise a composite score of distance plus a fixed
  penalty per transfer.
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
SUPPORTED_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite scoring: about 5 minutes of travel time at 1.5 minutes per km.
TRANSFER_PENALTY_METERS = 3333
# Extra cost for using a line that is not in the passenger's preference list.
PREFERENCE_PENALTY_METERS = 1000


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of SUPPORTED_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: Lines the passenger prefers; using other lines
            incurs a penalty. Empty list means no preference.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {SUPPORTED_MODES}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items with equal keys are dequeued in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given comparable key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Dijkstra-based optimal path search from a single source station.

    Args:
        graph: models.Graph instance.
        source: Station number of the origin.
        config: PathfindingConfig (defaults to shortest-distance mode).

    Attributes:
        dist_to: Mapping station number -> total distance in meters of the
            selected path from the source.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self._graph = graph
        self.source = source
        self.config = config or PathfindingConfig()

        # Per-state bookkeeping; a state is (station number, arrival line or None).
        self._state_cost = {}
        self._state_dist = {}
        self._state_pref = {}
        self._state_transfers = {}
        self._state_prev = {}

        self._best_state = {}     # station number -> best state reaching it
        self.dist_to = {}         # station number -> distance in meters
        self._cost_to = {}        # station number -> cost tuple

        self._run()
        self._select_best_states()

    def _make_cost(self, dist, pref, transfers):
        """Build the comparable cost tuple for a state under the configured mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, dist + pref)
        if mode == MODE_COMPREHENSIVE:
            return (dist + pref + TRANSFER_PENALTY_METERS * transfers, transfers)
        return (dist + pref, transfers)

    def _run(self):
        """Run Dijkstra's algorithm over the (station, line) state space."""
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start = (self.source, None)
        self._state_dist[start] = 0
        self._state_pref[start] = 0
        self._state_transfers[start] = 0
        self._state_cost[start] = self._make_cost(0, 0, 0)

        queue = MinPQ()
        queue.insert(self._state_cost[start], start)
        settled = set()

        while not queue.is_empty():
            cost, state = queue.del_min()
            if state in settled:
                continue
            settled.add(state)

            station, line_in = state
            dist_in = self._state_dist[state]
            pref_in = self._state_pref[state]
            transfers_in = self._state_transfers[state]

            for edge in self._graph.adj(station):
                transfers = transfers_in
                if line_in is not None and edge.line != line_in:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                next_state = (edge.dest, edge.line)
                if next_state in settled:
                    continue

                dist = dist_in + edge.distance
                pref = pref_in
                if preferred and edge.line not in preferred:
                    pref += PREFERENCE_PENALTY_METERS
                new_cost = self._make_cost(dist, pref, transfers)

                old_cost = self._state_cost.get(next_state)
                if old_cost is None or new_cost < old_cost:
                    self._state_cost[next_state] = new_cost
                    self._state_dist[next_state] = dist
                    self._state_pref[next_state] = pref
                    self._state_transfers[next_state] = transfers
                    self._state_prev[next_state] = (state, edge)
                    queue.insert(new_cost, next_state)

    def _select_best_states(self):
        """Choose, for every reached station, the cheapest arriving state."""
        for state, cost in self._state_cost.items():
            station = state[0]
            current = self._best_state.get(station)
            if current is None or cost < self._state_cost[current]:
                self._best_state[station] = state

        for station, state in self._best_state.items():
            self.dist_to[station] = self._state_dist[state]
            self._cost_to[station] = self._state_cost[state]

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Backtrack the optimal path to ``target``.

        Returns:
            (stations, edges): station numbers from source to target and the
            edges traversed in order. Both are empty if unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while True:
            stations.append(state[0])
            previous = self._state_prev.get(state)
            if previous is None:
                break
            prev_state, edge = previous
            edges.append(edge)
            state = prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the optimal path to ``target``."""
        if target not in self._best_state:
            return 0
        return self._state_transfers[self._best_state[target]]

    def get_cost(self, target):
        """Return the mode-specific cost tuple of the optimal path to ``target``."""
        return self._cost_to.get(target)
