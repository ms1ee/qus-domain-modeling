"""
Path-finding algorithms for the subway network.

Provides:
  * MinPQ            - binary-heap based min priority queue.
  * PathfindingConfig - query mode, transfer limit and line preferences.
  * ShortestPath     - Dijkstra's algorithm over (station, line) states, so that
                       transfers can be counted and optimised correctly.

Query modes:
  * shortest_distance - minimise total distance (meters).
  * least_transfer    - minimise transfers first, then distance.
  * comprehensive     - minimise a weighted score combining distance, transfer
                        penalty and line-preference penalty.
"""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in equivalent meters) added for every transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 800.0
# Penalty (in equivalent meters) added for every edge outside preferred lines.
NON_PREFERRED_LINE_PENALTY_METERS = 300.0


def _norm_line(line):
    """Normalise a line name for case-insensitive comparison."""
    return " ".join(str(line).split()).lower()


class MinPQ:
    """
    Min priority queue implemented on top of a binary heap.

    Insertion and removal are O(log n). A monotonically increasing counter is
    used as a tie-breaker so that items with equal keys never get compared.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    @property
    def size(self):
        """Number of items in the queue."""
        return len(self._heap)

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def insert(self, key, item):
        """Insert ``item`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def del_min(self):
        """Remove and return a ``(key, item)`` pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item


class PathfindingConfig:
    """
    Configuration for a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode="comprehensive", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(x).strip() for x in (preferred_lines or [])
                                if str(x).strip()]

    def validate(self):
        """
        Validate the configuration.

        Returns:
            PathfindingConfig: self, for chaining.

        Raises:
            ValueError: If the mode or the transfer limit is invalid.
        """
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Unsupported mode '{self.mode}', expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if (isinstance(self.max_transfers, bool)
                    or not isinstance(self.max_transfers, int)
                    or self.max_transfers < 0):
                raise ValueError("max_transfers must be a non-negative integer")
        return self

    def is_preferred(self, line):
        """Return True if ``line`` is preferred (always True when no preference is set)."""
        if not self.preferred_lines:
            return True
        if line is None:
            return False
        target = _norm_line(line)
        return any(_norm_line(p) == target for p in self.preferred_lines)


class _Label:
    """Best-known label of a search state (station, line)."""

    __slots__ = ("cost", "distance", "transfers", "nonpref", "prev", "edge")

    def __init__(self, cost, distance, transfers, nonpref, prev, edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.nonpref = nonpref
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """
    Dijkstra-based optimal path computation from a single source station.

    The search runs over states ``(station number, line of arriving edge)`` so
    that a change of line can be detected and counted as a transfer. Priority
    queue operations give the O((V+E) log V) complexity required by the PRD.

    Attributes:
        graph: The Graph being searched.
        source: Source station number.
        config: PathfindingConfig used for this search.
        dist_to: dict mapping station number -> total distance (meters) of the
                 best path found from the source.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = (config or PathfindingConfig()).validate()
        self.dist_to = {}
        self._labels = {}
        self._best = {}
        self._transfers = {}
        self._run()

    # ----------------------------------------------------------------- cost
    def _cost(self, distance, transfers, nonpref):
        """Compute the comparable cost key for the configured mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, distance, nonpref)
        if mode == "comprehensive":
            return (distance
                    + TRANSFER_PENALTY_METERS * transfers
                    + NON_PREFERRED_LINE_PENALTY_METERS * nonpref,)
        return (distance, nonpref)

    # ------------------------------------------------------------- search
    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        cfg = self.config
        start_state = (self.source, None)
        start_cost = self._cost(0.0, 0, 0)
        self._labels[start_state] = _Label(start_cost, 0.0, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(start_cost, start_state)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line = state
            label = self._labels[state]

            for edge in self.graph.adjacent(node):
                nxt = edge.other(node)
                is_transfer = line is not None and edge.line != line
                transfers = label.transfers + (1 if is_transfer else 0)
                if cfg.max_transfers is not None and transfers > cfg.max_transfers:
                    continue
                distance = label.distance + edge.weight
                nonpref = label.nonpref + (0 if cfg.is_preferred(edge.line) else 1)

                new_state = (nxt, edge.line)
                if new_state in settled:
                    continue
                cost = self._cost(distance, transfers, nonpref)
                old = self._labels.get(new_state)
                if old is not None and old.cost <= cost:
                    continue
                self._labels[new_state] = _Label(cost, distance, transfers,
                                                 nonpref, state, edge)
                pq.insert(cost, new_state)

        # Pick the best settled state for every station.
        for state in settled:
            node = state[0]
            label = self._labels[state]
            best_state = self._best.get(node)
            if best_state is None or label.cost < self._labels[best_state].cost:
                self._best[node] = state

        for node, state in self._best.items():
            label = self._labels[state]
            self.dist_to[node] = label.distance
            self._transfers[node] = label.transfers

    # ------------------------------------------------------------ queries
    def has_path_to(self, target):
        """Return True if ``target`` is reachable within the configured limits."""
        return target in self._best

    def distance_to(self, target):
        """Return the path distance in meters to ``target`` (raises KeyError if unreachable)."""
        return self.dist_to[target]

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``."""
        return self._transfers.get(target, 0)

    def path_with_edges(self, target):
        """
        Reconstruct the path from the source to ``target``.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects traversed in the same order).
            If ``target`` is unreachable, returns ([], []).
        """
        state = self._best.get(target)
        if state is None:
            return [], []
        nodes = []
        edges = []
        while state is not None:
            label = self._labels[state]
            nodes.append(state[0])
            if label.edge is not None:
                edges.append(label.edge)
            state = label.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges
