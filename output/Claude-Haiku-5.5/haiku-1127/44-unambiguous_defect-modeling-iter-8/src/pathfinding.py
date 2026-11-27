"""Path-finding algorithms for the subway network.

Provides a binary-heap priority queue (``MinPQ``), a configuration object
(``PathfindingConfig``) and a Dijkstra-based shortest path computation
(``ShortestPath``). The search runs over states ``(station, arriving line)``
so that line changes (transfers) can be counted, limited and penalised.
"""

from models import Graph  # noqa: F401  (documented dependency of ShortestPath)

TRANSFER_PENALTY_M = 500.0      # extra cost per transfer in comprehensive mode
PREFERENCE_PENALTY_M = 1000.0   # extra cost per edge on a non-preferred line

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
DEFAULT_MODE = "shortest_distance"


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Query configuration for path computation.

    Attributes:
        mode: One of ``shortest_distance``, ``least_transfer``, ``comprehensive``.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of line names that are preferred.
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Min-priority queue implemented as a binary heap.

    Items are stored with comparable keys; ``del_min`` returns the entry with
    the smallest key. Insertion and removal run in O(log n).
    """

    def __init__(self):
        self._heap = []  # list of (key, item) tuples

    @property
    def heap_size(self):
        """Number of entries currently in the queue."""
        return len(self._heap)

    def is_empty(self):
        """Return True if the queue has no entries."""
        return not self._heap

    def min_key(self):
        """Return the smallest key without removing the entry."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def insert(self, key, item):
        """Insert an item with the given key."""
        self._heap.append((key, item))
        self._sift_up(len(self._heap) - 1)

    def del_min(self):
        """Remove and return the ``(key, item)`` pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    def _sift_up(self, index):
        heap = self._heap
        entry = heap[index]
        while index > 0:
            parent = (index - 1) // 2
            if entry[0] < heap[parent][0]:
                heap[index] = heap[parent]
                index = parent
            else:
                break
        heap[index] = entry

    def _sift_down(self, index):
        heap = self._heap
        size = len(heap)
        entry = heap[index]
        while True:
            child = 2 * index + 1
            if child >= size:
                break
            if child + 1 < size and heap[child + 1][0] < heap[child][0]:
                child += 1
            if heap[child][0] < entry[0]:
                heap[index] = heap[child]
                index = child
            else:
                break
        heap[index] = entry


class ShortestPath:
    """Dijkstra-based path computation from a single source station.

    Attributes:
        dist_to: Mapping from station number to the actual travelled distance
            (meters) of the best path found to that station.
    """

    def __init__(self, graph, source, config=None):
        if not graph.contains_number(source):
            raise ValueError(f"source station number {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._states = {}   # state key -> state record
        self._best = {}     # station number -> best state key
        self._pq = MinPQ()
        self._compute()

    # ----- cost model ------------------------------------------------------
    def _cost(self, distance, transfers, preference_penalty):
        """Return the comparable cost tuple of a partial path."""
        mode = self.config.mode
        if mode == "shortest_distance":
            return (distance + preference_penalty, distance)
        if mode == "least_transfer":
            return (float(transfers), distance + preference_penalty)
        # comprehensive: distance plus a penalty for every transfer
        return (distance + preference_penalty + TRANSFER_PENALTY_M * transfers, distance)

    def _state_key(self, node, line, transfers):
        """Return the search-state key. Transfer count is part of the key only
        when a transfer limit is set, so that limited searches stay correct."""
        if self.config.max_transfers is None:
            return (node, line)
        return (node, line, transfers)

    # ----- Dijkstra --------------------------------------------------------
    def _compute(self):
        graph = self.graph
        limit = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        start_key = self._state_key(self.source, None, 0)
        start = {
            "node": self.source,
            "line": None,
            "transfers": 0,
            "dist": 0.0,
            "pref": 0.0,
            "cost": self._cost(0.0, 0, 0.0),
            "prev": None,
            "edge": None,
        }
        self._states[start_key] = start
        self._pq.insert(start["cost"], start_key)

        settled = set()
        while not self._pq.is_empty():
            cost, key = self._pq.del_min()
            if key in settled:
                continue
            record = self._states[key]
            if cost != record["cost"]:
                continue  # stale queue entry
            settled.add(key)

            node = record["node"]
            if node not in self._best:
                self._best[node] = key

            for edge in graph.adjacent(node):
                nxt = edge.other(node)
                transferred = record["line"] is not None and edge.line != record["line"]
                new_transfers = record["transfers"] + (1 if transferred else 0)
                if limit is not None and new_transfers > limit:
                    continue
                penalty = PREFERENCE_PENALTY_M if (preferred and edge.line not in preferred) else 0.0
                new_dist = record["dist"] + edge.weight
                new_pref = record["pref"] + penalty
                new_cost = self._cost(new_dist, new_transfers, new_pref)
                next_key = self._state_key(nxt, edge.line, new_transfers)
                existing = self._states.get(next_key)
                if existing is None or new_cost < existing["cost"]:
                    self._states[next_key] = {
                        "node": nxt,
                        "line": edge.line,
                        "transfers": new_transfers,
                        "dist": new_dist,
                        "pref": new_pref,
                        "cost": new_cost,
                        "prev": key,
                        "edge": edge,
                    }
                    self._pq.insert(new_cost, next_key)

        for node, key in self._best.items():
            self.dist_to[node] = self._states[key]["dist"]

    # ----- queries ---------------------------------------------------------
    def has_path_to(self, target):
        """Return True if a path from the source to ``target`` exists."""
        return target in self._best

    def path_with_edges(self, target):
        """Return ``(station_numbers, edges)`` of the best path to ``target``.

        ``station_numbers`` starts with the source and ends with the target;
        ``edges`` has one fewer element and ``edges[i]`` joins
        ``station_numbers[i]`` and ``station_numbers[i + 1]``.
        Returns ``([], [])`` if the target is unreachable.
        """
        key = self._best.get(target)
        if key is None:
            return [], []
        nodes = []
        edges = []
        record = self._states[key]
        while record is not None:
            nodes.append(record["node"])
            if record["edge"] is not None:
                edges.append(record["edge"])
            prev_key = record["prev"]
            record = self._states[prev_key] if prev_key is not None else None
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to ``target``."""
        _, edges = self.path_with_edges(target)
        return sum(
            1 for index in range(1, len(edges)) if edges[index - 1].line != edges[index].line
        )
