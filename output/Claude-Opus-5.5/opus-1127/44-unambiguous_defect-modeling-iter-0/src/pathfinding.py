"""Path calculation using Dijkstra's algorithm with a heap based priority queue.

The search runs over (station, current line[, transfers]) states so that
transfers at interchange stations can be counted and penalised exactly.
Complexity is O((V+E) log V) in the number of states.
"""

import heapq
import itertools
import math

from line_utils import canonical_line_key

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Distance-equivalent cost (meters) of one transfer in comprehensive mode.
DEFAULT_TRANSFER_PENALTY = 4000
# Weight multiplier applied to edges of preferred lines.
DEFAULT_PREFERENCE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration for path queries.

    Attributes:
        mode: one of ``VALID_MODES``.
        max_transfers: maximum allowed transfers (None = unlimited).
        preferred_lines: list of preferred line names.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None,
                 transfer_penalty=DEFAULT_TRANSFER_PENALTY,
                 preference_factor=DEFAULT_PREFERENCE_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode %r, expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            max_transfers = int(max_transfers)
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        else:
            preferred_lines = list(preferred_lines)
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = preferred_lines
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return "PathfindingConfig(mode=%r, max_transfers=%r, preferred_lines=%r)" % (
            self.mode, self.max_transfers, self.preferred_lines)


class MinPQ:
    """Minimum priority queue based on a binary heap (``heapq``)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    insert = push

    def pop(self):
        """Remove and return ``(priority, item)`` with the smallest priority."""
        if not self._heap:
            raise IndexError("pop from an empty priority queue")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    del_min = pop

    def peek(self):
        if not self._heap:
            raise IndexError("peek from an empty priority queue")
        priority, _, item = self._heap[0]
        return priority, item

    def is_empty(self):
        return not self._heap

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)


class ShortestPath:
    """Single-source path computation with Dijkstra's algorithm.

    Attributes:
        source: source station number.
        dist_to: dict station number -> actual distance (meters) of the best
                 route under the configured mode (``math.inf`` if unreachable).
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError("Source station %r is not in the graph" % (source,))
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: math.inf for v in graph.vertices()}
        self.dist_to[source] = 0
        self._transfer_to = {}
        self._final_state = {}
        self._edge_to = {}
        self._run()

    # ----- configuration helpers -----------------------------------
    def _preferred_keys(self):
        prefs = getattr(self.config, "preferred_lines", None) or []
        if isinstance(prefs, str):
            prefs = [p for p in prefs.split(",")]
        return {canonical_line_key(p) for p in prefs if p and str(p).strip()}

    def _key(self, dist, wdist, transfers):
        mode = getattr(self.config, "mode", MODE_SHORTEST_DISTANCE)
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, wdist, dist)
        if mode == MODE_COMPREHENSIVE:
            penalty = getattr(self.config, "transfer_penalty", DEFAULT_TRANSFER_PENALTY)
            return (wdist + transfers * penalty, transfers, dist)
        return (dist, transfers, wdist)

    # ----- Dijkstra -------------------------------------------------
    def _run(self):
        max_transfers = getattr(self.config, "max_transfers", None)
        limited = max_transfers is not None
        factor = getattr(self.config, "preference_factor", DEFAULT_PREFERENCE_FACTOR)
        preferred = self._preferred_keys()

        start = (self.source, None, 0 if limited else None)
        best = {start: self._key(0, 0, 0)}
        settled = set()
        pq = MinPQ()
        pq.push(best[start], (start, 0, 0, 0))

        while pq:
            key, (state, dist, wdist, transfers) = pq.pop()
            if state in settled:
                continue
            settled.add(state)
            v, cur_line = state[0], state[1]
            if v not in self._final_state:
                # First settled state of a station is the best one for it.
                self._final_state[v] = state
                self.dist_to[v] = dist
                self._transfer_to[v] = transfers
            for edge in self.graph.adj(v):
                line = edge.line
                is_transfer = cur_line is not None and line is not None and line != cur_line
                nt = transfers + (1 if is_transfer else 0)
                if limited and nt > max_transfers:
                    continue
                new_line = line if line is not None else cur_line
                ns = (edge.dest, new_line, nt if limited else None)
                if ns in settled:
                    continue
                w = edge.weight
                if preferred and line is not None and canonical_line_key(line) in preferred:
                    ww = w * factor
                else:
                    ww = w
                nd = dist + w
                nw = wdist + ww
                nk = self._key(nd, nw, nt)
                if ns not in best or nk < best[ns]:
                    best[ns] = nk
                    self._edge_to[ns] = (state, edge)
                    pq.push(nk, (ns, nd, nw, nt))

    # ----- queries --------------------------------------------------
    def has_path_to(self, target):
        return target in self._final_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to target.

        Both lists are empty when the target is unreachable.
        """
        if target not in self._final_state:
            return [], []
        state = self._final_state[target]
        edges = []
        while state in self._edge_to:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of transfers on the route to target (-1 if unreachable)."""
        if target not in self._final_state:
            return -1
        return self._transfer_to[target]
