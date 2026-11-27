"""Shortest-path computation on the subway graph using Dijkstra's algorithm.

The search runs over states (station number, line used to arrive). A change
of line between consecutive edges at a station counts as one transfer. This
lets the search honour transfer limits and minimum-transfer ordering exactly.
"""

import heapq
import itertools
from dataclasses import dataclass

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty (meters) added for each transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 1000.0
# Equivalent distance penalty (meters) added per edge not on a preferred line.
PREFERRED_LINE_PENALTY_METERS = 500.0


class PathfindingError(Exception):
    """Base error for path calculation problems."""


class PathNotFoundError(PathfindingError):
    """Raised when no route satisfies the query constraints."""


class MinPQ:
    """Binary-heap min priority queue used by Dijkstra's algorithm.

    Entries are (key, sequence, value); the sequence number guarantees that
    values are never compared directly. Insertion and removal are O(log n).
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    @property
    def size(self):
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        return not self._heap

    def insert(self, key, value):
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def min_key(self):
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def del_min(self):
        """Remove and return the (key, value) pair with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, value = heapq.heappop(self._heap)
        return key, value


class PathfindingConfig:
    """Query configuration for path calculation.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed transfers, or None for unlimited.
        preferred_lines: list of line names that are preferred.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self):
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{self.mode}', choose from {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")


class _SearchRecord:
    """Best-known label of a search state."""

    __slots__ = ("key", "weight", "transfers", "distance", "parent", "edge")

    def __init__(self, key, weight, transfers, distance, parent, edge):
        self.key = key
        self.weight = weight
        self.transfers = transfers
        self.distance = distance
        self.parent = parent
        self.edge = edge


class ShortestPath:
    """Single-source shortest path search on a Graph.

    Attributes:
        dist_to: dict mapping reachable station numbers to the actual travel
            distance in meters of the chosen path.
    """

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._records = {}
        self._best_state = {}
        self._run()

    def _make_key(self, transfers, weight):
        """Build the priority key for a label according to the search mode."""
        if self.config.mode == MODE_LEAST_TRANSFER:
            return (transfers, weight)
        return (weight,)

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        config = self.config
        start_state = (self.source, None)
        start_key = self._make_key(0, 0.0)
        self._records[start_state] = _SearchRecord(start_key, 0.0, 0, 0.0, None, None)

        pq = MinPQ()
        pq.insert(start_key, start_state)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            done.add(state)
            node, prev_line = state
            record = self._records[state]

            for edge in self.graph.adjacent(node):
                nxt_node = edge.other(node)
                is_transfer = prev_line is not None and edge.line != prev_line
                new_transfers = record.transfers + (1 if is_transfer else 0)
                if config.max_transfers is not None and new_transfers > config.max_transfers:
                    continue

                penalty = 0.0
                if config.preferred_lines and edge.line not in config.preferred_lines:
                    penalty = PREFERRED_LINE_PENALTY_METERS
                weight = record.weight + edge.distance + penalty
                if is_transfer and config.mode == MODE_COMPREHENSIVE:
                    weight += TRANSFER_PENALTY_METERS

                new_state = (nxt_node, edge.line)
                if new_state in done:
                    continue
                new_key = self._make_key(new_transfers, weight)
                existing = self._records.get(new_state)
                if existing is None or new_key < existing.key:
                    self._records[new_state] = _SearchRecord(
                        new_key,
                        weight,
                        new_transfers,
                        record.distance + edge.distance,
                        state,
                        edge,
                    )
                    pq.insert(new_key, new_state)

        # Select the best state for every station.
        for state, record in self._records.items():
            node = state[0]
            best = self._best_state.get(node)
            if best is None or record.key < self._records[best].key:
                self._best_state[node] = state
        for node, state in self._best_state.items():
            self.dist_to[node] = self._records[state].distance

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the query constraints."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return the station numbers and edges of the shortest path to ``target``.

        Returns:
            (list of station numbers from source to target, list of Edge objects)

        Raises:
            PathNotFoundError: if the target is unreachable.
        """
        if target not in self._best_state:
            raise PathNotFoundError(f"No path found to station number {target}")
        state = self._best_state[target]
        nodes = []
        edges = []
        while True:
            record = self._records[state]
            nodes.append(state[0])
            if record.parent is None:
                break
            edges.append(record.edge)
            state = record.parent
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the chosen path to ``target``."""
        if target not in self._best_state:
            raise PathNotFoundError(f"No path found to station number {target}")
        return self._records[self._best_state[target]].transfers


@dataclass
class Segment:
    """A contiguous ride on one line."""

    line: str
    start: str
    end: str
    stations: list
    distance_meters: float


@dataclass
class TransferInfo:
    """A transfer point between two line segments."""

    station: str
    from_line: str
    to_line: str
    all_lines: list


class Route:
    """A computed route with derived segment and transfer information."""

    def __init__(self, mode, station_sequence, edges, transfer_count, lines_at=None):
        self.mode = mode
        self.station_sequence = list(station_sequence)
        self.edges = list(edges)
        self.transfer_count = int(transfer_count)
        self._lines_at = lines_at
        self.segments = self._build_segments()
        self.transfers = self._build_transfers()

    @property
    def total_distance_meters(self):
        return sum(edge.distance for edge in self.edges)

    @property
    def involved_lines(self):
        """Ordered list of unique line names used by the route."""
        result = []
        for edge in self.edges:
            if edge.line not in result:
                result.append(edge.line)
        return result

    def _build_segments(self):
        segments = []
        for i, edge in enumerate(self.edges):
            current = self.station_sequence[i]
            nxt = self.station_sequence[i + 1]
            if not segments or segments[-1].line != edge.line:
                segments.append(Segment(edge.line, current, current, [current], 0.0))
            seg = segments[-1]
            seg.stations.append(nxt)
            seg.end = nxt
            seg.distance_meters += edge.distance
        return segments

    def _build_transfers(self):
        transfers = []
        for prev, nxt in zip(self.segments, self.segments[1:]):
            station = prev.end
            all_lines = list(self._lines_at(station)) if self._lines_at else []
            for line in (prev.line, nxt.line):
                if line not in all_lines:
                    all_lines.append(line)
            transfers.append(TransferInfo(station, prev.line, nxt.line, all_lines))
        return transfers


def compute_route(network, start_name, end_name, config=None):
    """Compute the route between two official station names.

    Args:
        network: a SubwayNetwork instance.
        start_name: official starting station name.
        end_name: official ending station name.
        config: PathfindingConfig (defaults to shortest distance, unlimited transfers).

    Returns:
        Route describing the stations, edges and transfers.

    Raises:
        PathNotFoundError: if no route satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    source = network.get_number(start_name)
    target = network.get_number(end_name)
    search = ShortestPath(network.graph, source, config)
    if not search.has_path_to(target):
        raise PathNotFoundError(
            f"No route found from '{start_name}' to '{end_name}' under the current constraints"
        )
    nodes, edges = search.path_with_edges(target)
    names = [network.get_name(number) for number in nodes]
    return Route(
        mode=config.mode,
        station_sequence=names,
        edges=edges,
        transfer_count=search.get_transfer_count(target),
        lines_at=network.get_station_lines,
    )
