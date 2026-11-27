"""
Path calculation for the Beijing Subway network.

Contains:
    * MinPQ: a binary min-heap priority queue (O(log n) insert / delete-min).
    * PathfindingConfig: query configuration (mode, transfer limit, line preference).
    * ShortestPath: Dijkstra's algorithm over (station, incoming line) states.

Because the cost of entering a station depends on the line we arrive on (a
transfer is counted when the line changes), the search runs over states
``(station_number, line_name)``. This makes transfer counting exact while
keeping the O((V+E) log V) Dijkstra complexity (with V and E scaled by the
number of lines per station, which is small in practice).

Path costs are tuples so that lexicographic priorities can be expressed:

    shortest_distance: (distance, transfers, off_preference)
    least_transfer:    (transfers, distance, off_preference)
    comprehensive:     (distance + PENALTY * transfers, transfers, off_preference)

Every component is non-negative and grows monotonically along a path, so
Dijkstra's algorithm remains correct.
"""
from __future__ import annotations

from models import Edge, Graph, normalize_text

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)


class MinPQ:
    """Binary min-heap priority queue.

    Items are stored with a priority; ``del_min`` removes the item with the
    smallest priority. Priorities only need to support the ``<`` operator.
    """

    def __init__(self, capacity: int = 16) -> None:
        self._capacity = max(1, int(capacity))
        self._heap: list[tuple] = []  # entries are (priority, item)

    @property
    def size(self) -> int:
        """Number of items currently in the queue."""
        return len(self._heap)

    @property
    def capacity(self) -> int:
        """Current capacity; grows (doubling) when the queue becomes full."""
        return self._capacity

    def is_empty(self) -> bool:
        """Return True if the queue contains no items."""
        return not self._heap

    def insert(self, priority, item) -> None:
        """Insert an item with the given priority."""
        self._heap.append((priority, item))
        self._swim(len(self._heap) - 1)
        if len(self._heap) > self._capacity:
            self._capacity *= 2

    def min_priority(self):
        """Return the smallest priority without removing it."""
        self._ensure_not_empty()
        return self._heap[0][0]

    def min_item(self):
        """Return the item with the smallest priority without removing it."""
        self._ensure_not_empty()
        return self._heap[0][1]

    def del_min(self):
        """Remove and return the item with the smallest priority."""
        self._ensure_not_empty()
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[1]

    def _ensure_not_empty(self) -> None:
        if not self._heap:
            raise IndexError("MinPQ is empty")

    def _swim(self, index: int) -> None:
        """Move the entry at ``index`` up until the heap property holds."""
        heap = self._heap
        while index > 0:
            parent = (index - 1) // 2
            if heap[index][0] < heap[parent][0]:
                heap[index], heap[parent] = heap[parent], heap[index]
                index = parent
            else:
                break

    def _sink(self, index: int) -> None:
        """Move the entry at ``index`` down until the heap property holds."""
        heap = self._heap
        size = len(heap)
        while True:
            child = 2 * index + 1
            if child >= size:
                break
            if child + 1 < size and heap[child + 1][0] < heap[child][0]:
                child += 1
            if heap[child][0] < heap[index][0]:
                heap[index], heap[child] = heap[child], heap[index]
                index = child
            else:
                break


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum number of transfers allowed, or None for no limit.
        preferred_lines: Line names preferred by the passenger. Segments on other
            lines are only used to break ties between otherwise equal routes.
    """

    def __init__(self, mode: str = MODE_SHORTEST_DISTANCE, max_transfers: int | None = None,
                 preferred_lines=None) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(line).strip() for line in (preferred_lines or []) if str(line).strip()]


class ShortestPath:
    """Dijkstra-based shortest path search from one source station.

    Attributes:
        algorithm: Name of the algorithm used ("Dijkstra").
        mode: The query mode taken from the configuration.
        dist_to: Mapping from station number to the total distance (meters) of
            the chosen path to that station. Unreachable stations are absent.
    """

    ALGORITHM_NAME = "Dijkstra"
    # Cost in meters added for every transfer in comprehensive mode.
    TRANSFER_PENALTY_M = 1000.0

    def __init__(self, graph: Graph, source: int, config: PathfindingConfig | None = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not part of the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.algorithm = self.ALGORITHM_NAME
        self.mode = self.config.mode
        self.dist_to: dict[int, float] = {}

        self._preferred = {normalize_text(line) for line in self.config.preferred_lines}
        # Per-state bookkeeping; a state is (station_number, line_of_arrival).
        self._cost: dict[tuple, tuple] = {}
        self._dist: dict[tuple, float] = {}
        self._transfers: dict[tuple, int] = {}
        self._offpref: dict[tuple, int] = {}
        self._edge_to: dict[tuple, tuple] = {}
        self._node_state: dict[int, tuple] = {}
        self._transfers_to: dict[int, int] = {}
        self._pq = MinPQ()
        self._run()

    def _cost_of(self, distance: float, transfers: int, off_preference: int) -> tuple:
        """Build the priority tuple for the accumulated path totals."""
        if self.mode == MODE_SHORTEST_DISTANCE:
            return (distance, transfers, off_preference)
        if self.mode == MODE_LEAST_TRANSFER:
            return (transfers, distance, off_preference)
        return (distance + self.TRANSFER_PENALTY_M * transfers, transfers, off_preference)

    def _record(self, state: tuple, distance: float, transfers: int, off: int, cost: tuple) -> None:
        self._cost[state] = cost
        self._dist[state] = distance
        self._transfers[state] = transfers
        self._offpref[state] = off

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over (station, line) states."""
        start = (self.source, None)
        self._record(start, 0.0, 0, 0, self._cost_of(0.0, 0, 0))
        self._pq.insert(self._cost[start], start)
        done: set[tuple] = set()

        while not self._pq.is_empty():
            state = self._pq.del_min()
            if state in done:
                continue  # stale queue entry
            done.add(state)
            node, line_in = state
            base_dist = self._dist[state]
            base_transfers = self._transfers[state]
            base_off = self._offpref[state]

            for edge in self.graph.adjacent(node):
                transfers = base_transfers + (1 if line_in is not None and edge.line != line_in else 0)
                if self.config.max_transfers is not None and transfers > self.config.max_transfers:
                    continue
                distance = base_dist + edge.weight
                off = base_off
                if self._preferred and normalize_text(edge.line) not in self._preferred:
                    off += 1
                next_state = (edge.dest, edge.line)
                if next_state in done:
                    continue
                cost = self._cost_of(distance, transfers, off)
                old = self._cost.get(next_state)
                if old is None or cost < old:
                    self._record(next_state, distance, transfers, off, cost)
                    self._edge_to[next_state] = (state, edge)
                    self._pq.insert(cost, next_state)

        # Pick the best finalised state for every station.
        best: dict[int, tuple] = {}
        for state in done:
            node = state[0]
            if node == self.source:
                continue
            if node not in best or self._cost[state] < self._cost[best[node]]:
                best[node] = state
        start_state = (self.source, None)
        best[self.source] = start_state

        for node, state in best.items():
            self._node_state[node] = state
            self.dist_to[node] = self._dist[state]
            self._transfers_to[node] = self._transfers[state]

    def has_path(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the configured constraints."""
        return target in self._node_state

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Reconstruct the path from the source to ``target``.

        Returns:
            A tuple ``(stations, edges)`` where ``stations`` is the ordered list of
            station numbers (source first, target last) and ``edges`` the ordered
            list of traversed edges. If the target is unreachable, both lists are empty.
        """
        if not self.has_path(target):
            return [], []
        start_state = (self.source, None)
        state = self._node_state[target]
        stations: list[int] = []
        edges: list[Edge] = []
        while state != start_state:
            previous, edge = self._edge_to[state]
            stations.append(state[0])
            edges.append(edge)
            state = previous
        stations.append(self.source)
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the chosen path to ``target``.

        Returns 0 for the source itself and for unreachable stations.
        """
        return self._transfers_to.get(target, 0)
