"""Shortest-path computation on the subway graph.

Implements Dijkstra's algorithm with a binary-heap priority queue (MinPQ),
supporting three query modes, a maximum transfer limit and line preferences.
"""

import heapq
import itertools

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
DEFAULT_MODE = "shortest_distance"

# Equivalent distance penalty (meters) added per transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1000.0
# Equivalent distance penalty (meters) added per segment on a non-preferred line.
PREFERENCE_PENALTY_M = 300.0


class NoPathError(Exception):
    """Raised when no route satisfies the query constraints."""


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed transfers, or None for unlimited.
        preferred_lines: list of preferred line names (empty means no preference).
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(line) for line in preferred_lines]

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class MinPQ:
    """Min-priority queue implemented on top of heapq (binary heap).

    Ties are broken by insertion order so items themselves are never compared.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def del_min(self):
        """Remove and return the item with the smallest priority."""
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        return heapq.heappop(self._heap)[2]

    def min_priority(self):
        """Return the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("min_priority from an empty priority queue")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)


class ShortestPath:
    """Single-source optimal paths computed with Dijkstra's algorithm.

    Search states are (station number, line the traveller is currently on), which lets
    the algorithm count transfers exactly. Results are computed eagerly in the constructor.

    Attributes:
        dist_to: dict station number -> travelled distance in meters on the optimal path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._transfers = {}     # station number -> transfer count on optimal path
        self._node_state = {}    # station number -> best settled search state
        self._parent = {}        # search state -> (previous state, edge used)
        self._run()

    def _cost(self, distance, transfers, penalty):
        """Comparable cost tuple for a partial path, according to the query mode."""
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, distance + penalty)
        if mode == "comprehensive":
            return (distance + penalty + transfers * TRANSFER_PENALTY_M,)
        return (distance + penalty,)

    def _run(self):
        """Dijkstra over (station, line) states using MinPQ."""
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start = (self.source, None)
        info = {start: (0.0, 0, 0.0)}  # state -> (distance, transfers, penalty)
        pq = MinPQ()
        pq.insert(self._cost(0.0, 0, 0.0), start)
        settled = set()

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)

            node, line = state
            distance, transfers, penalty = info[state]

            if node not in self._node_state:
                self._node_state[node] = state
                self.dist_to[node] = distance
                self._transfers[node] = transfers

            for edge in self.graph.neighbors(node):
                nxt = edge.other(node)
                new_transfers = transfers
                if line is not None and edge.line != line:
                    new_transfers += 1
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                edge_penalty = PREFERENCE_PENALTY_M if preferred and edge.line not in preferred else 0.0
                new_distance = distance + edge.weight
                new_penalty = penalty + edge_penalty
                new_state = (nxt, edge.line)
                if new_state in settled:
                    continue

                new_cost = self._cost(new_distance, new_transfers, new_penalty)
                old = info.get(new_state)
                if old is None or new_cost < self._cost(old[0], old[1], old[2]):
                    info[new_state] = (new_distance, new_transfers, new_penalty)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

    def has_path(self, target):
        """Return True if `target` is reachable under the query constraints."""
        return target in self._node_state

    def path_with_edges(self, target):
        """Return (station numbers, edges) of the optimal path from source to target.

        The station list starts with the source and ends with the target; the edge list
        has one fewer element. Unreachable targets yield ([], []).
        """
        if target not in self._node_state:
            return [], []
        state = self._node_state[target]
        nodes = [state[0]]
        edges = []
        while state in self._parent:
            prev_state, edge = self._parent[state]
            edges.append(edge)
            nodes.append(prev_state[0])
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Number of line transfers on the optimal path to target (0 if unreachable)."""
        return self._transfers.get(target, 0)
