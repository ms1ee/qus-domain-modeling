"""
Path computation for the subway network.

Implements a priority-queue based Dijkstra search. The search runs over
states of the form (station number, line used to arrive), which allows the
algorithm to count transfers, enforce a maximum transfer limit, and apply
line preferences while still finding the optimal route.
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# In comprehensive mode, each transfer is treated as this many meters of extra cost.
TRANSFER_PENALTY_M = 1000.0
# When line preferences are set, each edge outside the preferred lines adds this cost.
PREFERENCE_PENALTY_M = 500.0


class PathfindingConfig:
    """
    Configuration for a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum number of allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """
    Min priority queue implemented on top of a binary heap (heapq).

    Items with equal priority are returned in insertion order, and items are
    never compared directly.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert an item with the given priority. O(log n)."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return (priority, item) with the smallest priority. O(log n)."""
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
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """
    Dijkstra-based optimal path computation from a source station.

    Attributes:
        source: Source station number.
        config: The PathfindingConfig used for the search.
        dist_to: dict mapping reachable station number -> actual distance in meters
                 along the chosen route.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not part of the graph")
        self._graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._parent = {}         # state -> (previous state, Edge)
        self._best_state = {}     # station number -> best state
        self._best_info = {}      # station number -> (distance, transfers, penalty)
        self._run()

    def _cost(self, dist, transfers, penalty):
        """Return the comparable cost tuple of a route according to the mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, dist + penalty)
        if mode == MODE_COMPREHENSIVE:
            return (dist + penalty + TRANSFER_PENALTY_M * transfers,)
        return (dist + penalty,)

    def _run(self):
        """Execute Dijkstra's algorithm over (station, arrival line) states."""
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        start = (self.source, None)
        infos = {start: (0, 0, 0.0)}
        costs = {start: self._cost(0, 0, 0.0)}
        pq = MinPQ()
        pq.insert(costs[start], start)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            vertex, arrival_line = state
            dist, transfers, penalty = infos[state]

            for edge in self._graph.adj(vertex):
                new_transfers = transfers
                if arrival_line is not None and edge.line != arrival_line:
                    new_transfers += 1
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                new_penalty = penalty
                if preferred and edge.line not in preferred:
                    new_penalty += PREFERENCE_PENALTY_M

                new_info = (dist + edge.distance, new_transfers, new_penalty)
                next_state = (edge.dest, edge.line)
                if next_state in settled:
                    continue

                new_cost = self._cost(*new_info)
                old_cost = costs.get(next_state)
                if old_cost is None or new_cost < old_cost:
                    costs[next_state] = new_cost
                    infos[next_state] = new_info
                    self._parent[next_state] = (state, edge)
                    pq.insert(new_cost, next_state)

        best_cost = {}
        for state in settled:
            vertex = state[0]
            cost = costs[state]
            if vertex not in best_cost or cost < best_cost[vertex]:
                best_cost[vertex] = cost
                self._best_state[vertex] = state
                self._best_info[vertex] = infos[state]

        for vertex, info in self._best_info.items():
            self.dist_to[vertex] = info[0]

    def has_path_to(self, target):
        """Return True if the target station is reachable within the configured limits."""
        return target in self._best_state

    def path_with_edges(self, target):
        """
        Reconstruct the route from the source to the target.

        Returns:
            (list of station numbers from source to target, list of Edge objects along the route)

        Raises:
            ValueError: If the target is unreachable.
        """
        if target not in self._best_state:
            raise ValueError(f"No path from station {self.source} to station {target}")

        state = self._best_state[target]
        vertices = [state[0]]
        edges = []
        while state in self._parent:
            previous, edge = self._parent[state]
            edges.append(edge)
            vertices.append(previous[0])
            state = previous

        vertices.reverse()
        edges.reverse()
        return vertices, edges

    def get_transfer_count(self, target):
        """
        Return the number of line changes on the optimal route to the target.

        Raises:
            ValueError: If the target is unreachable.
        """
        if target not in self._best_info:
            raise ValueError(f"No path from station {self.source} to station {target}")
        return self._best_info[target][1]
