"""Path calculation: priority queue and Dijkstra shortest path.

The search runs on an expanded state space ``(station, current line[,
transfers])`` so that transfers at multi-line interchange stations are
counted correctly and different optimisation modes are supported.
"""

import heapq
import itertools
import math

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class MinPQ:
    """Heap-based minimum priority queue."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min(self):
        if not self._heap:
            raise IndexError("min from empty priority queue")
        key, _, item = self._heap[0]
        return key, item

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


def _norm_line(name):
    return "".join(str(name).lower().split())


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=3000, preference_factor=0.3):
        if mode not in MODES:
            raise ValueError(f"Invalid mode '{mode}', must be one of {', '.join(MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def is_preferred(self, line):
        if not self.preferred_lines:
            return True
        n = _norm_line(line)
        return any(_norm_line(p) == n for p in self.preferred_lines)


class ShortestPath:
    """Dijkstra's shortest path from a single source station number."""

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station number {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self.dist_to[source] = 0
        # state -> [distance, transfers, non-preferred distance, parent_state, edge]
        self._info = {}
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------
    def _key(self, dist, transfers, nonpref):
        cfg = self.config
        pf = cfg.preference_factor if cfg.preferred_lines else 0.0
        if cfg.mode == "least_transfer":
            return (transfers, dist + pf * nonpref, dist)
        if cfg.mode == "comprehensive":
            return (dist + cfg.transfer_penalty * transfers + pf * nonpref, transfers, dist)
        return (dist, transfers, nonpref)

    def _run(self):
        cfg = self.config
        limited = cfg.max_transfers is not None
        start = (self.source, None, 0 if limited else None)
        self._info[start] = [0, 0, 0, None, None]
        pq = MinPQ()
        pq.insert(self._key(0, 0, 0), start)
        settled = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            v, line, _t = state
            d, tr, npd, _, _ = self._info[state]
            for e in self.graph.adj(v):
                w = e.dest
                ntr = tr + (1 if (line is not None and e.line != line) else 0)
                if limited and ntr > cfg.max_transfers:
                    continue
                ns = (w, e.line, ntr if limited else None)
                if ns in settled:
                    continue
                nd = d + e.weight
                nnp = npd + (0 if cfg.is_preferred(e.line) else e.weight)
                nk = self._key(nd, ntr, nnp)
                old = self._info.get(ns)
                if old is None or nk < self._key(old[0], old[1], old[2]):
                    self._info[ns] = [nd, ntr, nnp, state, e]
                    pq.insert(nk, ns)

        best_keys = {}
        for state in settled:
            v = state[0]
            info = self._info[state]
            k = self._key(info[0], info[1], info[2])
            if v not in best_keys or k < best_keys[v]:
                best_keys[v] = k
                self._best_state[v] = state
        self._best_state[self.source] = start
        for v, state in self._best_state.items():
            self.dist_to[v] = self._info[state][0]

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target."""
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while True:
            info = self._info[state]
            parent, edge = info[3], info[4]
            if parent is None:
                break
            edges.append(edge)
            state = parent
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the computed path to target."""
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)


def count_transfers(edges):
    transfers = 0
    for prev, cur in zip(edges, edges[1:]):
        if prev.line != cur.line:
            transfers += 1
    return transfers
