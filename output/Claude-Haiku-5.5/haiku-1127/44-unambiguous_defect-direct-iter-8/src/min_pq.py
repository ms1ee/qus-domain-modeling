"""Binary-heap based minimum priority queue used by Dijkstra's algorithm."""

import heapq
import itertools


class MinPQ:
    """Minimum priority queue backed by a binary heap.

    Entries are stored as (key, sequence, item). The sequence number makes
    ordering stable and guarantees that items themselves are never compared.
    Insertions and removals run in O(log n) time.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        heapq.heappush(self._heap, (key, next(self._counter), item))

    def del_min(self):
        """Remove and return the item with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue underflow")
        return heapq.heappop(self._heap)[2]

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][2]

    def min_key(self):
        """Return the smallest key without removing its item."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0][0]

    def is_empty(self):
        """Return True when the queue holds no entries."""
        return not self._heap

    def size(self):
        """Return the number of entries in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)
