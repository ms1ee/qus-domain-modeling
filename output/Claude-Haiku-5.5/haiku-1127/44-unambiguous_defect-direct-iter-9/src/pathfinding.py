"""Shortest path computation with Dijkstra's algorithm.

The search runs over states ``(station_number, arrival_line)`` so that line
changes (transfers) can be counted and constrained exactly. Three query modes
are supported:

* ``shortest_distance``  - minimise the physical distance.
* ``least_transfer``     - minimise the number of transfers, then distance.
* ``comprehensive``      - distance plus a penalty per transfer.

``preferred_lines`` adds a soft penalty to edges that do not belong to the
preferred lines, and ``max_transfers`` prunes any route that exceeds the limit.
"""

from priority_queue import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

MODE_LABELS = {
    MODE_SHORTEST_DISTANCE: "Shortest distance",
    MODE_LEAST_TRANSFER: "Minimum transfers",
    MODE_COMPREHENSIVE: "Comprehensive optimal",
}

#: Equivalent distance (meters) added for every transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000.0
#: Cost added per transfer in least-transfer mode (dominates distance).
LEAST_TRANSFER_WEIGHT = 1.0e9
#: Penalty (meters) added for every edge outside the preferred lines.
LINE_PREFERENCE_PENALTY_M = 500.0


class PathfindingError(Exception):
    """Raised for invalid pathfinding requests."""


class PathNotFoundError(PathfindingError):
    """Raised when no path satisfies the given constraints."""


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum number of allowed transfers, or None (no limit).
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(
                f"unsupported mode {mode!r}; expected one of {', '.join(VALID_MODES)}"
            )
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        if preferred_lines is None:
            preferred = []
        elif isinstance(preferred_lines, str):
            preferred = [preferred_lines]
        else:
            preferred = list(preferred_lines)
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = preferred

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class _StateInfo:
    """Best known information for one ``(station, line)`` search state."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(self, cost, distance, transfers, prev, edge):
        self.cost = cost            # objective value used by the priority queue
        self.distance = distance    # real travelled distance in meters
        self.transfers = transfers  # number of transfers so far
        self.prev = prev            # predecessor state (or None for the source)
        self.edge = edge            # edge used to reach this state (or None)


class ShortestPath:
    """Single-source shortest path search over a :class:`models.Graph`.

    Attributes:
        dist_to: dict mapping reachable station number -> real distance (m)
            of the best route found to it.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise PathfindingError(f"station number {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}   # station number -> its best finalized state
        self._states = {}       # state -> _StateInfo
        self._run()

    # ----- cost model --------------------------------------------------------
    def _step_cost(self, distance, is_transfer, line):
        """Objective increment for traversing one edge."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            cost = distance + (LEAST_TRANSFER_WEIGHT if is_transfer else 0.0)
        elif mode == MODE_COMPREHENSIVE:
            cost = distance + (TRANSFER_PENALTY_M if is_transfer else 0.0)
        else:
            cost = float(distance)
        preferred = self.config.preferred_lines
        if preferred and line not in preferred:
            cost += LINE_PREFERENCE_PENALTY_M
        return cost

    # ----- Dijkstra ----------------------------------------------------------
    def _run(self):
        """Execute Dijkstra's algorithm with a priority queue.

        Complexity: O((V + E) log V) for a fixed number of lines per station.
        """
        start = (self.source, None)
        self._states[start] = _StateInfo(0.0, 0, 0, None, None)
        pq = MinPQ()
        pq.insert(0.0, start)
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            cost, state = pq.del_min()
            info = self._states[state]
            if cost > info.cost:
                continue  # stale queue entry
            node, line = state
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = info.distance

            for edge, neighbor in self.graph.neighbors(node):
                is_transfer = line is not None and edge.line != line
                transfers = info.transfers + (1 if is_transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue
                distance = info.distance + edge.distance
                new_cost = info.cost + self._step_cost(edge.distance, is_transfer, edge.line)
                next_state = (neighbor, edge.line)
                existing = self._states.get(next_state)
                if existing is None or new_cost < existing.cost:
                    self._states[next_state] = _StateInfo(
                        new_cost, distance, transfers, state, edge
                    )
                    pq.insert(new_cost, next_state)

    # ----- queries -----------------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current constraints."""
        return target in self._best_state

    def _require_path(self, target):
        if not self.graph.has_vertex(target):
            raise PathfindingError(f"station number {target!r} is not in the graph")
        if target not in self._best_state:
            raise PathNotFoundError(f"no path from {self.source!r} to {target!r}")
        return self._best_state[target]

    def path_with_edges(self, target):
        """Backtrack the route from the source to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the ordered list of
            station numbers (source first, target last) and ``edges`` the ordered
            list of :class:`models.Edge` objects traversed (``len(stations) - 1``
            items).

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        state = self._require_path(target)
        nodes = []
        edges = []
        while state is not None:
            info = self._states[state]
            nodes.append(state[0])
            if info.edge is not None:
                edges.append(info.edge)
            state = info.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best route to ``target``."""
        state = self._require_path(target)
        return self._states[state].transfers

    def get_distance(self, target):
        """Return the real distance (meters) of the best route to ``target``."""
        self._require_path(target)
        return self.dist_to[target]
