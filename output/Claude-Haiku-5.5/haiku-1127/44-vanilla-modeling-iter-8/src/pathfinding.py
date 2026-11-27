"""Path-finding algorithms for the subway network.

Dijkstra's algorithm is run on a state graph whose states are
``(station_number, arriving_line, transfer_count)``. Keeping the arriving line in
the state allows transfers (line changes) to be detected and penalised exactly.
A binary-heap priority queue (``MinPQ``) gives O((V+E) log V) behaviour.
"""

import heapq
import itertools
import math

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Cost constants (all in meters, the base unit of the path cost).
DEFAULT_TRANSFER_PENALTY_M = 1500.0      # comprehensive mode: cost of one transfer
LEAST_TRANSFER_WEIGHT_M = 1.0e9          # least_transfer mode: dominates any distance
TIE_BREAK_TRANSFER_M = 0.001             # shortest_distance mode: breaks ties by transfers
PREFERRED_LINE_PENALTY_M = 300.0         # penalty for riding a non-preferred line


class PathNotFoundError(Exception):
    """Raised when no path satisfying the constraints exists."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of preferred line names (empty means no preference).
        transfer_penalty_m: Composite-score penalty per transfer, in meters.
        preferred_line_penalty_m: Extra cost per edge on a non-preferred line.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None,
                 transfer_penalty_m=DEFAULT_TRANSFER_PENALTY_M,
                 preferred_line_penalty_m=PREFERRED_LINE_PENALTY_M):
        if mode not in VALID_MODES:
            raise ValueError("Unsupported mode %r, expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty_m = float(transfer_penalty_m)
        self.preferred_line_penalty_m = float(preferred_line_penalty_m)

    def transfer_cost(self):
        """Extra cost added when a transfer happens, depending on the mode."""
        if self.mode == MODE_LEAST_TRANSFER:
            return LEAST_TRANSFER_WEIGHT_M
        if self.mode == MODE_COMPREHENSIVE:
            return self.transfer_penalty_m
        return TIE_BREAK_TRANSFER_M

    def edge_cost(self, edge, is_transfer):
        """Cost of traversing ``edge`` under this configuration."""
        cost = edge.weight
        if is_transfer:
            cost += self.transfer_cost()
        if self.preferred_lines and edge.line not in self.preferred_lines:
            cost += self.preferred_line_penalty_m
        return cost


class MinPQ:
    """Min priority queue implemented on top of a binary heap (``heapq``)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()  # tie-breaker so items are never compared

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("min_priority of an empty priority queue")
        return self._heap[0][0]

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    Attributes:
        dist_to: dict mapping station number -> total distance in meters of the
            selected path from the source (computed for reachable stations).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError("Source station number %r is not in the graph" % (source,))
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}       # station number -> best state reaching it
        self._best_transfers = {}   # station number -> transfer count of best state
        self._prev = {}             # state -> (previous state, edge used)
        self._search()

    def _search(self):
        """Run Dijkstra's algorithm over the (station, line, transfers) state graph."""
        config = self.config
        track_transfers = config.max_transfers is not None
        start = (self.source, None, 0)
        best_cost = {start: 0.0}
        info = {start: (0.0, 0.0, 0)}  # state -> (cost, distance, transfers)
        settled = set()
        pq = MinPQ()
        pq.insert(0.0, start)

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, _ = state
            _, distance, transfers = info[state]

            # The first settled state of a station is its cheapest one.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = distance
                self._best_transfers[node] = transfers

            for edge in self.graph.adjacent(node):
                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + (1 if is_transfer else 0)
                if config.max_transfers is not None and new_transfers > config.max_transfers:
                    continue
                key_t = new_transfers if track_transfers else 0
                next_state = (edge.dest, edge.line, key_t)
                if next_state in settled:
                    continue
                new_cost = cost + config.edge_cost(edge, is_transfer)
                if new_cost < best_cost.get(next_state, math.inf):
                    best_cost[next_state] = new_cost
                    info[next_state] = (new_cost, distance + edge.weight, new_transfers)
                    self._prev[next_state] = (state, edge)
                    pq.insert(new_cost, next_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source under the constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the distance in meters of the path to ``target``."""
        if target not in self.dist_to:
            raise PathNotFoundError("No path from station %r to station %r" % (self.source, target))
        return self.dist_to[target]

    def path_with_edges(self, target):
        """Return the station numbers and edges of the path from source to ``target``.

        Returns:
            tuple: (list of station numbers in travel order, list of Edge objects in travel order).
            Both lists are empty if ``target`` is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes = []
        edges = []
        while True:
            nodes.append(state[0])
            if state not in self._prev:
                break
            prev_state, edge = self._prev[state]
            edges.append(edge)
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the path from source to ``target``."""
        if target not in self._best_transfers:
            raise PathNotFoundError("No path from station %r to station %r" % (self.source, target))
        return self._best_transfers[target]
