"""Path calculation: Dijkstra's shortest path search over the subway network.

The search runs over states (station, line-of-last-segment). This lets the
algorithm account for transfers: changing from one line to another at a
station costs one transfer. Three query modes are supported:

* shortest_distance - minimize the total distance;
* least_transfer    - minimize the number of transfers, then the distance;
* comprehensive     - minimize distance plus a penalty per transfer.

A line preference reduces the effective cost of segments on preferred lines,
and an optional maximum transfer limit prunes routes with too many transfers.
Dijkstra uses the priority queue MinPQ, giving O((V + E) log V) behaviour.
"""

from min_pq import MinPQ

# Effective cost multiplier applied to segments of preferred lines.
PREFERRED_LINE_FACTOR = 0.8

# Equivalent distance penalty (meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 800.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names that should be preferred.
    """

    MODE_SHORTEST_DISTANCE = "shortest_distance"
    MODE_LEAST_TRANSFER = "least_transfer"
    MODE_COMPREHENSIVE = "comprehensive"
    MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines:
            self.preferred_lines = [str(line).strip() for line in preferred_lines if str(line).strip()]
        else:
            self.preferred_lines = []
        self.validate()

    def validate(self):
        """Check the configuration values.

        Raises:
            ValueError: If the mode is unknown or max_transfers is invalid.
        """
        if self.mode not in self.MODES:
            raise ValueError(
                f"unknown path mode '{self.mode}', expected one of: {', '.join(self.MODES)}"
            )
        if self.max_transfers is not None:
            if (
                isinstance(self.max_transfers, bool)
                or not isinstance(self.max_transfers, int)
                or self.max_transfers < 0
            ):
                raise ValueError("max_transfers must be a non-negative integer or None")

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class ShortestPath:
    """Single-source shortest path computation with Dijkstra's algorithm.

    Attributes:
        source: Station number the search starts from.
        dist_to: dict station number -> real travelled distance in meters on
            the chosen route to that station (only reachable stations appear).
        config: The PathfindingConfig in use.
    """

    def __init__(self, graph, source, config=None):
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self._preferred = set(self.config.preferred_lines)
        self.dist_to = {}
        self._best_state = {}   # station number -> best (station, line) state
        self._parent = {}       # state -> (previous state, edge) or None for the source
        self._run()

    # ----- cost model ---------------------------------------------------

    def _adjusted_distance(self, edge):
        """Distance used for path comparison, reduced on preferred lines."""
        if edge.line in self._preferred:
            return edge.distance * PREFERRED_LINE_FACTOR
        return float(edge.distance)

    def _cost(self, transfers, adjusted):
        """Build the comparable cost tuple of a state according to the mode."""
        mode = self.config.mode
        if mode == PathfindingConfig.MODE_LEAST_TRANSFER:
            return (transfers, adjusted)
        if mode == PathfindingConfig.MODE_COMPREHENSIVE:
            return (adjusted + TRANSFER_PENALTY_M * transfers, adjusted)
        return (adjusted, transfers)

    # ----- Dijkstra search ----------------------------------------------

    def _run(self):
        """Run Dijkstra's algorithm over (station, line) states."""
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        info = {start: (0, 0, 0.0)}          # state -> (transfers, real m, adjusted m)
        best = {start: self._cost(0, 0.0)}   # state -> best known cost tuple
        self._parent[start] = None

        pq = MinPQ()
        pq.insert(best[start], start)
        done = set()

        while not pq.is_empty():
            _cost, state = pq.del_min()
            if state in done:
                continue
            done.add(state)

            vertex, line = state
            transfers, real, adjusted = info[state]
            # States are settled in non-decreasing cost order, so the first
            # settled state of a station is its best state.
            if vertex not in self.dist_to:
                self.dist_to[vertex] = real
                self._best_state[vertex] = state

            for edge in self._graph.adj(vertex):
                nxt = edge.other(vertex)
                next_state = (nxt, edge.line)
                if next_state in done:
                    continue
                new_transfers = transfers + (1 if line is not None and line != edge.line else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_real = real + edge.distance
                new_adjusted = adjusted + self._adjusted_distance(edge)
                new_cost = self._cost(new_transfers, new_adjusted)
                if next_state not in best or new_cost < best[next_state]:
                    best[next_state] = new_cost
                    info[next_state] = (new_transfers, new_real, new_adjusted)
                    self._parent[next_state] = (state, edge)
                    pq.insert(new_cost, next_state)

    # ----- results ------------------------------------------------------

    def has_path(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the travelled distance (meters) to ``target``, or None if unreachable."""
        return self.dist_to.get(target)

    def path_with_edges(self, target):
        """Return the route to ``target`` as (station numbers, edges).

        The station list starts with the source and ends with the target;
        the edge list has one entry fewer and holds the segments in order.
        If the target is unreachable, ([], []) is returned.
        """
        if target not in self._best_state:
            return [], []
        nodes = []
        edges = []
        cur = self._best_state[target]
        while True:
            nodes.append(cur[0])
            link = self._parent.get(cur)
            if link is None:
                break
            prev, edge = link
            edges.append(edge)
            cur = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the route to ``target``.

        Returns 0 if the target is unreachable or equals the source.
        """
        _nodes, edges = self.path_with_edges(target)
        transfers = 0
        for previous, current in zip(edges, edges[1:]):
            if previous.line != current.line:
                transfers += 1
        return transfers
