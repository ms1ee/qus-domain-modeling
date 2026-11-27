"""Shortest path computation over the subway graph using Dijkstra's algorithm.

Three query modes are supported:
    shortest_distance - minimise the total distance in meters.
    least_transfer    - minimise line changes first, then distance.
    comprehensive     - minimise distance plus penalties for transfers and for
                        travelling on non-preferred lines.

Path search runs over states (station, arrival line, transfers so far) so that
transfers can be counted and the maximum transfer limit can be enforced.
"""

import heapq
import itertools

TRANSFER_PENALTY_METERS = 1000
NON_PREFERRED_PENALTY_METERS = 300
VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
DEFAULT_MODE = "comprehensive"

_COST_LENGTH = {"shortest_distance": 2, "least_transfer": 3, "comprehensive": 1}


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed number of transfers, or None for no limit.
        preferred_lines: list of preferred line names (may be empty).
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def is_non_preferred(self, line):
        """True if a preference is set and ``line`` is not one of the preferred lines."""
        return bool(self.preferred_lines) and line not in self.preferred_lines


class MinPQ:
    """Binary-heap min priority queue (O(log n) insert and delete-min).

    Items with equal priority are returned in insertion order, and items are
    never compared with each other.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def delete_min(self):
        """Remove and return the (priority, item) pair with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


def _add_costs(a, b):
    return tuple(x + y for x, y in zip(a, b))


class ShortestPath:
    """Single-source shortest path computation (Dijkstra with a priority queue).

    Attributes:
        dist_to: dict mapping station number -> total distance (meters) of the
            selected path from the source.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._transfers = {}
        self._settled_state = {}  # station number -> best settled state key
        self._states = {}         # state key -> bookkeeping dict
        self._run()

    # ----- cost model -------------------------------------------------------

    def _zero_cost(self):
        return (0,) * _COST_LENGTH[self.config.mode]

    def _edge_cost(self, edge, switched):
        """Cost increment of traversing ``edge``; ``switched`` is 1 if it is a transfer."""
        nonpref = 1 if self.config.is_non_preferred(edge.line) else 0
        distance = edge.weight
        mode = self.config.mode
        if mode == "shortest_distance":
            return (distance, nonpref)
        if mode == "least_transfer":
            return (switched, nonpref, distance)
        return (
            distance
            + TRANSFER_PENALTY_METERS * switched
            + NON_PREFERRED_PENALTY_METERS * nonpref,
        )

    def _state_key(self, node, line, transfers):
        # Without a transfer limit, the transfer count does not affect feasibility,
        # so states are keyed only by (station, line) to keep the search small.
        if self.config.max_transfers is None:
            return (node, line, 0)
        return (node, line, transfers)

    # ----- Dijkstra main loop -----------------------------------------------

    def _run(self):
        max_transfers = self.config.max_transfers
        start_key = (self.source, None, 0)
        self._states[start_key] = {
            "cost": self._zero_cost(),
            "dist": 0,
            "transfers": 0,
            "prev": None,
            "edge": None,
        }
        pq = MinPQ()
        pq.insert(self._zero_cost(), start_key)
        settled = set()

        while not pq.is_empty():
            cost, key = pq.delete_min()
            if key in settled:
                continue
            settled.add(key)
            node, line, transfers = key
            state = self._states[key]

            # The first settled state of a station is its optimal state.
            if node not in self._settled_state:
                self._settled_state[node] = key
                self.dist_to[node] = state["dist"]
                self._transfers[node] = state["transfers"]

            for edge in self._graph.adjacent(node):
                neighbor = edge.other(node)
                switched = 1 if (line is not None and edge.line != line) else 0
                new_transfers = transfers + switched
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_key = self._state_key(neighbor, edge.line, new_transfers)
                if new_key in settled:
                    continue
                new_cost = _add_costs(cost, self._edge_cost(edge, switched))
                old = self._states.get(new_key)
                if old is None or new_cost < old["cost"]:
                    self._states[new_key] = {
                        "cost": new_cost,
                        "dist": state["dist"] + edge.weight,
                        "transfers": new_transfers,
                        "prev": key,
                        "edge": edge,
                    }
                    pq.insert(new_cost, new_key)

    # ----- public query API -------------------------------------------------

    def has_path_to(self, target):
        """True if a path from the source to ``target`` exists under the constraints."""
        return target in self._settled_state

    def path_with_edges(self, target):
        """Return (station numbers, edges) of the path from the source to ``target``.

        The station list starts at the source and ends at the target; the edge
        list has one fewer element and edges[i] joins stations[i] and stations[i+1].

        Raises:
            PathNotFoundError: if the target is unreachable under the constraints.
        """
        if target not in self._settled_state:
            raise PathNotFoundError(f"no path to station number {target}")
        key = self._settled_state[target]
        stations = []
        edges = []
        while True:
            info = self._states[key]
            stations.append(key[0])
            if info["edge"] is None:
                break
            edges.append(info["edge"])
            key = info["prev"]
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Number of line changes on the selected path to ``target``."""
        if target not in self._transfers:
            raise PathNotFoundError(f"no path to station number {target}")
        return self._transfers[target]


class Route:
    """Result of a path query.

    Attributes:
        stations: station numbers from source to target.
        edges: edges traversed, one fewer than stations.
        distance: total distance in meters.
        transfer_count: number of line changes.
    """

    def __init__(self, stations, edges, distance, transfer_count):
        self.stations = stations
        self.edges = edges
        self.distance = distance
        self.transfer_count = transfer_count


def find_route(graph, source, target, config=None):
    """Compute the route between two station numbers under the given configuration.

    Raises:
        PathNotFoundError: if no feasible route exists.
        ValueError: if a station number is not part of the graph.
    """
    if not graph.has_vertex(target):
        raise ValueError(f"unknown target station number: {target}")
    shortest = ShortestPath(graph, source, config)
    if not shortest.has_path_to(target):
        raise PathNotFoundError("no route satisfies the current constraints")
    stations, edges = shortest.path_with_edges(target)
    distance = sum(edge.weight for edge in edges)
    return Route(stations, edges, distance, shortest.get_transfer_count(target))
