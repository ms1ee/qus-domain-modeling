"""
Dijkstra-based shortest path computation with transfer awareness.

The search runs over states ``(station, current_line[, transfers])`` so that
line changes at interchange stations can be counted, limited
(``max_transfers``) and penalised (``least_transfer`` / ``comprehensive``
modes). A heap-based priority queue (``MinPQ``) gives O((V+E) log V).
"""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

#: Extra virtual cost (meters) per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
#: Weight multiplier for edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration of the path search."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        if isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines or [])

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Min priority queue backed by a binary heap (heapq)."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    insert = push

    def pop(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self.heap:
            raise IndexError("pop from empty priority queue")
        priority, _, item = heapq.heappop(self.heap)
        return priority, item

    del_min = pop

    def peek(self):
        if not self.heap:
            raise IndexError("peek from empty priority queue")
        priority, _, item = self.heap[0]
        return priority, item

    def is_empty(self):
        return not self.heap

    @property
    def size(self):
        return len(self.heap)

    def __len__(self):
        return len(self.heap)


class ShortestPath:
    """Single-source shortest paths from ``source`` (a station number)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}       # station -> actual distance (meters) of best path
        self.edge_to = {}       # station -> last Edge on best path
        self._best_state = {}   # station -> state
        self._parent = {}       # state -> (prev_state, edge)
        self._info = {}         # state -> (actual distance, transfers)
        self._preferred = set(self.config.preferred_lines)
        self._run()

    # ---- internals ------------------------------------------------------
    def _priority(self, weighted, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, weighted)
        if mode == "comprehensive":
            return (weighted + transfers * TRANSFER_PENALTY_METERS, transfers)
        return (weighted, transfers)

    def _edge_cost(self, edge):
        if self._preferred and edge.line in self._preferred:
            return edge.weight * PREFERRED_LINE_FACTOR
        return float(edge.weight)

    def _run(self):
        track_transfers = self.config.max_transfers is not None
        start = (self.source, None, 0 if track_transfers else None)
        best = {start: self._priority(0.0, 0)}
        weighted = {start: 0.0}
        self._info[start] = (0, 0)
        self._parent[start] = None
        visited = set()
        pq = MinPQ()
        pq.push(best[start], start)

        while not pq.is_empty():
            prio, state = pq.pop()
            if state in visited or prio > best.get(state, prio):
                continue
            visited.add(state)
            station, line, _ = state
            actual, transfers = self._info[state]
            if station not in self.dist_to:
                self.dist_to[station] = actual
                self._best_state[station] = state
                parent = self._parent[state]
                if parent is not None:
                    self.edge_to[station] = parent[1]

            for edge in self.graph.neighbors(station):
                new_t = transfers + (1 if (line is not None and edge.line != line) else 0)
                if track_transfers and new_t > self.config.max_transfers:
                    continue
                new_state = (edge.dest, edge.line, new_t if track_transfers else None)
                if new_state in visited:
                    continue
                new_w = weighted[state] + self._edge_cost(edge)
                new_prio = self._priority(new_w, new_t)
                if new_state not in best or new_prio < best[new_state]:
                    best[new_state] = new_prio
                    weighted[new_state] = new_w
                    self._info[new_state] = (actual + edge.weight, new_t)
                    self._parent[new_state] = (state, edge)
                    pq.push(new_prio, new_state)

    # ---- queries --------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to ``target``.

        Returns ``([], [])`` if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while self._parent.get(state) is not None:
            prev_state, edge = self._parent[state]
            edges.append(edge)
            state = prev_state
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to ``target``."""
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                count += 1
        return count
