"""Shortest-path computation for the subway network.

Dijkstra's algorithm is run over *states* of the form ``(station, line)``,
where ``line`` is the line used to arrive at the station. This makes transfer
counting exact: a transfer is counted whenever the line of the next edge differs
from the line of the previous edge, so multi-line interchange stations are
handled naturally.

Three query modes are supported:

* ``shortest_distance``: minimize total distance (ties broken by transfers).
* ``least_transfer``: minimize the number of transfers (ties broken by distance).
* ``comprehensive``: minimize a composite score, i.e. distance plus the
  equivalent distance of each transfer (about 5 minutes per transfer at
  1.5 minutes per kilometer).

Labels are compared as tuples. Every component of a label is accumulated
additively along the path, so Dijkstra's algorithm remains correct.
"""

import heapq
import itertools

from fare_calculator import MINUTES_PER_KM, MINUTES_PER_TRANSFER

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# A transfer is penalized by the distance-equivalent of its time cost (meters).
TRANSFER_PENALTY_METERS = MINUTES_PER_TRANSFER / MINUTES_PER_KM * 1000.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: Lines the passenger prefers. Edges on other lines are
            used as a tie-breaker so that preferred lines are favored.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Binary-heap based min priority queue.

    Items with equal keys are served in insertion order, and items are never
    compared directly, which keeps the queue safe for arbitrary payloads.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert ``item`` with priority ``key``. O(log n)."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key. O(log n)."""
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it. O(1)."""
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)


class _Label:
    """Best known information for one search state."""

    __slots__ = ("key", "dist", "transfers", "nonpref", "prev", "edge")

    def __init__(self, key, dist, transfers, nonpref, prev, edge):
        self.key = key
        self.dist = dist
        self.transfers = transfers
        self.nonpref = nonpref
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Dijkstra-based path search from a single source station.

    Args:
        graph: The ``models.Graph`` to search.
        source: Station number of the starting station.
        config: Optional ``PathfindingConfig``; defaults are used if omitted.

    Attributes:
        dist_to: Mapping of reachable station number to the total distance (m)
            of the optimal path found to it.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._preferred = set(self.config.preferred_lines)
        self.dist_to = {}
        self._labels = {}    # state (station, line) -> _Label
        self._settled = {}   # station -> best settled state
        self._run()

    def _make_key(self, dist, transfers, nonpref):
        """Build the comparison key of a label for the configured mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, dist, nonpref)
        if mode == MODE_COMPREHENSIVE:
            return (dist + TRANSFER_PENALTY_METERS * transfers, nonpref)
        return (dist, transfers, nonpref)

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        max_transfers = self.config.max_transfers
        pq = MinPQ()
        start_state = (self.source, None)
        start_label = _Label(self._make_key(0, 0, 0), 0, 0, 0, None, None)
        self._labels[start_state] = start_label
        pq.insert(start_label.key, start_state)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue  # stale queue entry
            settled.add(state)
            label = self._labels[state]
            vertex, current_line = state

            if vertex not in self._settled:
                self._settled[vertex] = state
                self.dist_to[vertex] = label.dist

            for edge in self._graph.adj(vertex):
                next_vertex = edge.other(vertex)
                next_state = (next_vertex, edge.line)
                if next_state in settled:
                    continue

                transfer = 1 if current_line is not None and current_line != edge.line else 0
                transfers = label.transfers + transfer
                if max_transfers is not None and transfers > max_transfers:
                    continue

                dist = label.dist + edge.distance
                nonpref = label.nonpref + (
                    1 if self._preferred and edge.line not in self._preferred else 0
                )
                key = self._make_key(dist, transfers, nonpref)
                existing = self._labels.get(next_state)
                if existing is None or key < existing.key:
                    self._labels[next_state] = _Label(key, dist, transfers, nonpref, state, edge)
                    pq.insert(key, next_state)

    def has_path_to(self, target):
        """Return True if a path from the source to ``target`` exists."""
        return target in self._settled

    def path_with_edges(self, target):
        """Reconstruct the optimal path from the source to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the ordered list of
            station numbers from source to target and ``edges`` is the ordered
            list of ``Edge`` objects traversed. Both lists are empty when the
            target is unreachable.
        """
        state = self._settled.get(target)
        if state is None:
            return [], []
        vertices = []
        edges = []
        while state is not None:
            label = self._labels[state]
            vertices.append(state[0])
            if label.edge is not None:
                edges.append(label.edge)
            state = label.prev
        vertices.reverse()
        edges.reverse()
        return vertices, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the path to ``target``.

        A transfer is counted each time consecutive edges belong to different
        lines. Returns 0 for unreachable targets.
        """
        _, edges = self.path_with_edges(target)
        return sum(1 for prev, nxt in zip(edges, edges[1:]) if prev.line != nxt.line)
