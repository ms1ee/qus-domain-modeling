"""Shortest-path computation with Dijkstra's algorithm.

Dijkstra is run over states ``(station_number, line_of_last_edge)``. This lets
the search account for transfers (a change of line at a station) exactly,
which is required by the minimum-transfer and comprehensive modes.

Cost models:
    shortest_distance : minimise total distance, transfers break ties
    least_transfer    : minimise transfers, distance breaks ties
    comprehensive     : distance plus a penalty per transfer
Line preference adds a soft penalty to edges that are not on a preferred line.
"""

from __future__ import annotations

from min_pq import MinPQ
from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for each transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 1000.0
# Equivalent distance (meters) charged for each edge outside preferred lines.
PREFERENCE_PENALTY_METERS = 500.0


class PathNotFoundError(Exception):
    """Raised when no path satisfies the query constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of ``VALID_MODES``.
        max_transfers: Maximum number of transfers allowed, or ``None`` for
            no limit.
        preferred_lines: Lines that are preferred (empty list = no preference).
    """

    def __init__(self, mode: str = MODE_COMPREHENSIVE, max_transfers=None,
                 preferred_lines=None) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: list[str] = list(preferred_lines or [])


class _Label:
    """Best known information about a search state."""

    __slots__ = ("cost", "distance", "transfers", "penalty", "prev", "edge")

    def __init__(self, cost, distance, transfers, penalty, prev, edge) -> None:
        self.cost = cost
        self.distance = distance
        self.transfers = transfers
        self.penalty = penalty
        self.prev = prev
        self.edge = edge


class ShortestPath:
    """Single-source optimal paths over a subway ``Graph``.

    Attributes:
        dist_to: Station number -> real travelled distance in meters of the
            best path found (reachable stations only).
        transfers_to: Station number -> number of transfers on that path.
    """

    def __init__(self, graph: Graph, source: int, config: PathfindingConfig = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: dict[int, float] = {}
        self.transfers_to: dict[int, int] = {}
        self._labels: dict[tuple, _Label] = {}
        self._best_state: dict[int, tuple] = {}
        self._run()

    # ----- cost model ---------------------------------------------------
    def _cost(self, distance: float, transfers: int, penalty: float) -> tuple:
        total = distance + penalty
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return (total, transfers)
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, total)
        return (total + TRANSFER_PENALTY_METERS * transfers,)

    # ----- Dijkstra -----------------------------------------------------
    def _run(self) -> None:
        preferred = set(self.config.preferred_lines)
        max_transfers = self.config.max_transfers

        start = (self.source, None)
        start_cost = self._cost(0.0, 0, 0.0)
        self._labels[start] = _Label(start_cost, 0.0, 0, 0.0, None, None)

        pq = MinPQ()
        pq.insert(start, start_cost)
        settled: set[tuple] = set()

        while not pq.is_empty():
            state = pq.del_min()
            if state in settled:
                continue
            settled.add(state)
            node, line = state
            label = self._labels[state]

            for edge in self.graph.neighbors(node):
                next_node = edge.other(node)
                next_state = (next_node, edge.line)
                if next_state in settled:
                    continue
                transfers = label.transfers
                if line is not None and edge.line != line:
                    transfers += 1
                if max_transfers is not None and transfers > max_transfers:
                    continue
                distance = label.distance + edge.weight
                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_METERS
                cost = self._cost(distance, transfers, penalty)
                existing = self._labels.get(next_state)
                if existing is None or cost < existing.cost:
                    self._labels[next_state] = _Label(
                        cost, distance, transfers, penalty, state, edge
                    )
                    pq.insert(next_state, cost)

        # Select the best state for every reachable station.
        for state, label in self._labels.items():
            if state not in settled:
                continue
            node = state[0]
            current = self._best_state.get(node)
            if current is None or label.cost < self._labels[current].cost:
                self._best_state[node] = state

        for node, state in self._best_state.items():
            label = self._labels[state]
            self.dist_to[node] = label.distance
            self.transfers_to[node] = label.transfers

    # ----- results ------------------------------------------------------
    def has_path_to(self, target: int) -> bool:
        return target in self._best_state

    def path_with_edges(self, target: int) -> tuple[list[int], list[Edge]]:
        """Return the station numbers and edges of the path source -> target.

        Raises:
            PathNotFoundError: If ``target`` cannot be reached under the
                configured constraints.
        """
        if not self.has_path_to(target):
            raise PathNotFoundError(f"station {target} is unreachable from the source")
        state = self._best_state[target]
        nodes: list[int] = []
        edges: list[Edge] = []
        while True:
            label = self._labels[state]
            nodes.append(state[0])
            if label.prev is None:
                break
            edges.append(label.edge)
            state = label.prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line transfers on the path to ``target``."""
        if not self.has_path_to(target):
            raise PathNotFoundError(f"station {target} is unreachable from the source")
        return self.transfers_to[target]
