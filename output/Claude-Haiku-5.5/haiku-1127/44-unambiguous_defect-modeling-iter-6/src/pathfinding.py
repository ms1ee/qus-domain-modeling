"""Shortest-path computation on the subway graph.

Dijkstra's algorithm runs over states ``(station, arriving_line)`` so that
line changes (transfers) can be counted and constrained. A priority queue
(``MinPQ``, a binary heap with decrease-key) gives O((V+E) log V) behaviour
for the number of states involved.
"""

from typing import Any, Dict, Hashable, List, Optional, Set, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for every transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 1500.0
# Extra cost (meters) charged for riding a line that is not preferred.
PREFERENCE_PENALTY_METERS = 2000.0

State = Tuple[int, Optional[str]]


class PathNotFoundError(Exception):
    """Raised when no path satisfying the constraints exists."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum number of line changes allowed (None = unlimited).
        preferred_lines: lines that are preferred (other lines are penalised).
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])


class MinPQ:
    """Indexed binary min-heap with decrease-key.

    Items are hashable objects, each stored at most once. ``capacity`` is an
    optional upper bound on the number of items held simultaneously.
    """

    def __init__(self, capacity: Optional[int] = None) -> None:
        if capacity is not None and capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._heap: List[Hashable] = []
        self._keys: Dict[Hashable, Any] = {}
        self._index: Dict[Hashable, int] = {}

    @property
    def size(self) -> int:
        """Number of items currently in the queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def contains(self, item: Hashable) -> bool:
        """Return True if ``item`` is currently queued."""
        return item in self._index

    def insert(self, item: Hashable, key: Any) -> None:
        """Insert a new item with the given priority key."""
        if item in self._index:
            raise ValueError("Item is already in the priority queue")
        if self.capacity is not None and len(self._heap) >= self.capacity:
            raise OverflowError("Priority queue capacity exceeded")
        self._keys[item] = key
        self._heap.append(item)
        self._index[item] = len(self._heap) - 1
        self._sift_up(len(self._heap) - 1)

    def decrease_key(self, item: Hashable, key: Any) -> None:
        """Lower the priority key of a queued item."""
        if item not in self._index:
            raise KeyError("Item is not in the priority queue")
        if not key < self._keys[item]:
            raise ValueError("New key must be smaller than the current key")
        self._keys[item] = key
        self._sift_up(self._index[item])

    def min_item(self) -> Hashable:
        """Return the item with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._heap[0]

    def min_key(self) -> Any:
        """Return the smallest key in the queue."""
        return self._keys[self.min_item()]

    def del_min(self) -> Hashable:
        """Remove and return the item with the smallest key."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        del self._index[top]
        del self._keys[top]
        if self._heap:
            self._heap[0] = last
            self._index[last] = 0
            self._sift_down(0)
        return top

    def _less(self, i: int, j: int) -> bool:
        return self._keys[self._heap[i]] < self._keys[self._heap[j]]

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._index[self._heap[i]] = i
        self._index[self._heap[j]] = j

    def _sift_up(self, k: int) -> None:
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sift_down(self, k: int) -> None:
        n = len(self._heap)
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


class _Label:
    """Best known label of a search state."""

    __slots__ = ("key", "cost", "dist", "transfers", "prev_state", "prev_edge")

    def __init__(self, key, cost, dist, transfers, prev_state, prev_edge) -> None:
        self.key = key
        self.cost = cost
        self.dist = dist
        self.transfers = transfers
        self.prev_state = prev_state
        self.prev_edge = prev_edge


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    Attributes:
        source: source station number.
        config: the PathfindingConfig used.
        dist_to: station number -> real travelled distance (meters) of the
            best path found to that station (reachable stations only).
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise KeyError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._labels: Dict[State, _Label] = {}
        self._final: Dict[int, State] = {}
        self._run()

    def _key(self, cost: float, transfers: int):
        """Priority key of a label according to the query mode."""
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return cost
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, cost)
        return cost + TRANSFER_PENALTY_METERS * transfers

    def _run(self) -> None:
        graph = self.graph
        config = self.config
        preferred: Set[str] = set(config.preferred_lines)
        capacity = max(1, graph.vertex_count * (len(graph.lines()) + 1))
        queue = MinPQ(capacity)

        start: State = (self.source, None)
        start_label = _Label(self._key(0.0, 0), 0.0, 0.0, 0, None, None)
        self._labels[start] = start_label
        queue.insert(start, start_label.key)
        settled: Set[State] = set()

        while not queue.is_empty():
            state = queue.del_min()
            settled.add(state)
            label = self._labels[state]
            station, arriving_line = state
            if station not in self._final:
                self._final[station] = state

            for edge in graph.adjacent(station):
                neighbour = edge.other_end(station)
                next_state: State = (neighbour, edge.line)
                if next_state in settled:
                    continue
                transfer = 1 if (arriving_line is not None and edge.line != arriving_line) else 0
                new_transfers = label.transfers + transfer
                if config.max_transfers is not None and new_transfers > config.max_transfers:
                    continue
                penalty = PREFERENCE_PENALTY_METERS if preferred and edge.line not in preferred else 0.0
                new_cost = label.cost + edge.distance + penalty
                new_key = self._key(new_cost, new_transfers)
                existing = self._labels.get(next_state)
                if existing is None:
                    self._labels[next_state] = _Label(
                        new_key, new_cost, label.dist + edge.distance,
                        new_transfers, state, edge,
                    )
                    queue.insert(next_state, new_key)
                elif new_key < existing.key:
                    existing.key = new_key
                    existing.cost = new_cost
                    existing.dist = label.dist + edge.distance
                    existing.transfers = new_transfers
                    existing.prev_state = state
                    existing.prev_edge = edge
                    queue.decrease_key(next_state, new_key)

        for station, state in self._final.items():
            self.dist_to[station] = self._labels[state].dist

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the constraints."""
        return target in self._final

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the station sequence and edge sequence from source to target.

        Raises:
            PathNotFoundError: if the target cannot be reached.
        """
        state = self._final.get(target)
        if state is None:
            raise PathNotFoundError("No path found between the given stations")
        stations: List[int] = []
        edges: List[Edge] = []
        current: Optional[State] = state
        while current is not None:
            label = self._labels[current]
            stations.append(current[0])
            if label.prev_edge is not None:
                edges.append(label.prev_edge)
            current = label.prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the path to ``target``.

        Raises:
            PathNotFoundError: if the target cannot be reached.
        """
        state = self._final.get(target)
        if state is None:
            raise PathNotFoundError("No path found between the given stations")
        return self._labels[state].transfers
