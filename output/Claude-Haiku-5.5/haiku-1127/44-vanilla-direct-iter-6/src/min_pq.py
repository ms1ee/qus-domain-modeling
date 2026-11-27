"""Indexed binary min-heap priority queue used by Dijkstra's algorithm.

Each item is stored at most once. Keys can be decreased (or increased) in
O(log n) time via ``put``, which is what Dijkstra's relaxation step needs.
Keys may be any mutually comparable objects, such as numbers or tuples.
"""


class MinPQ:
    """A min priority queue backed by a binary heap with an item index."""

    def __init__(self):
        self._heap = []   # heap-ordered list of items
        self._pos = {}    # item -> index of the item in self._heap
        self._key = {}    # item -> current priority key

    def __len__(self):
        return len(self._heap)

    def __contains__(self, item):
        return item in self._pos

    def size(self):
        """Return the number of items in the queue."""
        return len(self._heap)

    def is_empty(self):
        """Return True if the queue contains no items."""
        return not self._heap

    def put(self, item, key):
        """Insert an item, or update its key if it is already queued.

        Args:
            item: Any hashable item.
            key: Priority key; smaller keys are served first.
        """
        if item in self._pos:
            index = self._pos[item]
            old_key = self._key[item]
            self._key[item] = key
            if key < old_key:
                self._swim(index)
            elif old_key < key:
                self._sink(index)
            return
        self._key[item] = key
        self._heap.append(item)
        self._pos[item] = len(self._heap) - 1
        self._swim(len(self._heap) - 1)

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._heap[0]

    def min_key(self):
        """Return the smallest key without removing its item."""
        if not self._heap:
            raise IndexError("priority queue is empty")
        return self._key[self._heap[0]]

    def del_min(self):
        """Remove and return the ``(item, key)`` pair with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._heap:
            raise IndexError("priority queue is empty")
        item = self._heap[0]
        key = self._key[item]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._pos[last] = 0
            self._sink(0)
        del self._pos[item]
        del self._key[item]
        return item, key

    # ----- heap helpers -------------------------------------------------

    def _less(self, i, j):
        """Compare the keys stored at heap positions i and j."""
        return self._key[self._heap[i]] < self._key[self._heap[j]]

    def _swap(self, i, j):
        """Swap two heap positions and keep the position index up to date."""
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._pos[self._heap[i]] = i
        self._pos[self._heap[j]] = j

    def _swim(self, k):
        """Move the element at position k up until the heap property holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        """Move the element at position k down until the heap property holds."""
        n = len(self._heap)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            child = left
            right = left + 1
            if right < n and self._less(right, left):
                child = right
            if self._less(child, k):
                self._swap(k, child)
                k = child
            else:
                break
