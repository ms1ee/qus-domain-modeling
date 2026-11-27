"""Shortest-path computation over the subway graph using Dijkstra's algorithm.

Search runs over states ``(station, line, transfers)``. A transfer happens
when the incoming edge's line differs from the line of the previous edge.
Tracking the transfer count in the state makes the maximum-transfer limit
exact.

Path modes:
    shortest_distance: minimize total distance (meters).
    least_transfer:    minimize number of transfers, then distance.
    comprehensive:     minimize distance + TRANSFER_PENALTY_METERS per transfer.

If preferred lines are configured, edges on other lines receive a soft
penalty of LINE_PREFERENCE_PENALTY_METERS in every mode.
"""

import math

from models import Edge  # noqa: F401  (re-exported for convenience)

PATH_MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY_METERS = 1000.0
LEAST_TRANSFER_WEIGHT = 1.0e9
LINE_PREFERENCE_PENALTY_METERS = 500.0


class MinPQ:
    """Binary min-heap priority queue.

    Entries are stored as ``(key, sequence, item)`` so that equal keys are
    broken by insertion order and items never need to be comparable.
    """

    def __init__(self):
        self.heap = []
        self._sequence = 0

    @property
    def size(self):
        """Number of entries currently in the queue."""
        return len(self.heap)

    def is_empty(self):
        """Return True if the queue has no entries."""
        return not self.heap

    def insert(self, key, item):
        """Insert an item with the given priority key (O(log n))."""
        self._sequence += 1
        self.heap.append((key, self._sequence, item))
        self._swim(len(self.heap) - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        return self.heap[0][0]

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key (O(log n))."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        top = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i, j):
        return (self.heap[i][0], self.heap[i][1]) < (self.heap[j][0], self.heap[j][1])

    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self.heap)
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < n and self._less(left, smallest):
                smallest = left
            if right < n and self._less(right, smallest):
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of PATH_MODES.
        max_transfers: maximum allowed transfers, or None for unlimited.
        preferred_lines: list of preferred line names (soft preference).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in PATH_MODES:
            raise ValueError(f"unknown path mode '{mode}', expected one of {', '.join(PATH_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Dijkstra-based path search from one source station.

    Attributes:
        algorithm: name of the algorithm ("Dijkstra").
        dist_to: dict station number -> physical distance (meters) of the best path.
        edge_to: dict station number -> predecessor station number on the best path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"station number {source} is not part of the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.algorithm = "Dijkstra"
        self.dist_to = {}
        self.edge_to = {}
        self._transfers_to = {}
        self._best_state = {}
        self._state_cost = {}
        self._state_dist = {}
        self._state_transfers = {}
        self._state_prev = {}
        self._search()
        self._collect_results()

    def _edge_cost(self, edge, switched):
        """Return the search cost of traversing ``edge``."""
        cost = edge.distance
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += LINE_PREFERENCE_PENALTY_METERS
        if self.config.mode == "least_transfer":
            cost += LEAST_TRANSFER_WEIGHT * switched
        elif self.config.mode == "comprehensive":
            cost += TRANSFER_PENALTY_METERS * switched
        return cost

    def _search(self):
        """Run Dijkstra's algorithm over (station, line, transfers) states."""
        start = (self.source, None, 0)
        self._state_cost[start] = 0.0
        self._state_dist[start] = 0.0
        self._state_transfers[start] = 0

        pq = MinPQ()
        pq.insert(0.0, start)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, transfers = state
            dist = self._state_dist[state]

            for edge in self.graph.neighbors(node):
                nxt = edge.other(node)
                switched = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + switched
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                next_state = (nxt, edge.line, new_transfers)
                if next_state in settled:
                    continue
                new_cost = cost + self._edge_cost(edge, switched)
                if next_state not in self._state_cost or new_cost < self._state_cost[next_state]:
                    self._state_cost[next_state] = new_cost
                    self._state_dist[next_state] = dist + edge.distance
                    self._state_transfers[next_state] = new_transfers
                    self._state_prev[next_state] = (state, edge)
                    pq.insert(new_cost, next_state)

    def _collect_results(self):
        """Select the best state per station and fill the public result maps."""
        best = {}
        for state, cost in self._state_cost.items():
            node = state[0]
            if node not in best or cost < self._state_cost[best[node]]:
                best[node] = state
        self._best_state = best
        for node, state in best.items():
            self.dist_to[node] = self._state_dist[state]
            self._transfers_to[node] = self._state_transfers[state]
            if state in self._state_prev:
                self.edge_to[node] = self._state_prev[state][0][0]

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def get_distance(self, target):
        """Return the distance in meters to ``target`` (math.inf if unreachable)."""
        return self.dist_to.get(target, math.inf)

    def get_transfer_count(self, target):
        """Return the number of transfers on the best path to ``target`` (0 if unreachable)."""
        return self._transfers_to.get(target, 0)

    def path_with_edges(self, target):
        """Reconstruct the best path to ``target``.

        Returns:
            (list of station numbers from source to target, list of Edge objects
            in traversal order). Both lists are empty if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes = [state[0]]
        edges = []
        while state in self._state_prev:
            prev_state, edge = self._state_prev[state]
            edges.append(edge)
            nodes.append(prev_state[0])
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges
