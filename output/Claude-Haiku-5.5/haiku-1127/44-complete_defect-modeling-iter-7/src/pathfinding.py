"""Shortest path computation: priority queue, path configuration and Dijkstra search."""

from __future__ import annotations

from typing import Any, Optional

from .models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Default maximum number of line changes allowed in a route.
DEFAULT_MAX_TRANSFERS = 10
# Cost (in meters-equivalent) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000.0
# Cost added for each edge not served by a preferred line.
PREFERENCE_PENALTY_M = 500.0

# A search state: (station number, line the traveller is currently on, transfers so far).
State = tuple[int, Optional[str], int]


class NoPathError(Exception):
    """Raised when no route satisfying the constraints exists."""


class MinPQ:
    """Binary min-heap priority queue (O(log n) insert and delete-min).

    Items with equal priority are served in insertion order. Priorities may be
    any mutually comparable values (numbers or tuples).
    """

    def __init__(self) -> None:
        self._heap: list[tuple[Any, int, Any]] = []
        self._seq = 0

    @property
    def size(self) -> int:
        """Number of items currently in the queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def insert(self, item: Any, priority: Any) -> None:
        """Insert ``item`` with the given priority."""
        self._heap.append((priority, self._seq, item))
        self._seq += 1
        self._sift_up(len(self._heap) - 1)

    def min_item(self) -> Any:
        """Return the item with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][2]

    def del_min(self) -> Any:
        """Remove and return the item with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top[2]

    def _less(self, i: int, j: int) -> bool:
        """Compare heap entries by (priority, insertion sequence)."""
        a, b = self._heap[i], self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self._less(index, parent):
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index: int) -> None:
        size = len(self._heap)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and self._less(left, smallest):
                smallest = left
            if right < size and self._less(right, smallest):
                smallest = right
            if smallest == index:
                break
            self._swap(index, smallest)
            index = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: maximum number of line changes allowed.
        preferred_lines: lines favoured by the search (other lines carry a penalty).
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: int = DEFAULT_MAX_TRANSFERS,
        preferred_lines: Optional[list[str]] = None,
    ) -> None:
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: list[str] = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self) -> None:
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{self.mode}', expected one of {VALID_MODES}")
        if (
            isinstance(self.max_transfers, bool)
            or not isinstance(self.max_transfers, int)
            or self.max_transfers < 0
        ):
            raise ValueError("max_transfers must be a non-negative integer")


def _cost(mode: str, distance: float, transfers: int, penalty: float) -> tuple:
    """Compute the priority tuple of a search state according to the query mode."""
    if mode == MODE_LEAST_TRANSFER:
        return (transfers, distance + penalty)
    if mode == MODE_COMPREHENSIVE:
        return (distance + penalty + transfers * TRANSFER_PENALTY_M,)
    return (distance + penalty,)


class ShortestPath:
    """Dijkstra shortest path search over the subway graph.

    The search runs over states (station, current line, transfers so far) so that
    line changes at multi-line interchange stations and the transfer limit are
    handled exactly. Priorities are kept in a binary-heap MinPQ, giving
    O((V+E) log V) behaviour for the bounded state space.

    Attributes:
        dist_to: physical distance in meters from the source to each reachable station,
            along the route chosen by the query mode.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.algorithm = "Dijkstra"
        self.dist_to: dict[int, float] = {}
        self._cost: dict[State, tuple] = {}
        self._dist: dict[State, float] = {}
        self._pen: dict[State, float] = {}
        self._parent: dict[State, Optional[tuple[State, Edge]]] = {}
        self._best: dict[int, State] = {}
        self._run()

    def _run(self) -> None:
        """Execute Dijkstra's algorithm over the state space."""
        mode = self.config.mode
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        start: State = (self.source, None, 0)
        zero = _cost(mode, 0.0, 0, 0.0)
        self._cost[start] = zero
        self._dist[start] = 0.0
        self._pen[start] = 0.0
        self._parent[start] = None

        pq = MinPQ()
        pq.insert(start, zero)
        settled: set[State] = set()

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, transfers = state
            # The first settled state of a station is its optimal one.
            if node not in self._best:
                self._best[node] = state

            dist = self._dist[state]
            pen = self._pen[state]
            for edge in self.graph.adjacent(node):
                nxt_node = edge.other(node)
                new_transfers = transfers + (1 if line is not None and edge.line != line else 0)
                if new_transfers > max_transfers:
                    continue
                nxt: State = (nxt_node, edge.line, new_transfers)
                if nxt in settled:
                    continue
                new_dist = dist + edge.weight
                new_pen = pen + (PREFERENCE_PENALTY_M if preferred and edge.line not in preferred else 0.0)
                cost = _cost(mode, new_dist, new_transfers, new_pen)
                old = self._cost.get(nxt)
                if old is None or cost < old:
                    self._cost[nxt] = cost
                    self._dist[nxt] = new_dist
                    self._pen[nxt] = new_pen
                    self._parent[nxt] = (state, edge)
                    pq.insert(nxt, cost)

        self.dist_to = {node: self._dist[state] for node, state in self._best.items()}

    def _state_for(self, target: int) -> State:
        """Return the optimal search state of ``target``.

        Raises:
            NoPathError: if the target cannot be reached under the constraints.
        """
        if target not in self._best:
            raise NoPathError(f"no route found to station {target} within the given constraints")
        return self._best[target]

    def has_path(self, target: int) -> bool:
        """Return True if ``target`` is reachable under the query constraints."""
        return target in self._best

    def distance_to(self, target: int) -> float:
        """Return the physical distance in meters to ``target``."""
        return self._dist[self._state_for(target)]

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Reconstruct the path from the source to ``target``.

        Returns:
            A tuple (station numbers in order from source to target, edges in the same order).

        Raises:
            NoPathError: if the target is unreachable.
        """
        state = self._state_for(target)
        stations: list[int] = []
        edges: list[Edge] = []
        while True:
            stations.append(state[0])
            parent = self._parent[state]
            if parent is None:
                break
            prev_state, edge = parent
            edges.append(edge)
            state = prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the route to ``target``.

        Raises:
            NoPathError: if the target is unreachable.
        """
        return self._state_for(target)[2]
