"""Path calculation: priority queue and Dijkstra's shortest path algorithm.

Dijkstra runs over an expanded state space ``(station, line[, transfers])`` so
that transfers can be counted exactly, limited (``max_transfers``) and used in
the optimisation objective. Costs are tuples compared lexicographically; since
all components are non-negative and additive, Dijkstra remains correct.
Complexity is O((V+E) log V) on the expanded graph thanks to the binary heap.
"""

import heapq
import itertools

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)


class RouteNotFoundError(Exception):
    """Raised when no route can be found between two stations."""


def normalize_line_name(name):
    """Normalize a line name for loose comparison."""
    return "".join(str(name).split()).casefold()


class MinPQ:
    """Binary-heap based minimum priority queue.

    Items are ``(priority, value)``; ties are broken by insertion order so
    values never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, value=None):
        heapq.heappush(self._heap, (priority, next(self._counter), value))

    push = insert

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        priority, _, value = self._heap[0]
        return priority, value

    def del_min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        priority, _, value = heapq.heappop(self._heap)
        return priority, value

    pop = del_min

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: maximum number of transfers allowed (None = unlimited).
        preferred_lines: list of preferred line names.
        transfer_penalty: meters-equivalent penalty per transfer (comprehensive).
        preference_factor: weight multiplier for edges on preferred lines.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None, transfer_penalty=4000, preference_factor=0.8):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode %r, expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise TypeError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers cannot be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = [p for p in preferred_lines if str(p).strip()]
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return "PathfindingConfig(mode=%r, max_transfers=%r, preferred_lines=%r)" % (
            self.mode, self.max_transfers, self.preferred_lines)


class ShortestPath:
    """Dijkstra's single-source shortest path over a :class:`models.Graph`.

    Attributes:
        dist_to: dict station number -> travelled distance (meters) of the
            optimal route under the configured mode (``inf`` if unreachable).
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.graph}
        self.dist_to[source] = 0
        self._transfers_to = {source: 0}
        self._final_state = {}
        self._edge_to = {}
        self._preferred = {normalize_line_name(p) for p in self.config.preferred_lines}
        self._run()

    # ----- cost model --------------------------------------------------------
    def _cost(self, acc):
        d, t, w = acc
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (t, w, d)
        if mode == MODE_COMPREHENSIVE:
            return (w + self.config.transfer_penalty * t, t, d)
        # shortest distance: line preference only acts as a tie-breaker
        return (d, w, t)

    def _is_preferred(self, line):
        return bool(self._preferred) and normalize_line_name(line) in self._preferred

    # ----- algorithm -----------------------------------------------------------
    def _run(self):
        limited = self.config.max_transfers is not None
        max_t = self.config.max_transfers
        factor = self.config.preference_factor

        def key(station, line, transfers):
            return (station, line, transfers) if limited else (station, line)

        start = key(self.source, None, 0)
        self._start_state = start
        acc = {start: (0, 0, 0.0)}
        settled = set()
        pq = MinPQ()
        pq.insert(self._cost(acc[start]), start)

        while not pq.is_empty():
            priority, state = pq.del_min()
            if state in settled or priority != self._cost(acc[state]):
                continue
            settled.add(state)
            d, t, w = acc[state]
            station, line = state[0], state[1]
            if station not in self._final_state:
                self._final_state[station] = state
                self.dist_to[station] = d
                self._transfers_to[station] = t
            for edge in self.graph.graph.get(station, []):
                nt = t + (1 if line is not None and edge.line != line else 0)
                if limited and nt > max_t:
                    continue
                nkey = key(edge.dest, edge.line, nt)
                if nkey in settled:
                    continue
                weight = edge.weight * (factor if self._is_preferred(edge.line) else 1)
                candidate = (d + edge.weight, nt, w + weight)
                if nkey not in acc or self._cost(candidate) < self._cost(acc[nkey]):
                    acc[nkey] = candidate
                    self._edge_to[nkey] = (state, edge)
                    pq.insert(self._cost(candidate), nkey)

    # ----- queries -------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._final_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to ``target``.

        ``stations`` is the ordered list of station numbers; ``edges`` the
        ordered list of traversed edges (each oriented along the path).
        Returns ``([], [])`` if the target is unreachable.
        """
        if target not in self._final_state:
            return [], []
        edges = []
        state = self._final_state[target]
        while state != self._start_state:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        stations = [self.source] + [e.dest for e in edges]
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the route to ``target`` (0 if none)."""
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)


def count_transfers(edges):
    """Count line changes along an ordered list of edges."""
    return sum(1 for i in range(1, len(edges)) if edges[i].line != edges[i - 1].line)
