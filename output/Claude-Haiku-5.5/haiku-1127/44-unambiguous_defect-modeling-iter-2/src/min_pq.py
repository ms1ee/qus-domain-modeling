"""Indexed binary min-heap used as the priority queue of Dijkstra's algorithm.

All operations are O(log n) (insert, decrease_key, del_min) or O(1) (min_item),
which gives the overall O((V + E) log V) complexity of the shortest path search.
"""


class MinPQ:
    """Indexed min priority queue.

    Items must be hashable; keys must be mutually comparable. Each item may be
    present at most once, and its key can be lowered with ``decrease_key``.
    """

    def __init__(self, capacity=0):
        if capacity < 0:
            raise ValueError("Capacity must be non-negative")
        self._capacity = capacity
        self._heap = []   # heap-ordered list of items
        self._pos = {}    # item -> index inside the heap
        self._keys = {}   # item -> priority key

    @property
    def capacity(self):
        """Largest number of items held so far (initial hint at construction)."""
        return self._capacity

    @property
    def size(self):
        """Number of items currently in the queue."""
        return len(self._heap)

    def __len__(self):
        return len(self._heap)

    def is_empty(self):
        """Return True if the queue holds no items."""
        return not self._heap

    def contains(self, item):
        """Return True if ``item`` is currently in the queue."""
        return item in self._pos

    def insert(self, item, key):
        """Insert ``item`` with priority ``key``."""
        if item in self._pos:
            raise ValueError(f"Item {item!r} is already in the queue")
        self._keys[item] = key
        self._heap.append(item)
        self._pos[item] = len(self._heap) - 1
        self._swim(len(self._heap) - 1)
        if len(self._heap) > self._capacity:
            self._capacity = len(self._heap)

    def decrease_key(self, item, key):
        """Lower the priority of an existing item to ``key``."""
        if item not in self._pos:
            raise KeyError(f"Item {item!r} is not in the queue")
        if key > self._keys[item]:
            raise ValueError("New key must not be greater than the current key")
        self._keys[item] = key
        self._swim(self._pos[item])

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._heap[0]

    def min_key(self):
        """Return the smallest key in the queue."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._keys[self._heap[0]]

    def del_min(self):
        """Remove and return the item with the smallest key."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        del self._pos[top]
        del self._keys[top]
        if self._heap:
            self._heap[0] = last
            self._pos[last] = 0
            self._sink(0)
        return top

    # ------------------------------------------------------------------
    # Internal heap helpers
    # ------------------------------------------------------------------
    def _less(self, i, j):
        return self._keys[self._heap[i]] < self._keys[self._heap[j]]

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._pos[self._heap[i]] = i
        self._pos[self._heap[j]] = j

    def _swim(self, k):
        """Move the element at index ``k`` up until heap order is restored."""
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._swap(k, parent)
            k = parent

    def _sink(self, k):
        """Move the element at index ``k`` down until heap order is restored."""
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
