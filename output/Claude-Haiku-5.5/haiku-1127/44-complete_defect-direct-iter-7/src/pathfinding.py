"""Shortest path computation using Dijkstra's algorithm with a binary-heap priority queue.

The search runs over states (station, line of arrival edge, transfers so far), which
allows enforcing a maximum transfer limit and computing the number of line changes
along the chosen path. Complexity is O((V+E) log V) for an unconstrained search,
multiplied by the (small) number of transfer levels when a transfer limit is applied.
"""

from min_pq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Transfer cap used by the search when no maximum transfer limit is configured.
DEFAULT_TRANSFER_CAP = 10
# Extra search cost (in meters-equivalent) for riding a line not in the preference list.
PREFERENCE_PENALTY = 1000.0
# Extra search cost per transfer in comprehensive mode (meters-equivalent).
COMPREHENSIVE_TRANSFER_PENALTY = 500.0
# Very large cost per transfer in least_transfer mode, so transfers dominate distance.
LEAST_TRANSFER_WEIGHT = 1e9


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: one of MODES
        max_transfers: maximum allowed number of transfers, or None for no explicit limit
        preferred_lines: list of preferred line names (may be empty)
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        preferred = list(preferred_lines) if preferred_lines else []
        if not all(isinstance(line, str) for line in preferred):
            raise ValueError("preferred_lines must be a list of strings")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = preferred

    def transfer_limit(self):
        """Return the effective transfer cap used during the search."""
        if self.max_transfers is None:
            return DEFAULT_TRANSFER_CAP
        return self.max_transfers

    def step_cost(self, edge, is_transfer):
        """Return the search cost of traversing ``edge``.

        The search cost is only used to order the search; reported distances are
        always the real inter-station distances in meters.
        """
        cost = float(edge.weight)
        if self.preferred_lines and edge.line not in self.preferred_lines:
            cost += PREFERENCE_PENALTY
        if is_transfer:
            if self.mode == MODE_COMPREHENSIVE:
                cost += COMPREHENSIVE_TRANSFER_PENALTY
            elif self.mode == MODE_LEAST_TRANSFER:
                cost += LEAST_TRANSFER_WEIGHT
        return cost

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Single-source shortest path computation.

    Attributes:
        dist_to: dict station number -> real distance (meters) of the chosen path
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Source station number {source} is not in the graph")
        self._graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self.cost_to = {}
        self._best_state = {}   # station number -> best state key reaching it
        self._state_info = {}   # state -> (search cost, real distance, parent state, edge)
        self._run()

    def _run(self):
        limit = self.config.transfer_limit()
        start = (self.source, None, 0)
        self._state_info[start] = (0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        settled = set()

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line, transfers = state
            _, distance, _, _ = self._state_info[state]

            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = distance
                self.cost_to[node] = cost

            for edge in self._graph.adjacent(node):
                nxt = edge.other(node)
                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + (1 if is_transfer else 0)
                if new_transfers > limit:
                    continue
                new_state = (nxt, edge.line, new_transfers)
                if new_state in settled:
                    continue
                new_cost = cost + self.config.step_cost(edge, is_transfer)
                new_distance = distance + edge.distance
                old = self._state_info.get(new_state)
                if old is None or new_cost < old[0]:
                    self._state_info[new_state] = (new_cost, new_distance, state, edge)
                    pq.insert(new_cost, new_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return (stations, edges) of the shortest path from source to target.

        ``stations`` is the ordered list of station numbers from source to target;
        ``edges`` is the ordered list of Edge objects between consecutive stations.
        If the target is unreachable, ``([], [])`` is returned.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while state is not None:
            _, _, parent, edge = self._state_info[state]
            stations.append(state[0])
            if edge is not None:
                edges.append(edge)
            state = parent
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes along the path to ``target``."""
        _, edges = self.path_with_edges(target)
        count = 0
        for previous, current in zip(edges, edges[1:]):
            if previous.line != current.line:
                count += 1
        return count
