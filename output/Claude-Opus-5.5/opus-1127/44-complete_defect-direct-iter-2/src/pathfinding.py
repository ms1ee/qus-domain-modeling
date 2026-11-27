"""Path calculation: priority queue and Dijkstra-based shortest path search."""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance (meters) charged per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Multiplicative penalty for edges not on a preferred line.
NON_PREFERRED_LINE_FACTOR = 1.5


class MinPQ:
    """Heap based minimum priority queue (stable for equal priorities)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    insert = push

    def pop(self):
        if not self._heap:
            raise IndexError("pop from empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty priority queue")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


def _norm_line(line):
    return "".join(str(line).split()).lower()


class PathfindingConfig:
    """Configuration of the path search."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def validate(self):
        if self.mode not in VALID_MODES:
            raise ValueError("Invalid mode '%s', expected one of %s" % (self.mode, ", ".join(VALID_MODES)))
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int) or self.max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")


class ShortestPath:
    """Dijkstra shortest path search from a single source station number.

    The search runs over (station, current line[, transfers]) states, which
    makes transfers at multi-line interchange stations explicit and allows
    least-transfer / comprehensive optimization, transfer limits and line
    preferences.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        self._preferred = {_norm_line(l) for l in self.config.preferred_lines if str(l).strip()}
        self.dist_to = {v: float("inf") for v in graph.vertices()}
        self.dist_to[source] = 0
        self._edge_to = {}
        self._node_state = {}
        self._run()

    def _key(self, effective, transfers, real):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, effective, real)
        if mode == "comprehensive":
            return (effective + transfers * TRANSFER_PENALTY_METERS, transfers, real)
        return (effective, transfers, real)

    def _factor(self, line):
        if not self._preferred:
            return 1.0
        return 1.0 if _norm_line(line) in self._preferred else NON_PREFERRED_LINE_FACTOR

    def _run(self):
        track = self.config.max_transfers is not None
        limit = self.config.max_transfers
        start = (self.source, None, 0) if track else (self.source, None)
        info = {start: (0, 0, 0)}  # state -> (effective, transfers, real)
        best = {start: self._key(0, 0, 0)}
        self._edge_to[start] = None
        pq = MinPQ()
        pq.push(best[start], start)
        settled = set()
        while not pq.is_empty():
            key, state = pq.pop()
            if state in settled or key != best.get(state):
                continue
            settled.add(state)
            v, line = state[0], state[1]
            eff, trans, real = info[state]
            if v not in self._node_state:
                self._node_state[v] = state
                self.dist_to[v] = real
            for e in self.graph.adj(v):
                nt = trans + (1 if line is not None and e.line != line else 0)
                if track and nt > limit:
                    continue
                ns = (e.dest, e.line, nt) if track else (e.dest, e.line)
                if ns in settled:
                    continue
                ne = eff + e.weight * self._factor(e.line)
                nr = real + e.weight
                nk = self._key(ne, nt, nr)
                if ns not in best or nk < best[ns]:
                    best[ns] = nk
                    info[ns] = (ne, nt, nr)
                    self._edge_to[ns] = (state, e)
                    pq.push(nk, ns)
        self._info = info

    def has_path_to(self, target):
        return target in self._node_state

    def path_with_edges(self, target):
        """Return (station number sequence, edge sequence) from source to target."""
        if target not in self._node_state:
            return [], []
        edges = []
        state = self._node_state[target]
        while self._edge_to.get(state) is not None:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path (-1 if unreachable)."""
        if target not in self._node_state:
            return -1
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
