"""Priority queue implemented on top of a binary heap."""

import heapq
import itertools


class MinPQ:
    """Min-priority queue based on a binary heap.

    Items are stored as ``(key, value)`` pairs. A monotonically increasing
    sequence number is used as a tie-breaker so that values never need to be
    comparable with each other. Insert and delete-min run in O(log n).
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, value):
        """Insert ``value`` with priority ``key``."""
        heapq.heappush(self._heap, (key, next(self._counter), value))

    def del_min(self):
        """Remove and return the ``(key, value)`` pair with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        key, _, value = heapq.heappop(self._heap)
        return key, value

    def min_key(self):
        """Return the smallest key without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True if the queue contains no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)
