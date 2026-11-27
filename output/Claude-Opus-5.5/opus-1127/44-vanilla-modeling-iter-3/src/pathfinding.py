"""Path calculation: priority queue and Dijkstra-based shortest path search.

The search runs over states ``(station, arrival line[, transfers])`` so that
transfers at multi-line interchange stations are handled exactly. Costs are
tuples compared lexicographically, which lets the same algorithm serve the
three query modes:

* ``shortest_distance`` – minimise distance, then transfers
* ``least_transfer``    – minimise transfers, then distance
* ``comprehensive``     – minimise distance + transfer penalty
"""

import math

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) of one transfer in comprehensive mode
# (~5 minutes of transfer time at ~1.5 min/km).
TRANSFER_PENALTY_METERS = 3500
# Weight multiplier applied to non-preferred lines when a preference is set.
NON_PREFERRED_LINE_FACTOR = 1.3


class MinPQ:
    """Binary-heap based minimum priority queue.

    Items are stored with a key; ties are broken by insertion order so the
    items themselves never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def insert(self, key, item=None):
        entry = (key, self._counter, item)
        self._counter += 1
        self._heap.append(entry)
        self._swim(len(self._heap) - 1)

    push = insert

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        key, _, item = self._heap[0]
        return key, item

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[0], top[2]

    pop = del_min

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k] < heap[parent]:
                heap[k], heap[parent] = heap[parent], heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        heap = self._heap
        n = len(heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and heap[right] < heap[left]:
                child = right
            if heap[child] < heap[k]:
                heap[k], heap[child] = heap[child], heap[k]
                k = child
            else:
                break


class PathfindingConfig:
    """Configuration for a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None, transfer_penalty=TRANSFER_PENALTY_METERS,
                 non_preferred_factor=NON_PREFERRED_LINE_FACTOR):
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines)
        self.transfer_penalty = transfer_penalty
        self.non_preferred_factor = non_preferred_factor

    def __repr__(self):
        return ("PathfindingConfig(mode={!r}, max_transfers={!r}, "
                "preferred_lines={!r})").format(
                    self.mode, self.max_transfers, self.preferred_lines)


class ShortestPath:
    """Dijkstra shortest path from a single source station number."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        mode = self.config.mode or MODE_SHORTEST_DISTANCE
        if mode not in VALID_MODES:
            raise ValueError("Unknown path query mode: {!r}".format(mode))
        self._mode = mode
        max_t = self.config.max_transfers
        if max_t is not None and max_t < 0:
            raise ValueError("max_transfers must be non-negative")
        self._max_transfers = max_t
        self._preferred = set(self.config.preferred_lines or [])

        self.dist_to = {}       # station number -> actual distance (meters)
        self._best_state = {}   # station number -> best state
        self._parent = {}       # state -> (previous state, Edge)
        self._state_info = {}   # state -> (effective dist, transfers, real dist)
        self._run()

    # ----- internal -------------------------------------------------------
    def _make_state(self, v, line, transfers):
        if self._max_transfers is not None:
            return (v, line, transfers)
        return (v, line, -1)

    def _cost(self, eff, transfers, real):
        if self._mode == MODE_LEAST_TRANSFER:
            return (transfers, eff, real)
        if self._mode == MODE_COMPREHENSIVE:
            return (eff + self.config.transfer_penalty * transfers, transfers, real)
        return (eff, transfers, real)

    def _edge_factor(self, line):
        if self._preferred and line not in self._preferred:
            return self.config.non_preferred_factor
        return 1

    def _run(self):
        pq = MinPQ()
        best_cost = {}
        settled = set()

        start = self._make_state(self.source, None, 0)
        self._state_info[start] = (0, 0, 0)
        start_cost = self._cost(0, 0, 0)
        best_cost[start] = start_cost
        pq.insert(start_cost, start)
        adj = self.graph.adj

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled or cost != best_cost.get(state):
                continue
            settled.add(state)
            v, line = state[0], state[1]
            eff, transfers, real = self._state_info[state]
            if v not in self._best_state:
                self._best_state[v] = state
                self.dist_to[v] = real

            for edge in adj.get(v, ()):
                new_t = transfers + (1 if line is not None and edge.line != line else 0)
                if self._max_transfers is not None and new_t > self._max_transfers:
                    continue
                new_state = self._make_state(edge.dest, edge.line, new_t)
                if new_state in settled:
                    continue
                new_eff = eff + edge.weight * self._edge_factor(edge.line)
                new_real = real + edge.weight
                new_cost = self._cost(new_eff, new_t, new_real)
                old = best_cost.get(new_state)
                if old is None or new_cost < old:
                    best_cost[new_state] = new_cost
                    self._state_info[new_state] = (new_eff, new_t, new_real)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

    # ----- queries --------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return (station numbers, edges) from source to target.

        Returns ([], []) when the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        edges = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count

    def get_lines(self, target):
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines

    def get_transfer_points(self, target):
        """List of (station number, from_line, to_line) for each transfer."""
        path, edges = self.path_with_edges(target)
        points = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                points.append((path[i], edges[i - 1].line, edges[i].line))
        return points
