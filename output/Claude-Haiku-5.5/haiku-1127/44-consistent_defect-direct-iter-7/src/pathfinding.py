"""Shortest-path computation over the subway graph.

Dijkstra's algorithm runs over search states ``(station, arriving_line,
transfers_so_far)``. A transfer happens whenever the arriving line differs
from the line of the next edge. Each mode uses its own edge cost:

* ``shortest_distance``: cost = distance in meters.
* ``least_transfer``:    cost = large penalty per transfer + distance (tie-break).
* ``comprehensive``:     cost = estimated minutes (1.5 min/km + 5 min/transfer).

A soft line preference adds a penalty to edges outside the preferred lines.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from src.fare_calculator import MINUTES_PER_KM, MINUTES_PER_TRANSFER
from src.min_pq import MinPQ
from src.models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES: Tuple[str, ...] = (
    MODE_SHORTEST_DISTANCE,
    MODE_LEAST_TRANSFER,
    MODE_COMPREHENSIVE,
)

# Transfer limit applied when the user does not specify --max_transfers.
# It bounds the search state space and guarantees termination.
DEFAULT_TRANSFER_LIMIT = 10
TRANSFER_COST_LEAST_TRANSFER = 1_000_000.0
PREFERENCE_PENALTY = {
    MODE_SHORTEST_DISTANCE: 1000.0,  # meters
    MODE_LEAST_TRANSFER: 1000.0,     # meters (tie-break scale)
    MODE_COMPREHENSIVE: 1.0,         # minutes
}

State = Tuple[int, Optional[str], int]


class PathfindingConfig:
    """User-facing options for a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum number of transfers allowed, or None for no limit.
        preferred_lines: lines favoured by the route search (soft preference).
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[List[str]] = None,
    ) -> None:
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines) if preferred_lines else []
        self.validate()

    def validate(self) -> None:
        """Raise ValueError if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}"
            )
        if self.max_transfers is not None:
            if not isinstance(self.max_transfers, int) or isinstance(self.max_transfers, bool):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")

    def __repr__(self) -> str:
        return (
            f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
            f"preferred_lines={self.preferred_lines!r})"
        )


class ShortestPath:
    """Single-source shortest path computation (Dijkstra with a binary heap).

    Attributes:
        dist_to: mapping of station number -> minimal cost (mode dependent;
            in ``shortest_distance`` mode this is the distance in meters).
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number {source}")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()

        self._limit: int = (
            self.config.max_transfers
            if self.config.max_transfers is not None
            else DEFAULT_TRANSFER_LIMIT
        )
        self._cost: Dict[State, float] = {}
        self._prev: Dict[State, Tuple[State, Edge]] = {}
        self._best: Dict[int, State] = {}
        self.dist_to: Dict[int, float] = {}
        self._run()

    # ------------------------------------------------------------------ search
    def _edge_cost(self, edge: Edge, is_transfer: bool) -> float:
        """Cost of traversing ``edge`` under the configured mode."""
        mode = self.config.mode
        if mode == MODE_COMPREHENSIVE:
            cost = edge.weight / 1000.0 * MINUTES_PER_KM
            if is_transfer:
                cost += MINUTES_PER_TRANSFER
        elif mode == MODE_LEAST_TRANSFER:
            cost = edge.weight + (TRANSFER_COST_LEAST_TRANSFER if is_transfer else 0.0)
        else:
            cost = edge.weight

        preferred = self.config.preferred_lines
        if preferred and edge.line not in preferred:
            cost += PREFERENCE_PENALTY[mode]
        return cost

    def _run(self) -> None:
        start: State = (self.source, None, 0)
        self._cost[start] = 0.0
        pq = MinPQ()
        pq.insert(0.0, start)

        while not pq.is_empty():
            cost, state = pq.del_min()
            if cost > self._cost.get(state, math.inf):
                continue  # stale heap entry
            node, line, transfers = state

            for edge in self.graph.adjacent(node):
                is_transfer = line is not None and edge.line != line
                new_transfers = transfers + 1 if is_transfer else transfers
                if new_transfers > self._limit:
                    continue
                new_state: State = (edge.dest, edge.line, new_transfers)
                new_cost = cost + self._edge_cost(edge, is_transfer)
                if new_cost < self._cost.get(new_state, math.inf):
                    self._cost[new_state] = new_cost
                    self._prev[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

        # Pick the best search state for every station (lowest cost, then fewest transfers).
        for state, cost in self._cost.items():
            node = state[0]
            best = self._best.get(node)
            if best is None or (cost, state[2]) < (self._cost[best], best[2]):
                self._best[node] = state
        for node, state in self._best.items():
            self.dist_to[node] = self._cost[state]

    # ----------------------------------------------------------------- queries
    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable from the source."""
        return target in self._best

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return the route to ``target`` by backtracking predecessors.

        The station list is ordered from the target back to the source (end to
        start). ``edges[i]`` is the edge whose destination is ``stations[i]``
        and whose source is ``stations[i + 1]``. If the target is unreachable,
        ``([], [])`` is returned.
        """
        state = self._best.get(target)
        if state is None:
            return [], []

        stations: List[int] = []
        edges: List[Edge] = []
        current = state
        while current in self._prev:
            stations.append(current[0])
            prev_state, edge = self._prev[current]
            edges.append(edge)
            current = prev_state
        stations.append(current[0])  # the source station
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of transfers on the best route to ``target`` (0 if unreachable)."""
        state = self._best.get(target)
        if state is None:
            return 0
        return state[2]

    def get_total_distance(self, target: int) -> float:
        """Return the total distance in meters on the best route to ``target``."""
        _, edges = self.path_with_edges(target)
        return float(sum(edge.weight for edge in edges))
