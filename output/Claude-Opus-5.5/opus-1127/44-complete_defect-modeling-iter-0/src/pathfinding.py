"""
Path calculation: heap-based priority queue and Dijkstra shortest path.

The search runs on (station, current line[, transfers]) states, which makes
transfers at multi-line interchange stations explicit and allows supporting
transfer limits, least-transfer mode and line preferences while keeping the
O((V+E) log V) behaviour of Dijkstra's algorithm.
"""

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty (meters) of one transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Weight factor applied to edges of preferred lines.
PREFERRED_LINE_FACTOR = 0.8

INF = float("inf")


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self.heap = []

    @property
    def size(self):
        return len(self.heap)

    def __len__(self):
        return len(self.heap)

    def is_empty(self):
        return not self.heap

    def insert(self, item):
        self.heap.append(item)
        self._swim(len(self.heap) - 1)

    def min(self):
        if not self.heap:
            raise IndexError("Priority queue underflow")
        return self.heap[0]

    def del_min(self):
        if not self.heap:
            raise IndexError("Priority queue underflow")
        top = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self._sink(0)
        return top

    def _swim(self, k):
        heap = self.heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k] < heap[parent]:
                heap[k], heap[parent] = heap[parent], heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        heap = self.heap
        n = len(heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            if left + 1 < n and heap[left + 1] < heap[left]:
                child = left + 1
            if heap[child] < heap[k]:
                heap[k], heap[child] = heap[child], heap[k]
                k = child
            else:
                break


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        if isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines or [])

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Dijkstra shortest path from a source station number."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        if self.config.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{self.config.mode}'")
        self._preferred = set(self.config.preferred_lines or [])
        self.dist_to = {v: INF for v in graph.vertices()}
        self.edge_to = {}
        self._keys = {}
        self._info = {}          # state -> (weighted cost, distance, transfers)
        self._state_edge_to = {}  # state -> (previous state, edge)
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------
    def _weighted(self, edge):
        if self._preferred and edge.line in self._preferred:
            return edge.weight * PREFERRED_LINE_FACTOR
        return edge.weight

    def _key(self, wdist, transfers, dist):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, wdist, dist)
        if mode == MODE_COMPREHENSIVE:
            return (wdist + transfers * TRANSFER_PENALTY_METERS, transfers, dist)
        return (wdist, transfers, dist)

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0 if limit is not None else None)
        self._info[start] = (0, 0, 0)
        self._keys[start] = self._key(0, 0, 0)
        pq = MinPQ()
        counter = 0
        pq.insert((self._keys[start], counter, start))
        while not pq.is_empty():
            key, _, state = pq.del_min()
            if key > self._keys[state]:
                continue  # stale entry (lazy deletion)
            node, line, _ = state
            wd, d, t = self._info[state]
            for e in self.graph.adjacent(node):
                if e.dest == node:
                    continue
                switching = line is not None and e.line is not None and e.line != line
                nt = t + (1 if switching else 0)
                if limit is not None and nt > limit:
                    continue
                new_line = e.line if e.line is not None else line
                ns = (e.dest, new_line, nt if limit is not None else None)
                nwd = wd + self._weighted(e)
                nd = d + e.weight
                nk = self._key(nwd, nt, nd)
                old = self._keys.get(ns)
                if old is None or nk < old:
                    self._keys[ns] = nk
                    self._info[ns] = (nwd, nd, nt)
                    self._state_edge_to[ns] = (state, e)
                    counter += 1
                    pq.insert((nk, counter, ns))

        for state, key in self._keys.items():
            node = state[0]
            best = self._best_state.get(node)
            if best is None or key < self._keys[best]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._info[state][1]
            if state in self._state_edge_to:
                self.edge_to[node] = self._state_edge_to[state][1]

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Both lists are empty if the target is unreachable.
        """
        state = self._best_state.get(target)
        if state is None:
            return [], []
        edges = []
        while state in self._state_edge_to:
            prev, e = self._state_edge_to[state]
            edges.append(e)
            state = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the chosen path (-1 if unreachable)."""
        state = self._best_state.get(target)
        if state is None:
            return -1
        return self._info[state][2]
