"""Path calculation for the Beijing Subway network.

The module implements Dijkstra's algorithm on an expanded state space. A state
is a pair ``(station_number, arriving_line)``: this lets the search count line
transfers exactly. The priority queue is the indexed binary heap ``MinPQ``,
giving O((V + E) log V) behaviour.

Supported query modes:
    shortest_distance -- minimise total travelled distance (meters)
    least_transfer    -- minimise transfers, then distance
    comprehensive     -- minimise distance + transfer_penalty * transfers
Optional settings:
    max_transfers     -- paths with more transfers are discarded
    preferred_lines   -- edges on other lines receive a penalty in the search
                         cost (the reported distance stays the real distance)
"""

import math
from dataclasses import dataclass, field

from min_pq import MinPQ

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Cost (in meters) of each transfer in comprehensive mode.
DEFAULT_TRANSFER_PENALTY_M = 1000.0
# Extra search cost (in meters) for riding a line outside the preferred list.
DEFAULT_PREFERENCE_PENALTY_M = 500.0


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum allowed transfers, or None for no limit.
        preferred_lines: List of preferred line names (empty means no preference).
        transfer_penalty: Cost per transfer in comprehensive mode, in meters.
        preference_penalty: Extra search cost per non-preferred edge, in meters.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None,
                 transfer_penalty=DEFAULT_TRANSFER_PENALTY_M,
                 preference_penalty=DEFAULT_PREFERENCE_PENALTY_M):
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if (isinstance(max_transfers, bool) or not isinstance(max_transfers, int)
                    or max_transfers < 0):
                raise ValueError("max_transfers must be a non-negative integer")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])
        self.transfer_penalty = float(transfer_penalty)
        self.preference_penalty = float(preference_penalty)

    def penalty_for_edge(self, edge):
        """Return the extra search cost of riding ``edge``."""
        if not self.preferred_lines or edge.line in self.preferred_lines:
            return 0.0
        return self.preference_penalty

    def key(self, cost, transfers):
        """Build the priority key used by Dijkstra for a search state.

        Every component is non-decreasing along a path, so the keys are
        monotone and Dijkstra's algorithm remains correct.
        """
        if self.mode == MODE_SHORTEST_DISTANCE:
            return (cost, transfers)
        if self.mode == MODE_LEAST_TRANSFER:
            return (transfers, cost)
        return (cost + self.transfer_penalty * transfers, transfers)


class _StateInfo:
    """Bookkeeping for one search state (station, arriving line)."""

    __slots__ = ("cost", "distance", "transfers", "key", "prev", "edge")

    def __init__(self, cost, distance, transfers, key, prev, edge):
        self.cost = cost              # search cost including penalties
        self.distance = distance      # real travelled distance in meters
        self.transfers = transfers    # number of line changes so far
        self.key = key                # priority key
        self.prev = prev              # predecessor state, or None
        self.edge = edge              # edge used to reach this state, or None


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    Attributes:
        dist_to: dict station number -> real distance (meters) of the best path.
        transfers_to: dict station number -> transfer count of the best path.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self.transfers_to = {}
        self._best_state = {}   # station number -> best finalized state
        self._info = {}         # state -> _StateInfo
        self._run()

    def _run(self):
        """Execute Dijkstra's algorithm over (station, line) states."""
        cfg = self.config
        start = (self.source, None)
        start_info = _StateInfo(0.0, 0, 0, cfg.key(0.0, 0), None, None)
        self._info[start] = start_info

        pq = MinPQ()
        pq.put(start, start_info.key)
        while not pq.is_empty():
            state, _ = pq.del_min()
            info = self._info[state]
            node, line = state

            # The first state popped for a station has the minimum key for it.
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = info.distance
                self.transfers_to[node] = info.transfers

            for edge in self.graph.adj(node):
                transfers = info.transfers
                if line is not None and edge.line != line:
                    transfers += 1  # changing lines at this station
                if cfg.max_transfers is not None and transfers > cfg.max_transfers:
                    continue

                cost = info.cost + edge.distance + cfg.penalty_for_edge(edge)
                distance = info.distance + edge.distance
                key = cfg.key(cost, transfers)
                next_state = (edge.other(node), edge.line)

                old = self._info.get(next_state)
                if old is not None and old.key <= key:
                    continue
                self._info[next_state] = _StateInfo(cost, distance, transfers,
                                                    key, state, edge)
                pq.put(next_state, key)

    def has_path_to(self, target):
        """Return True if station ``target`` is reachable under the constraints."""
        return target in self._best_state

    def distance_to(self, target):
        """Return the travelled distance in meters, or ``math.inf`` if unreachable."""
        if target not in self._best_state:
            return math.inf
        return self.dist_to[target]

    def get_transfer_count(self, target):
        """Return the number of transfers on the best path, or -1 if unreachable."""
        return self.transfers_to.get(target, -1)

    def path_with_edges(self, target):
        """Return the station numbers and edges of the best path to ``target``.

        Returns:
            tuple: ``(stations, edges)`` where ``stations`` runs from the source
            to ``target`` and ``edges`` has one fewer element. Both lists are
            empty if the target is unreachable.
        """
        state = self._best_state.get(target)
        nodes, edges = [], []
        while state is not None:
            info = self._info[state]
            nodes.append(state[0])
            if info.edge is not None:
                edges.append(info.edge)
            state = info.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        """Return the station numbers of the best path to ``target``."""
        return self.path_with_edges(target)[0]


