"""Path calculation for the subway network.

Implements Dijkstra's shortest path algorithm on the directed subway graph.
The search state is (station, arriving line) so that line changes (transfers)
are counted exactly. Three query modes are supported:

    shortest_distance : minimise total distance (meters)
    least_transfer    : minimise number of transfers, then distance
    comprehensive     : minimise distance + TRANSFER_PENALTY_METERS * transfers

If preferred lines are configured, every segment operated by a non-preferred
line adds PREFERRED_LINE_PENALTY_METERS to the search cost (the reported
distance is unaffected).
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite score weight: one transfer is worth roughly 3 km of travel
# (about 5 minutes of extra time at 1.5 min/km, scaled to a distance penalty).
TRANSFER_PENALTY_METERS = 3000.0
# Extra search cost for each segment operated by a non-preferred line.
PREFERRED_LINE_PENALTY_METERS = 500.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for unlimited.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown path mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min priority queue implemented on top of a binary heap.

    Items with equal keys are served in insertion order; items are never compared.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return (key, item) with the smallest key."""
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class _SearchState:
    """A label in the Dijkstra search: a station reached while arriving on a given line."""

    __slots__ = ("node", "line", "distance", "penalty", "transfers", "parent", "edge")

    def __init__(self, node, line, distance, penalty, transfers, parent, edge):
        self.node = node            # station number
        self.line = line            # line of the last edge (None at the source)
        self.distance = distance    # accumulated real distance in meters
        self.penalty = penalty      # accumulated preference penalty (search cost only)
        self.transfers = transfers  # accumulated transfer count
        self.parent = parent        # previous _SearchState or None
        self.edge = edge            # Edge used to arrive here, or None at the source


class ShortestPath:
    """Dijkstra-based shortest path computation from a single source station.

    Args:
        graph: models.Graph instance.
        source: Station number of the starting station.
        config: PathfindingConfig (defaults to shortest-distance, no limits).

    Attributes:
        dist_to: dict mapping reachable station number -> real distance in meters
            of the best path found to it.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.adjacency:
            raise ValueError(f"Unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._best = {}
        self._search()

    def _make_key(self, distance, transfers, penalty):
        """Build the priority key for a search state according to the query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            return distance + penalty + transfers * TRANSFER_PENALTY_METERS
        return distance + penalty

    def _search(self):
        """Run Dijkstra's algorithm over (station, line) states."""
        cfg = self.config
        max_transfers = cfg.max_transfers
        preferred = set(cfg.preferred_lines)

        start = _SearchState(self.source, None, 0.0, 0.0, 0, None, None)
        pq = MinPQ()
        pq.insert(self._make_key(0.0, 0, 0.0), start)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            state_id = (state.node, state.line)
            if state_id in settled:
                continue
            settled.add(state_id)

            # The first settled state of a station is its best label.
            if state.node not in self._best:
                self._best[state.node] = state
                self.dist_to[state.node] = state.distance

            for edge in self.graph.neighbors(state.node):
                transfers = state.transfers
                if state.line is not None and edge.line != state.line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                if (edge.dest, edge.line) in settled:
                    continue

                penalty = state.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERRED_LINE_PENALTY_METERS

                distance = state.distance + edge.weight
                key = self._make_key(distance, transfers, penalty)
                next_state = _SearchState(edge.dest, edge.line, distance, penalty,
                                          transfers, state, edge)
                pq.insert(key, next_state)

    def is_reachable(self, target):
        """Return True if the target station can be reached under the configuration."""
        return target in self._best

    def path_with_edges(self, target):
        """Reconstruct the path from the source to the target by backtracking.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects along the path).
            If the target is unreachable, returns ([], []).
        """
        state = self._best.get(target)
        if state is None:
            return [], []
        nodes = []
        edges = []
        current = state
        while current is not None:
            nodes.append(current.node)
            if current.edge is not None:
                edges.append(current.edge)
            current = current.parent
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the best path to the target (0 if unreachable)."""
        state = self._best.get(target)
        return state.transfers if state is not None else 0
