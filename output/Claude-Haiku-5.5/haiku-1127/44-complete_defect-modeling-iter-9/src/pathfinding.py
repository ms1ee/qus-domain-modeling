"""Shortest path computation.

Implements Dijkstra's algorithm on the subway graph with a binary-heap priority
queue (MinPQ). The search runs over (station, arrival line) states so that line
changes (transfers) can be counted exactly, which enables the maximum-transfer
limit, the least-transfer mode and the line preference setting.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance penalty added per transfer in comprehensive mode.
TRANSFER_PENALTY_METERS = 1000.0
# Equivalent distance penalty added per ride on a non-preferred line.
PREFERENCE_PENALTY_METERS = 300.0


class PathNotFoundError(Exception):
    """Raised when no path exists between two stations under the given constraints."""


class MinPQ:
    """Binary min-heap priority queue of (key, item) pairs.

    Insertion and removal of the minimum run in O(log n), which gives the
    O((V+E) log V) complexity of Dijkstra's algorithm with this queue.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[object, object]] = []

    def insert(self, key: object, item: object) -> None:
        self._heap.append((key, item))
        self._sift_up(len(self._heap) - 1)

    def del_min(self) -> Tuple[object, object]:
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    def min(self) -> Tuple[object, object]:
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0]

    def is_empty(self) -> bool:
        return not self._heap

    def size(self) -> int:
        return len(self._heap)

    def _less(self, i: int, j: int) -> bool:
        return self._heap[i][0] < self._heap[j][0]

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self._less(index, parent):
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index: int) -> None:
        size = len(self._heap)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and self._less(left, smallest):
                smallest = left
            if right < size and self._less(right, smallest):
                smallest = right
            if smallest == index:
                break
            self._swap(index, smallest)
            index = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum number of line changes allowed, or None for no limit.
        preferred_lines: lines that are preferred; rides on other lines are penalized.
    """

    def __init__(
        self,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Sequence[str]] = None,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])


class _Label:
    """A search state: station reached while riding ``line``."""

    __slots__ = ("station", "line", "distance", "penalty", "transfers", "parent", "edge")

    def __init__(
        self,
        station: int,
        line: Optional[str],
        distance: float,
        penalty: float,
        transfers: int,
        parent: int,
        edge: Optional[Edge],
    ) -> None:
        self.station = station
        self.line = line
        self.distance = distance
        self.penalty = penalty
        self.transfers = transfers
        self.parent = parent
        self.edge = edge


class ShortestPath:
    """Single-source optimal path search using Dijkstra's algorithm.

    Attributes:
        dist_to: station number -> actual travelled distance (meters) of the
            optimal path found from the source.
    """

    def __init__(self, graph: Graph, source: int, config: Optional[PathfindingConfig] = None) -> None:
        if not graph.has_vertex(source):
            raise ValueError(f"source station {source} is not in the graph")
        self._graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to: Dict[int, float] = {}
        self._transfers_to: Dict[int, int] = {}
        self._labels: List[_Label] = []
        self._best_label: Dict[int, int] = {}
        self._run()

    def _cost_key(self, distance: float, penalty: float, transfers: int) -> Tuple[float, float]:
        """Ordering key of a label according to the configured mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (float(transfers), distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            return (distance + TRANSFER_PENALTY_METERS * transfers + penalty, float(transfers))
        return (distance + penalty, float(transfers))

    def _run(self) -> None:
        max_transfers = self.config.max_transfers
        preferred: Set[str] = set(self.config.preferred_lines)

        root = _Label(self.source, None, 0.0, 0.0, 0, -1, None)
        self._labels.append(root)
        root_key = self._cost_key(0.0, 0.0, 0)

        pq = MinPQ()
        pq.insert(root_key, 0)
        best_key: Dict[Tuple[int, Optional[str]], Tuple[float, float]] = {(self.source, None): root_key}
        settled: Set[Tuple[int, Optional[str]]] = set()

        while not pq.is_empty():
            _, index = pq.del_min()
            label = self._labels[index]
            state = (label.station, label.line)
            if state in settled:
                continue
            settled.add(state)

            # The first settled label of a station is its optimal label.
            if label.station not in self._best_label:
                self._best_label[label.station] = index
                self.dist_to[label.station] = label.distance
                self._transfers_to[label.station] = label.transfers

            for edge in self._graph.adjacent(label.station):
                nxt = edge.other(label.station)
                changes_line = label.line is not None and label.line != edge.line
                transfers = label.transfers + (1 if changes_line else 0)
                if max_transfers is not None and transfers > max_transfers:
                    continue

                next_state = (nxt, edge.line)
                if next_state in settled:
                    continue

                distance = label.distance + edge.weight
                penalty = label.penalty
                if preferred and edge.line not in preferred:
                    penalty += PREFERENCE_PENALTY_METERS

                key = self._cost_key(distance, penalty, transfers)
                previous = best_key.get(next_state)
                if previous is not None and previous <= key:
                    continue
                best_key[next_state] = key

                self._labels.append(_Label(nxt, edge.line, distance, penalty, transfers, index, edge))
                pq.insert(key, len(self._labels) - 1)

    def has_path_to(self, target: int) -> bool:
        """Return True if ``target`` is reachable from the source under the constraints."""
        return target in self._best_label

    def path_with_edges(self, target: int) -> Tuple[List[int], List[Edge]]:
        """Return (station numbers, edges) of the optimal path from source to target.

        The station list starts with the source and ends with the target; the
        edge list has one element fewer and is ordered along the path.
        Raises PathNotFoundError if the target is unreachable.
        """
        index = self._best_label.get(target)
        if index is None:
            raise PathNotFoundError(f"no path to station {target} under the current constraints")
        stations: List[int] = []
        edges: List[Edge] = []
        while index != -1:
            label = self._labels[index]
            stations.append(label.station)
            if label.edge is not None:
                edges.append(label.edge)
            index = label.parent
        stations.reverse()
        edges.reverse()
        return stations, edges

    def get_transfer_count(self, target: int) -> int:
        """Return the number of line changes on the optimal path to ``target``."""
        if target not in self._transfers_to:
            raise PathNotFoundError(f"no path to station {target} under the current constraints")
        return self._transfers_to[target]
