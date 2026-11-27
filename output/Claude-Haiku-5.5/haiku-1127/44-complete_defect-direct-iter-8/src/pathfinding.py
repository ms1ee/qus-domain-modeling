"""Shortest-path computation over the subway graph using Dijkstra's algorithm.

The search runs over states (station, line of the last edge). This allows the
number of line transfers to be tracked exactly, so transfer limits and
least-transfer routing are computed correctly at multi-line interchange stations.

Each state cost is an additive tuple compared lexicographically. Because every
step adds a non-negative cost, Dijkstra's greedy strategy remains correct.
"""

from dataclasses import dataclass

from errors import PathNotFoundError
from priority_queue import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty (meters) charged for every transfer in comprehensive mode.
TRANSFER_PENALTY_M = 300
# Equivalent distance penalty (meters) charged for each edge not on a preferred line.
PREFERENCE_PENALTY_M = 500


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names the passenger prefers.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


@dataclass
class RouteResult:
    """Result of a route query.

    Attributes:
        source: Station number of the origin.
        target: Station number of the destination.
        stations: Ordered station numbers from source to target.
        edges: Ordered edges traversed (len(stations) - 1 items).
        distance: Total travel distance in meters.
        transfer_count: Number of line changes along the route.
        mode: Query mode used.
    """

    source: int
    target: int
    stations: list
    edges: list
    distance: float
    transfer_count: int
    mode: str


class ShortestPath:
    """Single-source shortest path search.

    Attributes:
        source: Source station number.
        config: PathfindingConfig in effect.
        dist_to: dict station number -> travel distance (meters) of the best
            route found to that station under the active mode.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        # state (station, last_line) -> (key, distance, transfers, nonpreferred_edges)
        self._labels = {}
        # state -> (previous_state, edge)
        self._parent = {}
        # station -> best state reaching it
        self._best_state = {}
        self._run()

    # ----- cost model ----------------------------------------------------------
    def _make_key(self, distance, transfers, nonpreferred):
        """Build the additive, lexicographically comparable cost key for the mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, distance, nonpreferred)
        if mode == MODE_COMPREHENSIVE:
            return (distance + TRANSFER_PENALTY_M * transfers + PREFERENCE_PENALTY_M * nonpreferred,
                    distance, transfers, nonpreferred)
        return (distance, transfers, nonpreferred)

    # ----- Dijkstra ------------------------------------------------------------
    def _run(self):
        """Execute Dijkstra's algorithm with a priority queue."""
        max_transfers = self.config.max_transfers
        preferred = self.config.preferred_lines

        start_state = (self.source, None)
        start_key = self._make_key(0, 0, 0)
        self._labels[start_state] = (start_key, 0, 0, 0)

        pq = MinPQ()
        pq.insert(start_key, start_state)

        while not pq.is_empty():
            key, state = pq.del_min()
            label = self._labels[state]
            if key != label[0]:
                continue  # stale queue entry
            node, last_line = state
            _, distance, transfers, nonpreferred = label

            for edge in self._graph.adjacent(node):
                next_node = edge.other(node)
                transfer_inc = 1 if (last_line is not None and edge.line != last_line) else 0
                new_transfers = transfers + transfer_inc
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_distance = distance + edge.weight
                nonpref_inc = 1 if (preferred and edge.line not in preferred) else 0
                new_nonpreferred = nonpreferred + nonpref_inc
                new_key = self._make_key(new_distance, new_transfers, new_nonpreferred)
                new_state = (next_node, edge.line)
                old = self._labels.get(new_state)
                if old is None or new_key < old[0]:
                    self._labels[new_state] = (new_key, new_distance, new_transfers, new_nonpreferred)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

        # Select the best state per station.
        for state, label in self._labels.items():
            node = state[0]
            current = self._best_state.get(node)
            if current is None or label[0] < self._labels[current][0]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._labels[state][1]

    # ----- queries -------------------------------------------------------------
    def has_path(self, target):
        """Return True if `target` is reachable under the active constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the station sequence and edge sequence from source to target.

        Returns:
            (list of station numbers, list of Edge objects)

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        if not self.has_path(target):
            raise PathNotFoundError(f"No route found to station {target}")
        state = self._best_state[target]
        nodes = [target]
        edges = []
        while state in self._parent:
            previous, edge = self._parent[state]
            edges.append(edge)
            nodes.append(previous[0])
            state = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the best route to `target`.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        if not self.has_path(target):
            raise PathNotFoundError(f"No route found to station {target}")
        return self._labels[self._best_state[target]][2]


def find_route(graph, source, target, config=None):
    """Compute a complete route between two stations.

    Args:
        graph: The subway Graph.
        source: Station number of the origin.
        target: Station number of the destination.
        config: Optional PathfindingConfig.

    Returns:
        RouteResult describing the optimal route under the configuration.

    Raises:
        PathNotFoundError: If no route satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    if not graph.has_vertex(target):
        raise PathNotFoundError("No route found: destination is not part of the network")
    search = ShortestPath(graph, source, config)
    if not search.has_path(target):
        message = "No route found between the stations"
        if config.max_transfers is not None:
            message += f" within {config.max_transfers} transfer(s)"
        raise PathNotFoundError(message)
    stations, edges = search.path_with_edges(target)
    return RouteResult(
        source=source,
        target=target,
        stations=stations,
        edges=edges,
        distance=search.dist_to[target],
        transfer_count=search.get_transfer_count(target),
        mode=config.mode,
    )
