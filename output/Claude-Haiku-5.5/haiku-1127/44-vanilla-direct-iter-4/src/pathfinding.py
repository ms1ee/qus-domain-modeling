"""Shortest-path computation over the subway graph.

The search is Dijkstra's algorithm driven by a binary-heap priority queue
(``MinPQ``), giving O((V+E) log V) time complexity.

The search state is a pair ``(station, incoming_line)``. Tracking the line a
passenger arrived on allows transfers (line changes at interchange stations) to
be counted and penalised exactly, which is required by the minimum-transfer and
comprehensive modes.
"""

import heapq
import itertools
import math

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Extra search cost (meters equivalent) charged per transfer in comprehensive mode.
COMPREHENSIVE_TRANSFER_PENALTY_M = 2000.0
# Lexicographic weight of one transfer in least-transfer mode; larger than any
# realistic total distance so that transfers dominate the ordering.
LEAST_TRANSFER_WEIGHT = 1e9
# Extra search cost charged for each segment that is not on a preferred line.
PREFERENCE_PENALTY_M = 1000.0


class MinPQ:
    """Min priority queue implemented on top of a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()  # tie-breaker so values are never compared

    def insert(self, key, value):
        """Insert ``value`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def del_min(self):
        """Remove and return the ``(key, value)`` pair with the smallest key."""
        key, _, value = heapq.heappop(self._heap)
        return key, value

    def min_key(self):
        """Return the smallest key without removing it."""
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no elements."""
        return not self._heap

    def size(self):
        """Return the number of queued elements."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer`` or ``comprehensive``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names that are preferred (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown path mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Dijkstra-based optimal path computation from one source station.

    After construction the search has been run and the results are available:

    Attributes:
        dist_to: dict mapping station number to the actual travelled distance
            (meters) of the chosen path from the source.
    """

    def __init__(self, graph, source, config=None):
        """Run the search.

        Args:
            graph: ``models.Graph`` instance.
            source: Station number of the starting station.
            config: ``PathfindingConfig`` instance; defaults to shortest distance.

        Raises:
            ValueError: If ``source`` is not a vertex of ``graph``.
        """
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not part of the network")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._transfers = {}      # station number -> transfer count of chosen path
        self._best_state = {}     # station number -> best search state reaching it
        self._cost = {}           # search state -> accumulated search cost
        self._info = {}           # search state -> (distance, transfers, prev_state, edge)
        self._settled = set()
        self._run()

    # ------------------------------------------------------------ core search
    def _step_cost(self, edge, transfer_increment):
        """Return the search cost of traversing ``edge``."""
        cost = edge.weight
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += PREFERENCE_PENALTY_M
        if transfer_increment:
            if self.config.mode == MODE_LEAST_TRANSFER:
                cost += LEAST_TRANSFER_WEIGHT
            elif self.config.mode == MODE_COMPREHENSIVE:
                cost += COMPREHENSIVE_TRANSFER_PENALTY_M
        return cost

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        self._cost[start] = 0.0
        self._info[start] = (0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in self._settled:
                continue
            self._settled.add(state)
            node, line_in = state
            dist, transfers, _, _ = self._info[state]

            for edge in self.graph.adjacent_edges(node):
                nxt = edge.other(node)
                increment = 1 if (line_in is not None and edge.line != line_in) else 0
                new_transfers = transfers + increment
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                next_state = (nxt, edge.line)
                if next_state in self._settled:
                    continue
                new_cost = cost + self._step_cost(edge, increment)
                if new_cost < self._cost.get(next_state, math.inf):
                    self._cost[next_state] = new_cost
                    self._info[next_state] = (dist + edge.weight, new_transfers, state, edge)
                    pq.insert(new_cost, next_state)

        self._select_best_states()

    def _select_best_states(self):
        """Pick, for every reached station, the cheapest search state."""
        best = {}
        for state in self._settled:
            node = state[0]
            if node not in best or self._cost[state] < self._cost[best[node]]:
                best[node] = state
        for node, state in best.items():
            self._best_state[node] = state
            self.dist_to[node] = self._info[state][0]
            self._transfers[node] = self._info[state][1]

    # ------------------------------------------------------------- queries
    def has_path(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the travelled distance (meters) to ``target``, or None if unreachable."""
        return self.dist_to.get(target)

    def path_with_edges(self, target):
        """Return the station sequence and edge sequence from the source to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is a list of station
            numbers starting at the source and ending at ``target``, and ``edges``
            is the list of traversed ``Edge`` objects (``len(stations) - 1`` items).
            Both lists are empty if ``target`` is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while state is not None:
            _, _, prev_state, edge = self._info[state]
            stations.append(state[0])
            if edge is not None:
                edges.append(edge)
            state = prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the chosen path to ``target``.

        Returns 0 for the source itself and for unreachable targets.
        """
        return self._transfers.get(target, 0)
