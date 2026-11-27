"""Shortest path computation (Dijkstra with a heap-based priority queue).

Three query modes are supported:

* ``shortest_distance`` - minimise the total distance
* ``least_transfer``    - minimise the number of transfers, then distance
* ``comprehensive``     - minimise distance plus a penalty per transfer

The search runs over (station, current line[, transfers]) states, which
correctly handles multi-line interchange stations and allows enforcing a
maximum transfer limit and line preferences.
"""

import math

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")


class MinPQ:
    """Binary min-heap priority queue (stable for equal keys)."""

    def __init__(self):
        self._heap = []
        self._counter = 0

    def insert(self, key, item):
        entry = (key, self._counter, item)
        self._counter += 1
        heap = self._heap
        heap.append(entry)
        i = len(heap) - 1
        while i > 0:
            parent = (i - 1) // 2
            if heap[i][:2] < heap[parent][:2]:
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
            else:
                break

    push = insert

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            i = 0
            n = len(heap)
            while True:
                left = 2 * i + 1
                right = left + 1
                smallest = i
                if left < n and heap[left][:2] < heap[smallest][:2]:
                    smallest = left
                if right < n and heap[right][:2] < heap[smallest][:2]:
                    smallest = right
                if smallest == i:
                    break
                heap[i], heap[smallest] = heap[smallest], heap[i]
                i = smallest
        return top[0], top[2]

    pop = del_min

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty priority queue")
        return self._heap[0][0], self._heap[0][2]

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode '%s', expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        else:
            preferred_lines = list(preferred_lines)
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = preferred_lines

    def __repr__(self):
        return "PathfindingConfig(mode=%r, max_transfers=%r, preferred_lines=%r)" % (
            self.mode, self.max_transfers, self.preferred_lines)


class ShortestPath:
    """Dijkstra single-source shortest paths on a ``Graph``."""

    TRANSFER_PENALTY = 3000      # meters-equivalent penalty per transfer (comprehensive mode)
    PREFERENCE_FACTOR = 0.7      # weight multiplier for preferred lines

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self.edge_to = {}
        self._prev = {}
        self._best_state = {}
        self._transfers = {}
        self._run()

    # ------------------------------------------------------------------
    @staticmethod
    def _make_key(mode, dist, transfers, weighted, penalty):
        if mode == "least_transfer":
            return (transfers, weighted, dist)
        if mode == "comprehensive":
            return (weighted + transfers * penalty, transfers, dist)
        return (dist, transfers, weighted)

    def _run(self):
        cfg = self.config
        mode = getattr(cfg, "mode", "shortest_distance")
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode '%s'" % mode)
        limit = getattr(cfg, "max_transfers", None)
        preferred = set(getattr(cfg, "preferred_lines", None) or [])
        penalty = self.TRANSFER_PENALTY
        factor = self.PREFERENCE_FACTOR
        track_k = limit is not None

        for v in self.graph.vertices():
            self.dist_to[v] = math.inf

        src = self.source
        start = (src, None, 0 if track_k else None)
        comps = {start: (0, 0, 0.0)}
        keys = {start: self._make_key(mode, 0, 0, 0.0, penalty)}
        settled = []
        settled_set = set()
        pq = MinPQ()
        pq.insert(keys[start], start)

        while not pq.is_empty():
            key, s = pq.del_min()
            if s in settled_set or key != keys.get(s):
                continue
            settled_set.add(s)
            settled.append(s)
            node, line, _ = s
            d, t, w = comps[s]
            for e in self.graph.adj(node):
                changed = line is not None and e.line != line
                nt = t + 1 if changed else t
                if track_k and nt > limit:
                    continue
                ns = (e.dest, e.line, nt if track_k else None)
                if ns in settled_set:
                    continue
                nd = d + e.weight
                nw = w + e.weight * (factor if e.line in preferred else 1.0)
                nk = self._make_key(mode, nd, nt, nw, penalty)
                old = keys.get(ns)
                if old is None or nk < old:
                    keys[ns] = nk
                    comps[ns] = (nd, nt, nw)
                    self._prev[ns] = (s, e)
                    pq.insert(nk, ns)

        # choose the best state for every station
        best_key = {}
        for s in settled:
            node = s[0]
            k = keys[s]
            if node not in best_key or k < best_key[node]:
                best_key[node] = k
                self._best_state[node] = s
        for node, s in self._best_state.items():
            d, t, _ = comps[s]
            self.dist_to[node] = d
            self._transfers[node] = t
            prev = self._prev.get(s)
            if prev is not None:
                self.edge_to[node] = prev[1]

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
        s = self._best_state[target]
        while s in self._prev:
            prev_state, e = self._prev[s]
            edges.append(e)
            s = prev_state
        edges.reverse()
        nodes = [self.source] + [e.dest for e in edges]
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the path to ``target`` (0 if unreachable)."""
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count

    def get_transfer_stations(self, target):
        """Station numbers where a line change happens."""
        nodes, edges = self.path_with_edges(target)
        return [nodes[i] for i in range(1, len(edges)) if edges[i].line != edges[i - 1].line]

    def get_lines(self, target):
        """Ordered list of distinct lines used on the path."""
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
