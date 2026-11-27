"""
Shortest path computation (Dijkstra's algorithm with a heap priority queue).

The search runs over states (station, current line[, transfers]) so that
transfers can be counted correctly at multi-line interchange stations and
so that maximum-transfer limits and different optimisation modes can be
supported. Complexity is O((V+E) log V) per line-state layer.
"""

import heapq
import itertools

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Minimum priority queue backed by a binary heap."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        """Remove and return (priority, item) with the smallest priority."""
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

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Dijkstra shortest paths from a single source station number."""

    TRANSFER_PENALTY = 5000      # meters-equivalent penalty per transfer (comprehensive mode)
    PREFERENCE_FACTOR = 0.8      # weight multiplier for preferred lines (comprehensive mode)

    def __init__(self, graph, source, config=None):
        if source not in graph.graph:
            raise ValueError(f"Source station {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: float("inf") for v in graph.vertices()}
        self.dist_to[source] = 0
        self._labels = {}
        self._edge_to = {}
        self._best_state = {}
        self._run()

    def _key(self, dist, transfers, nonpref, weighted):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, dist, nonpref)
        if mode == "comprehensive":
            return (weighted, transfers, dist)
        return (dist, nonpref, transfers)

    def _run(self):
        max_t = self.config.max_transfers
        preferred = set(self.config.preferred_lines)
        pq = MinPQ()
        start = (self.source, None, 0)
        start_key = self._key(0, 0, 0, 0)
        self._labels[start] = (start_key, 0, 0, 0, 0)
        self._edge_to[start] = None
        pq.push(start_key, start)
        settled = set()

        while not pq.is_empty():
            key, state = pq.pop()
            if state in settled:
                continue
            if self._labels[state][0] != key:
                continue
            settled.add(state)
            node, line, _ = state
            _, dist, trans, nonpref, weighted = self._labels[state]

            best = self._best_state.get(node)
            if best is None or key < self._labels[best][0]:
                self._best_state[node] = state

            for e in self.graph.adj(node):
                is_transfer = line is not None and e.line != line
                nt = trans + (1 if is_transfer else 0)
                if max_t is not None and nt > max_t:
                    continue
                nd = dist + e.distance
                is_pref = e.line in preferred
                nnp = nonpref + (e.distance if preferred and not is_pref else 0)
                nw = (weighted + e.distance * (self.PREFERENCE_FACTOR if is_pref else 1)
                      + (self.TRANSFER_PENALTY if is_transfer else 0))
                nstate = (e.dest, e.line, nt if max_t is not None else 0)
                if nstate in settled:
                    continue
                nkey = self._key(nd, nt, nnp, nw)
                old = self._labels.get(nstate)
                if old is None or nkey < old[0]:
                    self._labels[nstate] = (nkey, nd, nt, nnp, nw)
                    self._edge_to[nstate] = (state, e)
                    pq.push(nkey, nstate)

        for node, state in self._best_state.items():
            self.dist_to[node] = self._labels[state][1]

    # ---- queries ---------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        edges = []
        state = self._best_state[target]
        while self._edge_to.get(state) is not None:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
