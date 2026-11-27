"""Binary-heap based minimum priority queue used by Dijkstra's algorithm."""

import heapq
import itertools


class MinPQ:
    """Minimum priority queue backed by a binary heap.

    Items with equal keys are returned in insertion order, which keeps the
    search deterministic and avoids comparing the items themselves.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return ``(key, item)`` with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self):
        """Return the smallest key without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        return self._heap[0][0]

    def is_empty(self) -> bool:
        """Return True if the queue has no items."""
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)
