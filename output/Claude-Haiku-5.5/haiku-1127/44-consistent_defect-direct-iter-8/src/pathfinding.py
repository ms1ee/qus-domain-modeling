"""Path search over the subway graph using Dijkstra's algorithm.

Three optimisation modes are supported:

* ``shortest_distance``: minimise the total distance in meters.
* ``least_transfer``: minimise the number of transfers, then the distance.
* ``comprehensive``: minimise a composite score, distance plus a penalty of
  ``TRANSFER_PENALTY_METERS`` per transfer (5 minutes of travel time is
  roughly 3.3 km at 1.5 minutes per kilometre).

The search runs over states ``(station number, line of the last edge)`` so
that line changes (transfers) can be counted and constrained correctly.
"""

from min_pq import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY_METERS = 3333.0
PREFERENCE_PENALTY_METERS = 200.0
TRANSFER_LEXICO_WEIGHT = 1e9
INFINITY = float("inf")


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: Lines the passenger prefers. Edges on other lines are
            penalised softly (they are still usable).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def validate(self):
        """Check the configuration and return self.

        Raises:
            ValueError: If the mode is unknown or max_transfers is negative.
        """
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unknown path mode '{self.mode}'; expected one of {VALID_MODES}")
        if self.max_transfers is not None:
            if not isinstance(self.max_transfers, int) or isinstance(self.max_transfers, bool):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        return self


class _Label:
    """Best known information about a search state."""

    __slots__ = ("key", "distance", "transfers", "prev", "edge")

    def __init__(self, key, distance, transfers, prev, edge):
        self.key = key              # search cost (mode dependent)
        self.distance = distance    # real accumulated distance in meters
        self.transfers = transfers  # accumulated transfer count
        self.prev = prev            # previous state, or None for the source
        self.edge = edge            # edge used to reach this state


class ShortestPath:
    """Single-source shortest path computation.

    The search is executed on construction.

    Attributes:
        dist_to: Mapping station number -> real distance in meters of the best
            path from the source. Unreachable stations are absent.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = (config or PathfindingConfig()).validate()
        self.dist_to = {}
        self._labels = {}        # state -> _Label
        self._best_state = {}    # station number -> best state reaching it
        self._run()

    # ------------------------------------------------------------------ search
    def _step_cost(self, edge, transfer_here):
        """Search cost added when traversing ``edge``."""
        cost = float(edge.distance)
        mode = self.config.mode
        if mode == "least_transfer":
            cost += transfer_here * TRANSFER_LEXICO_WEIGHT
        elif mode == "comprehensive":
            cost += transfer_here * TRANSFER_PENALTY_METERS
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            cost += PREFERENCE_PENALTY_METERS
        return cost

    def _run(self):
        """Dijkstra's algorithm using a heap-based MinPQ."""
        if not self.graph.has_vertex(self.source):
            return

        max_transfers = self.config.max_transfers
        start_state = (self.source, None)
        self._labels[start_state] = _Label(0.0, 0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start_state)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            label = self._labels[state]
            vertex, last_line = state
            for edge in self.graph.adjacent(vertex):
                transfer_here = 1 if (last_line is not None and edge.line != last_line) else 0
                new_transfers = label.transfers + transfer_here
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                next_state = (edge.dest, edge.line)
                if next_state in settled:
                    continue

                new_key = label.key + self._step_cost(edge, transfer_here)
                existing = self._labels.get(next_state)
                if existing is None or new_key < existing.key:
                    self._labels[next_state] = _Label(
                        new_key,
                        label.distance + edge.distance,
                        new_transfers,
                        state,
                        edge,
                    )
                    pq.insert(new_key, next_state)

        # Pick the best state for every reachable station.
        for state, label in self._labels.items():
            vertex = state[0]
            current = self._best_state.get(vertex)
            if current is None or label.key < self._labels[current].key:
                self._best_state[vertex] = state
        for vertex, state in self._best_state.items():
            self.dist_to[vertex] = self._labels[state].distance

    # ----------------------------------------------------------------- queries
    def has_path_to(self, target) -> bool:
        """Return True if ``target`` is reachable under the current constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the distance in meters to ``target`` (inf if unreachable)."""
        return self.dist_to.get(target, INFINITY)

    def path_with_edges(self, target):
        """Backtrack the optimal path to ``target``.

        Returns:
            A tuple ``(stations, edges)``. ``stations`` lists station numbers
            from the target back to the source (backtracking order, i.e. the
            order in which the path is generated), and ``edges`` lists the
            corresponding edges in the same order. For an unreachable target
            both lists are empty.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations = []
        edges = []
        while True:
            label = self._labels[state]
            stations.append(state[0])
            if label.prev is None:
                break
            edges.append(label.edge)
            state = label.prev
        return stations, edges

    def get_transfer_count(self, target) -> int:
        """Return the number of line changes on the path to ``target``."""
        _, edges = self.path_with_edges(target)
        return sum(1 for first, second in zip(edges, edges[1:]) if first.line != second.line)
