"""Shortest path computation based on Dijkstra's algorithm.

The search runs over states ``(station number, line of incoming edge)`` so
that line changes (transfers) can be counted and constrained. The cost of a
path depends on the selected mode:

* ``shortest_distance``: total distance in meters.
* ``least_transfer``: number of transfers first, distance second.
* ``comprehensive``: distance plus a fixed penalty per transfer.

Line preferences add a penalty to edges that are not on a preferred line.
Priority queue operations use the heap-based ``MinPQ`` class.
"""

import heapq
import itertools

SHORTEST_DISTANCE = "shortest_distance"
LEAST_TRANSFER = "least_transfer"
COMPREHENSIVE = "comprehensive"
VALID_MODES = (SHORTEST_DISTANCE, LEAST_TRANSFER, COMPREHENSIVE)

# Composite-score constants (in meter-equivalents)
TRANSFER_PENALTY_METERS = 3000          # one transfer ~ 3 km (about 5 minutes)
LEAST_TRANSFER_WEIGHT = 10 ** 9         # dominates distance for least_transfer mode
LINE_PREFERENCE_PENALTY_METERS = 500    # penalty for edges off the preferred lines


def _normalize_line(name):
    """Normalize a line name for case-insensitive comparison."""
    return str(name).strip().lower()


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}'; choose from {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def is_preferred(self, line):
        """Return True if the line is acceptable under the preference settings."""
        if not self.preferred_lines:
            return True
        wanted = {_normalize_line(p) for p in self.preferred_lines}
        return _normalize_line(line) in wanted


class MinPQ:
    """Min priority queue implemented on top of a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class _Label:
    """Best known label for a search state."""

    __slots__ = ("cost", "meters", "transfers", "prev_key", "prev_edge")

    def __init__(self, cost, meters, transfers, prev_key, prev_edge):
        self.cost = cost
        self.meters = meters
        self.transfers = transfers
        self.prev_key = prev_key
        self.prev_edge = prev_edge


class ShortestPath:
    """Single-source shortest path computation.

    Args:
        graph: A ``models.Graph`` instance.
        source: Station number of the origin.
        config: Optional ``PathfindingConfig``; defaults to shortest distance.

    Attributes:
        dist_to: Mapping station number -> distance in meters of the chosen
            path from the source (only reachable stations are present).
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._labels = {}      # (vertex, line) -> _Label
        self._best_key = {}    # vertex -> (vertex, line) of its best label
        self._run()

    # ----- cost model --------------------------------------------------------
    def _step_cost(self, edge, transfer):
        """Cost added when traversing ``edge``."""
        cost = edge.weight
        if not self.config.is_preferred(edge.line):
            cost += LINE_PREFERENCE_PENALTY_METERS
        if transfer:
            mode = self.config.mode
            if mode == LEAST_TRANSFER:
                cost += LEAST_TRANSFER_WEIGHT
            elif mode == COMPREHENSIVE:
                cost += TRANSFER_PENALTY_METERS
        return cost

    # ----- Dijkstra ----------------------------------------------------------
    def _run(self):
        source_key = (self.source, None)
        self._labels[source_key] = _Label(0, 0, 0, None, None)
        self._best_key[self.source] = source_key

        pq = MinPQ()
        pq.insert(0, source_key)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, key = pq.del_min()
            if key in settled:
                continue
            settled.add(key)

            vertex, last_line = key
            label = self._labels[key]

            for edge in self.graph.adj(vertex):
                transfer = last_line is not None and edge.line != last_line
                transfers = label.transfers + (1 if transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue

                new_key = (edge.dest, edge.line)
                if new_key in settled:
                    continue

                new_cost = label.cost + self._step_cost(edge, transfer)
                existing = self._labels.get(new_key)
                if existing is not None and new_cost >= existing.cost:
                    continue

                self._labels[new_key] = _Label(
                    new_cost, label.meters + edge.weight, transfers, key, edge
                )
                pq.insert(new_cost, new_key)

                best = self._best_key.get(edge.dest)
                if best is None or best == new_key or new_cost < self._labels[best].cost:
                    self._best_key[edge.dest] = new_key

        for vertex, key in self._best_key.items():
            self.dist_to[vertex] = self._labels[key].meters

    # ----- public queries ----------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_key

    def path_with_edges(self, target):
        """Return the path to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the list of
            station numbers from the source to the target and ``edges`` is the
            list of ``Edge`` objects traversed. Both are empty if unreachable.
        """
        if target not in self._best_key:
            return [], []
        key = self._best_key[target]
        stations = []
        edges = []
        while key is not None:
            label = self._labels[key]
            stations.append(key[0])
            if label.prev_edge is not None:
                edges.append(label.prev_edge)
            key = label.prev_key
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target`` (0 if unreachable)."""
        if target not in self._best_key:
            return 0
        return self._labels[self._best_key[target]].transfers
