"""
Shortest-path computation for the subway network.

Implements:
  * ``MinPQ``        - binary min-heap priority queue (O(log n) insert/delete-min).
  * ``PathfindingConfig`` - query configuration (mode, transfer limit, line preference).
  * ``ShortestPath`` - Dijkstra's algorithm driven by ``MinPQ``.

Search states are triples ``(station_number, arrival_line, transfers_so_far)``
so that transfer limits and least-transfer optimisation are exact. The
transfer count increases whenever consecutive edges belong to different lines.

Complexity: O((V+E) log V) for each fixed transfer bound, where the number
of states is bounded by V * L * (max_transfers + 1) with L the number of lines.
"""

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Transfer limit used when the caller does not specify one.
DEFAULT_MAX_TRANSFERS = 10

# Equivalent distance penalty (meters) charged per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 500.0

# Extra cost (meters) charged for travelling on a line that is not preferred.
LINE_PREFERENCE_PENALTY_METERS = 1000.0


class MinPQ:
    """
    Binary min-heap priority queue.

    Items are stored with their priority; ties are broken by insertion order
    so that comparison never falls back to comparing the items themselves.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def insert(self, priority, item):
        """Insert an item with the given (comparable) priority."""
        self._heap.append((priority, self._counter, item))
        self._counter += 1
        self._swim(len(self._heap) - 1)

    def del_min(self):
        """
        Remove and return the ``(priority, item)`` pair with the smallest priority.

        Raises:
            IndexError: If the queue is empty.
        """
        if self.is_empty():
            raise IndexError("priority queue underflow")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)

    def _less(self, i, j):
        a = self._heap[i]
        b = self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and self._less(right, left):
                child = right
            if self._less(child, k):
                self._swap(child, k)
                k = child
            else:
                break


class PathfindingConfig:
    """
    Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum number of transfers allowed (None = default limit).
        preferred_lines: List of line names that are preferred (others are penalised).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """
    Dijkstra-based path finder from a single source station.

    Args:
        graph: The ``Graph`` to search.
        source: Station number of the starting station.
        config: Optional ``PathfindingConfig``.

    Attributes:
        dist_to: dict mapping reachable station number -> travelled distance (meters)
                 of the selected path.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()

        if self.config.mode not in VALID_MODES:
            raise ValueError(f"unknown path mode '{self.config.mode}', expected one of {VALID_MODES}")

        max_transfers = self.config.max_transfers
        if max_transfers is None:
            max_transfers = DEFAULT_MAX_TRANSFERS
        if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
            raise ValueError("max_transfers must be a non-negative integer")
        self._max_transfers = max_transfers

        self._preferred = set(self.config.preferred_lines)

        if source not in graph.adjacency:
            raise ValueError(f"source station number {source} is not in the graph")

        self.dist_to = {}
        # state -> (cost tuple, actual distance, distance-cost, transfers)
        self._labels = {}
        # state -> (previous state, edge used)
        self._pred = {}
        # station number -> best final state
        self._best_state = {}

        self._run()

    # ------------------------------------------------------------ helpers
    def _cost_of(self, dist_cost, transfers):
        """Build the comparable cost tuple for the configured mode."""
        mode = self.config.mode
        if mode == "shortest_distance":
            return (dist_cost,)
        if mode == "least_transfer":
            return (transfers, dist_cost)
        # comprehensive: distance plus a penalty per transfer
        return (dist_cost + transfers * TRANSFER_PENALTY_METERS,)

    # ----------------------------------------------------------- Dijkstra
    def _run(self):
        """Run Dijkstra's algorithm over (station, line, transfers) states."""
        start = (self.source, None, 0)
        zero_cost = self._cost_of(0.0, 0)
        self._labels[start] = (zero_cost, 0.0, 0.0, 0)

        pq = MinPQ()
        pq.insert(zero_cost, start)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)

            node, line, transfers = state
            _, distance, dist_cost, _ = self._labels[state]

            for edge in self.graph.neighbors(node):
                nxt = edge.other_end(node)
                if nxt == node:
                    continue

                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + (1 if is_transfer else 0)
                if new_transfers > self._max_transfers:
                    continue

                step = float(edge.weight)
                if self._preferred and edge.line not in self._preferred:
                    step += LINE_PREFERENCE_PENALTY_METERS

                new_dist_cost = dist_cost + step
                new_distance = distance + float(edge.weight)
                new_cost = self._cost_of(new_dist_cost, new_transfers)
                new_state = (nxt, edge.line, new_transfers)

                if new_state in done:
                    continue

                known = self._labels.get(new_state)
                if known is None or new_cost < known[0]:
                    self._labels[new_state] = (new_cost, new_distance, new_dist_cost, new_transfers)
                    self._pred[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

        # Select the best finalised state for every reachable station.
        best = {}
        for state in self._labels:
            if state not in done:
                continue
            node = state[0]
            cost = self._labels[state][0]
            current = best.get(node)
            if current is None or cost < self._labels[current][0]:
                best[node] = state

        self._best_state = best
        for node, state in best.items():
            self.dist_to[node] = self._labels[state][1]

    # ------------------------------------------------------------- queries
    def has_path_to(self, target):
        """Return True if ``target`` (station number) is reachable under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """
        Reconstruct the path from the source to ``target``.

        Returns:
            (list[station number], list[Edge]): Station numbers in travel order
            (source first, target last) and the edges traversed between them.
            Both lists are empty if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []

        state = self._best_state[target]
        nodes = []
        edges = []
        while True:
            nodes.append(state[0])
            if state not in self._pred:
                break
            previous, edge = self._pred[state]
            edges.append(edge)
            state = previous

        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """
        Return the number of line changes on the path to ``target``.

        Returns 0 if the target is unreachable or equals the source.
        """
        _, edges = self.path_with_edges(target)
        transfers = 0
        for previous, current in zip(edges, edges[1:]):
            if previous.line != current.line:
                transfers += 1
        return transfers