@dataclass
class Route:
    """Result of a path query, with all information needed for reporting.

    Attributes:
        start: Starting station name.
        end: Ending station name.
        mode: Query mode used.
        stations: Ordered station names from start to end.
        edges: Edges traversed, one per consecutive station pair.
        segments: Line segments: list of ``{"line": str, "stations": [str]}``.
        transfer_stations: List of ``{"station", "from_line", "to_line"}``.
        lines: Unique line names in the order they are ridden.
        distance: Total distance in meters.
        transfer_count: Number of transfers.
    """

    start: str
    end: str
    mode: str
    stations: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfer_stations: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    distance: float = 0
    transfer_count: int = 0


def _build_segments(names, edges):
    """Group consecutive edges on the same line into segments."""
    segments = []
    if not edges:
        return segments
    current = {"line": edges[0].line, "stations": [names[0]]}
    for index, edge in enumerate(edges):
        if edge.line != current["line"]:
            segments.append(current)
            current = {"line": edge.line, "stations": [names[index]]}
        current["stations"].append(names[index + 1])
    segments.append(current)
    return segments


def plan_route(network, start, end, config=None):
    """Compute the route between two stations.

    Args:
        network: ``SubwayNetwork`` instance.
        start: Starting station name (must exist in the network).
        end: Ending station name (must exist in the network).
        config: ``PathfindingConfig`` or None for defaults.

    Returns:
        Route: The computed route.

    Raises:
        KeyError: If a station name is unknown.
        PathNotFoundError: If no path satisfies the constraints.
    """
    cfg = config if config is not None else PathfindingConfig()
    source = network.number_of(start)
    target = network.number_of(end)

    sp = ShortestPath(network.graph, source, cfg)
    if not sp.has_path_to(target):
        message = f"No route found from '{start}' to '{end}'"
        if cfg.max_transfers is not None:
            message += f" within the transfer limit of {cfg.max_transfers}"
        raise PathNotFoundError(message)

    numbers, edges = sp.path_with_edges(target)
    names = [network.name_of(number) for number in numbers]
    segments = _build_segments(names, edges)

    transfer_stations = []
    for index in range(1, len(segments)):
        transfer_stations.append({
            "station": segments[index]["stations"][0],
            "from_line": segments[index - 1]["line"],
            "to_line": segments[index]["line"],
        })

    lines = []
    for segment in segments:
        if segment["line"] not in lines:
            lines.append(segment["line"])

    return Route(
        start=start,
        end=end,
        mode=cfg.mode,
        stations=names,
        edges=edges,
        segments=segments,
        transfer_stations=transfer_stations,
        lines=lines,
        distance=sum(edge.distance for edge in edges),
        transfer_count=sp.get_transfer_count(target),
    )
