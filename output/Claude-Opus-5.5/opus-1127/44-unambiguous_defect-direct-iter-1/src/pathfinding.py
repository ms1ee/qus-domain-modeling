"""Path calculation: priority queue and Dijkstra-based shortest path.

Dijkstra's algorithm runs on an expanded state space ``(station, line,
transfers)`` so that transfer counting, maximum transfer limits and line
preferences can be honoured while still using the priority queue to obtain
O((V+E) log V) behaviour (with V/E the sizes of the expanded state graph).
"""

import itertools
import re

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for one transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Effective weight multiplier for edges on a preferred line.
PREFERENCE_FACTOR = 0.8


def normalize_line_name(name):
    """Normalise a line name for comparison ("Line 1" == "line1" == "1号线")."""
    if name is None:
        return ""
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    match = re.fullmatch(r"(\d+)号线", text)
    if match:
        return "line" + match.group(1)
    match = re.fullmatch(r"(\d+)", text)
    if match:
        return "line" + match.group(1)
    return text


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode {mode!r}; expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = [l for l in preferred_lines if l]

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self._heap = []

    def insert(self, item):
        heap = self._heap
        heap.append(item)
        i = len(heap) - 1
        while i > 0:
            parent = (i - 1) // 2
            if heap[i] < heap[parent]:
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
            else:
                break

    push = insert

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue underflow")
        return self._heap[0]

    def del_min(self):
        heap = self._heap
        if not heap:
            raise IndexError("Priority queue underflow")
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            n = len(heap)
            i = 0
            while True:
                left = 2 * i + 1
                right = left + 1
                smallest = i
                if left < n and heap[left] < heap[smallest]:
                    smallest = left
                if right < n and heap[right] < heap[smallest]:
                    smallest = right
                if smallest == i:
                    break
                heap[i], heap[smallest] = heap[smallest], heap[i]
                i = smallest
        return top

    pop = del_min

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Dijkstra shortest path from a single source station.

    Attributes:
        dist_to: dict station number -> real distance (meters) of the chosen
                 path (``inf`` if unreachable)
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._preferred = {normalize_line_name(l) for l in self.config.preferred_lines}
        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._edge_to = {}
        self._state_dist = {}
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------
    def _effective_weight(self, edge):
        if self._preferred and normalize_line_name(edge.line) in self._preferred:
            return edge.weight * PREFERENCE_FACTOR
        return float(edge.weight)

    def _make_cost(self, dist, eff, transfers):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, eff, dist)
        if mode == MODE_COMPREHENSIVE:
            return (eff + TRANSFER_PENALTY_METERS * transfers, transfers, dist)
        return (dist, transfers, eff)

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0)
        best_cost = {start: self._make_cost(0, 0.0, 0)}
        self._state_dist[start] = 0
        eff = {start: 0.0}
        trans = {start: 0}
        counter = itertools.count()
        pq = MinPQ()
        pq.insert((best_cost[start], next(counter), start))
        settled = set()

        while not pq.is_empty():
            cost, _, state = pq.del_min()
            if state in settled or cost != best_cost.get(state):
                continue
            settled.add(state)
            v, line, _ = state
            if v not in self._best_state:
                self._best_state[v] = state
                self.dist_to[v] = self._state_dist[state]
            for edge in self.graph.adj(v):
                w = edge.other(v)
                nt = trans[state] + (1 if line is not None and edge.line != line else 0)
                if limit is not None and nt > limit:
                    continue
                nkey = (w, edge.line, nt if limit is not None else 0)
                if nkey in settled:
                    continue
                nd = self._state_dist[state] + edge.weight
                ne = eff[state] + self._effective_weight(edge)
                nc = self._make_cost(nd, ne, nt)
                old = best_cost.get(nkey)
                if old is None or nc < old:
                    best_cost[nkey] = nc
                    self._state_dist[nkey] = nd
                    eff[nkey] = ne
                    trans[nkey] = nt
                    self._edge_to[nkey] = (state, edge)
                    pq.insert((nc, next(counter), nkey))

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) when the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes = [target]
        edges = []
        while state in self._edge_to:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            nodes.append(prev[0])
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the chosen path (0 if none/unreachable)."""
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)


def count_transfers(edges):
    count = 0
    for prev, cur in zip(edges, edges[1:]):
        if prev.line != cur.line:
            count += 1
    return count
