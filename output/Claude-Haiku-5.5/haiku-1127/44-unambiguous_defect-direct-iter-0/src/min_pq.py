"""Binary min-heap priority queue used by Dijkstra's algorithm.

Each entry is stored as ``(priority, sequence, item)``. The sequence number
keeps insertion order for equal priorities and guarantees that items are
never compared directly. Insert and delete-min run in O(log n).
"""


class MinPQ:
    """A minimum priority queue implemented as a binary heap."""

    def __init__(self):
        self._heap = []
        self._seq = 0

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        """Return True when the queue holds no entries."""
        return not self._heap

    def min(self):
        """Return ``(priority, item)`` of the smallest entry without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        top = self._heap[0]
        return top[0], top[2]

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        self._heap.append((priority, self._seq, item))
        self._seq += 1
        self._swim(len(self._heap) - 1)

    def del_min(self):
        """Remove and return ``(priority, item)`` of the smallest entry."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        heap = self._heap
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top[0], top[2]

    # ----- heap helpers -------------------------------------------------
    def _less(self, i, j):
        a = self._heap[i]
        b = self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k):
        """Move the entry at index k up until the heap order holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        """Move the entry at index k down until the heap order holds."""
        n = len(self._heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and self._less(right, left):
                child = right
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child
