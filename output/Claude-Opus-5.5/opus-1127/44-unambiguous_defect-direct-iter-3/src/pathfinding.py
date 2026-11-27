"""Path calculation: priority queue and Dijkstra shortest path.

Dijkstra runs over states ``(station, arriving line, transfers)`` so that line
changes (transfers) at interchange stations are tracked exactly. This lets the
algorithm support several modes (shortest distance, least transfers,
comprehensive), a maximum transfer limit and line preferences, while running in
O((V+E) log V) time with a binary-heap priority queue.
"""

import heapq
import itertools

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# In comprehensive mode one transfer "costs" as much as riding this distance.
TRANSFER_PENALTY_METERS = 3000
# Extra relative cost of riding a non-preferred line when preferences are set.
PREFERENCE_PENALTY_FACTOR = 0.3

INF = float("inf")


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode {mode!r}, expected one of {', '.join(VALID_MODES)}"
            )
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = list(preferred_lines)

    def __repr__(self):
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class MinPQ:
    """Heap-based minimum priority queue supporting decrease-key.

    Items are hashable keys; priorities are any comparable values.
    """

    _REMOVED = object()

    def __init__(self):
        self._heap = []
        self._entries = {}
        self._counter = itertools.count()

    def __len__(self):
        return len(self._entries)

    def size(self):
        return len(self._entries)

    def is_empty(self):
        return not self._entries

    def contains(self, item):
        return item in self._entries

    def __contains__(self, item):
        return item in self._entries

    def insert(self, item, priority):
        """Insert an item (replacing its priority if already present)."""
        if item in self._entries:
            self._remove(item)
        entry = [priority, next(self._counter), item]
        self._entries[item] = entry
        heapq.heappush(self._heap, entry)

    def decrease_key(self, item, priority):
        """Lower the priority of item (inserts it if absent)."""
        entry = self._entries.get(item)
        if entry is None or priority < entry[0]:
            self.insert(item, priority)

    def _remove(self, item):
        entry = self._entries.pop(item)
        entry[2] = MinPQ._REMOVED

    def min_priority(self):
        while self._heap and self._heap[0][2] is MinPQ._REMOVED:
            heapq.heappop(self._heap)
        if not self._heap:
            raise IndexError("min_priority from empty priority queue")
        return self._heap[0][0]

    def del_min(self):
        """Remove and return ``(item, priority)`` with the smallest priority."""
        while self._heap:
            priority, _, item = heapq.heappop(self._heap)
            if item is not MinPQ._REMOVED:
                del self._entries[item]
                return item, priority
        raise IndexError("del_min from empty priority queue")


class ShortestPath:
    """Dijkstra shortest path from a single source station.

    ``dist_to`` maps every vertex to the real distance (meters) of the best
    path found under the configured mode (``inf`` if unreachable).
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self._preferred = set(self.config.preferred_lines)
        self._track_transfers = self.config.max_transfers is not None

        self.dist_to = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._state_info = {}
        self._edge_to = {}
        self._best_state = {}
        self._run()

    # ------------------------------------------------------------------ cost
    def _cost(self, distance, penalty, transfers):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            return (distance + penalty + transfers * TRANSFER_PENALTY_METERS,
                    transfers)
        return (distance + penalty, transfers)

    def _edge_penalty(self, edge):
        if self._preferred and edge.line not in self._preferred:
            return edge.weight * PREFERENCE_PENALTY_FACTOR
        return 0

    # ------------------------------------------------------------- algorithm
    def _run(self):
        start = (self.source, None, 0)
        start_cost = self._cost(0, 0, 0)
        # state -> (cost, real distance, penalty, transfers)
        self._state_info[start] = (start_cost, 0, 0, 0)
        self._edge_to[start] = None
        settled = set()
        pq = MinPQ()
        pq.insert(start, start_cost)
        max_t = self.config.max_transfers

        while not pq.is_empty():
            state, _ = pq.del_min()
            settled.add(state)
            u, line, _ = state
            _, dist, penalty, transfers = self._state_info[state]
            for edge in self.graph.adjacent(u):
                w = edge.other(u)
                new_transfers = transfers + (
                    1 if line is not None and edge.line != line else 0
                )
                if max_t is not None and new_transfers > max_t:
                    continue
                new_state = (w, edge.line,
                             new_transfers if self._track_transfers else 0)
                if new_state in settled:
                    continue
                new_dist = dist + edge.weight
                new_penalty = penalty + self._edge_penalty(edge)
                new_cost = self._cost(new_dist, new_penalty, new_transfers)
                old = self._state_info.get(new_state)
                if old is None or new_cost < old[0]:
                    self._state_info[new_state] = (
                        new_cost, new_dist, new_penalty, new_transfers)
                    self._edge_to[new_state] = (state, edge)
                    pq.decrease_key(new_state, new_cost)

        for state, info in self._state_info.items():
            node = state[0]
            best = self._best_state.get(node)
            if best is None or info[0] < self._state_info[best][0]:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._state_info[state][1]

    # --------------------------------------------------------------- queries
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to target.

        Stations are station numbers in travel order; edges are the Edge
        objects traversed in order. Returns ``([], [])`` if unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        nodes = []
        edges = []
        state = self._best_state[target]
        while state is not None:
            nodes.append(state[0])
            link = self._edge_to.get(state)
            if link is None:
                break
            prev_state, edge = link
            edges.append(edge)
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes on the path to target (0 if unreachable)."""
        if not self.has_path_to(target):
            return 0
        return self._state_info[self._best_state[target]][3]

    def get_lines(self, target):
        """Ordered list of distinct lines used on the path to target."""
        lines = []
        for edge in self.path_with_edges(target)[1]:
            if not lines or lines[-1] != edge.line:
                if edge.line not in lines:
                    lines.append(edge.line)
        return lines

    def get_transfer_stations(self, target):
        """Station numbers where a transfer happens on the path to target."""
        nodes, edges = self.path_with_edges(target)
        result = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                result.append(nodes[i])
        return result
