"""Path calculation: priority queue, route configuration and Dijkstra's algorithm.

Dijkstra's algorithm is run over labels of the form (station, arrival line),
which allows line changes (transfers) to be counted exactly. The search key
depends on the query mode:

* shortest_distance : minimise total distance (meters)
* least_transfer    : minimise transfers first, then distance
* comprehensive     : minimise a composite score in estimated minutes
                      (1.5 min per km + 5 min per transfer)

Lines not in the configured preference list add a small search penalty
(PREFERENCE_PENALTY_M, in meters-equivalent); reported distances are the
real travelled distances.
"""

from fare_calculator import AVERAGE_MINUTES_PER_KM, MINUTES_PER_TRANSFER

SHORTEST_DISTANCE = "shortest_distance"
LEAST_TRANSFER = "least_transfer"
COMPREHENSIVE = "comprehensive"
VALID_MODES = (SHORTEST_DISTANCE, LEAST_TRANSFER, COMPREHENSIVE)

# Search-only penalty (meters-equivalent) for each edge outside the preferred lines.
PREFERENCE_PENALTY_M = 200.0


class MinPQ:
    """Min-priority queue implemented as a binary heap of (key, item) pairs."""

    def __init__(self):
        self._heap = []

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self._heap.append((key, item))
        self._sift_up(len(self._heap) - 1)

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

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

    def __len__(self):
        return len(self._heap)

    def _sift_up(self, index):
        heap = self._heap
        while index > 0:
            parent = (index - 1) // 2
            if heap[index][0] < heap[parent][0]:
                heap[index], heap[parent] = heap[parent], heap[index]
                index = parent
            else:
                break

    def _sift_down(self, index):
        heap = self._heap
        size = len(heap)
        while True:
            left = 2 * index + 1
            if left >= size:
                break
            child = left
            right = left + 1
            if right < size and heap[right][0] < heap[left][0]:
                child = right
            if heap[child][0] < heap[index][0]:
                heap[index], heap[child] = heap[child], heap[index]
                index = child
            else:
                break


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (empty means no preference).
    """

    def __init__(self, mode=SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown path mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [] if preferred_lines is None else list(preferred_lines)

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class _Label:
    """Best known label for a search state (station, arrival line)."""

    __slots__ = ("key", "distance", "transfers", "penalty", "prev_state", "edge")

    def __init__(self, key, distance, transfers, penalty, prev_state, edge):
        self.key = key
        self.distance = distance
        self.transfers = transfers
        self.penalty = penalty
        self.prev_state = prev_state
        self.edge = edge


class ShortestPath:
    """Single-source optimal path computation using Dijkstra's algorithm.

    Attributes:
        dist_to: dict mapping reachable station number -> travelled distance (meters).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source!r}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._labels = {}
        self._settled_order = []
        self._settled = set()
        self._best_states = {}
        self._run()

    # ----- search key -----------------------------------------------------
    def _key(self, distance, transfers, penalty):
        """Compute the priority key of a label according to the query mode."""
        mode = self.config.mode
        if mode == LEAST_TRANSFER:
            return (transfers, distance + penalty)
        if mode == COMPREHENSIVE:
            return ((distance / 1000.0) * AVERAGE_MINUTES_PER_KM
                    + transfers * MINUTES_PER_TRANSFER
                    + (penalty / 1000.0) * AVERAGE_MINUTES_PER_KM)
        return distance + penalty

    # ----- Dijkstra -------------------------------------------------------
    def _run(self):
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        start_state = (self.source, None)
        start_label = _Label(self._key(0.0, 0, 0.0), 0.0, 0, 0.0, None, None)
        self._labels[start_state] = start_label

        pq = MinPQ()
        pq.insert(start_label.key, start_state)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in self._settled:
                continue
            self._settled.add(state)
            self._settled_order.append(state)
            label = self._labels[state]
            vertex, arrival_line = state

            for edge in self.graph.adj(vertex):
                nxt = edge.other(vertex)
                new_state = (nxt, edge.line)
                if new_state in self._settled:
                    continue

                transfers = label.transfers
                if arrival_line is not None and edge.line != arrival_line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_M

                distance = label.distance + edge.weight
                key = self._key(distance, transfers, penalty)
                existing = self._labels.get(new_state)
                if existing is None or key < existing.key:
                    self._labels[new_state] = _Label(key, distance, transfers, penalty, state, edge)
                    pq.insert(key, new_state)

        # Select the best settled label for every reachable station (deterministic order).
        for state in self._settled_order:
            vertex = state[0]
            label = self._labels[state]
            current = self._best_states.get(vertex)
            if current is None or label.key < self._labels[current].key:
                self._best_states[vertex] = state
        for vertex, state in self._best_states.items():
            self.dist_to[vertex] = self._labels[state].distance

    # ----- queries --------------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_states

    def path_with_edges(self, target):
        """Return the optimal path from the source to ``target``.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects along the path).
            If the target is unreachable, returns ([], []).
        """
        if target not in self._best_states:
            return [], []
        state = self._best_states[target]
        vertices = []
        edges = []
        while True:
            label = self._labels[state]
            vertices.append(state[0])
            if label.prev_state is None:
                break
            edges.append(label.edge)
            state = label.prev_state
        vertices.reverse()
        edges.reverse()
        return vertices, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the optimal path to ``target``.

        Returns 0 if the target is unreachable (use has_path_to to distinguish).
        """
        if target not in self._best_states:
            return 0
        return self._labels[self._best_states[target]].transfers
