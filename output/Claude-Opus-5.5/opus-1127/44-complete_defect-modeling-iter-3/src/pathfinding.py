"""Shortest path computation (Dijkstra with a heap-based priority queue).

The search runs over states ``(station, current line[, transfers])`` so that
transfers can be counted exactly, limited (``max_transfers``) and penalised
(``least_transfer`` / ``comprehensive`` modes).  Complexity is
O((V+E) log V) in the number of states, which is a small constant multiple
of the number of stations.
"""

import math

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance penalty of one transfer in comprehensive mode (meters).
TRANSFER_PENALTY_METERS = 3000
# Weight multiplier applied to edges on preferred lines.
PREFERENCE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=TRANSFER_PENALTY_METERS, preference_factor=PREFERENCE_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Binary min-heap priority queue.

    Items are stored with a monotonically increasing counter so that ties on
    the key never require comparing the items themselves.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def insert(self, key, item):
        entry = (key, self._counter, item)
        self._counter += 1
        heap = self._heap
        heap.append(entry)
        # sift up
        i = len(heap) - 1
        while i > 0:
            parent = (i - 1) // 2
            if heap[i][:2] < heap[parent][:2]:
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
            else:
                break

    push = insert

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        key, _, item = self._heap[0]
        return key, item

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key."""
        heap = self._heap
        if not heap:
            raise IndexError("Priority queue is empty")
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            # sift down
            n = len(heap)
            i = 0
            while True:
                left = 2 * i + 1
                if left >= n:
                    break
                smallest = left
                right = left + 1
                if right < n and heap[right][:2] < heap[left][:2]:
                    smallest = right
                if heap[smallest][:2] < heap[i][:2]:
                    heap[i], heap[smallest] = heap[smallest], heap[i]
                    i = smallest
                else:
                    break
        return top[0], top[2]

    pop = del_min

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Single-source optimal paths using Dijkstra's algorithm.

    :param graph: a ``models.Graph``
    :param source: source station number
    :param config: optional ``PathfindingConfig``
    """

    def __init__(self, graph, source, config=None):
        if config is None:
            config = PathfindingConfig()
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self.edge_to = {}
        self._best_state = {}
        self._parent = {}
        self._state_dist = {}
        self._state_wdist = {}
        self._state_transfers = {}
        self._run()

    # ------------------------------------------------------------------ core
    def _cost(self, weighted_distance, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, weighted_distance)
        if mode == "comprehensive":
            return (weighted_distance + transfers * self.config.transfer_penalty, transfers)
        return (weighted_distance, transfers)

    def _run(self):
        cfg = self.config
        limited = cfg.max_transfers is not None
        preferred = set(cfg.preferred_lines)
        factor = cfg.preference_factor

        start = (self.source, None, 0 if limited else None)
        self._state_dist[start] = 0
        self._state_wdist[start] = 0.0
        self._state_transfers[start] = 0
        best_cost = {start: self._cost(0.0, 0)}

        pq = MinPQ()
        pq.insert(best_cost[start], start)
        settled = set()

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled or cost > best_cost[state]:
                continue
            settled.add(state)
            node, line_in, _ = state
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = self._state_dist[state]
                if state in self._parent:
                    self.edge_to[node] = self._parent[state][1]

            t = self._state_transfers[state]
            wd = self._state_wdist[state]
            d = self._state_dist[state]
            for edge in self.graph.adjacent(node):
                nt = t + (1 if (line_in is not None and edge.line != line_in) else 0)
                if limited and nt > cfg.max_transfers:
                    continue
                ns = (edge.dest, edge.line, nt if limited else None)
                if ns in settled:
                    continue
                w = edge.weight * factor if (preferred and edge.line in preferred) else edge.weight
                nwd = wd + w
                nc = self._cost(nwd, nt)
                if ns not in best_cost or nc < best_cost[ns]:
                    best_cost[ns] = nc
                    self._state_wdist[ns] = nwd
                    self._state_dist[ns] = d + edge.weight
                    self._state_transfers[ns] = nt
                    self._parent[ns] = (state, edge)
                    pq.insert(nc, ns)

    # --------------------------------------------------------------- queries
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from the source to ``target``.

        ``stations`` is the ordered list of station numbers (including both
        endpoints); ``edges`` the ordered list of traversed edges.  Both lists
        are empty if ``target`` is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        edges = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the path to ``target`` (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        return self._state_transfers[self._best_state[target]]
