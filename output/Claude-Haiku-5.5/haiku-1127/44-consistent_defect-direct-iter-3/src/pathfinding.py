"""
Path calculation module.

Implements Dijkstra's shortest path algorithm on the subway graph with a
heap-based priority queue (MinPQ). Three query modes are supported:

* ``shortest_distance`` - minimise the total distance in meters.
* ``least_transfer``    - minimise the number of transfers, then the distance.
* ``comprehensive``     - minimise a composite score mixing distance (km)
                          and transfers.

Transfer limits and line preferences are honoured by the search.
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite score: one transfer is worth this many kilometers of travel.
TRANSFER_PENALTY_KM = 2.0
# Extra cost (in meters) added for each edge that is not on a preferred line.
PREFERENCE_PENALTY_M = 1000.0


class PathfindingConfig:
    """
    Configuration for a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed number of transfers, or None for no limit.
        preferred_lines: List of preferred line names (empty = no preference).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """
    Min priority queue implemented on top of a binary heap.

    Items are (key, value) pairs; the smallest key is returned first.
    A monotonically increasing counter is used as a tie-breaker so that
    values never need to be comparable.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, value):
        """Insert a value with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def del_min(self):
        """Remove and return the (key, value) pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue underflow")
        key, _, value = heapq.heappop(self._heap)
        return key, value

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """
    Dijkstra-based single-source shortest path computation.

    Attributes:
        dist_to: dict mapping station number -> actual distance (meters)
                 from the source. Only reachable stations are present.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()

        self.dist_to = {}          # actual distance in meters
        self._penalized_to = {}    # distance including preference penalties
        self.transfers_to = {}     # number of transfers on the best path
        self.edge_to = {}          # station -> incoming Edge on the best path
        self._key_to = {}          # station -> priority key used for comparison

        self._run()

    # ----- cost model --------------------------------------------------------
    def _key(self, penalized_distance, transfers):
        """Compute the priority key for a label according to the query mode."""
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return penalized_distance
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, penalized_distance)
        # comprehensive: linear combination with non-negative coefficients
        return penalized_distance / 1000.0 + TRANSFER_PENALTY_KM * transfers

    def _preference_penalty(self, edge):
        """Return the extra cost for an edge not on a preferred line."""
        prefs = self.config.preferred_lines
        if prefs and edge.line not in prefs:
            return PREFERENCE_PENALTY_M
        return 0.0

    # ----- main algorithm ----------------------------------------------------
    def _run(self):
        """Run Dijkstra's algorithm from the source vertex."""
        src = self.source
        self.dist_to[src] = 0
        self._penalized_to[src] = 0.0
        self.transfers_to[src] = 0
        self._key_to[src] = self._key(0.0, 0)

        pq = MinPQ()
        pq.insert(self._key_to[src], src)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, v = pq.del_min()
            if v in settled:
                continue  # stale queue entry
            settled.add(v)

            for edge in self.graph.adj(v):
                w = edge.dest
                if w in settled:
                    continue

                # A transfer happens when the line changes at an interchange.
                is_transfer = v != src and self.edge_to[v].line != edge.line
                transfers_new = self.transfers_to[v] + (1 if is_transfer else 0)
                if max_transfers is not None and transfers_new > max_transfers:
                    continue

                penalized_new = self._penalized_to[v] + edge.weight + self._preference_penalty(edge)
                key = self._key(penalized_new, transfers_new)

                if w not in self._key_to or key < self._key_to[w]:
                    self._key_to[w] = key
                    self._penalized_to[w] = penalized_new
                    self.dist_to[w] = self.dist_to[v] + edge.weight
                    self.transfers_to[w] = transfers_new
                    self.edge_to[w] = edge
                    pq.insert(key, w)

    # ----- queries -----------------------------------------------------------
    def has_path_to(self, target):
        """Return True if target is reachable from the source."""
        return target in self.dist_to

    def distance_to(self, target):
        """Return the distance in meters to target, or float('inf') if unreachable."""
        return self.dist_to.get(target, float("inf"))

    def get_transfer_count(self, target):
        """Return the number of transfers on the computed path to target."""
        return self.transfers_to.get(target, 0)

    def path_with_edges(self, target):
        """
        Backtrack the shortest path from target to the source.

        Returns:
            (stations, edges) where
              * stations is a list of station numbers ordered from target
                back to the source (backtracking order, starts with target,
                ends with the source);
              * edges is a list of Edge objects in the same backtracking
                order: edges[i] is the travel-direction edge that goes from
                stations[i + 1] to stations[i].
            If target is unreachable, returns ([], []).
        """
        if not self.has_path_to(target):
            return [], []
        stations = [target]
        edges = []
        v = target
        while v != self.source:
            edge = self.edge_to[v]
            edges.append(edge)
            v = edge.source
            stations.append(v)
        return stations, edges
