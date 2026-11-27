"""Binary min-heap priority queue used by the Dijkstra implementation.

The queue stores (key, item) pairs and always returns the pair with the
smallest key first. Keys may be any mutually comparable values, including
tuples, which allows lexicographic cost comparison.

Insertion and removal run in O(log n) time, which gives Dijkstra's algorithm
its O((V + E) log V) bound when combined with lazy deletion.
"""


class MinPQ:
    """A binary min-heap keyed priority queue (lazy deletion friendly)."""

    def __init__(self):
        # Parallel arrays: _keys[i] is the priority of _items[i].
        self._keys = []
        self._items = []

    def __len__(self):
        return len(self._keys)

    def size(self):
        """Return the number of entries currently in the queue."""
        return len(self._keys)

    def is_empty(self):
        """Return True when the queue holds no entries."""
        return not self._keys

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

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self._keys.append(key)
        self._items.append(item)
        self._swim(len(self._keys) - 1)

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue underflow")
        top_key = self._keys[0]
        top_item = self._items[0]
        last_key = self._keys.pop()
        last_item = self._items.pop()
        if self._keys:
            self._keys[0] = last_key
            self._items[0] = last_item
            self._sink(0)
        return top_key, top_item

    # ------------------------------------------------------------------
    # Heap maintenance helpers
    # ------------------------------------------------------------------
    def _less(self, i, j):
        return self._keys[i] < self._keys[j]

    def _swap(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k):
        """Move the element at index k up until heap order is restored."""
        while k > 0:
            parent = (k - 1) // 2
            if self._less(k, parent):
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sink(self, k):
        """Move the element at index k down until heap order is restored."""
        n = len(self._keys)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if self._less(child, k):
                self._swap(child, k)
                k = child
            else:
                break
