"""Shortest-path computation on the subway graph.

Implements Dijkstra's algorithm with a binary-heap priority queue (MinPQ).
The search runs over states (station, line-of-last-edge) so that transfers
(line changes at interchange stations) can be counted exactly. Supported
objectives:
    shortest_distance : minimize total distance (ties broken by transfers)
    least_transfer    : minimize transfers (ties broken by distance)
    comprehensive     : minimize distance + transfer penalty (composite score)
Optional constraints: max_transfers and preferred lines (non-preferred lines
receive a soft penalty).
"""

# A 5-minute transfer expressed in meters at the 1.5 min/km speed model.
TRANSFER_PENALTY_METERS = 5.0 / 1.5 * 1000.0
# Soft penalty applied to each edge that is not on a preferred line.
LINE_PREFERENCE_PENALTY_METERS = 2000.0

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed transfers, or None for unlimited.
        preferred_lines: list of preferred line names (may be empty).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}'; choose from {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary min-heap priority queue keyed by comparable keys.

    Only keys are compared; items may be any object.
    """

    def __init__(self, capacity=0):
        self._keys = []
        self._items = []
        self.capacity = capacity

    @property
    def size(self):
        """Number of elements currently in the queue."""
        return len(self._keys)

    def is_empty(self):
        """Return True when the queue has no elements."""
        return not self._keys

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self._keys.append(key)
        self._items.append(item)
        self._swim(len(self._keys) - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def del_min(self):
        """Remove and return (key, item) with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        key, item = self._keys[0], self._items[0]
        last = len(self._keys) - 1
        self._swap(0, last)
        self._keys.pop()
        self._items.pop()
        if self._keys:
            self._sink(0)
        return key, item

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._keys[k] < self._keys[parent]:
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._keys)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._keys[child + 1] < self._keys[child]:
                child += 1
            if self._keys[child] < self._keys[k]:
                self._swap(k, child)
                k = child
            else:
                break


class ShortestPath:
    """Single-source optimal paths over the subway graph.

    Attributes:
        dist_to: dict station number -> total distance in meters of the best
            path found to that station (only reachable stations are present).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}   # station number -> best settled state
        self._labels = {}       # state -> (distance, transfers, penalty)
        self._edge_to = {}      # state -> (previous state, Edge)
        self._run()

    # ----- objective ----------------------------------------------------------
    def _priority(self, label):
        """Map a label (distance, transfers, penalty) to a comparable key."""
        distance, transfers, penalty = label
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, distance + penalty)
        if mode == "comprehensive":
            return (distance + transfers * TRANSFER_PENALTY_METERS + penalty,)
        return (distance + penalty, transfers)

    # ----- Dijkstra -----------------------------------------------------------
    def _run(self):
        start_state = (self.source, None)
        start_label = (0.0, 0, 0.0)
        self._labels[start_state] = start_label

        pq = MinPQ()
        pq.insert(self._priority(start_label), start_state)
        settled = set()
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state
            distance, transfers, penalty = self._labels[state]

            # The first settled state of a station is its best label.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = distance

            for edge in self.graph.adj(node):
                nxt = edge.other(node)
                new_transfers = transfers
                if line is not None and edge.line != line:
                    new_transfers += 1  # line change = transfer at this station
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_penalty = penalty
                if preferred and edge.line not in preferred:
                    new_penalty += LINE_PREFERENCE_PENALTY_METERS
                new_label = (distance + edge.weight, new_transfers, new_penalty)
                next_state = (nxt, edge.line)
                if next_state in settled:
                    continue
                old = self._labels.get(next_state)
                if old is None or self._priority(new_label) < self._priority(old):
                    self._labels[next_state] = new_label
                    self._edge_to[next_state] = (state, edge)
                    pq.insert(self._priority(new_label), next_state)

    # ----- queries ------------------------------------------------------------
    def has_path_to(self, target):
        """Return True if `target` is reachable under the current constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the path distance in meters, or infinity if unreachable."""
        return self.dist_to.get(target, float("inf"))

    def get_transfer_count(self, target):
        """Return the number of transfers on the best path to `target`.

        Returns 0 when the target is unreachable (check has_path_to first).
        """
        state = self._best_state.get(target)
        if state is None:
            return 0
        return self._labels[state][1]

    def path_with_edges(self, target):
        """Reconstruct the path to `target`.

        Returns:
            (list of station numbers from source to target, list of Edge objects
            traversed in order). Both are empty when the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        nodes = [target]
        edges = []
        while state in self._edge_to:
            prev_state, edge = self._edge_to[state]
            edges.append(edge)
            nodes.append(prev_state[0])
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges
