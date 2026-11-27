"""Shortest path computation on the subway graph using Dijkstra's algorithm.

Three query modes are supported:

* ``shortest_distance`` - minimise the total travelled distance.
* ``least_transfer``    - minimise the number of line changes, using the
  distance as a tie-breaker.
* ``comprehensive``     - minimise a composite score: distance plus a penalty
  per transfer (``TRANSFER_PENALTY_M``).

If ``preferred_lines`` is configured, edges on other lines receive a penalty
(``PREFERENCE_PENALTY_M``) so that routes on preferred lines are favoured.
The maximum transfer limit prunes any route that exceeds it.

Costs are tuples ``(primary, secondary)`` compared lexicographically; both
components are non-negative and additive, which keeps Dijkstra correct.
"""

from .min_pq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite score: each transfer is treated as 1.5 km of extra travel.
TRANSFER_PENALTY_M = 1500.0
# Extra cost (in meters) for riding a line that is not preferred.
PREFERENCE_PENALTY_M = 500.0


class PathNotFoundError(Exception):
    """Raised when no path exists between two stations under the constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def is_preferred(self, line):
        """Return True if ``line`` is acceptable without preference penalty."""
        return not self.preferred_lines or line in self.preferred_lines

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Single-source shortest path search (Dijkstra with a binary-heap queue).

    Attributes:
        dist_to: dict mapping station number -> real travelled distance in
            meters along the chosen path (only reachable stations are present).
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._cost_to = {}
        self._edge_to = {}
        self._transfers_to = {}
        self._compute()

    def _edge_increment(self, edge, prev_line):
        """Compute the cost increments and transfer count for traversing ``edge``.

        Returns:
            tuple: ``(transfer, primary_increment, secondary_increment)``.
        """
        cfg = self.config
        transfer = 1 if prev_line is not None and edge.line != prev_line else 0
        penalty = 0.0 if cfg.is_preferred(edge.line) else PREFERENCE_PENALTY_M

        if cfg.mode == MODE_SHORTEST_DISTANCE:
            primary = edge.distance + penalty
            secondary = 0.0
        elif cfg.mode == MODE_LEAST_TRANSFER:
            primary = float(transfer)
            secondary = edge.distance + penalty
        else:  # MODE_COMPREHENSIVE
            primary = edge.distance + transfer * TRANSFER_PENALTY_M + penalty
            secondary = float(edge.distance)
        return transfer, float(primary), float(secondary)

    def _compute(self):
        """Run Dijkstra's algorithm from the source station."""
        src = self.source
        self._cost_to[src] = (0.0, 0.0)
        self.dist_to[src] = 0
        self._transfers_to[src] = 0

        pq = MinPQ()
        pq.insert((0.0, 0.0), src)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            cost, v = pq.del_min()
            if v in settled:
                continue
            settled.add(v)

            prev_line = self._edge_to[v].line if v in self._edge_to else None
            for edge in self.graph.adj(v):
                w = edge.dest
                if w in settled:
                    continue

                transfer, p_inc, s_inc = self._edge_increment(edge, prev_line)
                transfers = self._transfers_to[v] + transfer
                if max_transfers is not None and transfers > max_transfers:
                    continue

                new_cost = (cost[0] + p_inc, cost[1] + s_inc)
                if w not in self._cost_to or new_cost < self._cost_to[w]:
                    self._cost_to[w] = new_cost
                    self.dist_to[w] = self.dist_to[v] + edge.distance
                    self._transfers_to[w] = transfers
                    self._edge_to[w] = edge
                    pq.insert(new_cost, w)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._cost_to

    def path_with_edges(self, target):
        """Reconstruct the path from the source to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` is the ordered list
            of station numbers (source first, target last) and ``edges`` is the
            ordered list of ``Edge`` objects between consecutive stations.

        Raises:
            PathNotFoundError: If ``target`` is unreachable.
        """
        if not self.has_path_to(target):
            raise PathNotFoundError(f"no path found to station number {target}")
        edges = []
        node = target
        while node != self.source:
            edge = self._edge_to[node]
            edges.append(edge)
            node = edge.source
        edges.reverse()
        stations = [self.source] + [edge.dest for edge in edges]
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target``.

        Raises:
            PathNotFoundError: If ``target`` is unreachable.
        """
        if not self.has_path_to(target):
            raise PathNotFoundError(f"no path found to station number {target}")
        return self._transfers_to[target]
