"""
Path calculation for the subway network.

Provides:
  * MinPQ: a binary min-heap priority queue used by Dijkstra's algorithm.
  * PathfindingConfig: query mode, transfer limit and line preference.
  * ShortestPath: Dijkstra's algorithm over (station, line) states, which
    allows counting transfers and supports the three query modes:
      - shortest_distance: minimise total distance (meters).
      - least_transfer:    minimise transfers, distance breaks ties.
      - comprehensive:     distance plus a penalty per transfer.

Time complexity is O((V + E) log V) (times the constant number of line
states per station) thanks to the heap-based priority queue.
"""

import math
from typing import Dict, List, Optional, Tuple

from models import Edge, Graph

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance of one transfer in comprehensive mode:
# about 5 minutes at 1.5 minutes per kilometre (5 / 1.5 km ~ 3333 m).
TRANSFER_PENALTY_METERS = 3333.0
# Extra cost for riding an edge that is not on a preferred line.
PREFERENCE_PENALTY_METERS = 500.0
# Large weight that makes one transfer dominate any distance in least_transfer mode.
LEAST_TRANSFER_WEIGHT = 1.0e9

# A search state is (station number, line of the edge used to arrive).
State = Tuple[int, Optional[str]]


def _normalize_line(name):
    """Normalize a line name for case/space-insensitive comparison."""
    return str(name).strip().lower().replace(" ", "")


class Node:
    """A heap entry holding a priority and an item."""

    __slots__ = ("priority", "item")

    def __init__(self, priority, item):
        self.priority = priority
        self.item = item


class MinPQ:
    """Binary min-heap priority queue.

    insert and del_min run in O(log n); the minimum is at the root.
    """

    def __init__(self):
        self._heap: List[Node] = []

    @property
    def size(self):
        """Number of elements currently in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        """Return True if the queue holds no elements."""
        return not self._heap

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        self._heap.append(Node(priority, item))
        self._swim(len(self._heap) - 1)

    def min_node(self):
        """Return (without removing) the node with the smallest priority."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        return self._heap[0]

    def del_min(self):
        """Remove and return the node with the smallest priority."""
        if not self._heap:
            raise IndexError("MinPQ is empty")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top

    def _swim(self, k):
        heap = self._heap
        while k > 0:
            parent = (k - 1) // 2
            if heap[k].priority < heap[parent].priority:
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
            if left < n and heap[left].priority < heap[smallest].priority:
                smallest = left
            if right < n and heap[right].priority < heap[smallest].priority:
                smallest = right
            if smallest == k:
                break
            heap[k], heap[smallest] = heap[smallest], heap[k]
            k = smallest


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: One of VALID_MODES.
        max_transfers: Maximum allowed transfers, or None for unlimited.
        preferred_lines: List of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {VALID_MODES}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines)


class ShortestPath:
    """Dijkstra-based path finder from a single source station.

    Attributes:
        dist_to: dict station number -> travelled distance (meters) of the best path.
        edge_to: dict station number -> last Edge of the best path.
        transfers_to: dict station number -> number of transfers on the best path.
    """

    def __init__(self, graph, source, config=None):
        if source not in graph.number_to_station:
            raise ValueError(f"Unknown source station number {source}")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self._preferred = {_normalize_line(p) for p in self.config.preferred_lines}

        self.dist_to: Dict[int, float] = {}
        self.edge_to: Dict[int, Optional[Edge]] = {}
        self.transfers_to: Dict[int, int] = {}
        self.cost_to: Dict[int, float] = {}

        # state -> (cost, distance, transfers, parent_state, edge_used)
        self._states: Dict[State, tuple] = {}
        self._best_state: Dict[int, State] = {}
        self._run()

    def _increment(self, edge, switched):
        """Cost added by riding ``edge``, depending on mode and line changes."""
        inc = edge.weight
        if switched:
            if self.config.mode == MODE_LEAST_TRANSFER:
                inc += LEAST_TRANSFER_WEIGHT
            elif self.config.mode == MODE_COMPREHENSIVE:
                inc += TRANSFER_PENALTY_METERS
        if self._preferred and _normalize_line(edge.line) not in self._preferred:
            inc += PREFERENCE_PENALTY_METERS
        return inc

    def _run(self):
        """Run Dijkstra over (station, line) states."""
        max_transfers = self.config.max_transfers
        states = self._states
        start: State = (self.source, None)
        states[start] = (0.0, 0.0, 0, None, None)

        pq = MinPQ()
        pq.insert(0.0, start)
        settled = set()

        while not pq.is_empty():
            state = pq.del_min().item
            if state in settled:
                continue
            settled.add(state)
            cost, dist, transfers, _, _ = states[state]
            node, line = state

            for edge in self.graph.adjacent(node):
                nxt = edge.other(node)
                switched = line is not None and edge.line != line
                new_transfers = transfers + (1 if switched else 0)
                if max_transfers is not None and new_transfers > max_transfers:
                    continue
                new_state: State = (nxt, edge.line)
                if new_state in settled:
                    continue
                new_cost = cost + self._increment(edge, switched)
                new_dist = dist + edge.weight
                old = states.get(new_state)
                if old is None or new_cost < old[0]:
                    states[new_state] = (new_cost, new_dist, new_transfers, state, edge)
                    pq.insert(new_cost, new_state)

        # Pick the best state for every station.
        best: Dict[int, State] = {}
        for st, info in states.items():
            number = st[0]
            if number not in best or info[0] < states[best[number]][0]:
                best[number] = st
        self._best_state = best
        for number, st in best.items():
            cost, dist, transfers, _, edge = states[st]
            self.cost_to[number] = cost
            self.dist_to[number] = dist
            self.transfers_to[number] = transfers
            self.edge_to[number] = edge

    def has_path(self, target):
        """Return True if ``target`` is reachable under the current configuration."""
        return target in self._best_state

    def path_with_edges(self, target):
        """Return (station numbers, edges) of the best path from source to target.

        Returns ([], []) if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        states = self._states
        state = self._best_state[target]
        nodes = []
        edges = []
        while state is not None:
            _, _, _, parent, edge = states[state]
            nodes.append(state[0])
            if edge is not None:
                edges.append(edge)
            state = parent
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of transfers on the best path to target (0 if unreachable)."""
        return self.transfers_to.get(target, 0)
