"""Path calculation: indexed min priority queue and Dijkstra-based shortest path search."""

import math

from models import Graph  # noqa: F401  (type reference for documentation)

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Used when no maximum transfer limit is configured, to keep the search space finite.
DEFAULT_TRANSFER_CAP = 10
# Extra cost (in meters-equivalent) charged for each transfer in comprehensive mode.
TRANSFER_PENALTY_COMPREHENSIVE_M = 500.0
# Lexicographic weight of a transfer in least_transfer mode (dominates distances).
LEAST_TRANSFER_WEIGHT = 1e9
# Extra cost charged for riding a non-preferred line when a line preference is set.
LINE_PREFERENCE_PENALTY_M = 300.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def transfer_cost(self):
        """Additional search cost of one line change, depending on the mode."""
        if self.mode == MODE_LEAST_TRANSFER:
            return LEAST_TRANSFER_WEIGHT
        if self.mode == MODE_COMPREHENSIVE:
            return TRANSFER_PENALTY_COMPREHENSIVE_M
        return 0.0

    def line_penalty(self, line):
        """Additional search cost of riding ``line`` (non-preferred lines are penalized)."""
        if self.preferred_lines and line not in self.preferred_lines:
            return LINE_PREFERENCE_PENALTY_M
        return 0.0


class MinPQ:
    """Indexed binary min-heap priority queue with decrease-key support.

    Items must be hashable and unique within the queue. All core operations
    run in O(log n) time.
    """

    def __init__(self, capacity=None):
        self._capacity = capacity
        self._items = []
        self._keys = []
        self._index = {}  # item -> position in the heap arrays

    @property
    def size(self):
        return len(self._items)

    @property
    def capacity(self):
        return self._capacity if self._capacity is not None else len(self._items)

    def is_empty(self):
        return not self._items

    def contains(self, item):
        return item in self._index

    def insert(self, item, key):
        """Insert ``item`` with priority ``key``."""
        if item in self._index:
            raise ValueError("Item already present in priority queue")
        if self._capacity is not None and len(self._items) >= self._capacity:
            raise OverflowError("Priority queue capacity exceeded")
        self._items.append(item)
        self._keys.append(key)
        self._index[item] = len(self._items) - 1
        self._swim(len(self._items) - 1)

    def decrease_key(self, item, key):
        """Lower the priority of ``item`` to ``key``. Returns True if the key changed."""
        pos = self._index[item]
        if key >= self._keys[pos]:
            return False
        self._keys[pos] = key
        self._swim(pos)
        return True

    def min_item(self):
        if not self._items:
            raise IndexError("Priority queue is empty")
        return self._items[0]

    def min_key(self):
        if not self._keys:
            raise IndexError("Priority queue is empty")
        return self._keys[0]

    def del_min(self):
        """Remove and return the item with the smallest key."""
        if not self._items:
            raise IndexError("Priority queue is empty")
        item = self._items[0]
        last = len(self._items) - 1
        self._swap(0, last)
        self._items.pop()
        self._keys.pop()
        del self._index[item]
        if self._items:
            self._sink(0)
        return item

    def _less(self, i, j):
        return self._keys[i] < self._keys[j]

    def _swap(self, i, j):
        self._items[i], self._items[j] = self._items[j], self._items[i]
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._index[self._items[i]] = i
        self._index[self._items[j]] = j

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._items)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child


class _StateInfo:
    """Best known information for one search state (station, arrival line, transfers)."""

    __slots__ = ("cost", "dist", "transfers", "prev", "edge")

    def __init__(self, cost, dist, transfers, prev, edge):
        self.cost = cost            # search cost (distance plus mode/preference penalties)
        self.dist = dist            # actual accumulated distance in meters
        self.transfers = transfers  # number of line changes so far
        self.prev = prev            # predecessor state, or None for the source
        self.edge = edge            # edge used to arrive in this state, or None for the source


class ShortestPath:
    """Dijkstra-based path search over the subway graph.

    The search runs over states (station, line of arrival, transfers so far),
    which lets it count transfers exactly, enforce the maximum transfer limit,
    and handle multi-line interchange stations (each interchange is one station
    node, and line changes at it are detected from the edges used).

    Attributes:
        source: Source station number.
        dist_to: dict station number -> actual distance in meters of the best path.
        edge_to: dict station number -> edge used to arrive at the station on the best path.
        config: PathfindingConfig in use.
    """

    def __init__(self, graph, source, config=None):
        if not graph.contains_node(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self.edge_to = {}
        self._best_state = {}  # station number -> finalized best state
        self._info = {}        # state -> _StateInfo
        self._search()

    def _search(self):
        cfg = self.config
        cap = cfg.max_transfers if cfg.max_transfers is not None else DEFAULT_TRANSFER_CAP
        transfer_cost = cfg.transfer_cost()

        start = (self.source, None, 0)
        self._info[start] = _StateInfo(0.0, 0.0, 0, None, None)
        pq = MinPQ()
        pq.insert(start, 0.0)

        while not pq.is_empty():
            state = pq.del_min()
            node, line, transfers = state
            info = self._info[state]

            # The first finalized state of a station is its best state.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = info.dist
                self.edge_to[node] = info.edge

            for edge in self.graph.adjacent(node):
                nxt = edge.other_end(node)
                new_transfers = transfers
                edge_cost = float(edge.distance)
                if line is not None and edge.line != line:
                    new_transfers += 1
                    edge_cost += transfer_cost
                if new_transfers > cap:
                    continue
                edge_cost += cfg.line_penalty(edge.line)

                new_state = (nxt, edge.line, new_transfers)
                new_cost = info.cost + edge_cost
                existing = self._info.get(new_state)
                if existing is None or new_cost < existing.cost:
                    self._info[new_state] = _StateInfo(
                        new_cost, info.dist + edge.distance, new_transfers, state, edge
                    )
                    if pq.contains(new_state):
                        pq.decrease_key(new_state, new_cost)
                    else:
                        pq.insert(new_state, new_cost)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the distance in meters to ``target``, or infinity if unreachable."""
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return ``(station_numbers, edges)`` of the best path from source to target.

        ``station_numbers`` starts with the source and ends with the target;
        ``edges`` has one fewer element. Both are empty if target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        nodes = []
        edges = []
        current = state
        while current is not None:
            nodes.append(current[0])
            info = self._info[current]
            if info.edge is not None:
                edges.append(info.edge)
            current = info.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to target (0 if unreachable)."""
        state = self._best_state.get(target)
        if state is None:
            return 0
        return self._info[state].transfers
