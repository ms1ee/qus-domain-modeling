"""Binary-heap based minimum priority queue used by Dijkstra's algorithm."""

import heapq
import itertools


class MinPQ:
    """Minimum priority queue implemented on top of a binary heap.

    Items are inserted with a numeric key; ``del_min`` removes the item with
    the smallest key in O(log n). A monotonically increasing counter breaks
    ties so that arbitrary (unorderable) items can be stored safely.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert ``item`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return the ``(key, item)`` pair with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
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
        """Return True if the queue holds no items."""
        return not self._heap

    def __len__(self):
        return len(self._heap)
