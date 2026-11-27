"""Shortest-path computation on the subway graph using Dijkstra's algorithm.

The search runs over states ``(station number, current line, transfers so far)``
so that the number of line changes can be bounded (``max_transfers``) and
minimised (``least_transfer`` mode). The priority queue is a binary heap
implemented by ``MinPQ``, giving O((V + E) log V) behaviour.
"""

from __future__ import annotations

from errors import PathNotFoundError
from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

DEFAULT_MAX_TRANSFERS = 10

# Extra cost (in meters-equivalent) charged per line change.
TRANSFER_WEIGHT_LEAST = 10_000_000.0  # dominates distance: minimise transfers first
TRANSFER_PENALTY_COMPREHENSIVE = 1000.0  # balances distance against transfer inconvenience
# Extra cost charged for each segment that is not on a preferred line.
LINE_PREFERENCE_PENALTY = 500.0


class PathfindingConfig:
    """User-selected options for a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum number of line changes allowed, or ``None`` for no limit.
        preferred_lines: Lines the passenger prefers to ride.
    """

    def __init__(
        self,
        mode: str = MODE_COMPREHENSIVE,
        max_transfers: int | None = DEFAULT_MAX_TRANSFERS,
        preferred_lines: list[str] | None = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}', choose from {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: list[str] = list(preferred_lines or [])


class MinPQ:
    """Binary min-heap priority queue.

    Entries are ``(priority, sequence, item)`` so that ties are broken by
    insertion order and items never need to be comparable.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, object]] = []
        self._sequence = 0

    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def insert(self, item: object, priority: float) -> None:
        """Add an item with the given priority."""
        self._heap.append((priority, self._sequence, item))
        self._sequence += 1
        self._swim(len(self._heap) - 1)

    def min(self) -> object:
        """Return the item with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][2]

    def del_min(self) -> object:
        """Remove and return the item with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[2]

    def _less(self, i: int, j: int) -> bool:
        a = self._heap[i]
        b = self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k: int) -> None:
        """Move the element at index ``k`` up until the heap property holds."""
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._swap(k, parent)
            k = parent

    def _sink(self, k: int) -> None:
        """Move the element at index ``k`` down until the heap property holds."""
        n = len(self._heap)
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


class ShortestPath:
    """Dijkstra search from a source station over a ``Graph``.

    Attributes:
        graph: The network being searched.
        source: Station number of the origin.
        config: The ``PathfindingConfig`` used for this search.
        mode: Convenience copy of ``config.mode``.
        dist_to: Mapping of reachable station number -> real travelled distance (meters)
            along the chosen path to that station.
    """

    def __init__(self, graph: Graph, source: int, config: PathfindingConfig | None = None) -> None:
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.mode = self.config.mode
        self.dist_to: dict[int, float] = {}
        self._cost: dict[tuple, float] = {}
        self._real: dict[tuple, float] = {}
        self._edge_to: dict[tuple, tuple[tuple, Edge]] = {}
        self._best: dict[int, tuple] = {}
        self._run()

    def _edge_cost(self, edge: Edge, transfer_flag: int) -> float:
        """Return the search cost of traversing ``edge`` under the configured mode."""
        cost = edge.weight
        if self.mode == MODE_LEAST_TRANSFER:
            cost += transfer_flag * TRANSFER_WEIGHT_LEAST
        elif self.mode == MODE_COMPREHENSIVE:
            cost += transfer_flag * TRANSFER_PENALTY_COMPREHENSIVE
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += LINE_PREFERENCE_PENALTY
        return cost

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line, transfers) states."""
        start = (self.source, None, 0)
        self._cost[start] = 0.0
        self._real[start] = 0.0
        pq = MinPQ()
        pq.insert(start, 0.0)
        settled: set[tuple] = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, transfers = state

            for edge in self.graph.adjacent(node):
                flag = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + flag
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                neighbour = edge.other(node)
                next_state = (neighbour, edge.line, new_transfers)
                if next_state in settled:
                    continue
                new_cost = self._cost[state] + self._edge_cost(edge, flag)
                if next_state not in self._cost or new_cost < self._cost[next_state]:
                    self._cost[next_state] = new_cost
                    self._real[next_state] = self._real[state] + edge.weight
                    self._edge_to[next_state] = (state, edge)
                    pq.insert(next_state, new_cost)

        # Pick the cheapest state for each reachable station.
        for state, cost in self._cost.items():
            node = state[0]
            current = self._best.get(node)
            if current is None or cost < self._cost[current]:
                self._best[node] = state
        for node, state in self._best.items():
            self.dist_to[node] = self._real[state]

    def has_path(self, target: int) -> bool:
        """Return True if ``target`` is reachable from the source."""
        return target in self._best

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Reconstruct the path from the source to ``target``.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` lists station numbers
            from source to target and ``edges`` lists the traversed edges in order.
            ``len(edges) == len(stations) - 1``.

        Raises:
            PathNotFoundError: If the target is unreachable within the constraints.
        """
        state = self._best.get(target)
        if state is None:
            raise PathNotFoundError("no route found between the two stations within the transfer limit")
        nodes = [target]
        edges: list[Edge] = []
        while state in self._edge_to:
            previous, edge = self._edge_to[state]
            edges.append(edge)
            nodes.append(previous[0])
            state = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes along the path to ``target``.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        _, edges = self.path_with_edges(target)
        count = 0
        for previous, current in zip(edges, edges[1:]):
            if previous.line != current.line:
                count += 1
        return count
