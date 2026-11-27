"""Shortest path computation (Dijkstra) on the subway graph."""

INF = float("inf")

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Extra cost (meters) applied per transfer in comprehensive mode,
# modelling walking distance / time at interchange stations.
TRANSFER_PENALTY = 3000
# Weight multiplier for edges on preferred lines.
PREFERENCE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError("Unknown mode: %r" % (mode,))
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    def is_default(self):
        return (self.mode == "shortest_distance" and self.max_transfers is None
                and not self.preferred_lines)


class MinPQ:
    """Binary-heap minimum priority queue."""

    def __init__(self):
        self.heap = []

    def __len__(self):
        return len(self.heap)

    def is_empty(self):
        return not self.heap

    def push(self, item):
        heap = self.heap
        heap.append(item)
        i = len(heap) - 1
        while i > 0:
            parent = (i - 1) // 2
            if heap[i] < heap[parent]:
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
            else:
                break

    def pop(self):
        heap = self.heap
        if not heap:
            raise IndexError("pop from empty MinPQ")
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            i, n = 0, len(heap)
            while True:
                left, right, smallest = 2 * i + 1, 2 * i + 2, i
                if left < n and heap[left] < heap[smallest]:
                    smallest = left
                if right < n and heap[right] < heap[smallest]:
                    smallest = right
                if smallest == i:
                    break
                heap[i], heap[smallest] = heap[smallest], heap[i]
                i = smallest
        return top

    def peek(self):
        if not self.heap:
            raise IndexError("peek from empty MinPQ")
        return self.heap[0]


class ShortestPath:
    """Dijkstra single-source shortest paths from station number ``source``.

    ``dist_to`` maps every known station number to the actual distance
    (meters) of the selected path, or ``inf`` if unreachable.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._node_state = {}   # node -> final state
        self._parent = {}       # state -> (prev_state, edge) or None
        if self.config.is_default():
            self._run_simple()
        else:
            self._run_advanced()

    # ------------------------------------------------------------------
    def _run_simple(self):
        """Classic Dijkstra by distance using a simple linear scan."""
        dist = {v: INF for v in self.graph.vertices()}
        dist[self.source] = 0
        visited = set()
        self._parent[self.source] = None
        while True:
            u, best = None, INF
            for v, d in dist.items():
                if v not in visited and d < best:
                    u, best = v, d
            if u is None:
                break
            visited.add(u)
            self._node_state[u] = u
            for e in self.graph.edges_from(u):
                nd = best + e.weight
                if nd < dist.get(e.dest, INF):
                    dist[e.dest] = nd
                    self._parent[e.dest] = (u, e)
        self.dist_to = dist

    def _edge_cost(self, edge):
        w = edge.weight
        if self.config.preferred_lines and edge.line in self.config.preferred_lines:
            w = w * PREFERENCE_FACTOR
        return w

    def _key(self, eff, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, eff)
        if mode == "comprehensive":
            return (eff + transfers * TRANSFER_PENALTY, transfers)
        return (eff, transfers)

    def _run_advanced(self):
        """Dijkstra on (station, line[, transfers]) states with a MinPQ."""
        max_t = self.config.max_transfers
        dist = {v: INF for v in self.graph.vertices()}
        dist[self.source] = INF
        start = (self.source, None, 0)
        g = {start: (0, 0, 0)}  # state -> (effective cost, transfers, actual)
        self._parent[start] = None
        pq = MinPQ()
        counter = 0
        pq.push((self._key(0, 0), counter, start))
        settled = set()
        while not pq.is_empty():
            key, _, state = pq.pop()
            if state in settled:
                continue
            settled.add(state)
            node, line, _t = state
            eff, transfers, actual = g[state]
            if node not in self._node_state:
                self._node_state[node] = state
                dist[node] = actual
            for e in self.graph.edges_from(node):
                nt = transfers + (1 if line is not None and e.line != line else 0)
                if max_t is not None and nt > max_t:
                    continue
                nstate = (e.dest, e.line, nt if max_t is not None else 0)
                if nstate in settled:
                    continue
                neff = eff + self._edge_cost(e)
                nkey = self._key(neff, nt)
                old = g.get(nstate)
                if old is None or nkey < self._key(old[0], old[1]):
                    g[nstate] = (neff, nt, actual + e.weight)
                    self._parent[nstate] = (state, e)
                    counter += 1
                    pq.push((nkey, counter, nstate))
        self.dist_to = dist

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._node_state

    def path_with_edges(self, target):
        """Return (station numbers from source to target, edges used).

        Returns ([], []) if the target is unreachable.
        """
        if target not in self._node_state:
            return [], []
        state = self._node_state[target]
        edges = []
        while True:
            entry = self._parent.get(state)
            if entry is None:
                break
            prev, edge = entry
            edges.append(edge)
            state = prev
        edges.reverse()
        if not edges:
            return [target], []
        nodes = [edges[0].source] + [e.dest for e in edges]
        return nodes, edges

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
