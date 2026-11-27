"""Shortest path calculation for the subway network.

Implements Dijkstra's algorithm with a binary-heap priority queue
(``MinPQ``), running in O((V + E) log V). The search operates on states of
the form ``(station, current_line, transfer_bucket)`` so that line changes
(transfers), maximum transfer limits and line preferences can be honored
exactly while still returning the optimal path for the chosen mode.
"""

from models import Edge, Graph

INF = float("inf")

# Cost (in meters-equivalent) added per transfer in "comprehensive" mode.
TRANSFER_PENALTY_COMPREHENSIVE_M = 1500.0
# Very large per-transfer weight used in "least_transfer" mode so that the
# number of transfers dominates the total distance.
LEAST_TRANSFER_WEIGHT_M = 1.0e7
# Cost (in meters-equivalent) added for every edge outside the preferred lines.
PREFERENCE_PENALTY_M = 500.0


class MinPQ:
    """Min-priority queue implemented as an explicit binary heap."""

    def __init__(self):
        self._heap = []  # entries: (key, sequence, item)
        self._seq = 0

    def __len__(self) -> int:
        return len(self._heap)

    def size(self) -> int:
        """Return the number of entries in the queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True if the queue holds no entries."""
        return not self._heap

    def insert(self, key: float, item) -> None:
        """Insert an item with the given priority key."""
        self._heap.append((key, self._seq, item))
        self._seq += 1
        self._swim(len(self._heap) - 1)

    def min(self):
        """Return (key, item) with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        key, _, item = self._heap[0]
        return key, item

    def del_min(self):
        """Remove and return (key, item) with the smallest key."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i: int, j: int) -> bool:
        a = self._heap[i]
        b = self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k: int) -> None:
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k: int) -> None:
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
                self._swap(k, child)
                k = child
            else:
                break


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of line names preferred during routing.
    """

    SHORTEST_DISTANCE = "shortest_distance"
    LEAST_TRANSFER = "least_transfer"
    COMPREHENSIVE = "comprehensive"
    MODES = (SHORTEST_DISTANCE, LEAST_TRANSFER, COMPREHENSIVE)

    def __init__(self, mode: str = SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in self.MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {', '.join(self.MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    """Dijkstra-based shortest path search from a single source station.

    Args:
        graph: The subway ``Graph``.
        source: Station number of the starting station.
        config: Optional ``PathfindingConfig``; defaults to shortest distance
            with no transfer limit and no line preference.

    Attributes:
        dist_to: Mapping from station number to the minimal search cost
            (equal to the distance in meters for the default configuration).
    """

    def __init__(self, graph: Graph, source: int, config: PathfindingConfig = None):
        if not graph.has_node(source):
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._state_cost = {}   # state -> accumulated search cost
        self._state_info = {}   # state -> (distance_m, transfers)
        self._edge_to = {}      # state -> (previous_state, Edge)
        self._best_state = {}   # station number -> best state reaching it
        self._run()

    def _step_cost(self, edge: Edge, transfer_delta: int) -> float:
        """Search cost of traversing ``edge`` under the current configuration."""
        cost = edge.distance
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            cost += PREFERENCE_PENALTY_M
        if self.config.mode == PathfindingConfig.LEAST_TRANSFER:
            cost += transfer_delta * LEAST_TRANSFER_WEIGHT_M
        elif self.config.mode == PathfindingComprehensiveMode.VALUE:
            cost += transfer_delta * TRANSFER_PENALTY_COMPREHENSIVE_M
        return cost

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line, bucket) states."""
        max_transfers = self.config.max_transfers
        start_state = (self.source, None, 0)
        self._state_cost[start_state] = 0.0
        self._state_info[start_state] = (0.0, 0)

        pq = MinPQ()
        pq.insert(0.0, start_state)

        while not pq.is_empty():
            cost, state = pq.del_min()
            if cost > self._state_cost[state]:
                continue  # stale queue entry
            node, line, _ = state
            dist_m, transfers = self._state_info[state]

            for neighbor, edge in self.graph.neighbors(node):
                delta = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + delta
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                bucket = 0 if max_transfers is None else new_transfers
                new_state = (neighbor, edge.line, bucket)
                new_cost = cost + self._step_cost(edge, delta)
                if new_cost < self._state_cost.get(new_state, INF):
                    self._state_cost[new_state] = new_cost
                    self._state_info[new_state] = (dist_m + edge.distance, new_transfers)
                    self._edge_to[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

        for state, cost in self._state_cost.items():
            node = state[0]
            current = self._best_state.get(node)
            if current is None or cost < self._state_cost[current]:
                self._best_state[node] = state
        self.dist_to = {node: self._state_cost[state] for node, state in self._best_state.items()}

    def has_path(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the configuration."""
        return target in self._best_state

    def path_with_edges(self, target: int):
        """Return ``(station_numbers, edges)`` from the source to ``target``.

        Returns ``([], [])`` if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        nodes = [target]
        edges = []
        while state in self._edge_to:
            previous, edge = self._edge_to[state]
            edges.append(edge)
            nodes.append(previous[0])
            state = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the path to ``target``.

        Returns -1 if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return -1
        return self._state_info[state][1]

    def get_path_distance(self, target: int) -> float:
        """Return the actual travelled distance in meters to ``target``.

        Returns -1.0 if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return -1.0
        return self._state_info[state][0]


class PathfindingComprehensiveMode:
    """Helper namespace holding the comprehensive mode constant."""

    VALUE = PathfindingConfig.COMPREHENSIVE
