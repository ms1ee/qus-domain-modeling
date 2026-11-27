"""Minimum priority queue implemented as a binary min-heap."""


class MinPQ:
    """Binary min-heap of (key, item) pairs ordered by key.

    Insert and delete-min run in O(log n), which gives Dijkstra's algorithm
    its O((V+E) log V) running time.
    """

    def __init__(self):
        self._keys = []
        self._items = []

    def __len__(self):
        return len(self._keys)

    def is_empty(self):
        """Return True if the queue holds no elements."""
        return not self._keys

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self._keys.append(key)
        self._items.append(item)
        self._swim(len(self._keys) - 1)

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        min_key, min_item = self._keys[0], self._items[0]
        last = len(self._keys) - 1
        self._swap(0, last)
        self._keys.pop()
        self._items.pop()
        if self._keys:
            self._sink(0)
        return min_key, min_item

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k):
        """Move the element at index k up until heap order holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._keys[k] < self._keys[parent]:
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        """Move the element at index k down until heap order holds."""
        n = len(self._keys)
        while True:
            left = 2 * k + 1
            right = left + 1
            smallest = k
            if left < n and self._keys[left] < self._keys[smallest]:
                smallest = left
            if right < n and self._keys[right] < self._keys[smallest]:
                smallest = right
            if smallest == k:
                break
            self._swap(k, smallest)
            k = smallest
