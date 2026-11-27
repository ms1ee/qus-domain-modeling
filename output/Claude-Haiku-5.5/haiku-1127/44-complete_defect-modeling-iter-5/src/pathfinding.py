"""Shortest path computation on the subway graph.

Dijkstra's algorithm is run over states ``(station number, line of last edge)``
so that line transfers can be counted, limited and penalized. A binary-heap
priority queue (``MinPQ``) gives O((V+E) log V) behaviour.

Modes:
    shortest_distance: minimize the total physical distance.
    least_transfer:    minimize the number of transfers, then the distance.
    comprehensive:     minimize distance plus a penalty per transfer.

Line preference: edges that are not on a preferred line receive a soft penalty.
"""

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Cost added per transfer in comprehensive mode (equivalent meters).
TRANSFER_PENALTY_M = 1000.0
# Cost added per transfer in least_transfer mode; dominates any realistic distance.
LEAST_TRANSFER_WEIGHT = 1e7
# Cost added for every edge not on a preferred line.
LINE_PENALTY_M = 500.0


class NoPathError(Exception):
    """Raised when no path exists to the requested station."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class MinPQ:
    """Min priority queue implemented as a binary heap.

    Items are stored as ``(key, item)`` pairs in ``heap``; ``size`` is the number
    of stored pairs. Lower keys are served first.
    """

    def __init__(self):
        self.heap = []
        self.size = 0

    def is_empty(self):
        """Return True if the queue holds no elements."""
        return self.size == 0

    def __len__(self):
        return self.size

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self.heap.append((key, item))
        self.size += 1
        self._swim(self.size - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if self.size == 0:
            raise IndexError("MinPQ is empty")
        return self.heap[0][0]

    def del_min(self):
        """Remove and return the ``(key, item)`` pair with the smallest key."""
        if self.size == 0:
            raise IndexError("MinPQ is empty")
        top = self.heap[0]
        last = self.heap.pop()
        self.size -= 1
        if self.size > 0:
            self.heap[0] = last
            self._sink(0)
        return top

    def _less(self, i, j):
        return self.heap[i][0] < self.heap[j][0]

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
        while True:
            child = 2 * k + 1
            if child >= self.size:
                break
            right = child + 1
            if right < self.size and self._less(right, child):
                child = right
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child


class _Label:
    """Best known label of a search state."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(self, cost, distance, transfers, prev, edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Dijkstra-based shortest path computation from a source station.

    Attributes:
        dist_to: dict station number -> physical distance (meters) of the chosen path.
        cost_to: dict station number -> optimization cost of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.adjacency:
            raise ValueError(f"Source station {source} is not part of the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self.cost_to = {}
        self._labels = {}
        self._settled = {}
        self._run()

    def _edge_cost(self, edge, transferred):
        """Return the optimization cost of traversing ``edge``."""
        mode = self.config.mode
        cost = float(edge.distance)
        if transferred:
            if mode == MODE_LEAST_TRANSFER:
                cost += LEAST_TRANSFER_WEIGHT
            elif mode == MODE_COMPREHENSIVE:
                cost += TRANSFER_PENALTY_M
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += LINE_PENALTY_M
        return cost

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        self._labels[start] = _Label(0.0, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            label = self._labels[state]
            node, line = state

            if node not in self._settled:
                self._settled[node] = state
                self.dist_to[node] = label.distance
                self.cost_to[node] = label.cost

            for edge in self.graph.neighbors(node):
                transferred = line is not None and edge.line != line
                transfers = label.transfers + (1 if transferred else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue
                next_state = (edge.other(node), edge.line)
                if next_state in done:
                    continue
                new_cost = label.cost + self._edge_cost(edge, transferred)
                new_distance = label.distance + edge.distance
                old = self._labels.get(next_state)
                if old is None or new_cost < old.cost:
                    self._labels[next_state] = _Label(
                        new_cost, new_distance, transfers, state, edge
                    )
                    pq.insert(new_cost, next_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._settled

    def path_with_edges(self, target):
        """Reconstruct the path from the source to ``target``.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects traversed in order).

        Raises:
            NoPathError: If the target is unreachable.
        """
        if target not in self._settled:
            raise NoPathError(f"No path to station {target}")
        state = self._settled[target]
        label = self._labels[state]
        nodes = [state[0]]
        edges = []
        while label.prev is not None:
            edges.append(label.edge)
            state = label.prev
            nodes.append(state[0])
            label = self._labels[state]
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the path to ``target``.

        Raises:
            NoPathError: If the target is unreachable.
        """
        if target not in self._settled:
            raise NoPathError(f"No path to station {target}")
        return self._labels[self._settled[target]].transfers
