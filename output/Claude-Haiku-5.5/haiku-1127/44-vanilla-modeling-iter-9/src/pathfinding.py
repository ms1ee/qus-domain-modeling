"""Shortest path computation for the subway graph.

Dijkstra's algorithm runs on a state graph whose states are pairs
(station number, line of the edge used to arrive). This lets the search
count line changes (transfers) exactly while still finding the optimal path
for each query mode:

    shortest_distance : minimise total distance
    least_transfer    : minimise the number of transfers, then distance
    comprehensive     : minimise estimated travel time (distance + transfers)

Complexity: O((V + E) log V) with the binary-heap priority queue MinPQ.
"""

import math

from fare_calculator import calculate_estimated_time

MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Virtual distance added to segments that are not on a preferred line.
# It only affects route ranking, never the reported real distance.
PREFERENCE_PENALTY_M = 500.0


class MinPQ:
    """Binary min-heap priority queue.

    Entries are (priority, item). Priorities may be numbers or tuples. A
    monotonically increasing sequence number breaks ties so that items are
    never compared directly.
    """

    def __init__(self):
        self.heap = []
        self._counter = 0

    @property
    def size(self):
        """Number of entries in the queue."""
        return len(self.heap)

    def is_empty(self):
        """Return True if the queue has no entries."""
        return not self.heap

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        self._counter += 1
        self.heap.append((priority, self._counter, item))
        self._swim(len(self.heap) - 1)

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        return self.heap[0][0]

    def del_min(self):
        """Remove and return (priority, item) with the smallest priority."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        top = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i, j):
        a = self.heap[i]
        b = self.heap[j]
        if a[0] != b[0]:
            return a[0] < b[0]
        return a[1] < b[1]

    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._swap(k, parent)
            k = parent

    def _sink(self, k):
        n = len(self.heap)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of MODES.
        max_transfers: maximum allowed transfers, or None for no limit.
        preferred_lines: list of line names that are preferred.
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unsupported mode '{mode}'; choose from {', '.join(MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(line) for line in (preferred_lines or []) if line]


class _StateInfo:
    """Best known label of a search state (station, arriving line)."""

    __slots__ = ("key", "real_distance", "penalized_distance", "transfers", "prev_state", "edge")

    def __init__(self, key, real_distance, penalized_distance, transfers, prev_state, edge):
        self.key = key
        self.real_distance = real_distance
        self.penalized_distance = penalized_distance
        self.transfers = transfers
        self.prev_state = prev_state
        self.edge = edge


class ShortestPath:
    """Single-source optimal path computation using Dijkstra's algorithm.

    Attributes:
        dist_to: dict mapping station number -> real travelled distance in
            meters of the chosen path (math.inf if unreachable).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Unknown source station number {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {node: math.inf for node in graph.nodes()}
        self._states = {}
        self._best_state = {}
        self._run()

    def _make_key(self, penalized_distance, transfers):
        """Build the comparable priority key for a label under the current mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (float(transfers), penalized_distance)
        if mode == "comprehensive":
            return (calculate_estimated_time(penalized_distance, transfers), penalized_distance)
        return (penalized_distance, float(transfers))

    def _run(self):
        """Run Dijkstra's algorithm over the (station, line) state graph."""
        preferred = set(self.config.preferred_lines)
        limit = self.config.max_transfers

        start = (self.source, None)
        start_key = self._make_key(0.0, 0)
        self._states[start] = _StateInfo(start_key, 0.0, 0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(start_key, start)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line_in = state
            info = self._states[state]

            for edge in self.graph.adjacent(node):
                new_state = (edge.dest, edge.line)
                if new_state in settled:
                    continue

                # Boarding a different line than the one we arrived on is a transfer.
                transfers = info.transfers
                if line_in is not None and edge.line != line_in:
                    transfers += 1
                if limit is not None and transfers > limit:
                    continue

                penalty = PREFERENCE_PENALTY_M if preferred and edge.line not in preferred else 0.0
                real = info.real_distance + edge.distance
                penalized = info.penalized_distance + edge.distance + penalty
                new_key = self._make_key(penalized, transfers)

                old = self._states.get(new_state)
                if old is None or new_key < old.key:
                    self._states[new_state] = _StateInfo(new_key, real, penalized,
                                                         transfers, state, edge)
                    pq.insert(new_key, new_state)

        self._select_best_states()

    def _select_best_states(self):
        """Choose, for every station, the best label reaching it."""
        self._best_state = {self.source: (self.source, None)}
        for state, info in self._states.items():
            node = state[0]
            if node == self.source:
                continue
            current = self._best_state.get(node)
            if current is None or info.key < self._states[current].key:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._states[state].real_distance

    def has_path(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Reconstruct the optimal path to ``target``.

        Returns:
            (list of station numbers from source to target, list of Edge objects).
            Both lists are empty if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        nodes = []
        edges = []
        while state is not None:
            info = self._states[state]
            nodes.append(state[0])
            if info.edge is not None:
                edges.append(info.edge)
            state = info.prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the optimal path to ``target``.

        Returns 0 if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return 0
        return self._states[state].transfers
