"""Shortest-path computation on the subway graph.

The search runs Dijkstra's algorithm over states ``(station, line, transfers)``
so that line changes (transfers) at interchange stations are handled exactly.
A binary-heap priority queue (``MinPQ``) gives O((V+E) log V) behaviour.
"""

import heapq
import itertools

from src.models import Edge, Graph  # noqa: F401  (Edge kept for type reference)

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite score: every transfer is treated as this many meters of extra cost.
TRANSFER_PENALTY_METERS = 1500.0
# Soft line preference: edges outside the preferred lines cost this much extra.
LINE_PREFERENCE_PENALTY_METERS = 500.0


class PathfindingConfig:
    """Query configuration.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: list of preferred line names (soft preference).
    """

    def __init__(self, mode: str = MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: list[str] = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min priority queue implemented with a binary heap (``heapq``).

    Items with equal keys are served in insertion order; items themselves are
    never compared.
    """

    def __init__(self):
        self._heap: list = []
        self._counter = itertools.count()

    def insert(self, key, item) -> None:
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def is_empty(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class _Label:
    """A search state reached during Dijkstra's algorithm."""

    __slots__ = ("node", "line", "transfers", "cost", "distance", "prev", "edge")

    def __init__(self, node, line, transfers, cost, distance, prev, edge):
        self.node = node              # station number
        self.line = line              # line of the last edge (None at source)
        self.transfers = transfers    # transfers used so far
        self.cost = cost              # accumulated cost incl. penalties (meters)
        self.distance = distance      # true accumulated distance (meters)
        self.prev = prev              # previous label (for path backtracking)
        self.edge = edge              # edge used to reach this label


class ShortestPath:
    """Single-source shortest path search.

    Attributes:
        source: source station number.
        dist_to: station number -> true travelled distance (meters) of the
            best route found to that station.
    """

    def __init__(self, graph: Graph, source: int, config: PathfindingConfig = None):
        if not graph.has_node(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self._graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to: dict[int, float] = {}
        self._best: dict[int, _Label] = {}
        self._run()

    # ----- algorithm --------------------------------------------------------
    def _priority(self, label: _Label) -> tuple:
        """Priority tuple (smaller is better) according to the query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (label.transfers, label.cost)
        if mode == MODE_COMPREHENSIVE:
            return (label.cost + label.transfers * TRANSFER_PENALTY_METERS,)
        return (label.cost,)

    def _run(self) -> None:
        prefs = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start = _Label(self.source, None, 0, 0.0, 0.0, None, None)
        pq = MinPQ()
        best_priority = {(self.source, None, 0): self._priority(start)}
        pq.insert(best_priority[(self.source, None, 0)], start)
        settled = set()

        while not pq.is_empty():
            _, label = pq.del_min()
            state = (label.node, label.line, label.transfers)
            if state in settled:
                continue
            settled.add(state)

            # The first settled label of a station is its optimal label.
            if label.node not in self._best:
                self._best[label.node] = label
                self.dist_to[label.node] = label.distance

            for edge in self._graph.adjacent(label.node):
                nxt = edge.other(label.node)
                transfers = label.transfers
                if label.line is not None and edge.line != label.line:
                    transfers += 1  # line change at this station = transfer
                if max_transfers is not None and transfers > max_transfers:
                    continue
                penalty = LINE_PREFERENCE_PENALTY_METERS if (prefs and edge.line not in prefs) else 0.0
                new_label = _Label(
                    nxt,
                    edge.line,
                    transfers,
                    label.cost + edge.weight + penalty,
                    label.distance + edge.weight,
                    label,
                    edge,
                )
                new_state = (nxt, edge.line, transfers)
                if new_state in settled:
                    continue
                prio = self._priority(new_label)
                old = best_priority.get(new_state)
                if old is not None and old <= prio:
                    continue
                best_priority[new_state] = prio
                pq.insert(prio, new_label)

    # ----- queries ----------------------------------------------------------
    def has_path(self, target: int) -> bool:
        """True if ``target`` is reachable under the current constraints."""
        return target in self._best

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Return ``(station_numbers, edges)`` from source to target.

        Returns ``([], [])`` if the target is unreachable.
        """
        label = self._best.get(target)
        if label is None:
            return [], []
        nodes: list[int] = []
        edges: list[Edge] = []
        current = label
        while current is not None:
            nodes.append(current.node)
            if current.edge is not None:
                edges.append(current.edge)
            current = current.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Number of transfers on the best route to ``target`` (0 if unreachable)."""
        label = self._best.get(target)
        return label.transfers if label is not None else 0
