"""Shortest path computation for the subway network.

Dijkstra's algorithm is run over a state space of ``(station, line)`` pairs so
that line changes (transfers) can be counted and constrained. A priority queue
implemented as a binary heap (``MinPQ``) provides the O((V+E) log V) bound.

Query modes:
    shortest_distance: minimise total distance in meters.
    least_transfer:    minimise number of transfers, then distance.
    comprehensive:     minimise a blended cost: distance plus penalties for
                       each transfer and each segment on a non-preferred line.
"""

TRANSFER_PENALTY_M = 1500.0
NON_PREFERRED_PENALTY_M = 300.0
VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class MinPQ:
    """Min-priority queue backed by a binary heap.

    Keys are compared with the ``<`` operator. Values are arbitrary objects.
    """

    def __init__(self):
        self._keys = []
        self._values = []

    def __len__(self):
        return len(self._keys)

    def is_empty(self):
        """Return True if the queue holds no elements."""
        return not self._keys

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def insert(self, key, value):
        """Insert a (key, value) pair."""
        self._keys.append(key)
        self._values.append(value)
        self._sift_up(len(self._keys) - 1)

    def del_min(self):
        """Remove and return the (key, value) pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        key, value = self._keys[0], self._values[0]
        last_key = self._keys.pop()
        last_value = self._values.pop()
        if self._keys:
            self._keys[0] = last_key
            self._values[0] = last_value
            self._sift_down(0)
        return key, value

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._values[i], self._values[j] = self._values[j], self._values[i]

    def _sift_up(self, index):
        while index > 0:
            parent = (index - 1) // 2
            if self._keys[index] < self._keys[parent]:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index):
        size = len(self._keys)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and self._keys[left] < self._keys[smallest]:
                smallest = left
            if right < size and self._keys[right] < self._keys[smallest]:
                smallest = right
            if smallest == index:
                break
            self._swap(index, smallest)
            index = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: Line names the passenger prefers to ride.
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        if value not in VALID_MODES:
            raise ValueError(f"Unknown mode '{value}', expected one of {', '.join(VALID_MODES)}")
        self._mode = value

    @property
    def max_transfers(self):
        return self._max_transfers

    @max_transfers.setter
    def max_transfers(self, value):
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self._max_transfers = value


class ShortestPath:
    """Dijkstra-based shortest path search from a single source station.

    Attributes:
        dist_to: Mapping from station number to the total distance (meters)
            of the best path found from the source.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        # state (station, arrival_line) -> cost tuple
        self._cost = {}
        # state -> (distance, transfers, non_preferred_count, previous_state, edge)
        self._info = {}
        # station number -> best final state
        self._best_state = {}
        self._run()

    @staticmethod
    def _make_cost(mode, distance, transfers, non_preferred):
        """Build a comparable cost tuple for the given mode."""
        if mode == "shortest_distance":
            return (distance, non_preferred)
        if mode == "least_transfer":
            return (transfers, non_preferred, distance)
        # comprehensive
        return (distance + TRANSFER_PENALTY_M * transfers
                + NON_PREFERRED_PENALTY_M * non_preferred,)

    def _run(self):
        """Execute Dijkstra's algorithm over the (station, line) state space."""
        cfg = self.config
        mode = cfg.mode
        max_transfers = cfg.max_transfers
        preferred = set(cfg.preferred_lines)

        start = (self.source, None)
        start_cost = self._make_cost(mode, 0, 0, 0)
        self._cost[start] = start_cost
        self._info[start] = (0, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(start_cost, start)

        while not pq.is_empty():
            cost, state = pq.del_min()
            if cost != self._cost[state]:
                continue  # stale queue entry
            vertex, line = state
            distance, transfers, non_preferred = self._info[state][0:3]

            for edge in self.graph.adjacent(vertex):
                nxt = edge.other(vertex)
                new_transfers = transfers + (1 if line is not None and edge.line != line else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_non_preferred = non_preferred + (
                    1 if preferred and edge.line not in preferred else 0)
                new_distance = distance + edge.weight
                new_cost = self._make_cost(mode, new_distance, new_transfers, new_non_preferred)
                next_state = (nxt, edge.line)
                old_cost = self._cost.get(next_state)
                if old_cost is None or new_cost < old_cost:
                    self._cost[next_state] = new_cost
                    self._info[next_state] = (new_distance, new_transfers,
                                              new_non_preferred, state, edge)
                    pq.insert(new_cost, next_state)

        # Select the best state for every reached station.
        for state, cost in self._cost.items():
            vertex = state[0]
            best = self._best_state.get(vertex)
            if best is None or cost < self._cost[best]:
                self._best_state[vertex] = state
        for vertex, state in self._best_state.items():
            self.dist_to[vertex] = self._info[state][0]

    def _require_state(self, target):
        state = self._best_state.get(target)
        if state is None:
            raise ValueError(f"No path from station {self.source} to station {target}")
        return state

    def has_path(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Backtrack the optimal path to ``target``.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` is the list of
            station numbers from source to target and ``edges`` the list of
            edges traversed between consecutive stations.

        Raises:
            ValueError: If the target is unreachable.
        """
        state = self._require_state(target)
        stations = []
        edges = []
        while state is not None:
            stations.append(state[0])
            info = self._info[state]
            if info[4] is not None:
                edges.append(info[4])
            state = info[3]
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the optimal path to ``target``."""
        return self._info[self._require_state(target)][1]
