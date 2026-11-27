"""Binary min-heap priority queue used by Dijkstra's algorithm.

Insertion and removal of the minimum both run in O(log n), which gives the
O((V + E) log V) overall complexity of the shortest path search.
"""


class MinPQ:
    """A min priority queue implemented as an array-based binary heap.

    Each element is a (key, item) pair. Keys must support the ``<``
    operator; items are never compared, so they may be arbitrary objects.
    """

    def __init__(self):
        self._keys = []
        self._items = []

    def __len__(self):
        return len(self._keys)

    def size(self):
        """Return the number of elements currently stored."""
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

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._items:
            raise IndexError("priority queue is empty")
        return self._items[0]

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue underflow")
        last = len(self._keys) - 1
        self._swap(0, last)
        key = self._keys.pop()
        item = self._items.pop()
        if self._keys:
            self._sink(0)
        return key, item

    # ----- heap helpers -------------------------------------------------

    def _less(self, i, j):
        return self._keys[i] < self._keys[j]

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k):
        """Move the element at index k up until the heap property holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        """Move the element at index k down until the heap property holds."""
        n = len(self._keys)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            smallest = left
            right = left + 1
            if right < n and self._less(right, left):
                smallest = right
            if self._less(smallest, k):
                self._swap(k, smallest)
                k = smallest
            else:
                break
