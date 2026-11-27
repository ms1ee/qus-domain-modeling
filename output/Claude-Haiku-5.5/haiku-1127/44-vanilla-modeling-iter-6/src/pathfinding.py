"""Shortest path computation (Dijkstra with a binary-heap priority queue)
and route construction for the subway network."""

from fare_calculator import (
    MINUTES_PER_KM,
    MINUTES_PER_TRANSFER,
    Sum_money,
    calculate_estimated_time,
)
from models import Route, Transfer
from subway_errors import InvalidQueryError, PathNotFoundError

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)
DEFAULT_MODE = MODE_SHORTEST_DISTANCE
DEFAULT_MAX_TRANSFERS = 10

# A transfer costs this many meters in the comprehensive mode. It is derived
# from the time model: 5 minutes of transfer time equals 5/1.5 km of travel.
COMPREHENSIVE_TRANSFER_PENALTY_M = MINUTES_PER_TRANSFER / MINUTES_PER_KM * 1000.0
# In least_transfer mode a transfer dominates any realistic distance.
LEAST_TRANSFER_WEIGHT_M = 1e9
# Extra cost (meters) for riding a line that is not in the preference list.
PREFERENCE_PENALTY_M = 50.0

MODE_TRANSFER_COST = {
    MODE_SHORTEST_DISTANCE: 0.0,
    MODE_LEAST_TRANSFER: LEAST_TRANSFER_WEIGHT_M,
    MODE_COMPREHENSIVE: COMPREHENSIVE_TRANSFER_PENALTY_M,
}


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum number of line transfers allowed (>= 0).
        preferred_lines: list of preferred line names (may be empty).
    """

    def __init__(self, mode=DEFAULT_MODE, max_transfers=DEFAULT_MAX_TRANSFERS,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(
                f"unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if (isinstance(max_transfers, bool) or not isinstance(max_transfers, int)
                or max_transfers < 0):
            raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []

    @property
    def transfer_cost(self):
        """Cost (in the internal scalar metric) added for every transfer."""
        return MODE_TRANSFER_COST[self.mode]


class MinPQ:
    """Binary min-heap priority queue.

    Items are stored as (key, sequence, item) triples; the sequence number
    keeps ordering stable and avoids comparing items directly.
    """

    def __init__(self):
        self.heap = []
        self.size = 0
        self._seq = 0

    def is_empty(self):
        """Return True if the queue holds no items."""
        return self.size == 0

    def insert(self, key, item):
        """Insert an item with the given priority key. O(log n)."""
        self._seq += 1
        self.heap.append((key, self._seq, item))
        self.size += 1
        self._swim(self.size - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        return self.heap[0][0]

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key. O(log n)."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        top = self.heap[0]
        last = self.heap.pop()
        self.size -= 1
        if self.size > 0:
            self.heap[0] = last
            self._sink(0)
        return top[0], top[2]

    def _less(self, i, j):
        return self.heap[i][:2] < self.heap[j][:2]

    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < self.size and self._less(left, smallest):
                smallest = left
            if right < self.size and self._less(right, smallest):
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest


class ShortestPath:
    """Dijkstra-based shortest path computation from one source station.

    The search runs over states (station, current line, transfers used), which
    lets the algorithm account for transfer costs and transfer limits. After
    construction:
        dist_to: dict station number -> travelled distance (meters) of the
                 best route to that station for the configured mode.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.number_to_station:
            raise InvalidQueryError(f"unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._cost = {}
        self._meters = {}
        self._prev = {}
        self._best = {}
        self._run()

    def _run(self):
        """Execute Dijkstra's algorithm and pick the best state per station."""
        transfer_cost = self.config.transfer_cost
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        start = (self.source, None, 0)
        self._cost[start] = 0.0
        self._meters[start] = 0.0
        self._prev[start] = None

        pq = MinPQ()
        pq.insert(0.0, start)
        settled = set()

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line, transfers = state

            for edge in self.graph.get_edges(node):
                nxt = edge.other(node)
                is_transfer = line is not None and line != edge.line
                new_transfers = transfers + (1 if is_transfer else 0)
                if new_transfers > max_transfers:
                    continue
                step = float(edge.weight)
                if preferred and edge.line not in preferred:
                    step += PREFERENCE_PENALTY_M
                if is_transfer:
                    step += transfer_cost
                new_state = (nxt, edge.line, new_transfers)
                if new_state in settled:
                    continue
                new_cost = cost + step
                old = self._cost.get(new_state)
                if old is None or new_cost < old:
                    self._cost[new_state] = new_cost
                    self._meters[new_state] = self._meters[state] + edge.weight
                    self._prev[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

        # Choose the best state for every reachable station.
        for state, cost in self._cost.items():
            node = state[0]
            key = (cost, state[2], self._meters[state])
            current = self._best.get(node)
            if current is None or key < current[0]:
                self._best[node] = (key, state)
        for node, (_, state) in self._best.items():
            self.dist_to[node] = self._meters[state]

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the configuration."""
        return target in self._best

    def path_with_edges(self, target):
        """Return (station numbers, edges) from the source to ``target``.

        Returns ([], []) if the target is unreachable.
        """
        if not self.has_path_to(target):
            return [], []
        state = self._best[target][1]
        nodes = []
        edges = []
        while True:
            nodes.append(state[0])
            prev = self._prev[state]
            if prev is None:
                break
            prev_state, edge = prev
            edges.append(edge)
            state = prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line transfers on the best path to ``target``.

        Raises:
            PathNotFoundError: if the target is unreachable.
        """
        if not self.has_path_to(target):
            raise PathNotFoundError("target station is unreachable")
        return self._best[target][1][2]


def extract_transfers(station_names, edges):
    """Derive the transfer list from station names and the edges of a path."""
    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append(Transfer(station_names[i], edges[i - 1].line,
                                      edges[i].line))
    return transfers


def involved_lines(edges):
    """Return the ordered, de-duplicated list of lines used by a path."""
    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def find_route(graph, start_name, end_name, config=None):
    """Compute the complete Route between two station names.

    Raises:
        InvalidQueryError: for unknown stations or identical endpoints.
        PathNotFoundError: if no route satisfies the configuration.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise InvalidQueryError(
            "Starting station cannot be the same as the ending station")
    src = graph.lookup_number(start_name)
    dst = graph.lookup_number(end_name)
    if src is None or dst is None:
        raise InvalidQueryError("unknown start or end station")

    sp = ShortestPath(graph, src, config)
    if not sp.has_path_to(dst):
        raise PathNotFoundError(
            f"No route found from '{start_name}' to '{end_name}' "
            f"within {config.max_transfers} transfers")

    nodes, edges = sp.path_with_edges(dst)
    names = [graph.name_of(n) for n in nodes]
    distance = float(sum(edge.weight for edge in edges))
    transfers = extract_transfers(names, edges)
    transfer_count = len(transfers)
    fare = Sum_money(distance)
    minutes = calculate_estimated_time(distance, transfer_count)

    return Route(
        start_station=start_name,
        end_station=end_name,
        mode=config.mode,
        station_names=names,
        edges=edges,
        total_distance_meters=distance,
        transfer_count=transfer_count,
        estimated_time_minutes=minutes,
        fare_yuan=fare,
        transfers=transfers,
        lines=involved_lines(edges),
    )
