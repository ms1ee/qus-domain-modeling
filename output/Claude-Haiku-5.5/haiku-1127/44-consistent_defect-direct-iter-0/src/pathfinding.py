"""Path calculation: Dijkstra shortest paths with transfer and preference handling.

Labels are compared lexicographically as (primary, secondary) cost tuples:
    shortest_distance : primary = distance (m) [+ preference penalty]
    least_transfer    : primary = transfers, secondary = distance (m) [+ preference penalty]
    comprehensive     : primary = distance + TRANSFER_PENALTY_M * transfers [+ preference penalty]
"""

from min_pq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for each transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1500.0
# Penalty (meters) charged for riding a line not in the preference list.
PREFERENCE_PENALTY_M = 800.0


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Single-source shortest paths with Dijkstra's algorithm.

    Attributes:
        graph: The Graph being searched.
        source: Source station number.
        config: The PathfindingConfig in use.
        dist_to: dict station number -> physical distance (meters) from source.
        cost_to: dict station number -> composite cost tuple used for ordering.
        transfers_to: dict station number -> number of line changes on the route.
        edge_to: dict station number -> Edge used to reach it on the shortest tree.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.adj:
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {source: 0}
        self.cost_to = {source: (0.0, 0.0)}
        self.transfers_to = {source: 0}
        self.edge_to = {}
        self._run()

    def _increment(self, edge, transfer_inc):
        """Return the cost increment (primary, secondary) for traversing an edge."""
        penalty = 0.0
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            penalty = PREFERENCE_PENALTY_M

        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return (edge.distance + penalty, 0.0)
        if mode == MODE_LEAST_TRANSFER:
            return (float(transfer_inc), edge.distance + penalty)
        # comprehensive
        return (edge.distance + TRANSFER_PENALTY_M * transfer_inc + penalty, 0.0)

    def _run(self):
        """Execute Dijkstra's algorithm using the MinPQ priority queue."""
        pq = MinPQ()
        pq.insert(self.source, self.cost_to[self.source])
        settled = set()
        max_tr = self.config.max_transfers

        while not pq.is_empty():
            v, _ = pq.del_min()
            if v in settled:
                continue  # stale heap entry (lazy deletion)
            settled.add(v)

            prev_edge = self.edge_to.get(v)  # final once v is settled
            for edge in self.graph.adjacent(v):
                w = edge.dest
                if w in settled:
                    continue
                # Special handling of transfer stations: a line change at v
                # counts as one transfer.
                transfer_inc = 1 if (prev_edge is not None and prev_edge.line != edge.line) else 0
                new_transfers = self.transfers_to[v] + transfer_inc
                if max_tr is not None and new_transfers > max_tr:
                    continue

                inc = self._increment(edge, transfer_inc)
                cand = (self.cost_to[v][0] + inc[0], self.cost_to[v][1] + inc[1])
                if w not in self.cost_to or cand < self.cost_to[w]:
                    self.cost_to[w] = cand
                    self.dist_to[w] = self.dist_to[v] + edge.distance
                    self.transfers_to[w] = new_transfers
                    self.edge_to[w] = edge
                    pq.insert(w, cand)

    def has_path_to(self, target):
        """Return True if target is reachable from the source under the constraints."""
        return target in self.cost_to

    def path_with_edges(self, target):
        """Backtrack the shortest path from source to target.

        Returns:
            tuple: (stations, edges) where stations is the list of station
            numbers from source to target and edges is the list of Edge objects
            between consecutive stations. Both are empty if unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        edges = []
        v = target
        while v != self.source:
            edge = self.edge_to[v]
            edges.append(edge)
            v = edge.source
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to target (0 if unreachable)."""
        _, edges = self.path_with_edges(target)
        return sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)


class RouteResult:
    """Result of a successful route query.

    Attributes:
        source: Source station number.
        target: Target station number.
        station_numbers: Station numbers from source to target.
        edges: Edges between consecutive stations.
        distance_m: Total physical distance in meters.
        transfer_count: Number of transfers on the route.
    """

    def __init__(self, source, target, station_numbers, edges, distance_m, transfer_count):
        self.source = source
        self.target = target
        self.station_numbers = station_numbers
        self.edges = edges
        self.distance_m = distance_m
        self.transfer_count = transfer_count


def compute_route(graph, source, target, config=None):
    """Compute the optimal route between two stations.

    Args:
        graph: The subway Graph.
        source: Starting station number.
        target: Ending station number.
        config: Optional PathfindingConfig.

    Returns:
        RouteResult describing the route.

    Raises:
        PathNotFoundError: If no route satisfies the constraints.
        ValueError: If source is not part of the graph.
    """
    sp = ShortestPath(graph, source, config)
    if not sp.has_path_to(target):
        raise PathNotFoundError("No route found between the stations under the current constraints")
    stations, edges = sp.path_with_edges(target)
    distance_m = sum(e.distance for e in edges)
    transfers = sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
    return RouteResult(source, target, stations, edges, distance_m, transfers)
