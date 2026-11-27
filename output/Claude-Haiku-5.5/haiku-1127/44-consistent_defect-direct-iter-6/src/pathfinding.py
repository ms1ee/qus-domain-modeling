"""Path calculation based on Dijkstra's shortest path algorithm.

The search runs over labels of the form ``(station_number, line, transfers)``
so that transfers can be counted and limited while the search proceeds.
Costs are measured in meters, with optional penalties for transfers and for
using lines outside the passenger's preference.
"""

from minpq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Upper bound on transfers explored, which keeps the label space finite.
HARD_TRANSFER_LIMIT = 10
# Extra cost (meters) for each edge on a non-preferred line.
LINE_PREFERENCE_PENALTY_M = 500.0
# Dominant transfer penalty so that the fewest transfers are minimized first.
LEAST_TRANSFER_PENALTY_M = 1_000_000.0
# Composite score: roughly 5 minutes of travel time expressed in meters
# (5 min at 1.5 min/km is about 3.3 km).
COMPREHENSIVE_TRANSFER_PENALTY_M = 3300.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed transfers, or None for no explicit limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode {mode!r}; expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(line).strip()
                                for line in (preferred_lines or [])
                                if str(line).strip()]

    def transfer_penalty(self):
        """Return the cost penalty added for every transfer in this mode."""
        if self.mode == MODE_LEAST_TRANSFER:
            return LEAST_TRANSFER_PENALTY_M
        if self.mode == MODE_COMPREHENSIVE:
            return COMPREHENSIVE_TRANSFER_PENALTY_M
        return 0.0

    def effective_transfer_limit(self):
        """Return the transfer limit actually enforced during search."""
        if self.max_transfers is None:
            return HARD_TRANSFER_LIMIT
        return min(self.max_transfers, HARD_TRANSFER_LIMIT)


class PathResult:
    """Result of a path query.

    Attributes:
        station_numbers: Station numbers from start to end.
        edges: Edges traversed, in order from start to end.
        distance: Total physical distance in meters.
        transfer_count: Number of line changes along the path.
        cost: Optimization cost of the path (includes penalties).
    """

    def __init__(self, station_numbers, edges, distance, transfer_count, cost):
        self.station_numbers = station_numbers
        self.edges = edges
        self.distance = distance
        self.transfer_count = transfer_count
        self.cost = cost


class ShortestPath:
    """Dijkstra-based shortest path computation from a single source.

    Attributes:
        dist_to: Dictionary mapping reachable station numbers to the physical
            distance in meters of the best path found to them.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._cost_to = {}
        self._best_label = {}
        self._label_cost = {}
        self._label_dist = {}
        self._edge_to = {}
        self._run()

    def _run(self):
        """Run Dijkstra's algorithm over (station, line, transfers) labels."""
        config = self.config
        transfer_limit = config.effective_transfer_limit()
        transfer_penalty = config.transfer_penalty()
        preferred = set(config.preferred_lines)

        start = (self.source, None, 0)
        self._label_cost[start] = 0.0
        self._label_dist[start] = 0
        queue = MinPQ()
        queue.insert(0.0, start)
        settled = set()

        while not queue.is_empty():
            cost, label = queue.del_min()
            if label in settled:
                continue
            settled.add(label)
            node, line, transfers = label

            # Labels are settled in order of cost, so the first label seen
            # for a station is its best label.
            if node not in self._best_label:
                self._best_label[node] = label
                self.dist_to[node] = self._label_dist[label]
                self._cost_to[node] = cost

            for edge in self.graph.adj(node):
                next_transfers = transfers
                step = float(edge.weight)
                if line is not None and edge.line != line:
                    next_transfers += 1
                    if next_transfers > transfer_limit:
                        continue
                    step += transfer_penalty
                if preferred and edge.line not in preferred:
                    step += LINE_PREFERENCE_PENALTY_M

                next_label = (edge.dest, edge.line, next_transfers)
                if next_label in settled:
                    continue
                next_cost = cost + step
                known = self._label_cost.get(next_label)
                if known is None or next_cost < known:
                    self._label_cost[next_label] = next_cost
                    self._label_dist[next_label] = self._label_dist[label] + edge.weight
                    self._edge_to[next_label] = (label, edge)
                    queue.insert(next_cost, next_label)

    def has_path_to(self, target):
        """Return True if the target station can be reached."""
        return target in self._best_label

    def cost_to(self, target):
        """Return the optimization cost to the target, or None if unreachable."""
        return self._cost_to.get(target)

    def get_transfer_count(self, target):
        """Return the number of transfers on the path to the target."""
        if target not in self._best_label:
            return 0
        return self._best_label[target][2]

    def path_with_edges(self, target):
        """Backtrack the path to the target.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects traversed in order).
            If the target is unreachable, returns ([], []).
        """
        if target not in self._best_label:
            return [], []
        label = self._best_label[target]
        nodes = []
        edges = []
        while True:
            nodes.append(label[0])
            link = self._edge_to.get(label)
            if link is None:
                break
            previous, edge = link
            edges.append(edge)
            label = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges


def find_path(graph, source, target, config=None):
    """Find the optimal path between two station numbers.

    Returns:
        PathResult, or None if no path satisfies the configuration.
    """
    search = ShortestPath(graph, source, config)
    if not search.has_path_to(target):
        return None
    nodes, edges = search.path_with_edges(target)
    distance = sum(edge.distance for edge in edges)
    return PathResult(nodes, edges, distance,
                      search.get_transfer_count(target), search.cost_to(target))


def find_shortest_distance_path(graph, source, target, max_transfers=None,
                                preferred_lines=None):
    """Shortest-distance query (minimizes physical distance)."""
    config = PathfindingConfig(MODE_SHORTEST_DISTANCE, max_transfers, preferred_lines)
    return find_path(graph, source, target, config)


def find_least_transfer_path(graph, source, target, max_transfers=None,
                             preferred_lines=None):
    """Minimum-transfer query (transfers first, distance as tie-breaker)."""
    config = PathfindingConfig(MODE_LEAST_TRANSFER, max_transfers, preferred_lines)
    return find_path(graph, source, target, config)


def find_comprehensive_path(graph, source, target, max_transfers=None,
                            preferred_lines=None):
    """Comprehensive query balancing distance and transfers."""
    config = PathfindingConfig(MODE_COMPREHENSIVE, max_transfers, preferred_lines)
    return find_path(graph, source, target, config)
