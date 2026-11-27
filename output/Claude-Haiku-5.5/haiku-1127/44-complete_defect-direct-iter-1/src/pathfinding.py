"""Shortest path computation using Dijkstra's algorithm with a priority queue.

The search runs over states (station number, line used to arrive). This lets
the algorithm count line changes (transfers) exactly and handle multi-line
interchange stations correctly.

Supported modes:
    shortest_distance: minimize total distance in meters.
    least_transfer:    minimize transfers first, then distance.
    comprehensive:     minimize distance plus a penalty per transfer.

Line preferences add a penalty to distance for edges on non-preferred lines.
"""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
DEFAULT_MODE = "shortest_distance"
TRANSFER_PENALTY_M = 500.0      # equivalent distance penalty per transfer (comprehensive mode)
PREFERENCE_PENALTY_M = 300.0    # penalty per edge on a non-preferred line


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Min priority queue backed by a binary heap.

    Items with equal keys are served in insertion order thanks to a counter
    tie-breaker, so the items themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("min_key from an empty priority queue")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)


class ShortestPath:
    """Dijkstra-based shortest path search from a single source station.

    Attributes:
        dist_to: dict mapping reachable station number -> actual distance in meters.
        transfers_to: dict mapping reachable station number -> transfer count.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.adj:
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()

        self.dist_to = {}
        self.transfers_to = {}
        self._state_for = {}   # station -> best settled state (station, line)
        self._info = {}        # state -> (distance, transfers, accumulated penalty)
        self._best_key = {}    # state -> best priority key found so far
        self._edge_to = {}     # state -> (previous state, Edge)

        self._run()

    def _make_key(self, effective_distance, transfers):
        """Build the priority key for a state according to the query mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, effective_distance)
        if mode == "comprehensive":
            return (effective_distance + TRANSFER_PENALTY_M * transfers,)
        return (effective_distance,)

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start = (self.source, None)
        self._info[start] = (0.0, 0, 0.0)
        self._best_key[start] = self._make_key(0.0, 0)

        pq = MinPQ()
        pq.insert(self._best_key[start], start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled or key != self._best_key[state]:
                continue  # stale queue entry
            settled.add(state)

            station, line = state
            dist, transfers, penalty = self._info[state]

            # The first settled state of a station is its optimal state.
            if station not in self._state_for:
                self._state_for[station] = state
                self.dist_to[station] = dist
                self.transfers_to[station] = transfers

            for edge in self.graph.adjacent(station):
                nxt = edge.other(station)

                # A transfer happens when the line changes (not at the origin).
                new_transfers = transfers
                if line is not None and edge.line != line:
                    new_transfers += 1
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                new_dist = dist + edge.weight
                new_penalty = penalty
                if preferred and edge.line not in preferred:
                    new_penalty += PREFERENCE_PENALTY_M

                nstate = (nxt, edge.line)
                if nstate in settled:
                    continue

                nkey = self._make_key(new_dist + new_penalty, new_transfers)
                best = self._best_key.get(nstate)
                if best is None or nkey < best:
                    self._best_key[nstate] = nkey
                    self._info[nstate] = (new_dist, new_transfers, new_penalty)
                    self._edge_to[nstate] = (state, edge)
                    pq.insert(nkey, nstate)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source (within limits)."""
        return target in self._state_for

    def distance_to(self, target):
        """Return the distance in meters to ``target``, or infinity if unreachable."""
        return self.dist_to.get(target, float("inf"))

    def get_transfer_count(self, target):
        """Return the number of transfers on the path to ``target``.

        Returns -1 if the target is unreachable.
        """
        return self.transfers_to.get(target, -1)

    def path_with_edges(self, target):
        """Reconstruct the path from the source to ``target``.

        Returns:
            (stations, edges): ``stations`` is the ordered list of station numbers
            from source to target; ``edges`` is the ordered list of Edge objects
            between consecutive stations. Both are empty if unreachable.
        """
        if target not in self._state_for:
            return [], []

        stations = []
        edges = []
        state = self._state_for[target]
        while True:
            stations.append(state[0])
            if state not in self._edge_to:
                break
            prev_state, edge = self._edge_to[state]
            edges.append(edge)
            state = prev_state

        stations.reverse()
        edges.reverse()
        return stations, edges
