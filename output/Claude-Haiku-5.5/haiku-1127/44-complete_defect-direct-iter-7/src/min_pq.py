"""Binary min-heap priority queue used by the Dijkstra implementation."""


class MinPQ:
    """A min priority queue implemented as an explicit binary heap.

    Each entry is stored as (priority, sequence_number, item). The sequence
    number makes ordering deterministic when priorities are equal (FIFO for ties).
    Insert and delete-min run in O(log n) time.
    """

    def __init__(self):
        self._heap = []
        self._seq = 0

    def insert(self, priority, item):
        """Insert an item with the given priority."""
        self._heap.append((priority, self._seq, item))
        self._seq += 1
        self._sift_up(len(self._heap) - 1)

    def del_min(self):
        """Remove and return the (priority, item) pair with the smallest priority."""
        if not self._heap:
            raise IndexError("delete-min from an empty priority queue")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top[0], top[2]

    def peek_min(self):
        """Return the (priority, item) pair with the smallest priority without removing it."""
        if not self._heap:
            raise IndexError("peek on an empty priority queue")
        return self._heap[0][0], self._heap[0][2]

    def is_empty(self):
        """Return True if the queue has no elements."""
        return not self._heap

    def size(self):
        """Return the number of elements in the queue."""
        return len(self._heap)

    def _less(self, i, j):
        a = self._heap[i]
        b = self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sift_down(self, k):
        n = len(self._heap)
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < n and self._less(left, smallest):
                smallest = left
            if right < n and self._less(right, smallest):
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest
