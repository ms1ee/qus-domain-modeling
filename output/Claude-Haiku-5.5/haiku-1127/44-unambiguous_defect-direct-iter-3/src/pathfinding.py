"""Shortest path computation on the subway graph using Dijkstra's algorithm.

Supported query modes:
  * ``shortest_distance`` - minimise the total distance in metres.
  * ``least_transfer``    - minimise the number of line changes, then distance.
  * ``comprehensive``     - minimise distance plus a penalty per transfer.

``max_transfers`` limits the number of line changes allowed on a route, and
``preferred_lines`` makes segments on other lines slightly more expensive so
that routes along preferred lines are favoured.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from errors import PathNotFoundError
from min_pq import MinPQ
from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES: Tuple[str, ...] = (
    MODE_SHORTEST_DISTANCE,
    MODE_LEAST_TRANSFER,
    MODE_COMPREHENSIVE,
)

# Equivalent distance (metres) added for every transfer in comprehensive mode.
TRANSFER_PENALTY_M: float = 500.0
# Equivalent distance (metres) added per metre-segment on non-preferred lines.
NON_PREFERRED_LINE_PENALTY_M: float = 300.0


def normalize_line_name(name: str) -> str:
    """Normalise a line name for case- and whitespace-insensitive comparison."""
    return " ".join(str(name).split()).casefold()


class PathfindingConfig:
    """Settings that control how a route is calculated."""

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])

    def validate(self) -> None:
        """Raise ``ValueError`` if the configuration is invalid."""
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"unknown mode '{self.mode}', expected one of {', '.join(VALID_MODES)}"
            )
        if self.max_transfers is not None:
            if isinstance(self.max_transfers, bool) or not isinstance(
                self.max_transfers, int
            ):
                raise ValueError("max_transfers must be an integer")
            if self.max_transfers < 0:
                raise ValueError("max_transfers must be >= 0")

    def is_preferred_line(self, line: str) -> bool:
        """True if ``line`` is preferred (always True when no preference is set)."""
        if not self.preferred_lines:
            return True
        target = normalize_line_name(line)
        return any(normalize_line_name(p) == target for p in self.preferred_lines)


class ShortestPath:
    """Single-source shortest paths computed with Dijkstra's algorithm.

    The priority queue (``MinPQ``, a binary heap) gives O((V + E) log V) time.
    Path costs are compared as tuples, so the chosen criterion depends on the
    configured mode. ``dist_to`` always contains the real distance in metres
    of the chosen route, independent of penalties.
    """

    def __init__(
        self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None
    ) -> None:
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.config.validate()
        if not graph.has_vertex(source):
            raise ValueError(f"unknown source station number: {source}")

        self.dist_to: Dict[int, int] = {}          # real distance in metres
        self.edge_to: Dict[int, Edge] = {}         # predecessor edge
        self.transfers: Dict[int, int] = {}        # transfers along chosen route
        self._key_to: Dict[int, tuple] = {}        # comparison key per vertex
        self._effective: Dict[int, float] = {}     # distance incl. penalties

        self._compute()

    # ----------------------------------------------------------------- helpers
    def _make_key(self, effective: float, transfers: int) -> tuple:
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, effective)
        if mode == MODE_COMPREHENSIVE:
            return (effective + TRANSFER_PENALTY_M * transfers, transfers)
        return (effective, transfers)

    def _line_penalty(self, line: str) -> float:
        if not self.config.preferred_lines or self.config.is_preferred_line(line):
            return 0.0
        return NON_PREFERRED_LINE_PENALTY_M

    # --------------------------------------------------------------- algorithm
    def _compute(self) -> None:
        source = self.source
        self.dist_to[source] = 0
        self.transfers[source] = 0
        self._effective[source] = 0.0
        self._key_to[source] = self._make_key(0.0, 0)

        pq = MinPQ()
        pq.insert(self._key_to[source], source)
        settled = set()
        max_transfers = self.config.max_transfers

        while not pq.is_empty():
            _, u = pq.del_min()
            if u in settled:
                continue
            settled.add(u)

            incoming_line = self.edge_to[u].line if u != source else None

            for edge in self.graph.adjacent(u):
                v = edge.other(u)
                if v in settled:
                    continue

                # A transfer happens when the line changes at an interior station.
                is_transfer = 1 if (
                    incoming_line is not None and incoming_line != edge.line
                ) else 0
                transfers = self.transfers[u] + is_transfer
                if max_transfers is not None and transfers > max_transfers:
                    continue

                effective = (
                    self._effective[u]
                    + edge.distance
                    + self._line_penalty(edge.line)
                )
                key = self._make_key(effective, transfers)
                if v not in self._key_to or key < self._key_to[v]:
                    self._key_to[v] = key
                    self._effective[v] = effective
                    self.transfers[v] = transfers
                    self.dist_to[v] = self.dist_to[u] + edge.distance
                    self.edge_to[v] = edge
                    pq.insert(key, v)

    # ------------------------------------------------------------------ queries
    def has_path_to(self, target: int) -> bool:
        return target in self.dist_to

    def distance_to(self, target: int) -> int:
        if not self.has_path_to(target):
            raise PathNotFoundError(f"no path to station number {target}")
        return self.dist_to[target]

    def get_transfer_count(self, target: int) -> int:
        """Number of line changes on the route from the source to ``target``."""
        if not self.has_path_to(target):
            raise PathNotFoundError(f"no path to station number {target}")
        return self.transfers[target]

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return ``(station numbers, edges)`` from the source to ``target``.

        The station list has one more element than the edge list.
        """
        if not self.has_path_to(target):
            raise PathNotFoundError(f"no path to station number {target}")

        vertices = [target]
        edges: List[Edge] = []
        v = target
        while v != self.source:
            edge = self.edge_to[v]
            edges.append(edge)
            v = edge.other(v)
            vertices.append(v)
        vertices.reverse()
        edges.reverse()
        return vertices, edges
