"""Shortest-path computation on the subway graph (Dijkstra with a heap-based priority queue)."""

from models import Graph, PathNotFoundError

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Composite-score penalty for each line change (expressed in meters-equivalent).
TRANSFER_PENALTY_M = 2000.0
# Lexicographic weight that makes transfers dominate distance in least_transfer mode.
LEXICOGRAPHIC_TRANSFER_WEIGHT = 1e12
# Extra cost for riding a line that is not in the passenger's line preference list.
PREFERRED_LINE_PENALTY_M = 500.0


class PathfindingConfig:
    """Options controlling how a route is computed.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed line changes, or None for no limit.
        preferred_lines: list of line names to prefer (empty means no preference).
    """

    def __init__(self, mode="comprehensive", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None and (not isinstance(max_transfers, int) or max_transfers < 0):
            raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class MinPQ:
    """Indexed binary min-heap keyed by float priorities.

    Supports insert, delete-min, and priority updates in O(log n), which gives
    Dijkstra's algorithm its O((V+E) log V) bound.
    """

    def __init__(self):
        self._items = []
        self._prios = []
        self._index = {}

    def size(self):
        return len(self._items)

    def is_empty(self):
        return not self._items

    def contains(self, item):
        return item in self._index

    def min(self):
        if not self._items:
            raise IndexError("priority queue is empty")
        return self._items[0]

    def min_priority(self):
        if not self._prios:
            raise IndexError("priority queue is empty")
        return self._prios[0]

    def insert(self, item, priority):
        """Insert a new item. Raises ValueError if it is already present."""
        if item in self._index:
            raise ValueError("item already in priority queue")
        self._items.append(item)
        self._prios.append(priority)
        pos = len(self._items) - 1
        self._index[item] = pos
        self._sift_up(pos)

    def update(self, item, priority):
        """Insert the item or change its priority (decrease or increase key)."""
        if item not in self._index:
            self.insert(item, priority)
            return
        pos = self._index[item]
        old = self._prios[pos]
        self._prios[pos] = priority
        if priority < old:
            self._sift_up(pos)
        else:
            self._sift_down(pos)

    def del_min(self):
        """Remove and return the item with the smallest priority."""
        if not self._items:
            raise IndexError("priority queue is empty")
        top = self._items[0]
        last_item = self._items.pop()
        last_prio = self._prios.pop()
        del self._index[top]
        if self._items:
            self._items[0] = last_item
            self._prios[0] = last_prio
            self._index[last_item] = 0
            self._sift_down(0)
        return top

    def _swap(self, i, j):
        self._items[i], self._items[j] = self._items[j], self._items[i]
        self._prios[i], self._prios[j] = self._prios[j], self._prios[i]
        self._index[self._items[i]] = i
        self._index[self._items[j]] = j

    def _sift_up(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._prios[k] < self._prios[parent]:
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sift_down(self, k):
        n = len(self._items)
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < n and self._prios[left] < self._prios[smallest]:
                smallest = left
            if right < n and self._prios[right] < self._prios[smallest]:
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest


class _SearchState:
    """Best-known information for a search state (station, arrival line)."""

    __slots__ = ("cost", "distance", "transfers", "prev", "edge")

    def __init__(self, cost, distance, transfers, prev, edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Dijkstra-based optimal path search from a single source station.

    The search runs over states (station number, line used to arrive), so line
    changes at interchange stations are detected and counted correctly. The cost
    of a state depends on the configured mode:

      * shortest_distance: total distance (plus line-preference penalties).
      * least_transfer: transfer count first, then distance.
      * comprehensive: distance plus a fixed penalty per transfer.

    Attributes:
        dist_to: station number -> actual travelled distance (meters) of the best path.
    """

    def __init__(self, graph, source, config=None):
        if not isinstance(graph, Graph):
            raise TypeError("graph must be a Graph instance")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._states = {}
        self._search()

    def _step_cost(self, edge, transfer):
        """Cost added by traversing an edge in the configured mode."""
        cost = float(edge.distance)
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            cost += PREFERRED_LINE_PENALTY_M
        if transfer:
            if self.config.mode == "least_transfer":
                cost += LEXICOGRAPHIC_TRANSFER_WEIGHT
            elif self.config.mode == "comprehensive":
                cost += TRANSFER_PENALTY_M
        return cost

    def _search(self):
        start = (self.source, None)
        self._states[start] = _SearchState(0.0, 0.0, 0, None, None)
        queue = MinPQ()
        queue.insert(start, 0.0)
        settled = set()
        max_transfers = self.config.max_transfers

        while not queue.is_empty():
            state = queue.del_min()
            settled.add(state)
            node, line = state
            info = self._states[state]

            # The first settled state of a station is its optimal state.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = info.distance

            for edge in self.graph.adj(node):
                transfer = line is not None and edge.line != line
                transfers = info.transfers + (1 if transfer else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue
                next_state = (edge.dest, edge.line)
                if next_state in settled:
                    continue
                cost = info.cost + self._step_cost(edge, transfer)
                existing = self._states.get(next_state)
                if existing is None or cost < existing.cost:
                    self._states[next_state] = _SearchState(
                        cost, info.distance + edge.distance, transfers, state, edge
                    )
                    queue.update(next_state, cost)

    def has_path_to(self, target):
        """Return True if the target station is reachable under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return (station numbers, edges) from the source to the target.

        Raises:
            PathNotFoundError: if the target is unreachable.
        """
        if target not in self._best_state:
            raise PathNotFoundError(f"No path found to station {target}")
        state = self._best_state[target]
        nodes = []
        edges = []
        while state is not None:
            info = self._states[state]
            nodes.append(state[0])
            if info.edge is not None:
                edges.append(info.edge)
            state = info.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to the target."""
        if target not in self._best_state:
            raise PathNotFoundError(f"No path found to station {target}")
        return self._states[self._best_state[target]].transfers

    def get_distance(self, target):
        """Return the travelled distance in meters on the best path to the target."""
        if target not in self._best_state:
            raise PathNotFoundError(f"No path found to station {target}")
        return self.dist_to[target]
