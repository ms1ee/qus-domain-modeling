"""Dijkstra-based shortest path computation with transfer awareness."""

MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Comprehensive mode: one transfer is considered equivalent to this many meters.
TRANSFER_PENALTY_METERS = 3000
# Extra cost factor applied to distance travelled on non-preferred lines.
NON_PREFERRED_FACTOR = 0.2


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = 0

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def insert(self, priority, item):
        self._heap.append((priority, self._counter, item))
        self._counter += 1
        self._swim(len(self._heap) - 1)

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i, j):
        return self._heap[i][:2] < self._heap[j][:2]

    def _swim(self, k):
        while k > 0:
            p = (k - 1) // 2
            if self._less(k, p):
                self._heap[k], self._heap[p] = self._heap[p], self._heap[k]
                k = p
            else:
                break

    def _sink(self, k):
        n = len(self._heap)
        while True:
            l = 2 * k + 1
            if l >= n:
                break
            c = l
            if l + 1 < n and self._less(l + 1, l):
                c = l + 1
            if self._less(c, k):
                self._heap[k], self._heap[c] = self._heap[c], self._heap[k]
                k = c
            else:
                break


class ShortestPath:
    """Dijkstra's algorithm over (station, line) states from a source station."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self._pref = set(self.config.preferred_lines)
        self._max_t = self.config.max_transfers
        self._best = {}     # state -> cost
        self._info = {}     # state -> (distance, transfers, non_preferred_distance)
        self._parent = {}   # state -> (prev_state, edge)
        self._target_state = {}
        self.dist_to = {v: float("inf") for v in graph.vertices()}
        self._run()

    def _state(self, station, line, transfers):
        if self._max_t is not None:
            return (station, line, transfers)
        return (station, line)

    def _cost(self, d, t, np_):
        mode = self.config.mode
        if mode == "least_transfer":
            return (t, d, np_)
        if mode == "comprehensive":
            score = d + t * TRANSFER_PENALTY_METERS + np_ * NON_PREFERRED_FACTOR
            return (score, d, t)
        return (d, t, np_)

    def _run(self):
        start = self._state(self.source, None, 0)
        self._best[start] = self._cost(0, 0, 0)
        self._info[start] = (0, 0, 0)
        self._parent[start] = None
        pq = MinPQ()
        pq.insert(self._best[start], start)
        while not pq.is_empty():
            cost, state = pq.del_min()
            if cost > self._best.get(state, cost):
                continue
            station, line = state[0], state[1]
            d, t, np_ = self._info[state]
            for e in self.graph.adj(station):
                nt = t + (1 if line is not None and e.line != line else 0)
                if self._max_t is not None and nt > self._max_t:
                    continue
                nd = d + e.weight
                nnp = np_ + (e.weight if self._pref and e.line not in self._pref else 0)
                nc = self._cost(nd, nt, nnp)
                ns = self._state(e.dest, e.line, nt)
                if ns not in self._best or nc < self._best[ns]:
                    self._best[ns] = nc
                    self._info[ns] = (nd, nt, nnp)
                    self._parent[ns] = (state, e)
                    pq.insert(nc, ns)
        for state, cost in self._best.items():
            st = state[0]
            cur = self._target_state.get(st)
            if cur is None or cost < self._best[cur]:
                self._target_state[st] = state
        for st, state in self._target_state.items():
            self.dist_to[st] = self._info[state][0]

    def has_path_to(self, target):
        return target in self._target_state

    def path_with_edges(self, target):
        """Return (stations, edges) from source to target; ([], []) if unreachable."""
        if target not in self._target_state:
            return [], []
        edges = []
        state = self._target_state[target]
        while self._parent.get(state) is not None:
            prev, e = self._parent[state]
            edges.append(e)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
