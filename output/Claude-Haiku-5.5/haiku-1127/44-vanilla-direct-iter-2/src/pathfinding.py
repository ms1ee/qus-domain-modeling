"""Path calculation: Dijkstra's algorithm with a binary-heap priority queue.

The search runs over (station, arriving line) states so that line changes
(transfers) can be counted and constrained. Three query modes are supported:

* shortest_distance - minimise total travelled distance (meters)
* least_transfer    - minimise the number of transfers, then the distance
* comprehensive     - minimise an estimated travel time that combines distance
                      (about 1.5 min/km) and transfers (about 5 min each)

Line preference: edges on lines not listed in ``preferred_lines`` incur a
penalty of PREFERENCE_PENALTY_METERS during the search. The reported distance
is always the real travelled distance.
"""

import heapq
import itertools

from fare_calculator import MINUTES_PER_KM, MINUTES_PER_TRANSFER

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

PREFERENCE_PENALTY_METERS = 1000.0


class NoPathError(Exception):
    """Raised when no path exists between two stations under the given constraints."""


class PathfindingConfig:
    """Configuration for path queries.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum allowed number of transfers, or None for no limit.
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
            raise ValueError(f"Unknown path mode '{self.mode}'. Valid modes: {', '.join(VALID_MODES)}")
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(self.max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if self.max_transfers < 0:
                raise ValueError("max_transfers cannot be negative")


class MinPQ:
    """Min priority queue implemented on top of a binary heap (heapq)."""

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return (key, item) with the smallest key."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)


class _Label:
    """Best known information for a search state."""

    __slots__ = ("cost", "distance", "transfers", "penalty", "prev_state", "prev_edge")

    def __init__(self, cost, distance, transfers, penalty, prev_state, prev_edge):
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.penalty = penalty
        self.prev_state = prev_state
        self.prev_edge = prev_edge


class ShortestPath:
    """Single-source shortest path computation.

    Attributes:
        dist_to: dict mapping reachable station numbers to the real travelled
                 distance in meters from the source.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"Source vertex {source!r} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()

        self.dist_to = {}
        self._labels = {}          # (station, arriving line) -> _Label
        self._node_state = {}      # station -> finalised best state
        self._run()

    def _cost(self, distance, transfers, penalty):
        """Return a comparable cost tuple for the configured mode."""
        total = distance + penalty
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, total)
        if mode == MODE_COMPREHENSIVE:
            score = (total / 1000.0) * MINUTES_PER_KM + transfers * MINUTES_PER_TRANSFER
            return (score, total)
        return (total, transfers)

    def _run(self):
        """Run Dijkstra's algorithm over (station, line) states."""
        start_state = (self.source, None)
        self._labels[start_state] = _Label(
            cost=self._cost(0, 0, 0.0),
            distance=0.0,
            transfers=0,
            penalty=0.0,
            prev_state=None,
            prev_edge=None,
        )

        queue = MinPQ()
        queue.insert(self._labels[start_state].cost, start_state)
        finalised = set()
        max_transfers = self.config.max_transfers
        preferred = set(self.config.preferred_lines)

        while not queue.is_empty():
            _, state = queue.del_min()
            if state in finalised:
                continue
            finalised.add(state)

            node, arriving_line = state
            label = self._labels[state]
            if node not in self._node_state:
                self._node_state[node] = state
                self.dist_to[node] = label.distance

            for edge in self.graph.adjacent_edges(node):
                next_node = edge.other(node)
                next_state = (next_node, edge.line)
                if next_state in finalised:
                    continue

                transfer = 1 if (arriving_line is not None and edge.line != arriving_line) else 0
                new_transfers = label.transfers + transfer
                if max_transfers is not None and new_transfers > max_transfers:
                    continue

                new_distance = label.distance + edge.distance
                new_penalty = label.penalty
                if preferred and edge.line not in preferred:
                    new_penalty += PREFERENCE_PENALTY_METERS

                new_cost = self._cost(new_distance, new_transfers, new_penalty)
                existing = self._labels.get(next_state)
                if existing is None or new_cost < existing.cost:
                    self._labels[next_state] = _Label(
                        cost=new_cost,
                        distance=new_distance,
                        transfers=new_transfers,
                        penalty=new_penalty,
                        prev_state=state,
                        prev_edge=edge,
                    )
                    queue.insert(new_cost, next_state)

    def has_path_to(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._node_state

    def path_with_edges(self, target):
        """Return (station numbers, edges) from the source to ``target``.

        Raises NoPathError if the target is unreachable.
        """
        if target not in self._node_state:
            raise NoPathError(f"No path found to station number {target}")
        state = self._node_state[target]
        nodes = []
        edges = []
        while state is not None:
            label = self._labels[state]
            nodes.append(state[0])
            if label.prev_edge is not None:
                edges.append(label.prev_edge)
            state = label.prev_state
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target``."""
        if target not in self._node_state:
            raise NoPathError(f"No path found to station number {target}")
        return self._labels[self._node_state[target]].transfers


class Route:
    """Result of a path query with station names and edges."""

    def __init__(self, stations, edges, distance, transfer_count, config):
        self.stations = stations
        self.edges = edges
        self.distance = distance
        self.transfer_count = transfer_count
        self.config = config


def find_route(network, source_name, target_name, config=None):
    """Compute a route between two stations given by name."""
    config = config if config is not None else PathfindingConfig()
    source = network.number_of(source_name)
    target = network.number_of(target_name)
    sp = ShortestPath(network.graph, source, config)
    numbers, edges = sp.path_with_edges(target)
    stations = [network.name_of(number) for number in numbers]
    return Route(
        stations=stations,
        edges=edges,
        distance=sp.dist_to[target],
        transfer_count=sp.get_transfer_count(target),
        config=config,
    )
