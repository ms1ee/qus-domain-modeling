"""Dijkstra-based path computation with transfer-aware modes."""

import math

from models import MinPQ

MODES = ("shortest_distance", "least_transfer", "comprehensive")
# Equivalent distance penalty (meters) of one transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 3000
# Weight multiplier applied to non-preferred lines when preferences exist.
NON_PREFERRED_FACTOR = 1.3


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Single-source shortest paths over a Graph from a station number."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self.dist_to[source] = 0
        self._final = {}
        self._parent = {}
        self._run()

    def _initial_key(self):
        return (0, 0) if self.config.mode == "least_transfer" else 0

    def _next_key(self, prev, edge, is_transfer):
        w = edge.weight
        prefs = self.config.preferred_lines
        if prefs and edge.line not in prefs:
            w = w * NON_PREFERRED_FACTOR
        mode = self.config.mode
        if mode == "least_transfer":
            return (prev[0] + (1 if is_transfer else 0), prev[1] + w)
        if mode == "comprehensive":
            return prev + w + (TRANSFER_PENALTY_METERS if is_transfer else 0)
        return prev + w

    def _run(self):
        max_t = self.config.max_transfers
        track_t = max_t is not None
        start = (self.source, None, 0)
        best = {start: self._initial_key()}
        actual = {start: 0}
        parent = {start: (None, None)}
        settled = set()
        pq = MinPQ()
        pq.push(best[start], start)
        while not pq.is_empty():
            key, state = pq.pop()
            if state in settled:
                continue
            settled.add(state)
            node, line, t = state
            for e in self.graph.adj.get(node, []):
                is_transfer = line is not None and e.line != line
                nt = t + (1 if is_transfer else 0)
                if track_t and nt > max_t:
                    continue
                ns = (e.dest, e.line, nt if track_t else 0)
                if ns in settled:
                    continue
                nkey = self._next_key(key, e, is_transfer)
                if ns not in best or nkey < best[ns]:
                    best[ns] = nkey
                    actual[ns] = actual[state] + e.weight
                    parent[ns] = (state, e)
                    pq.push(nkey, ns)

        node_best = {}
        for state in settled:
            node = state[0]
            if node not in node_best or best[state] < best[node_best[node]]:
                node_best[node] = state
        # Source itself is always reached with zero cost.
        node_best[self.source] = start
        self._final = node_best
        self._parent = parent
        for node, state in node_best.items():
            self.dist_to[node] = actual[state]

    def has_path_to(self, target):
        return target in self._final

    def path_with_edges(self, target):
        """Return (station number list, edge list) from source to target."""
        if target not in self._final:
            return [], []
        edges = []
        state = self._final[target]
        while True:
            prev, edge = self._parent[state]
            if prev is None:
                break
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
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
