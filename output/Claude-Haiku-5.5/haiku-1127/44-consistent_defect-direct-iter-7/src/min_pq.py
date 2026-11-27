"""Binary-heap based minimum priority queue used by Dijkstra's algorithm."""
from __future__ import annotations

import heapq
import itertools
from typing import Any, List, Tuple


class MinPQ:
    """A min-priority queue backed by a binary heap.

    Items with equal priority are dequeued in insertion order, which keeps the
    behaviour deterministic and avoids comparing the items themselves.
    Decrease-key is implemented lazily: callers insert a new entry with the
    lower priority and skip stale entries when they are dequeued.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[float, int, Any]] = []
        self._counter = itertools.count()

    def insert(self, priority: float, item: Any) -> None:
        """Add an item with the given priority (O(log n))."""
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def min(self) -> Tuple[float, Any]:
        """Return (priority, item) with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = self._heap[0]
        return priority, item

    def del_min(self) -> Tuple[float, Any]:
        """Remove and return (priority, item) with the smallest priority (O(log n))."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def is_empty(self) -> bool:
        """Return True when the queue contains no items."""
        return not self._heap

    def size(self) -> int:
        """Return the number of items currently stored."""
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)
