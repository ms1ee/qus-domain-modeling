"""Shortest path computation (Dijkstra with an indexed binary-heap priority queue)."""
from __future__ import annotations

from typing import Dict, Hashable, List, Optional, Tuple

from models import Edge, Graph


class MinPQ:
    """Indexed binary min-heap priority queue.

    Items are hashable keys; each item appears at most once and its priority
    can be decreased in O(log n). Operations are O(log n), which yields the
    O((V+E) log V) Dijkstra complexity.
    """

    def __init__(self, capacity: int = 16) -> None:
        self.capacity = max(1, int(capacity))
        self._heap: List[list] = []  # entries: [priority, item]
        self._index: Dict[Hashable, int] = {}

    @property
    def size(self) -> int:
        """Number of items currently stored."""
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True when the queue holds no items."""
        return not self._heap

    def contains(self, item: Hashable) -> bool:
        """Return True if the item is currently in the queue."""
        return item in self._index

    def priority_of(self, item: Hashable) -> float:
        """Return the current priority of an item."""
        return self._heap[self._index[item]][0]

    def insert(self, item: Hashable, priority: float) -> None:
        """Insert a new item with the given priority."""
        if item in self._index:
            raise KeyError(f"item {item!r} is already in the queue")
        self._heap.append([priority, item])
        self._index[item] = len(self._heap) - 1
        self._sift_up(len(self._heap) - 1)

    def decrease_key(self, item: Hashable, priority: float) -> None:
        """Lower the priority of an item already in the queue."""
        i = self._index[item]
        if priority > self._heap[i][0]:
            raise ValueError("new priority is greater than the current priority")
        self._heap[i][0] = priority
        self._sift_up(i)

    def min(self) -> Tuple[Hashable, float]:
        """Return (item, priority) with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][1], self._heap[0][0]

    def del_min(self) -> Tuple[Hashable, float]:
        """Remove and return (item, priority) with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        del self._index[top[1]]
        if self._heap:
            self._heap[0] = last
            self._index[last[1]] = 0
            self._sift_down(0)
        return top[1], top[0]

    def _swap(self, i: int, j: int) -> None:
        h = self._heap
        h[i], h[j] = h[j], h[i]
        self._index[h[i][1]] = i
        self._index[h[j][1]] = j

    def _sift_up(self, k: int) -> None:
        while k > 0:
            parent = (k - 1) // 2
            if self._heap[k][0] < self._heap[parent][0]:
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
            if left < n and self._heap[left][0] < self._heap[smallest][0]:
                smallest = left
            if right < n and self._heap[right][0] < self._heap[smallest][0]:
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: Lines preferred by the passenger; using other lines is penalized.
    """

    MODES = ("shortest_distance", "least_transfer", "comprehensive")

    def __init__(
        self,
        mode: str = "shortest_distance",
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        if mode not in self.MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {self.MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])


# Extra cost (in meters-equivalent) added for each transfer, per mode.
TRANSFER_PENALTY = {
    "shortest_distance": 0.0,
    "least_transfer": 1_000_000.0,
    "comprehensive": 1_000.0,
}
# Extra cost for riding a line that is not in the preference list.
PREFERENCE_PENALTY = 2_000.0
# Hard limit on transfers when no max_transfers is configured (guarantees termination).
DEFAULT_TRANSFER_CAP = 10

# Search state: (station number, line of the last edge or None, transfers so far).
State = Tuple[int, Optional[str], int]


class ShortestPath:
    """Dijkstra's shortest path computation from a single source station.

    The search runs over states that also remember the current line and the number
    of transfers, so transfer penalties and transfer limits can be applied correctly.
    ``dist_to`` reports, for each station, the actual travelled distance (meters)
    of the best state found at that station.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"source station number {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._best_state: Dict[int, State] = {}
        self._parent: Dict[State, Tuple[State, Edge]] = {}
        self._run()

    def _run(self) -> None:
        """Execute Dijkstra's algorithm with the indexed priority queue."""
        penalty = TRANSFER_PENALTY[self.config.mode]
        cap = self.config.max_transfers
        if cap is None:
            cap = DEFAULT_TRANSFER_CAP
        preferred = set(self.config.preferred_lines)

        start: State = (self.source, None, 0)
        cost: Dict[State, float] = {start: 0.0}
        dist: Dict[State, float] = {start: 0.0}
        done = set()

        pq = MinPQ(self.graph.vertex_count)
        pq.insert(start, 0.0)
        while not pq.is_empty():
            state, _ = pq.del_min()
            done.add(state)
            station, line, transfers = state

            if station not in self.dist_to:
                self.dist_to[station] = dist[state]
                self._best_state[station] = state

            current_cost = cost[state]
            for edge in self.graph.adjacent(station):
                nxt = edge.other(station)
                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + (1 if is_transfer else 0)
                if new_transfers > cap:
                    continue
                new_state: State = (nxt, edge.line, new_transfers)
                if new_state in done:
                    continue

                step = edge.distance
                if is_transfer:
                    step += penalty
                if preferred and edge.line not in preferred:
                    step += PREFERENCE_PENALTY
                new_cost = current_cost + step

                old_cost = cost.get(new_state)
                if old_cost is None or new_cost < old_cost:
                    cost[new_state] = new_cost
                    dist[new_state] = dist[state] + edge.distance
                    self._parent[new_state] = (state, edge)
                    if pq.contains(new_state):
                        pq.decrease_key(new_state, new_cost)
                    else:
                        pq.insert(new_state, new_cost)

    def has_path(self, target: int) -> bool:
        """Return True if the target station is reachable from the source."""
        return target in self._best_state

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Reconstruct the path to ``target``.

        Returns:
            (station numbers from source to target, edges between consecutive stations).
            Both lists are empty if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = [state[0]]
        edges: List[Edge] = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            stations.append(prev[0])
            state = prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes along the path to ``target``."""
        _, edges = self.path_with_edges(target)
        return sum(1 for prev, nxt in zip(edges, edges[1:]) if prev.line != nxt.line)
