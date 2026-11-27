"""Binary min-heap priority queue used by the Dijkstra implementation."""


class MinPQ:
    """A minimum priority queue implemented as a binary heap.

    Each entry is a (key, item) pair. The entry with the smallest key is
    returned first. Insertion and removal both run in O(log n) time.
    """

    def __init__(self):
        # 1-based heap storage; index 0 is an unused sentinel.
        self._keys = [None]
        self._items = [None]
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        """Return True if the queue holds no entries."""
        return self._size == 0

    def min_key(self):
        """Return the smallest key without removing it."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        return self._keys[1]

    def insert(self, key, item):
        """Insert an item with the given priority key."""
        self._size += 1
        self._keys.append(key)
        self._items.append(item)
        self._swim(self._size)

    def del_min(self):
        """Remove and return the (key, item) pair with the smallest key."""
        if self.is_empty():
            raise IndexError("priority queue is empty")
        key, item = self._keys[1], self._items[1]
        self._exchange(1, self._size)
        self._keys.pop()
        self._items.pop()
        self._size -= 1
        self._sink(1)
        return key, item

    # ----- heap helpers -------------------------------------------------

    def _less(self, i, j):
        return self._keys[i] < self._keys[j]

    def _exchange(self, i, j):
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k):
        """Move the element at index k up until heap order holds."""
        while k > 1 and self._less(k, k // 2):
            self._exchange(k, k // 2)
            k //= 2

    def _sink(self, k):
        """Move the element at index k down until heap order holds."""
        while 2 * k <= self._size:
            j = 2 * k
            if j < self._size and self._less(j + 1, j):
                j += 1
            if not self._less(j, k):
                break
            self._exchange(k, j)
            k = j
