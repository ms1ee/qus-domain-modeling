"""Shortest-path computation on the subway graph using Dijkstra's algorithm.

Search runs over states (station, incoming line) so that line changes can be
counted as transfers. Three optimisation modes are supported:

* shortest_distance - minimise total distance in meters.
* least_transfer    - minimise transfers first, distance second.
* comprehensive     - minimise distance plus a penalty per transfer.

Line preference is applied as a multiplicative penalty on the distance of
edges that belong to lines other than the preferred ones. The maximum transfer
limit prunes any search branch that exceeds it.
"""
import heapq
import itertools

from errors import PathNotFoundError

SUPPORTED_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Extra cost (in meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 800.0

# Multiplier applied to edges of non-preferred lines when a preference is set.
NON_PREFERRED_LINE_FACTOR = 1.5


class PathfindingConfig:
    """Query configuration for path computation.

    Attributes:
        mode: one of SUPPORTED_MODES.
        max_transfers: maximum allowed transfers, or None for no limit.
        preferred_lines: list of preferred line names (empty = no preference).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in SUPPORTED_MODES:
            raise ValueError("unsupported mode '{}'".format(mode))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def is_preferred_line(self, line):
        """Return True if ``line`` is preferred (or no preference is set)."""
        return not self.preferred_lines or line in self.preferred_lines


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Insertion and removal cost O(log n). A sequence counter breaks ties so
    that items themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert ``item`` with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return the (priority, item) pair with the smallest priority."""
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
        """Return True if the queue holds no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class _Label:
    """Best known information for one search state."""

    __slots__ = ("cost", "weighted", "distance", "transfers", "prev_state", "edge")

    def __init__(self, cost, weighted, distance, transfers, prev_state, edge):
        self.cost = cost              # tuple used for ordering labels
        self.weighted = weighted      # distance including preference penalties
        self.distance = distance      # real travelled distance in meters
        self.transfers = transfers    # number of line changes so far
        self.prev_state = prev_state  # predecessor state, None for the source
        self.edge = edge              # edge used to reach this state


class ShortestPath:
    """Dijkstra-based shortest path computation from a single source station.

    Attributes:
        source: station number of the start station.
        config: PathfindingConfig used for the computation.
        dist_to: dict mapping reachable station numbers to the real travelled
            distance (meters) of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError("unknown source station number {}".format(source))
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._labels = {}        # state (node, line) -> _Label
        self._best_state = {}    # node -> best state reaching it
        self._relax_all()
        self._index_best_states()

    # ------------------------------------------------------------------ #
    # Core algorithm
    # ------------------------------------------------------------------ #
    def _make_cost(self, weighted, transfers):
        """Build the ordering key for a label according to the query mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, weighted)
        if mode == "comprehensive":
            return (weighted + TRANSFER_PENALTY_METERS * transfers,)
        return (weighted,)

    def _relax_all(self):
        """Run Dijkstra's algorithm over (station, line) states."""
        start_state = (self.source, None)
        start_cost = self._make_cost(0.0, 0)
        self._labels[start_state] = _Label(start_cost, 0.0, 0.0, 0, None, None)

        queue = MinPQ()
        queue.insert(start_cost, start_state)
        finalized = set()
        max_transfers = self.config.max_transfers

        while not queue.is_empty():
            _, state = queue.del_min()
            if state in finalized:
                continue
            finalized.add(state)

            node, line = state
            label = self._labels[state]
            for edge in self._graph.adjacent(node):
                next_node = edge.other(node)
                transfers = label.transfers
                if line is not None and line != edge.line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue

                factor = 1.0
                if not self.config.is_preferred_line(edge.line):
                    factor = NON_PREFERRED_LINE_FACTOR
                weighted = label.weighted + edge.distance * factor
                distance = label.distance + edge.distance

                new_state = (next_node, edge.line)
                if new_state in finalized:
                    continue
                cost = self._make_cost(weighted, transfers)
                current = self._labels.get(new_state)
                if current is None or cost < current.cost:
                    self._labels[new_state] = _Label(
                        cost, weighted, distance, transfers, state, edge
                    )
                    queue.insert(cost, new_state)

    def _index_best_states(self):
        """Select the best state for every reached station and fill dist_to."""
        for state in self._labels:
            node = state[0]
            current = self._best_state.get(node)
            if current is None or self._labels[state].cost < self._labels[current].cost:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._labels[state].distance

    # ------------------------------------------------------------------ #
    # Public query API
    # ------------------------------------------------------------------ #
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the configured limits."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the path from the source to ``target``.

        Returns:
            (stations, edges): ``stations`` is the list of station numbers from
            source to target (inclusive); ``edges`` is the list of Edge objects
            traversed between consecutive stations. Both are empty if the
            target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        nodes = []
        edges = []
        state = self._best_state[target]
        while True:
            label = self._labels[state]
            nodes.append(state[0])
            if label.prev_state is None:
                break
            edges.append(label.edge)
            state = label.prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the path to ``target``.

        Returns:
            int transfer count, or -1 if the target is unreachable.
        """
        if not self.has_path_to(target):
            return -1
        return self._labels[self._best_state[target]].transfers

    def require_path_to(self, target):
        """Raise PathNotFoundError if ``target`` is unreachable."""
        if not self.has_path_to(target):
            raise PathNotFoundError("no path found to station number {}".format(target))
