"""Shortest path computation (Dijkstra's algorithm with a binary-heap priority queue).

The search runs over states (station number, line used to arrive). This makes
transfer counting exact and allows the maximum-transfer limit and line
preferences to be enforced during the search.

Query modes:
    shortest_distance: minimise total distance (ties broken by fewer transfers).
    least_transfer:    minimise transfers (ties broken by distance).
    comprehensive:     minimise distance + TRANSFER_PENALTY_M per transfer.
"""

import heapq
import itertools

SHORTEST_DISTANCE = "shortest_distance"
LEAST_TRANSFER = "least_transfer"
COMPREHENSIVE = "comprehensive"
VALID_MODES = (SHORTEST_DISTANCE, LEAST_TRANSFER, COMPREHENSIVE)

# Equivalent distance cost (meters) of a single transfer in comprehensive mode.
TRANSFER_PENALTY_M = 3000
# Sort-key penalty (meters) for each edge that is not on a preferred line.
PREFERENCE_PENALTY_M = 1500


class NoPathError(Exception):
    """Raised when no path exists between two stations under the given constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names that are preferred.
    """

    def __init__(self, mode=SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self):
        """Validate the configuration.

        Raises:
            ValueError: If the mode, transfer limit or preferred lines are invalid.
        """
        if self.mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if not all(isinstance(line, str) for line in self.preferred_lines):
            raise ValueError("preferred_lines must contain only strings")


class MinPQ:
    """Min priority queue backed by a binary heap.

    Items are stored with their keys; a monotonically increasing sequence number
    breaks ties so that items themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given key in O(log n)."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key in O(log n).

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue underflow")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it (IndexError if empty)."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class _Label:
    """Accumulated values for a search state."""

    __slots__ = ("dist", "transfers", "penalty")

    def __init__(self, dist, transfers, penalty):
        self.dist = dist
        self.transfers = transfers
        self.penalty = penalty


class ShortestPath:
    """Dijkstra shortest path search from a single source station.

    Attributes:
        dist_to: dict mapping reachable station numbers to the travelled distance
            (meters) of their best path.
    """

    def __init__(self, graph, source, config=None):
        """Run the search immediately.

        Args:
            graph: A models.Graph instance.
            source: Source station number.
            config: Optional PathfindingConfig; defaults to shortest distance mode.

        Raises:
            ValueError: If the source is not in the graph or the config is invalid.
        """
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self.dist_to = {}
        self._transfers_to = {}
        self._settled_state = {}
        self._prev = {}
        self._run()

    def _key(self, label):
        """Return the sort key of a label according to the query mode."""
        effective = label.dist + label.penalty
        mode = self.config.mode
        if mode == LEAST_TRANSFER:
            return (label.transfers, effective)
        if mode == COMPREHENSIVE:
            return (effective + label.transfers * TRANSFER_PENALTY_M, label.dist)
        return (effective, label.transfers)

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        start = (self.source, None)
        labels = {start: _Label(0, 0, 0)}
        pq = MinPQ()
        pq.insert(self._key(labels[start]), start)
        settled = set()
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state
            label = labels[state]

            if node not in self._settled_state:
                self._settled_state[node] = state
                self.dist_to[node] = label.dist
                self._transfers_to[node] = label.transfers

            for edge in self.graph.adjacent_edges(node):
                nxt = edge.other(node)
                transfers = label.transfers
                if line is not None and line != edge.line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_M
                new_state = (nxt, edge.line)
                if new_state in settled:
                    continue
                new_label = _Label(label.dist + edge.weight, transfers, penalty)
                new_key = self._key(new_label)
                old = labels.get(new_state)
                if old is None or new_key < self._key(old):
                    labels[new_state] = new_label
                    self._prev[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the configured constraints."""
        return target in self._settled_state

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``.

        Raises:
            NoPathError: If the target is unreachable.
        """
        if target not in self._transfers_to:
            raise NoPathError(f"station {target} is unreachable from {self.source}")
        return self._transfers_to[target]

    def path_with_edges(self, target):
        """Reconstruct the best path to ``target``.

        Returns:
            tuple: (list of station numbers from source to target, list of Edge
            objects traversed in order). The edge list is empty when the target
            equals the source.

        Raises:
            NoPathError: If the target is unreachable.
        """
        if target not in self._settled_state:
            raise NoPathError(f"station {target} is unreachable from {self.source}")
        state = self._settled_state[target]
        nodes = [state[0]]
        edges = []
        while state in self._prev:
            prev_state, edge = self._prev[state]
            edges.append(edge)
            nodes.append(prev_state[0])
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges
