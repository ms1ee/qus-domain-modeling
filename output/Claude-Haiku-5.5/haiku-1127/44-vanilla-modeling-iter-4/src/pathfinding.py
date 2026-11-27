"""Path calculation: indexed min-priority queue, Dijkstra shortest paths and
route helpers for shortest-distance, minimum-transfer and comprehensive queries.

Dijkstra runs over labels ``(station, arriving line, transfers so far)`` so that
transfer counts, transfer limits and line preferences can be enforced exactly.
"""

import math

from models import Path, Transfer

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Composite metric: one transfer is worth this many meters of travel.
TRANSFER_PENALTY_M = 3000.0
# Extra cost added for every edge on a line outside the preferred lines.
PREFERENCE_PENALTY_M = 2000.0
# Weight that makes transfers dominate distance in least-transfer mode.
LEAST_TRANSFER_WEIGHT = 1e9
# Upper bound on transfers explored internally (keeps the label space finite).
HARD_TRANSFER_CAP = 10


class PathfindingConfig:
    """Options controlling how paths are computed.

    Attributes:
        mode: One of ``MODES``.
        max_transfers: Maximum number of transfers allowed, or None for no limit.
        preferred_lines: Lines preferred by the user (list of line names).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {MODES}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class MinPQ:
    """Indexed binary min-heap keyed by priority.

    Items are integers (state ids). ``decrease_key`` runs in O(log n), giving
    the O((V+E) log V) bound for Dijkstra.
    """

    def __init__(self):
        self.heap = []      # array of items arranged as a binary heap
        self._index = {}    # item -> position in heap
        self._keys = {}     # item -> priority

    @property
    def size(self):
        """Number of items currently in the queue."""
        return len(self.heap)

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self.heap

    def contains(self, item):
        """Return True if ``item`` is currently queued."""
        return item in self._index

    def min_item(self):
        """Return the item with the smallest priority without removing it."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        return self.heap[0]

    def insert(self, item, key):
        """Insert ``item`` with priority ``key``."""
        if item in self._index:
            raise ValueError(f"item {item} is already in the queue")
        self._keys[item] = key
        self.heap.append(item)
        self._index[item] = len(self.heap) - 1
        self._swim(len(self.heap) - 1)

    def decrease_key(self, item, key):
        """Lower the priority of a queued item."""
        if item not in self._index:
            raise KeyError(f"item {item} is not in the queue")
        if key > self._keys[item]:
            raise ValueError("decrease_key cannot increase a priority")
        self._keys[item] = key
        self._swim(self._index[item])

    def del_min(self):
        """Remove and return the item with the smallest priority."""
        if not self.heap:
            raise IndexError("priority queue is empty")
        top = self.heap[0]
        last = self.heap.pop()
        del self._index[top]
        if self.heap:
            self.heap[0] = last
            self._index[last] = 0
            self._sink(0)
        del self._keys[top]
        return top

    def _less(self, i, j):
        return self._keys[self.heap[i]] < self._keys[self.heap[j]]

    def _exchange(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self._index[self.heap[i]] = i
        self._index[self.heap[j]] = j

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._exchange(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self.heap)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._exchange(k, child)
            k = child


class _Label:
    """A Dijkstra search state: station reached on ``line`` after ``transfers`` changes."""

    __slots__ = ("id", "station", "line", "transfers", "distance", "penalty",
                 "cost", "pred", "edge")

    def __init__(self, label_id, station, line, transfers):
        self.id = label_id
        self.station = station
        self.line = line
        self.transfers = transfers
        self.distance = 0.0
        self.penalty = 0.0
        self.cost = math.inf
        self.pred = -1
        self.edge = None


class ShortestPath:
    """Dijkstra-based optimal path computation from a source station.

    Attributes:
        graph: The Graph searched.
        source: Source station number.
        config: PathfindingConfig in use.
        optimization_mode: The configured mode string.
        dist_to: dict[station number, best weighted cost] (inf if unreachable).
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.adjacency:
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.optimization_mode = self.config.mode
        self.dist_to = {vertex: math.inf for vertex in graph.adjacency}
        self._labels = []
        self._label_ids = {}
        self._best = {}
        self._run()

    # ------------------------------------------------------------------ search
    def _transfer_limit(self):
        if self.config.max_transfers is None:
            return HARD_TRANSFER_CAP
        return min(self.config.max_transfers, HARD_TRANSFER_CAP)

    def _cost(self, distance, transfers, penalty):
        """Scalar cost of a label according to the configured mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return transfers * LEAST_TRANSFER_WEIGHT + distance + penalty
        if mode == MODE_COMPREHENSIVE:
            return distance + transfers * TRANSFER_PENALTY_M + penalty
        return distance + penalty

    def _get_label(self, station, line, transfers):
        key = (station, line, transfers)
        label_id = self._label_ids.get(key)
        if label_id is None:
            label_id = len(self._labels)
            label = _Label(label_id, station, line, transfers)
            self._labels.append(label)
            self._label_ids[key] = label_id
            return label
        return self._labels[label_id]

    def _run(self):
        limit = self._transfer_limit()
        preferred = set(self.config.preferred_lines)
        queue = MinPQ()
        settled = set()

        root = self._get_label(self.source, None, 0)
        root.cost = 0.0
        queue.insert(root.id, 0.0)

        while not queue.is_empty():
            current_id = queue.del_min()
            settled.add(current_id)
            current = self._labels[current_id]

            for edge in self.graph.neighbors(current.station):
                next_station = edge.other(current.station)
                transfers = current.transfers
                if current.line is not None and current.line != edge.line:
                    transfers += 1
                if transfers > limit:
                    continue
                distance = current.distance + edge.distance
                penalty = current.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_M
                cost = self._cost(distance, transfers, penalty)

                label = self._get_label(next_station, edge.line, transfers)
                if label.id in settled or cost >= label.cost:
                    continue
                label.cost = cost
                label.distance = distance
                label.penalty = penalty
                label.pred = current_id
                label.edge = edge
                if queue.contains(label.id):
                    queue.decrease_key(label.id, cost)
                else:
                    queue.insert(label.id, cost)

        # Choose the best label per station for dist_to and path reconstruction.
        for label in self._labels:
            if label.cost < self.dist_to.get(label.station, math.inf):
                self.dist_to[label.station] = label.cost
                self._best[label.station] = label.id

    # ------------------------------------------------------------------ queries
    def _best_label(self, target):
        label_id = self._best.get(target)
        if label_id is None:
            return None
        return self._labels[label_id]

    def reachable(self, target):
        """Return True if ``target`` can be reached under the current constraints."""
        return self._best_label(target) is not None

    def path_with_edges(self, target):
        """Return ``(station numbers, edges)`` of the optimal path to ``target``.

        Returns ``([], [])`` if the target is unreachable.
        """
        label = self._best_label(target)
        if label is None:
            return [], []
        stations = []
        edges = []
        current = label
        while current.pred != -1:
            stations.append(current.station)
            edges.append(current.edge)
            current = self._labels[current.pred]
        stations.append(current.station)
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the optimal path to ``target``."""
        label = self._best_label(target)
        return label.transfers if label is not None else 0

    def get_distance(self, target):
        """Return the actual travelled distance (meters) to ``target`` (inf if unreachable)."""
        label = self._best_label(target)
        return label.distance if label is not None else math.inf


def build_path(graph, stations, edges):
    """Create a ``models.Path`` from station numbers and edges.

    Transfers are the positions where consecutive edges use different lines.
    """
    names = [graph.name_of(number) for number in stations]
    total = float(sum(edge.distance for edge in edges))
    involved = []
    for edge in edges:
        if edge.line not in involved:
            involved.append(edge.line)
    transfers = []
    for index in range(1, len(edges)):
        previous_line = edges[index - 1].line
        current_line = edges[index].line
        if previous_line != current_line:
            transfers.append(Transfer(names[index], [previous_line, current_line]))
    return Path(
        station_sequence=names,
        edges=list(edges),
        total_distance=total,
        transfer_count=len(transfers),
        involved_lines=involved,
        transfers=transfers,
    )


def find_route(graph, start_name, end_name, config=None):
    """Compute the optimal route between two station names.

    Returns:
        models.Path, or None if no route satisfies the constraints.

    Raises:
        ValueError: If either station name is unknown.
    """
    start = graph.number_of(start_name)
    end = graph.number_of(end_name)
    if start is None:
        raise ValueError(f"Unknown starting station '{start_name}'")
    if end is None:
        raise ValueError(f"Unknown ending station '{end_name}'")
    shortest = ShortestPath(graph, start, config)
    if not shortest.reachable(end):
        return None
    stations, edges = shortest.path_with_edges(end)
    return build_path(graph, stations, edges)
