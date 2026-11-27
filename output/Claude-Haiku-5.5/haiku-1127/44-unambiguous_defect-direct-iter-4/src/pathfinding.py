"""Shortest path computation for the Beijing Subway network.

Dijkstra's algorithm is run over a state space of (station, arriving line) pairs,
which allows transfers to be counted exactly. A binary-heap priority queue (MinPQ)
drives the search, giving O((V+E) log V) behaviour.

Cost model per mode:
    shortest_distance : total distance in meters.
    least_transfer    : (number of transfers, total distance) compared lexicographically.
    comprehensive     : distance plus TRANSFER_PENALTY_METERS per transfer.
Lines outside the preferred list (if any are configured) add PREFERENCE_PENALTY_METERS
to the search cost; reported distances are always the real distances.
"""

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)
DEFAULT_MODE = MODE_COMPREHENSIVE

# Search-only penalties (in meters-equivalent); they do not change reported distances.
TRANSFER_PENALTY_METERS = 1000.0
PREFERENCE_PENALTY_METERS = 500.0


class PathNotFoundError(Exception):
    """Raised when no path exists between two stations under the current settings."""


class PathfindingConfig:
    """Configuration for path queries.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of transfers allowed, or None for no limit.
        preferred_lines: Lines favoured by the search (list of line names).
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])
        self.validate()

    def validate(self):
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{self.mode}'; expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Min priority queue implemented as an array-based binary heap.

    Items are (key, value) pairs; ordering uses only the key.
    """

    def __init__(self):
        self._keys = []
        self._values = []

    def __len__(self):
        return len(self._keys)

    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._keys)

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._keys

    def insert(self, key, value):
        """Insert a value with the given priority key."""
        self._keys.append(key)
        self._values.append(value)
        self._swim(len(self._keys) - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("Priority queue is empty")
        return self._keys[0]

    def del_min(self):
        """Remove and return the (key, value) pair with the smallest key."""
        if not self._keys:
            raise IndexError("Priority queue is empty")
        top_key, top_value = self._keys[0], self._values[0]
        last_key = self._keys.pop()
        last_value = self._values.pop()
        if self._keys:
            self._keys[0] = last_key
            self._values[0] = last_value
            self._sink(0)
        return top_key, top_value

    def _swim(self, index):
        """Move the item at ``index`` up until the heap property holds."""
        keys = self._keys
        while index > 0:
            parent = (index - 1) // 2
            if keys[index] < keys[parent]:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sink(self, index):
        """Move the item at ``index`` down until the heap property holds."""
        keys = self._keys
        size = len(keys)
        while True:
            left = 2 * index + 1
            if left >= size:
                break
            child = left
            right = left + 1
            if right < size and keys[right] < keys[left]:
                child = right
            if keys[child] < keys[index]:
                self._swap(index, child)
                index = child
            else:
                break

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._values[i], self._values[j] = self._values[j], self._values[i]


class _SearchState:
    """A reached (station, arriving line) state in the Dijkstra search."""

    __slots__ = ("node", "line", "cost", "distance", "transfers", "prev", "edge")

    def __init__(self, node, line, cost, distance, transfers, prev, edge):
        self.node = node
        self.line = line
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Single-source shortest paths from a source station using Dijkstra's algorithm.

    Attributes:
        dist_to: Mapping station number -> actual distance (meters) from the source
            along the best path found to that station.
    """

    def __init__(self, graph, source, config=None):
        """Run the search from ``source`` (a station number) over ``graph``."""
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        if not graph.has_vertex(source):
            raise ValueError(f"Unknown source station number {source!r}")
        self.dist_to = {}
        self._best = {}
        self._search()

    def _step_cost(self, base, transfer, effective_distance):
        """Return the cost tuple after traversing one edge from a state with cost ``base``."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            increment = (1.0 if transfer else 0.0, effective_distance)
        elif mode == MODE_COMPREHENSIVE:
            increment = (effective_distance + (TRANSFER_PENALTY_METERS if transfer else 0.0), 0.0)
        else:
            increment = (effective_distance, 0.0)
        return (base[0] + increment[0], base[1] + increment[1])

    def _search(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers
        start = _SearchState(self.source, None, (0.0, 0.0), 0, 0, None, None)

        queue = MinPQ()
        queue.insert(start.cost, start)
        best_cost = {(self.source, None): start.cost}
        settled = set()

        while not queue.is_empty():
            cost, state = queue.del_min()
            key = (state.node, state.line)
            if key in settled:
                continue
            settled.add(key)
            # States are settled in non-decreasing cost order, so the first one
            # settled for a station is its best state.
            if state.node not in self._best:
                self._best[state.node] = state

            for edge in self.graph.adjacent(state.node):
                nxt = edge.other(state.node)
                if nxt == self.source:
                    continue
                transfer = state.line is not None and edge.line != state.line
                transfers = state.transfers + (1 if transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue
                next_key = (nxt, edge.line)
                if next_key in settled:
                    continue
                penalty = PREFERENCE_PENALTY_METERS if preferred and edge.line not in preferred else 0.0
                new_cost = self._step_cost(cost, transfer, edge.weight + penalty)
                old_cost = best_cost.get(next_key)
                if old_cost is None or new_cost < old_cost:
                    best_cost[next_key] = new_cost
                    queue.insert(
                        new_cost,
                        _SearchState(nxt, edge.line, new_cost, state.distance + edge.weight,
                                     transfers, state, edge),
                    )

        for node, state in self._best.items():
            self.dist_to[node] = state.distance

    def has_path(self, target) -> bool:
        """Return True if ``target`` (station number) is reachable under the config."""
        return target in self._best

    def _state_for(self, target):
        state = self._best.get(target)
        if state is None:
            raise PathNotFoundError(f"No path found to station number {target!r} "
                                    f"under the current settings")
        return state

    def path_with_edges(self, target):
        """Return the station numbers and edges of the best path from source to target.

        Returns:
            (nodes, edges): ``nodes`` is the list of station numbers from source to
            target; ``edges`` is the list of Edge objects between consecutive nodes.

        Raises:
            PathNotFoundError: If the target cannot be reached.
        """
        state = self._state_for(target)
        nodes = []
        edges = []
        current = state
        while current.prev is not None:
            nodes.append(current.node)
            edges.append(current.edge)
            current = current.prev
        nodes.append(current.node)
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target) -> int:
        """Return the number of line transfers on the best path to ``target``."""
        return self._state_for(target).transfers
