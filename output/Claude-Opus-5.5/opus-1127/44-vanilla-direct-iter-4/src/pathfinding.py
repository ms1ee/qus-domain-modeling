"""Path calculation: priority queue and Dijkstra-based shortest path search.

The search operates on states (station, arriving line[, transfers]) so that
transfers can be counted exactly, supporting three query modes:

* ``shortest_distance`` - minimise total distance
* ``least_transfer``    - minimise transfers, then distance
* ``comprehensive``     - minimise distance + transfer penalty (composite score)

Maximum transfer limits and line preferences are also supported.
"""

import math

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)


class MinPQ:
    """Binary-heap based minimum priority queue."""

    def __init__(self):
        self._heap = []

    def __len__(self):
        return len(self._heap)

    def size(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

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

    def min(self):
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._heap[0]

    def del_min(self):
        heap = self._heap
        if not heap:
            raise IndexError("Priority queue is empty")
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


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None, transfer_penalty=5000,
                 preference_factor=0.8):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        # equivalent distance (meters) of one transfer in comprehensive mode
        self.transfer_penalty = transfer_penalty
        # weight multiplier applied to edges on preferred lines (for scoring only)
        self.preference_factor = preference_factor


class ShortestPath:
    """Dijkstra shortest paths from a single source station number."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source!r} is not in the graph")
        self.dist_to = {v: math.inf for v in graph.vertices()}
        # state -> (cost, distance, transfers, pref_distance, prev_state, edge)
        self._info = {}
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------
    def _cost(self, distance, transfers, pref_distance):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, pref_distance, distance)
        if mode == MODE_COMPREHENSIVE:
            return (pref_distance + transfers * self.config.transfer_penalty,
                    distance, transfers)
        return (distance, transfers, pref_distance)

    def _state(self, v, line, transfers):
        if self.config.max_transfers is None:
            return (v, line)
        return (v, line, transfers)

    def _run(self):
        cfg = self.config
        max_t = cfg.max_transfers
        preferred = set(cfg.preferred_lines)
        factor = cfg.preference_factor
        info = self._info
        settled = set()
        pq = MinPQ()
        counter = 0

        start = self._state(self.source, None, 0)
        cost0 = self._cost(0, 0, 0.0)
        info[start] = (cost0, 0, 0, 0.0, None, None)
        pq.insert((cost0, counter, start))

        while not pq.is_empty():
            cost, _, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            v, line = state[0], state[1]
            _, d, t, pd, _, _ = info[state]

            best = self._best_state.get(v)
            if best is None or cost < info[best][0]:
                self._best_state[v] = state

            for e in self.graph.adj(v):
                w = e.other(v)
                nt = t + (1 if (line is not None and e.line != line) else 0)
                if max_t is not None and nt > max_t:
                    continue
                ns = self._state(w, e.line, nt)
                if ns in settled:
                    continue
                nd = d + e.weight
                npd = pd + e.weight * (factor if e.line in preferred else 1)
                ncost = self._cost(nd, nt, npd)
                old = info.get(ns)
                if old is None or ncost < old[0]:
                    info[ns] = (ncost, nd, nt, npd, state, e)
                    counter += 1
                    pq.insert((ncost, counter, ns))

        for v, state in self._best_state.items():
            self.dist_to[v] = info[state][1]

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target.

        Returns ([], []) if the target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        stations = []
        edges = []
        state = self._best_state[target]
        while state is not None:
            stations.append(state[0])
            _, _, _, _, prev, edge = self._info[state]
            if edge is not None:
                edges.append(edge)
            state = prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to target."""
        if not self.has_path_to(target):
            raise ValueError(f"No path to station {target!r}")
        return self._info[self._best_state[target]][2]

    def transfer_stations(self, target):
        """Station numbers where a line change happens along the path."""
        stations, edges = self.path_with_edges(target)
        result = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                result.append(stations[i])
        return result

    def lines_on_path(self, target):
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
