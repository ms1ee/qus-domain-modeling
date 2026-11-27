"""Shortest path computation on the subway graph.

Implements Dijkstra's algorithm with a binary-heap priority queue (``MinPQ``).
The search runs over states ``(station number, arriving line)`` so that line
changes (transfers) can be counted and limited. Three query modes are offered:

* ``shortest_distance`` - minimise the total distance in meters.
* ``least_transfer``    - minimise the number of transfers, then distance.
* ``comprehensive``     - minimise distance plus a penalty per transfer.

Optional line preference adds a soft penalty to connections that do not
belong to a preferred line; ``max_transfers`` prunes routes with too many
transfers.
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite-score penalty per transfer (about 5 minutes at 1.5 min/km,
# i.e. roughly 3.3 km expressed in meters).
TRANSFER_PENALTY_M = 3300

# Soft penalty for using a line that is not in the preferred list.
PREFERENCE_PENALTY_M = 1000


class PathNotFoundError(Exception):
    """Raised when no route satisfies the requested constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self):
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Unknown mode '{self.mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if not isinstance(self.max_transfers, int) or self.max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")


class MinPQ:
    """Minimum priority queue backed by ``heapq`` (binary heap).

    Items with equal priority are returned in insertion order; the items
    themselves are never compared.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._heap)


class _Label:
    """Best known information for one search state."""

    __slots__ = ("key", "cost", "distance", "transfers", "parent", "edge")

    def __init__(self, key, cost, distance, transfers, parent, edge):
        self.key = key              # comparable priority for the current mode
        self.cost = cost            # accumulated cost (distance + penalties)
        self.distance = distance    # true accumulated distance in meters
        self.transfers = transfers  # accumulated number of transfers
        self.parent = parent        # previous state tuple, or None
        self.edge = edge            # edge used to arrive in this state


def _make_key(mode, cost, transfers):
    """Build the mode-specific comparable priority for a label."""
    if mode == MODE_SHORTEST_DISTANCE:
        return (cost,)
    if mode == MODE_LEAST_TRANSFER:
        return (transfers, cost)
    # comprehensive: composite score balancing distance and transfers
    return (cost + TRANSFER_PENALTY_M * transfers,)


class ShortestPath:
    """Dijkstra's algorithm from a single source station.

    Attributes:
        dist_to: Mapping of reachable station number to the distance in meters
            of the best route found to it.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number: {source}")
        self._graph = graph
        self._source = source
        self._config = config if config is not None else PathfindingConfig()
        self._labels = {}        # state (station, line) -> _Label
        self._best_state = {}    # station number -> best state tuple
        self.dist_to = {}
        self._run()

    @property
    def source(self):
        """Source station number of this search."""
        return self._source

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        cfg = self._config
        preferred = set(cfg.preferred_lines)

        start_state = (self._source, None)
        start_label = _Label(key=_make_key(cfg.mode, 0, 0), cost=0, distance=0,
                             transfers=0, parent=None, edge=None)
        self._labels[start_state] = start_label

        pq = MinPQ()
        pq.insert(start_label.key, start_state)

        while not pq.is_empty():
            key, state = pq.del_min()
            label = self._labels[state]
            if key != label.key:
                continue  # stale queue entry

            station, arrival_line = state
            for edge in self._graph.adj(station):
                transfers = label.transfers
                if arrival_line is not None and edge.line != arrival_line:
                    transfers += 1
                if cfg.max_transfers is not None and transfers > cfg.max_transfers:
                    continue

                penalty = PREFERENCE_PENALTY_M if (
                    preferred and edge.line not in preferred) else 0
                cost = label.cost + edge.weight + penalty
                distance = label.distance + edge.weight
                next_state = (edge.dest, edge.line)
                next_key = _make_key(cfg.mode, cost, transfers)

                old = self._labels.get(next_state)
                if old is None or next_key < old.key:
                    self._labels[next_state] = _Label(
                        key=next_key, cost=cost, distance=distance,
                        transfers=transfers, parent=state, edge=edge)
                    pq.insert(next_key, next_state)

        # Select the best state per station and expose true distances.
        for state, label in self._labels.items():
            station = state[0]
            best = self._best_state.get(station)
            if best is None or label.key < self._labels[best].key:
                self._best_state[station] = state
        for station, state in self._best_state.items():
            self.dist_to[station] = self._labels[state].distance

    def has_path_to(self, target) -> bool:
        """Return True if a route from the source to ``target`` exists."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Backtrack the route to ``target``.

        Returns:
            ``(stations, edges)`` where ``stations`` lists station numbers from
            the target back to the source (end to start) and ``edges`` lists the
            connections in the same order: ``edges[i]`` arrives at
            ``stations[i]`` from ``stations[i + 1]``. Returns ``([], [])`` if the
            target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        stations = []
        edges = []
        state = self._best_state[target]
        while True:
            label = self._labels[state]
            stations.append(state[0])
            if label.parent is None:
                break
            edges.append(label.edge)
            state = label.parent
        return stations, edges

    def get_transfer_count(self, target) -> int:
        """Return the number of line changes on the best route to ``target``.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        if target not in self._best_state:
            raise PathNotFoundError(f"Station {target} is unreachable")
        return self._labels[self._best_state[target]].transfers
