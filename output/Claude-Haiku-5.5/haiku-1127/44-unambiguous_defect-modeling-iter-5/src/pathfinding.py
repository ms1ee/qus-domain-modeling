"""Shortest-path computation on the subway graph.

Dijkstra's algorithm is run over "states" (station, arriving line) so that
transfers between lines can be counted and constrained. Costs are compared
lexicographically using tuples whose meaning depends on the query mode:

* shortest_distance: minimise total distance (plus soft line-preference penalties)
* least_transfer:    minimise number of transfers, then distance
* comprehensive:     minimise distance plus a fixed penalty per transfer
"""

import heapq
import itertools

from models import Edge

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty (meters) for each transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000.0
# Soft penalty (meters) for riding a line not in the preferred list.
PREFERENCE_PENALTY_M = 500.0


class PathNotFoundError(Exception):
    """Raised when no path exists between two stations under the given constraints."""


class MinPQ:
    """Binary min-priority queue based on the heapq heap.

    Uses lazy deletion: the same item may be inserted several times with
    different priorities; callers skip stale entries when they are popped.

    Attributes:
        size: Number of entries currently in the queue (read-only property).
        capacity: Capacity hint; grows automatically if exceeded.
    """

    def __init__(self, capacity=0):
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._capacity = capacity
        self._heap = []
        self._counter = itertools.count()

    @property
    def size(self):
        return len(self._heap)

    @property
    def capacity(self):
        return self._capacity

    def is_empty(self):
        return not self._heap

    def insert(self, item, priority):
        """Insert an item with a priority (smaller is served first)."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))
        if len(self._heap) > self._capacity:
            self._capacity = len(self._heap)

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def del_min(self):
        """Remove and return the item with the smallest priority."""
        if not self._heap:
            raise IndexError("priority queue underflow")
        return heapq.heappop(self._heap)[2]


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of line names that are preferred when routing.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self):
        """Raise ValueError if the configuration is inconsistent."""
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if not isinstance(self.preferred_lines, list):
            raise ValueError("preferred_lines must be a list")


class ShortestPath:
    """Single-source shortest paths over a Graph using Dijkstra's algorithm.

    Complexity: O((V + E) log V) per run, thanks to the heap-based MinPQ.
    The search is run over (station, line) states, so transfers are tracked
    exactly; the number of states is bounded by the number of edges.

    Attributes:
        dist_to: dict mapping station number -> actual distance in meters of the
            best path found to that station under the configured mode.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        if not graph.has_node(source):
            raise ValueError(f"Source station number {source} is not in the graph")
        self.dist_to = {}
        self._info = {}          # state -> (cost, transfers, actual_distance)
        self._parent = {}        # state -> (previous_state, Edge) or None
        self._best_state = {}    # station number -> best state reaching it
        self._run()

    def _priority(self, cost, transfers, actual):
        """Build the lexicographic priority tuple for a state under the current mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, cost, actual)
        if mode == MODE_COMPREHENSIVE:
            return (cost + transfers * TRANSFER_PENALTY_M, actual)
        return (cost, actual)

    def _run(self):
        start = (self.source, None)
        self._info[start] = (0.0, 0, 0.0)
        self._parent[start] = None

        pq = MinPQ(self.graph.node_count)
        pq.insert(start, self._priority(0.0, 0, 0.0))

        settled = set()
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state
            cost, transfers, actual = self._info[state]

            for edge in self.graph.adjacent(node):
                other = edge.other(node)
                new_transfers = transfers
                if line is not None and edge.line != line:
                    new_transfers += 1
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                nstate = (other, edge.line)
                if nstate in settled:
                    continue

                penalty = PREFERENCE_PENALTY_M if preferred and edge.line not in preferred else 0.0
                cand = (cost + edge.weight + penalty, new_transfers, actual + edge.weight)
                old = self._info.get(nstate)
                if old is None or self._priority(*cand) < self._priority(*old):
                    self._info[nstate] = cand
                    self._parent[nstate] = (state, edge)
                    pq.insert(nstate, self._priority(*cand))

        # Pick the best state for every reachable station.
        for state, cand in self._info.items():
            node = state[0]
            current = self._best_state.get(node)
            if current is None or self._priority(*cand) < self._priority(*self._info[current]):
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._info[state][2]

    def has_path_to(self, target):
        """Return True if the target station is reachable under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the station sequence and the connection sequence from source to target.

        Returns:
            (list of station numbers, list of Edge objects oriented along the path).
            For source == target the edge list is empty.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            raise PathNotFoundError(f"No path found to station number {target}")

        chain = []
        cur = state
        while True:
            chain.append(cur)
            parent = self._parent[cur]
            if parent is None:
                break
            prev_state, edge = parent
            chain.append(None)  # placeholder to keep structure simple below
            chain.pop()
            chain[-1] = cur
            self._pending_edge = None
            cur = prev_state
            # record the edge that led to the previous state's successor
            chain_edges_marker = (prev_state, edge, cur)
            chain.append(chain_edges_marker)

        # Rebuild the sequences from the chain (states and edge markers alternate).
        states = []
        raw_edges = []
        for item in chain:
            if isinstance(item, tuple) and len(item) == 3 and isinstance(item[1], Edge):
                raw_edges.append(item)
            else:
                states.append(item)
        states.reverse()
        raw_edges.reverse()

        nodes = [s[0] for s in states]
        oriented = []
        for prev_state, edge, next_state in raw_edges:
            oriented.append(Edge(prev_state[0], next_state[0], edge.distance, edge.line))
        return nodes, oriented

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``.

        Raises:
            PathNotFoundError: If the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            raise PathNotFoundError(f"No path found to station number {target}")
        return self._info[state][1]
