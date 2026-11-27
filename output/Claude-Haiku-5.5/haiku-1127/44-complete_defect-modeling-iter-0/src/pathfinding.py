"""Route search based on Dijkstra's algorithm with a binary-heap priority queue.

The search runs over states ``(station number, arrival line)`` so that line
changes (transfers) can be counted and limited. Supported query modes:

* ``shortest_distance`` - minimize total distance (ties broken by transfers).
* ``least_transfer``    - minimize transfers (ties broken by distance).
* ``comprehensive``     - minimize distance plus a penalty per transfer.

A line preference, when set, makes edges on non-preferred lines more costly in
the search (the reported distance stays the real distance).
"""

import heapq
import itertools

# Search penalty (in meters) added per transfer in ``comprehensive`` mode.
TRANSFER_PENALTY_M = 500.0
# Search cost multiplier for edges on lines outside the preference list.
NON_PREFERRED_LINE_FACTOR = 1.5


class MinPQ:
    """Min priority queue implemented on top of ``heapq`` (binary heap).

    Insertion and removal cost O(log n). A sequence counter keeps the ordering
    stable and avoids comparing the items themselves.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert ``item`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no elements."""
        return not self._heap

    def size(self):
        """Return the number of queued elements."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of ``MODES``.
        max_transfers: maximum number of line changes allowed, or None for no limit.
        preferred_lines: list of preferred line names (may be empty).
    """

    MODE_SHORTEST_DISTANCE = "shortest_distance"
    MODE_LEAST_TRANSFER = "least_transfer"
    MODE_COMPREHENSIVE = "comprehensive"
    MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in self.MODES:
            raise ValueError("Unsupported mode '{}'; choose from {}".format(mode, ", ".join(self.MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Dijkstra-based path search from one source station.

    Args:
        graph: the ``Graph`` keyed by station numbers.
        source: station number of the starting station.
        config: optional ``PathfindingConfig``.

    Attributes:
        dist_to: station number -> real distance in meters along the chosen path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError("Source station number {} is not in the graph".format(source))
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._transfers_to = {}
        self._best_state = {}   # station number -> (station, line) state
        self._parent = {}       # state -> (previous state, edge) or None
        self._search()

    # ----- cost model --------------------------------------------------------
    def _key(self, weighted, transfers):
        """Build the (monotone) priority key for a partial path."""
        mode = self.config.mode
        if mode == PathfindingConfig.MODE_LEAST_TRANSFER:
            return (transfers, weighted)
        if mode == PathfindingConfig.MODE_COMPREHENSIVE:
            return (weighted + TRANSFER_PENALTY_M * transfers, transfers)
        return (weighted, transfers)

    def _edge_weight(self, edge):
        """Search cost contribution of an edge (honours line preference)."""
        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            return float(edge.distance) * NON_PREFERRED_LINE_FACTOR
        return float(edge.distance)

    # ----- search ------------------------------------------------------------
    def _search(self):
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        self._parent[start] = None
        real = {start: 0.0}
        weighted = {start: 0.0}
        transfers = {start: 0}
        keys = {start: self._key(0.0, 0)}

        pq = MinPQ()
        pq.insert(keys[start], start)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            station, line = state

            # The first time a station is settled gives its optimal state.
            if station not in self.dist_to:
                self.dist_to[station] = real[state]
                self._transfers_to[station] = transfers[state]
                self._best_state[station] = state

            for edge in self._graph.adj(station):
                neighbor = edge.other(station)
                next_transfers = transfers[state]
                if line is not None and edge.line != line:
                    next_transfers += 1
                if max_transfers is not None and next_transfers > max_transfers:
                    continue
                next_state = (neighbor, edge.line)
                if next_state in done:
                    continue
                next_weighted = weighted[state] + self._edge_weight(edge)
                next_key = self._key(next_weighted, next_transfers)
                if next_state in keys and keys[next_state] <= next_key:
                    continue
                keys[next_state] = next_key
                weighted[next_state] = next_weighted
                real[next_state] = real[state] + edge.distance
                transfers[next_state] = next_transfers
                self._parent[next_state] = (state, edge)
                pq.insert(next_key, next_state)

    # ----- results -----------------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the path to ``target`` as (station numbers, edges).

        The station list starts with the source and ends with the target; the
        edge list has one element fewer. Unreachable targets yield ([], []).
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        states = []
        edges = []
        while state is not None:
            states.append(state)
            parent = self._parent.get(state)
            if parent is None:
                break
            previous, edge = parent
            edges.append(edge)
            state = previous
        states.reverse()
        edges.reverse()
        return [station for station, _ in states], edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target`` (0 if unreachable)."""
        return self._transfers_to.get(target, 0)
