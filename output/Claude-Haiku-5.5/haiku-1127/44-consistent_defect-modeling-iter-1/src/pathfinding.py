"""Path-finding algorithms for the subway network.

Implements a binary-heap priority queue (``MinPQ``), path configuration
(``PathfindingConfig``), and Dijkstra's shortest-path algorithm
(``ShortestPath``).

Dijkstra runs over states ``(station_number, arriving_line)`` so that line
changes (transfers) can be counted and limited. Three cost models are
supported:

* ``shortest_distance``: minimise total distance in meters.
* ``least_transfer``:    minimise transfers first, then distance.
* ``comprehensive``:     distance plus a fixed penalty per transfer.

A non-preferred line penalty is applied when a line preference is configured.
"""

import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in meter-equivalents) for riding a non-preferred line segment.
PREFERENCE_PENALTY_METERS = 500.0
# Penalty (in meter-equivalents) for each transfer in the comprehensive mode.
TRANSFER_PENALTY_METERS = 1500.0


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items with equal keys are dequeued in insertion order.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key."""
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

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``MODES``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: Lines preferred by the passenger (list of names).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unsupported mode '{mode}'; expected one of {MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    """Dijkstra-based shortest path computation from one source station.

    Attributes:
        dist_to: dict mapping reached station numbers to the accumulated
            distance (meters) of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Source station {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._transfers = {}
        self._best = {}      # station number -> best (node, line) state
        self._prev = {}      # state -> (previous state, edge) or None
        self._run()

    # -- cost model ---------------------------------------------------------

    def _cost(self, distance, transfers, penalties):
        """Compute the comparable cost of a partial path according to the mode."""
        preference = penalties * PREFERENCE_PENALTY_METERS
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, distance + preference)
        if mode == "comprehensive":
            return distance + transfers * TRANSFER_PENALTY_METERS + preference
        return distance + preference

    # -- Dijkstra -------------------------------------------------------------

    def _run(self):
        """Run Dijkstra's algorithm from the source station."""
        start = (self.source, None)
        cost_of = {start: self._cost(0.0, 0, 0)}
        dist_of = {start: 0.0}
        trans_of = {start: 0}
        pen_of = {start: 0}
        self._prev = {start: None}

        pq = MinPQ()
        pq.insert(cost_of[start], start)
        done = set()
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            node, line = state

            # The first time a station is settled gives its optimal state.
            if node not in self._best:
                self._best[node] = state
                self.dist_to[node] = dist_of[state]
                self._transfers[node] = trans_of[state]

            for edge in self.graph.adj(node):
                transfers = trans_of[state]
                if line is not None and edge.line != line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                penalties = pen_of[state]
                if preferred and edge.line not in preferred:
                    penalties += 1

                distance = dist_of[state] + edge.distance
                new_state = (edge.dest, edge.line)
                if new_state in done:
                    continue
                new_cost = self._cost(distance, transfers, penalties)
                if new_state not in cost_of or new_cost < cost_of[new_state]:
                    cost_of[new_state] = new_cost
                    dist_of[new_state] = distance
                    trans_of[new_state] = transfers
                    pen_of[new_state] = penalties
                    self._prev[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

    # -- queries --------------------------------------------------------------

    def has_path(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best

    def path_with_edges(self, target):
        """Reconstruct the path from the source to ``target`` by backtracking.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the list of
            station numbers in travel order (source first, target last) and
            ``edges`` is the list of traversed ``Edge`` objects. Both lists are
            empty if the target is unreachable.
        """
        if target not in self._best:
            return [], []
        state = self._best[target]
        stations = [state[0]]
        edges = []
        while self._prev[state] is not None:
            prev_state, edge = self._prev[state]
            edges.append(edge)
            stations.append(prev_state[0])
            state = prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the path to ``target`` (0 if unreachable)."""
        return self._transfers.get(target, 0)
