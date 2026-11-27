"""Path computation: Dijkstra's shortest-path algorithm over (station, line) states.

Each state records the station reached and the line the passenger is currently
riding, which allows transfers (line changes) to be counted and constrained
correctly at multi-line interchange stations.
"""

import itertools

from errors import FareCalculationError, PathCalculationError
from fare_calculator import SPEED_MINUTES_PER_KM, TRANSFER_TIME_MINUTES, Sum_money
from models import Route, Transfer

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Extra distance-equivalent cost (meters) for riding a non-preferred line.
PREFERENCE_PENALTY_METERS = 500.0


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed transfers, or None for no limit.
        preferred_lines: list of preferred line names (empty for no preference).
    """

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class MinPQ:
    """Binary min-heap priority queue (keys compared as tuples).

    Insertion and removal run in O(log n); used by Dijkstra's algorithm to
    obtain the overall O((V+E) log V) complexity.
    """

    def __init__(self):
        self._heap = []  # entries: (key, sequence, item)
        self._seq = itertools.count()

    def insert(self, item, key):
        self._heap.append((key, next(self._seq), item))
        self._swim(len(self._heap) - 1)

    def del_min(self):
        if not self._heap:
            raise IndexError("del_min from empty priority queue")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[2]

    def min_key(self):
        if not self._heap:
            raise IndexError("min_key from empty priority queue")
        return self._heap[0][0]

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)

    def _less(self, i, j):
        return self._heap[i][:2] < self._heap[j][:2]

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._heap)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child


class _Label:
    """Best known label for a (station, line) state."""

    __slots__ = ("cost", "dist", "eff", "transfers", "prev", "edge")

    def __init__(self, cost, dist, eff, transfers, prev, edge):
        self.cost = cost            # tuple used for ordering
        self.dist = dist            # real travelled distance (meters)
        self.eff = eff              # distance including preference penalties
        self.transfers = transfers  # number of line changes so far
        self.prev = prev            # previous state
        self.edge = edge            # edge used to reach this state


class ShortestPath:
    """Dijkstra-based single-source optimal path computation.

    Cost ordering per mode:
        shortest_distance: (distance, transfers)
        least_transfer:    (transfers, distance)
        comprehensive:     (estimated minutes) = 1.5 min/km + 5 min per transfer
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        if self.config.mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{self.config.mode}'")
        self.dist_to = {}      # station number -> travelled distance (meters)
        self._labels = {}      # (station, line) -> _Label
        self._best = {}        # station number -> best (station, line) state
        self._search()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def has_path_to(self, target):
        """Return True if the target station is reachable from the source."""
        return target in self._best

    def path_with_edges(self, target):
        """Backtrack the optimal path to target.

        Returns:
            (station_numbers, edges) from source to target. Both lists are
            empty if the target is unreachable.
        """
        state = self._best.get(target)
        if state is None:
            return [], []
        stations = []
        edges = []
        cur = state
        while cur is not None:
            label = self._labels[cur]
            stations.append(cur[0])
            if label.edge is not None:
                edges.append(label.edge)
            cur = label.prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the optimal path to target (0 if unreachable)."""
        state = self._best.get(target)
        if state is None:
            return 0
        return self._labels[state].transfers

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _cost(self, eff_meters, transfers):
        mode = self.config.mode
        if mode == "shortest_distance":
            return (eff_meters, transfers)
        if mode == "least_transfer":
            return (transfers, eff_meters)
        # comprehensive: estimated travel time in minutes
        minutes = (eff_meters / 1000.0) * SPEED_MINUTES_PER_KM + transfers * TRANSFER_TIME_MINUTES
        return (minutes,)

    def _preference_penalty(self, edge):
        if self.config.preferred_lines and edge.line not in self.config.preferred_lines:
            return PREFERENCE_PENALTY_METERS
        return 0.0

    def _search(self):
        max_transfers = self.config.max_transfers
        start = (self.source, None)
        start_cost = self._cost(0.0, 0)
        self._labels[start] = _Label(start_cost, 0.0, 0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(start, start_cost)
        done = set()

        while not pq.is_empty():
            state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            station, line = state
            label = self._labels[state]

            for edge in self.graph.adjacent(station):
                transfers = label.transfers
                if line is not None and edge.line != line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                nxt = (edge.dest, edge.line)
                if nxt in done:
                    continue
                dist = label.dist + edge.distance
                eff = label.eff + edge.distance + self._preference_penalty(edge)
                cost = self._cost(eff, transfers)
                existing = self._labels.get(nxt)
                if existing is None or cost < existing.cost:
                    self._labels[nxt] = _Label(cost, dist, eff, transfers, state, edge)
                    pq.insert(nxt, cost)

        # Choose the best state for each station.
        for state, label in self._labels.items():
            station = state[0]
            current = self._best.get(station)
            if current is None or label.cost < self._labels[current].cost:
                self._best[station] = state
        for station, state in self._best.items():
            self.dist_to[station] = self._labels[state].dist


def extract_transfers(station_names, edges):
    """Identify transfer points (line changes) along an edge sequence."""
    transfers = []
    for i in range(1, len(edges)):
        prev_line = edges[i - 1].line
        next_line = edges[i].line
        if prev_line != next_line:
            transfers.append(Transfer(station_names[i], [prev_line, next_line]))
    return transfers


def plan_route(network, start_name, end_name, config=None):
    """Compute the route between two official station names.

    Returns:
        A Route object, or None if no route satisfies the constraints.

    Raises:
        PathCalculationError: if the path computation fails.
        FareCalculationError: if the fare cannot be calculated.
    """
    config = config if config is not None else PathfindingConfig()
    try:
        source = network.get_number(start_name)
        target = network.get_number(end_name)
        sp = ShortestPath(network.graph, source, config)
        if not sp.has_path_to(target):
            return None
        numbers, edges = sp.path_with_edges(target)
        names = [network.get_name(n) for n in numbers]
        total = sum(edge.distance for edge in edges)
        transfers = extract_transfers(names, edges)
        if config.max_transfers is not None and len(transfers) > config.max_transfers:
            return None
    except (KeyError, IndexError, ValueError) as exc:
        raise PathCalculationError(f"path calculation failed: {exc}") from exc

    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    try:
        fare = Sum_money(total)
    except ValueError as exc:
        raise FareCalculationError(f"fare calculation failed: {exc}") from exc

    return Route(
        start_station=start_name,
        end_station=end_name,
        mode=config.mode,
        station_sequence=names,
        edges=edges,
        total_distance_meters=total,
        transfer_count=len(transfers),
        transfers=transfers,
        lines=lines,
        fare_yuan=fare,
        max_transfers=config.max_transfers,
        line_preference=", ".join(config.preferred_lines) if config.preferred_lines else None,
    )
