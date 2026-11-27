"""Shortest path computation over the subway graph using Dijkstra's algorithm.

Weight factors:
  * Base weight: inter-station distance in meters.
  * Transfer penalty: an extra cost added whenever the passenger changes lines,
    depending on the selected query mode.
  * Line preference: edges on preferred lines are slightly discounted.
Complexity: O((V + E) log V) thanks to the binary-heap priority queue MinPQ.
"""

import math

from models import (
    Path,
    Segment,
    TransferInfo,
    PathNotFoundError,
    PathfindingError,
)

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Extra cost (in meter-equivalents) charged for every transfer, per mode.
TRANSFER_PENALTY_M = {
    MODE_SHORTEST_DISTANCE: 0.0,
    MODE_LEAST_TRANSFER: 100000.0,   # dominates distance: minimise transfers first
    MODE_COMPREHENSIVE: 1500.0,      # balance between distance and transfers
}

# Cost multiplier applied to edges on a preferred line.
PREFERRED_LINE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration for a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
                raise ValueError("max_transfers must be a non-negative integer or None")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    @property
    def transfer_penalty(self):
        """Cost added per line change for the configured mode."""
        return TRANSFER_PENALTY_M[self.mode]

    def edge_cost(self, edge):
        """Return the cost of traversing ``edge`` under this configuration."""
        cost = edge.weight
        if edge.line in self.preferred_lines:
            cost *= PREFERRED_LINE_FACTOR
        return cost


class MinPQ:
    """Binary min-heap priority queue keyed by a float priority."""

    class _Node:
        __slots__ = ("key", "value")

        def __init__(self, key, value):
            self.key = key
            self.value = value

    def __init__(self):
        self._heap = []

    @property
    def size(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def min_key(self):
        """Return the smallest key without removing it."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        return self._heap[0].key

    def insert(self, key, value):
        """Insert ``value`` with priority ``key``."""
        self._heap.append(MinPQ._Node(key, value))
        self._swim(len(self._heap) - 1)

    def del_min(self):
        """Remove and return the (key, value) pair with the smallest key."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top.key, top.value

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k].key < heap[parent].key:
                heap[k], heap[parent] = heap[parent], heap[k]
                k = parent
            else:
                break

    def _sink(self, k):
        heap = self._heap
        n = len(heap)
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < n and heap[left].key < heap[smallest].key:
                smallest = left
            if right < n and heap[right].key < heap[smallest].key:
                smallest = right
            if smallest == k:
                break
            heap[k], heap[smallest] = heap[smallest], heap[k]
            k = smallest


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm."""

    def __init__(self, graph, source, config=None):
        if source not in graph.adjacency:
            raise ValueError(f"Source station number {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        # Accumulated cost from the source to each reached station.
        self.dist_to = {source: 0.0}
        # Last edge used to reach each station (for backtracking).
        self.edge_to = {}
        self._settled = set()
        self._run()

    def _run(self):
        pq = MinPQ()
        pq.insert(0.0, self.source)
        penalty = self.config.transfer_penalty
        while not pq.is_empty():
            dist, vertex = pq.del_min()
            if vertex in self._settled:
                continue
            self._settled.add(vertex)
            # Line the passenger is riding when arriving at ``vertex``.
            incoming_line = self.edge_to[vertex].line if vertex in self.edge_to else None
            for edge in self.graph.neighbors(vertex):
                nxt = edge.other(vertex)
                if nxt in self._settled:
                    continue
                cost = self.config.edge_cost(edge)
                if incoming_line is not None and edge.line != incoming_line:
                    cost += penalty
                candidate = dist + cost
                if candidate < self.dist_to.get(nxt, math.inf):
                    self.dist_to[nxt] = candidate
                    self.edge_to[nxt] = edge
                    pq.insert(candidate, nxt)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self.dist_to

    def path_with_edges(self, target):
        """Return (station numbers, edges) from the source to ``target``.

        Returns ([], []) if the target is unreachable.
        """
        if target not in self.dist_to:
            return [], []
        nodes = [target]
        edges = []
        vertex = target
        while vertex != self.source:
            edge = self.edge_to[vertex]
            edges.append(edge)
            vertex = edge.other(vertex)
            nodes.append(vertex)
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target``."""
        _, edges = self.path_with_edges(target)
        return sum(1 for prev, cur in zip(edges, edges[1:]) if prev.line != cur.line)


def _build_segments(names, edges):
    """Group consecutive edges on the same line into Segment objects."""
    segments = []
    if not edges:
        return segments
    seg_start = 0
    for k in range(1, len(edges) + 1):
        if k == len(edges) or edges[k].line != edges[seg_start].line:
            seg_edges = edges[seg_start:k]
            seg_names = names[seg_start:k + 1]
            segments.append(Segment(
                line=seg_edges[0].line,
                start=seg_names[0],
                end=seg_names[-1],
                stations=list(seg_names),
                distance_m=sum(e.distance for e in seg_edges),
            ))
            seg_start = k
    return segments


def _compute_path(graph, start, end, config):
    """Run Dijkstra once and convert the result into a Path object."""
    sp = ShortestPath(graph, start, config)
    if not sp.has_path_to(end):
        raise PathNotFoundError(
            f"No route found between '{graph.name_of(start)}' and '{graph.name_of(end)}'"
        )
    nodes, edges = sp.path_with_edges(end)
    names = [graph.name_of(n) for n in nodes]
    segments = _build_segments(names, edges)

    transfers = []
    for idx in range(1, len(segments)):
        transfers.append(TransferInfo(
            station=segments[idx].start,
            from_line=segments[idx - 1].line,
            to_line=segments[idx].line,
        ))

    involved = []
    for seg in segments:
        if seg.line not in involved:
            involved.append(seg.line)

    total_distance = sum(e.distance for e in edges)
    return Path(
        station_sequence=names,
        total_distance_m=total_distance,
        transfer_count=len(transfers),
        involved_lines=involved,
        segments=segments,
        transfers=transfers,
    )


def find_route(graph, start_name, end_name, config=None):
    """Compute the route between two stations according to ``config``.

    If ``max_transfers`` is exceeded by a distance-oriented route, the
    minimum-transfer route is tried as a fallback. Raises PathNotFoundError
    if no route exists and PathfindingError if the transfer limit cannot be met.
    """
    config = config or PathfindingConfig()
    start = graph.number_of(start_name)
    end = graph.number_of(end_name)

    if start == end:
        return Path(
            station_sequence=[start_name],
            total_distance_m=0.0,
            transfer_count=0,
            involved_lines=[],
            segments=[],
            transfers=[],
        )

    path = _compute_path(graph, start, end, config)
    used_config = config
    if (config.max_transfers is not None
            and path.transfer_count > config.max_transfers
            and config.mode != MODE_LEAST_TRANSFER):
        used_config = PathfindingConfig(MODE_LEAST_TRANSFER, config.max_transfers, config.preferred_lines)
        path = _compute_path(graph, start, end, used_config)

    if used_config.max_transfers is not None and path.transfer_count > used_config.max_transfers:
        raise PathfindingError(
            f"The route requires {path.transfer_count} transfer(s), which exceeds the "
            f"maximum of {used_config.max_transfers}"
        )
    return path
