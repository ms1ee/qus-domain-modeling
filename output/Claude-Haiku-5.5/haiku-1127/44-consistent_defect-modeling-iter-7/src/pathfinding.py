"""
Path calculation for the Beijing Subway network.

Implements Dijkstra's algorithm with a heap-based priority queue (MinPQ).
The search runs over states (station number, line used to arrive), which
lets the algorithm detect transfers and enforce transfer limits.

Modes:
    shortest_distance: minimise total distance in meters.
    least_transfer:    minimise number of transfers first, distance second.
    comprehensive:     composite score = distance + penalty per transfer.

Line preference adds a penalty to edges that are not on a preferred line.
"""

import heapq
import itertools


MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite scoring constants (in meters-equivalent cost units).
TRANSFER_PENALTY_COMPREHENSIVE_M = 1500.0
TRANSFER_WEIGHT_LEAST_TRANSFER_M = 10_000_000.0  # larger than any realistic total distance
LINE_PREFERENCE_PENALTY_M = 300.0


class NoPathError(Exception):
    """Raised when no route exists between two stations under the given constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_COMPREHENSIVE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}'")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap minimum priority queue (ties broken by insertion order)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, item, priority):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return (item, priority) with the smallest priority.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return item, priority

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    @property
    def size(self):
        """Number of items currently in the queue."""
        return len(self._heap)


class ShortestPath:
    """Dijkstra's shortest path computation from a single source station.

    Attributes:
        dist_to: dict mapping station number -> total distance in meters of the
                 chosen path from the source (only for reachable stations).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Unknown source station number '{source}'")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._state_cost = {}
        self._state_distance = {}
        self._state_transfers = {}
        self._state_pred = {}      # state -> (previous state, Edge)
        self._best_state = {}      # station number -> best state reaching it
        self._run()

    def _edge_cost(self, edge, is_transfer):
        """Return the search cost of traversing an edge under the configured mode."""
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            cost = edge.weight
        elif mode == MODE_LEAST_TRANSFER:
            cost = edge.weight + (TRANSFER_WEIGHT_LEAST_TRANSFER_M if is_transfer else 0.0)
        else:
            cost = edge.weight + (TRANSFER_PENALTY_COMPREHENSIVE_M if is_transfer else 0.0)
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            cost += LINE_PREFERENCE_PENALTY_M
        return cost

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        start = (self.source, None)
        self._state_cost[start] = 0.0
        self._state_distance[start] = 0.0
        self._state_transfers[start] = 0
        self._best_state[self.source] = start

        pq = MinPQ()
        pq.insert(start, 0.0)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            state, cost = pq.del_min()
            if state in settled or cost > self._state_cost[state]:
                continue  # stale queue entry
            settled.add(state)
            node, line = state

            for edge in self.graph.neighbors(node):
                is_transfer = line is not None and edge.line != line
                new_transfers = self._state_transfers[state] + (1 if is_transfer else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                next_state = (edge.dest, edge.line)
                if next_state in settled:
                    continue
                new_cost = cost + self._edge_cost(edge, is_transfer)
                if next_state not in self._state_cost or new_cost < self._state_cost[next_state]:
                    self._state_cost[next_state] = new_cost
                    self._state_distance[next_state] = self._state_distance[state] + edge.weight
                    self._state_transfers[next_state] = new_transfers
                    self._state_pred[next_state] = (state, edge)
                    pq.insert(next_state, new_cost)
                    best = self._best_state.get(edge.dest)
                    if best is None or new_cost < self._state_cost[best]:
                        self._best_state[edge.dest] = next_state

        self.dist_to = {node: self._state_distance[st] for node, st in self._best_state.items()}

    def reachable(self, target):
        """Return True if the target station can be reached under the constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the complete path from the source to the target.

        The path is reconstructed by backtracking from the target and then reversed.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects along the path)

        Raises:
            NoPathError: If the target cannot be reached.
        """
        if target not in self._best_state:
            raise NoPathError(f"No path to station '{target}'")
        state = self._best_state[target]
        nodes = []
        edges = []
        while True:
            nodes.append(state[0])
            if state not in self._state_pred:
                break
            previous, edge = self._state_pred[state]
            edges.append(edge)
            state = previous
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the chosen path to the target.

        Raises:
            NoPathError: If the target cannot be reached.
        """
        if target not in self._best_state:
            raise NoPathError(f"No path to station '{target}'")
        return self._state_transfers[self._best_state[target]]
