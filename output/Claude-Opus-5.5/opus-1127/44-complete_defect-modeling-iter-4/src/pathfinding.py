"""
Shortest path computation (Dijkstra with a heap-based priority queue).

The search runs over (station, current line[, transfers]) states so that
transfers at multi-line interchange stations are detected correctly and
modes such as "least_transfer" or a maximum transfer limit can be honoured.
Complexity is O((V+E) log V) per line-state layer.
"""

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in meters) applied per transfer in "comprehensive" mode.
TRANSFER_PENALTY_METERS = 2000
# Weight factor applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary min-heap priority queue.

    Entries are (priority, insertion counter, item); the counter guarantees
    a stable order and avoids comparing items.
    """

    def __init__(self):
        self._heap = []
        self._counter = 0

    def __len__(self):
        return len(self._heap)

    def size(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def insert(self, priority, item):
        self._heap.append((priority, self._counter, item))
        self._counter += 1
        self._swim(len(self._heap) - 1)

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        p, _, item = self._heap[0]
        return p, item

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k][:2] < heap[parent][:2]:
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
            if right < n and heap[right][:2] < heap[left][:2]:
                child = right
            if heap[child][:2] < heap[k][:2]:
                heap[k], heap[child] = heap[child], heap[k]
                k = child
            else:
                break


class ShortestPath:
    """Dijkstra shortest path from a single source station.

    Attributes:
        dist_to: dict station number -> actual distance (meters) of the best
            path found under the configured mode.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        if self.config.mode not in VALID_MODES:
            raise ValueError(f"Unknown path query mode: {self.config.mode}")
        if self.config.max_transfers is not None and self.config.max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.dist_to = {}
        self.edge_to = {}          # state -> (previous state, edge)
        self._best_state = {}      # station -> settled state
        self._transfers_to = {}
        self._run()

    # ------------------------------------------------------------------
    def _key(self, weighted, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, weighted)
        if mode == "comprehensive":
            return (weighted + TRANSFER_PENALTY_METERS * transfers, transfers)
        return (weighted, transfers)

    def _edge_cost(self, edge):
        preferred = self.config.preferred_lines
        if preferred and edge.line in preferred:
            return edge.weight * PREFERRED_LINE_FACTOR
        return edge.weight

    def _run(self):
        max_t = self.config.max_transfers
        track = max_t is not None
        start = (self.source, None, 0)
        # state -> (key, weighted distance, actual distance, transfers)
        info = {start: (self._key(0, 0), 0, 0, 0)}
        pq = MinPQ()
        pq.insert(info[start][0], start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled or info[state][0] != key:
                continue
            settled.add(state)
            v, line, _ = state
            _, wd, actual, t = info[state]
            if v not in self.dist_to:
                self.dist_to[v] = actual
                self._best_state[v] = state
                self._transfers_to[v] = t
            for e in self.graph.adjacent(v):
                nt = t + (1 if line is not None and e.line != line else 0)
                if track and nt > max_t:
                    continue
                nstate = (e.dest, e.line, nt if track else 0)
                if nstate in settled:
                    continue
                nwd = wd + self._edge_cost(e)
                nkey = self._key(nwd, nt)
                old = info.get(nstate)
                if old is None or nkey < old[0]:
                    info[nstate] = (nkey, nwd, actual + e.weight, nt)
                    self.edge_to[nstate] = (state, e)
                    pq.insert(nkey, nstate)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) when the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while state in self.edge_to:
            prev, edge = self.edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to target (0 if none/unreachable)."""
        _, edges = self.path_with_edges(target)
        count = 0
        for prev, cur in zip(edges, edges[1:]):
            if prev.line != cur.line:
                count += 1
        return count
