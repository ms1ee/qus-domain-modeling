"""
Path calculation module.

Implements Dijkstra's algorithm (priority-queue optimised) over an expanded
state space (station, current line[, transfers]) so that transfers at
multi-line interchange stations are handled correctly.

Supported modes:
    * shortest_distance - minimise total distance (ties -> fewer transfers)
    * least_transfer    - minimise transfers (ties -> shorter distance)
    * comprehensive     - minimise distance + transfers * transfer_penalty
"""

from __future__ import annotations

import itertools
from typing import Dict, List, Optional, Tuple

from models import Edge, Graph, MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")

# Equivalent distance (meters) charged per transfer in comprehensive mode.
# Models walking distance / waiting time at interchange stations.
DEFAULT_TRANSFER_PENALTY = 3000
# Weight multiplier applied (for routing score only) to non-preferred lines.
DEFAULT_NON_PREFERRED_FACTOR = 1.5

INF = float("inf")


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode: str = "shortest_distance",
                 max_transfers: Optional[int] = None,
                 preferred_lines: Optional[List[str]] = None,
                 transfer_penalty: float = DEFAULT_TRANSFER_PENALTY,
                 non_preferred_factor: float = DEFAULT_NON_PREFERRED_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', must be one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers cannot be negative")
        if transfer_penalty < 0:
            raise ValueError("transfer_penalty cannot be negative")
        if non_preferred_factor < 1:
            raise ValueError("non_preferred_factor must be >= 1")
        self.mode = mode
        self.max_transfers = max_transfers
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.preferred_lines = [p.strip() for p in preferred_lines if p and p.strip()]
        self.transfer_penalty = transfer_penalty
        self.non_preferred_factor = non_preferred_factor

    def __repr__(self) -> str:
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


def _norm_line(name: Optional[str]) -> str:
    return " ".join(str(name).split()).lower() if name is not None else ""


class ShortestPath:
    """Dijkstra single-source shortest paths from ``source`` (station number)."""

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to: Dict[int, float] = {v: INF for v in graph.vertices()}
        self.dist_to[source] = 0
        self._transfers_to: Dict[int, int] = {source: 0}
        self._best_state: Dict[int, tuple] = {}
        self._parent: Dict[tuple, Optional[Tuple[tuple, Edge]]] = {}
        self._preferred = {_norm_line(p) for p in self.config.preferred_lines}
        self._run()

    # ------------------------------------------------------------ internals
    def _edge_score(self, edge: Edge) -> float:
        if self._preferred and _norm_line(edge.line) not in self._preferred:
            return edge.weight * self.config.non_preferred_factor
        return edge.weight

    def _cost(self, score_dist: float, transfers: int, dist: float) -> tuple:
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, score_dist, dist)
        if mode == "comprehensive":
            return (score_dist + transfers * self.config.transfer_penalty, transfers, dist)
        return (score_dist, transfers, dist)

    def _run(self) -> None:
        max_t = self.config.max_transfers
        track = max_t is not None
        start = (self.source, None, 0 if track else None)
        # info[state] = (distance, transfers, score_distance)
        info: Dict[tuple, Tuple[float, int, float]] = {start: (0, 0, 0)}
        best_cost: Dict[tuple, tuple] = {start: self._cost(0, 0, 0)}
        settled = set()
        self._parent[start] = None
        counter = itertools.count()
        pq = MinPQ()
        pq.insert((best_cost[start], next(counter), start))

        while pq:
            cost, _, state = pq.del_min()
            if state in settled or cost > best_cost[state]:
                continue
            settled.add(state)
            v, line, _t = state
            d, t, sd = info[state]
            for edge in self.graph.adj(v):
                w = edge.other(v)
                new_t = t + (1 if (line is not None and edge.line != line) else 0)
                if track and new_t > max_t:
                    continue
                new_d = d + edge.weight
                new_sd = sd + self._edge_score(edge)
                ns = (w, edge.line, new_t if track else None)
                if ns in settled:
                    continue
                nc = self._cost(new_sd, new_t, new_d)
                if ns not in best_cost or nc < best_cost[ns]:
                    best_cost[ns] = nc
                    info[ns] = (new_d, new_t, new_sd)
                    self._parent[ns] = (state, edge)
                    pq.insert((nc, next(counter), ns))

        # Pick, for every vertex, the best state reaching it.
        best_for_vertex: Dict[int, tuple] = {}
        for state in settled:
            v = state[0]
            if v not in best_for_vertex or best_cost[state] < best_cost[best_for_vertex[v]]:
                best_for_vertex[v] = state
        best_for_vertex[self.source] = start
        for v, state in best_for_vertex.items():
            self._best_state[v] = state
            self.dist_to[v] = info[state][0]
            self._transfers_to[v] = info[state][1]

    # ------------------------------------------------------------ queries
    def has_path_to(self, target: int) -> bool:
        return target in self._best_state

    def distance_to(self, target: int) -> float:
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return (stations, edges) of the best path to ``target``.

        Returns ([], []) if ``target`` is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        stations: List[int] = [target]
        edges: List[Edge] = []
        while True:
            parent = self._parent.get(state)
            if parent is None:
                break
            prev_state, edge = parent
            edges.append(edge)
            stations.append(prev_state[0])
            state = prev_state
        stations.reverse()
        edges.reverse()
        return stations, edges

    def path_to(self, target: int) -> List[int]:
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target: int) -> int:
        """Number of transfers on the best path to ``target`` (-1 if unreachable)."""
        if target not in self._best_state:
            return -1
        return self._transfers_to[target]

    def get_transfers(self, target: int) -> List[Tuple[int, str, str]]:
        """List of (station number, from_line, to_line) transfers along the path."""
        stations, edges = self.path_with_edges(target)
        result = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                result.append((stations[i], edges[i - 1].line, edges[i].line))
        return result

    def get_lines(self, target: int) -> List[str]:
        """Ordered distinct list of lines used on the path."""
        _, edges = self.path_with_edges(target)
        lines: List[str] = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
