"""Path calculation: priority queue, path configuration and Dijkstra's algorithm.

Dijkstra's algorithm is run over states (station number, arrival line). This makes
transfer counting exact: a transfer happens whenever consecutive edges belong to
different lines. Priority queue operations are O(log V), giving an overall
complexity of O((V + E) log V) for the search.
"""

import heapq
import itertools


VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance (meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 3000
# Equivalent distance (meters) added for each edge that is not on a preferred line.
PREFERRED_LINE_PENALTY_M = 1000


class MinPQ:
    """Min priority queue implemented on top of a binary heap (heapq)."""

    def __init__(self):
        self._heap = []
        self._seq = itertools.count()  # tie-breaker so items are never compared

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._seq), item))

    def del_min(self):
        """Remove and return the item with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return heapq.heappop(self._heap)[2]

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
            - "shortest_distance": minimise total distance.
            - "least_transfer": minimise transfers, then distance.
            - "comprehensive": minimise distance + TRANSFER_PENALTY_M * transfers.
        max_transfers: maximum allowed transfers, or None for no limit.
        preferred_lines: list of preferred line names; edges on other lines
            receive PREFERRED_LINE_PENALTY_M as an extra cost (soft preference).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}'. Choose from {VALID_MODES}")
        if max_transfers is not None and (not isinstance(max_transfers, int) or max_transfers < 0):
            raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class _Label:
    """Best known label for a search state."""

    __slots__ = ("key", "distance", "penalty", "transfers", "prev", "edge")

    def __init__(self, key, distance, penalty, transfers, prev, edge):
        self.key = key  # comparable score used by the priority queue
        self.distance = distance  # real travelled distance (meters)
        self.penalty = penalty  # accumulated preference penalty
        self.transfers = transfers  # number of line changes so far
        self.prev = prev  # previous state, or None for the source
        self.edge = edge  # edge used to reach this state


class ShortestPath:
    """Dijkstra-based optimal path computation from a single source station.

    Attributes:
        dist_to: station number -> real distance (meters) of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._labels = {}  # state (node, line) -> _Label
        self._best = {}  # node -> first (optimal) settled state
        self._run()

    def _score(self, distance, penalty, transfers):
        """Compute the comparable priority of a label according to the mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, distance + penalty)
        if mode == "comprehensive":
            return (distance + penalty + TRANSFER_PENALTY_M * transfers, transfers)
        return (distance + penalty, transfers)

    def _preference_penalty(self, line):
        """Return the soft penalty for travelling on ``line``."""
        preferred = self.config.preferred_lines
        if preferred and line not in preferred:
            return PREFERRED_LINE_PENALTY_M
        return 0

    def _run(self):
        """Run Dijkstra's algorithm over (station, line) states."""
        max_transfers = self.config.max_transfers
        start_state = (self.source, None)
        start_label = _Label(self._score(0, 0, 0), 0, 0, 0, None, None)
        self._labels[start_state] = start_label

        pq = MinPQ()
        pq.insert(start_label.key, start_state)
        settled = set()

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line = state
            label = self._labels[state]
            if node not in self._best:
                self._best[node] = state
                self.dist_to[node] = label.distance

            for edge in self.graph.neighbors(node):
                nxt = edge.other(node)
                step = 1 if (line is not None and edge.line != line) else 0
                transfers = label.transfers + step
                if max_transfers is not None and transfers > max_transfers:
                    continue
                distance = label.distance + edge.weight
                penalty = label.penalty + self._preference_penalty(edge.line)
                key = self._score(distance, penalty, transfers)

                next_state = (nxt, edge.line)
                if next_state in settled:
                    continue
                existing = self._labels.get(next_state)
                if existing is not None and existing.key <= key:
                    continue
                self._labels[next_state] = _Label(key, distance, penalty, transfers, state, edge)
                pq.insert(key, next_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best

    def path_with_edges(self, target):
        """Return the path to ``target`` as (station numbers, edges).

        The station list starts at the source and ends at the target. The edge
        list has one fewer element. Returns ([], []) if the target is unreachable.
        """
        state = self._best.get(target)
        if state is None:
            return [], []
        stations = []
        edges = []
        current = state
        while True:
            label = self._labels[current]
            stations.append(current[0])
            if label.prev is None:
                break
            edges.append(label.edge)
            current = label.prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target`` (0 if unreachable)."""
        state = self._best.get(target)
        if state is None:
            return 0
        return self._labels[state].transfers
