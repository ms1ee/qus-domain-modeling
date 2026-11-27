"""Binary min-heap priority queue used by Dijkstra's algorithm."""


class MinPQ:
    """Minimum priority queue implemented as a binary heap.

    Items are stored with a priority; the item with the smallest priority is
    removed first. Priorities may be any mutually comparable values, including
    tuples. Ties are broken by insertion order.
    """

    def __init__(self):
        self._heap = []  # entries: (priority, sequence_number, item)
        self._seq = 0

    def insert(self, item, priority):
        """Insert an item with the given priority."""
        self._heap.append((priority, self._seq, item))
        self._seq += 1
        self._swim(len(self._heap) - 1)

    def min(self):
        """Return (item, priority) with the smallest priority without removing it.

        Raises:
            IndexError: If the queue is empty.
        """
        if self.is_empty():
            raise IndexError("priority queue underflow")
        priority, _, item = self._heap[0]
        return item, priority

    def del_min(self):
        """Remove and return (item, priority) with the smallest priority.

        Raises:
            IndexError: If the queue is empty.
        """
        if self.is_empty():
            raise IndexError("priority queue underflow")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sink(0)
        return top[2], top[0]

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def _less(self, i, j):
        return self._heap[i][:2] < self._heap[j][:2]

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _swim(self, k):
        """Move the element at index k up until heap order is restored."""
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._swap(k, parent)
            k = parent

    def _sink(self, k):
        """Move the element at index k down until heap order is restored."""
        n = len(self._heap)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._swap(k, child)
            k = child
