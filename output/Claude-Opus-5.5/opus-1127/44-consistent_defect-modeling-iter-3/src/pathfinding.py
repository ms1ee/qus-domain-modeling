"""Dijkstra based path computation over the subway graph."""

import heapq
import math

MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Penalty (in meters) equivalent to one transfer for comprehensive scoring:
# 5 minutes per transfer at 1.5 minutes per kilometer.
TRANSFER_PENALTY_METERS = 5.0 / 1.5 * 1000.0
# Weight multiplier applied to edges on non-preferred lines.
NON_PREFERRED_FACTOR = 1.5


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None,
                 preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary-heap min priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = 0

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, self._counter, item))
        self._counter += 1

    insert = push

    def pop(self):
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def del_min(self):
        return self.pop()

    def is_empty(self):
        return not self._heap

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


def _norm(line):
    return "".join(str(line).split()).lower() if line is not None else ""


class ShortestPath:
    """Dijkstra's algorithm with line-aware states (for transfer handling)."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        if self.config.mode not in MODES:
            raise ValueError(f"Unknown path mode: {self.config.mode}")
        if self.config.max_transfers is not None and self.config.max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self._preferred = {_norm(l) for l in self.config.preferred_lines if l}
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self.dist_to[source] = 0
        self._best_state = {}
        self._info = {}  # key -> [cost, eff, dist, transfers, parent, edge, line]
        self._run()

    # ------------------------------------------------------------------
    def _key(self, v, line, transfers):
        if self.config.max_transfers is not None:
            return (v, line, transfers)
        return (v, line, None)

    def _cost(self, eff, transfers):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, eff)
        if mode == "comprehensive":
            return (eff + transfers * TRANSFER_PENALTY_METERS, transfers)
        return (eff, transfers)

    def _edge_weight(self, edge):
        if not self._preferred or _norm(edge.line) in self._preferred:
            return edge.weight
        return edge.weight * NON_PREFERRED_FACTOR

    def _run(self):
        pq = MinPQ()
        start = self._key(self.source, None, 0)
        self._info[start] = [self._cost(0, 0), 0, 0, 0, None, None, None]
        pq.push(self._info[start][0], start)
        settled = set()
        max_t = self.config.max_transfers
        while not pq.is_empty():
            cost, key = pq.pop()
            if key in settled:
                continue
            info = self._info[key]
            if cost != info[0]:
                continue
            settled.add(key)
            v = key[0]
            _, eff, dist, transfers, _, _, line = info
            if v not in self._best_state:
                self._best_state[v] = key
                self.dist_to[v] = dist
            for edge in self.graph.edges_from(v):
                new_line = edge.line if edge.line is not None else line
                nt = transfers
                if line is not None and new_line != line:
                    nt += 1
                if max_t is not None and nt > max_t:
                    continue
                neff = eff + self._edge_weight(edge)
                nd = dist + edge.weight
                nkey = self._key(edge.dest, new_line, nt)
                if nkey in settled:
                    continue
                ncost = self._cost(neff, nt)
                old = self._info.get(nkey)
                if old is None or ncost < old[0]:
                    self._info[nkey] = [ncost, neff, nd, nt, key, edge, new_line]
                    pq.push(ncost, nkey)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return (station numbers from source to target, edges used)."""
        if target not in self._best_state:
            return [], []
        edges = []
        key = self._best_state[target]
        while key is not None:
            info = self._info[key]
            if info[5] is not None:
                edges.append(info[5])
            key = info[4]
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        if target not in self._best_state:
            return 0
        return self._info[self._best_state[target]][3]
