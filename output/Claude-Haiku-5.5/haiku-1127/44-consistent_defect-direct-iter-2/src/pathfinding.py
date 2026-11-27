"""Dijkstra-based path search over the subway graph.

Search states are (station number, line of the arriving edge). Tracking the
arriving line lets the search count line changes (transfers) exactly and
apply transfer penalties, and enforce the maximum transfer limit.

Modes:
    shortest_distance: minimise the total distance in meters.
    least_transfer:    minimise the number of transfers, distance as tie-breaker.
    comprehensive:     minimise distance plus a time-equivalent penalty per transfer.

Line preference: edges on lines not listed in preferred_lines receive a
penalty, so preferred lines are used whenever they do not cost much more.
"""

from min_pq import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Roughly 5 minutes of travel time expressed in meters (1.5 min per km).
TRANSFER_PENALTY_M = 3333.0
# Dominant weight used in least_transfer mode so transfers outweigh distance.
LEAST_TRANSFER_WEIGHT = 1.0e9
# Penalty applied to an edge that is not on a preferred line.
LINE_PREFERENCE_PENALTY_M = 500.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: list of preferred line names (may be empty).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class _Record:
    """Best known information about one search state."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(self, cost, distance, transfers, prev, edge):
        self.cost = cost            # weighted cost used for ordering
        self.distance = distance    # real travelled distance in meters
        self.transfers = transfers  # number of line changes so far
        self.prev = prev            # previous search state key
        self.edge = edge            # edge used to reach this state


class ShortestPath:
    """Single-source shortest path computation using Dijkstra's algorithm.

    Attributes:
        dist_to: dict station number -> travelled distance (meters) of the
            chosen best path to that station. Unreachable stations are absent.
    """

    def __init__(self, graph, source, config=None):
        """
        Args:
            graph: models.Graph instance.
            source: station number of the starting station.
            config: PathfindingConfig, defaults to shortest distance without limits.

        Raises:
            ValueError: if the source station is not in the graph.
        """
        if not graph.has_node(source):
            raise ValueError(f"unknown source station number: {source}")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._records = {}   # search state -> _Record
        self._chosen = {}    # station number -> best search state reaching it
        self._run()

    # ----- core algorithm -----
    def _edge_cost(self, edge, transfer):
        """Compute the weighted cost of traversing an edge."""
        cfg = self.config
        cost = edge.weight
        if cfg.mode == "least_transfer":
            if transfer:
                cost += LEAST_TRANSFER_WEIGHT
        elif cfg.mode == "comprehensive":
            if transfer:
                cost += TRANSFER_PENALTY_M
        if cfg.preferred_lines and edge.line not in cfg.preferred_lines:
            cost += LINE_PREFERENCE_PENALTY_M
        return cost

    def _run(self):
        """Run Dijkstra's algorithm over (station, line) search states."""
        start = (self.source, None)
        records = self._records
        records[start] = _Record(0.0, 0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state
            rec = records[state]

            for edge in self._graph.edges_from(node):
                transfer = line is not None and edge.line != line
                transfers = rec.transfers + (1 if transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue
                new_state = (edge.dest, edge.line)
                if new_state in settled:
                    continue
                new_cost = rec.cost + self._edge_cost(edge, transfer)
                old = records.get(new_state)
                if old is None or new_cost < old.cost:
                    records[new_state] = _Record(
                        new_cost, rec.distance + edge.weight, transfers, state, edge
                    )
                    pq.insert(new_cost, new_state)

        # Choose the cheapest search state for every reachable station.
        for state, rec in records.items():
            node = state[0]
            current = self._chosen.get(node)
            if current is None or rec.cost < records[current].cost:
                self._chosen[node] = state
        for node, state in self._chosen.items():
            self.dist_to[node] = records[state].distance

    # ----- public query API -----
    def has_path_to(self, target):
        """Return True if the target station is reachable from the source."""
        return target in self._chosen

    def path_with_edges(self, target):
        """Return the path to target as (station numbers, edges).

        The station list runs from the source to the target and contains one
        more element than the edge list. Unreachable targets yield ([], []).
        """
        state = self._chosen.get(target)
        if state is None:
            return [], []
        nodes = []
        edges = []
        while state is not None:
            rec = self._records[state]
            nodes.append(state[0])
            if rec.edge is not None:
                edges.append(rec.edge)
            state = rec.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the chosen path to target (0 if unreachable)."""
        state = self._chosen.get(target)
        if state is None:
            return 0
        return self._records[state].transfers

    def get_cost(self, target):
        """Return the weighted search cost of the chosen path to target (inf if unreachable)."""
        state = self._chosen.get(target)
        if state is None:
            return float("inf")
        return self._records[state].cost
