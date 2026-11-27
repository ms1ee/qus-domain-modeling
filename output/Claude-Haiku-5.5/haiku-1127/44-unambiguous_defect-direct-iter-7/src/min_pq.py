"""Binary min-heap priority queue used by Dijkstra's algorithm."""


class MinPQ:
    """Min priority queue implemented as an array-based binary heap.

    Insertion and removal of the minimum both run in O(log n), which gives
    Dijkstra's algorithm its O((V + E) log V) running time.
    Keys are compared with the ``<`` operator, so tuples work as keys.
    """

    def __init__(self) -> None:
        self._keys: list = []
        self._items: list = []

    def insert(self, item, key) -> None:
        """Add ``item`` with priority ``key``."""
        self._keys.append(key)
        self._items.append(item)
        self._swim(len(self._keys) - 1)

    def del_min(self):
        """Remove and return the item with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._keys:
            raise IndexError("priority queue is empty")
        self._exch(0, len(self._keys) - 1)
        self._keys.pop()
        item = self._items.pop()
        if self._keys:
            self._sink(0)
        return item

    def min_key(self):
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def is_empty(self) -> bool:
        return not self._keys

    def __len__(self) -> int:
        return len(self._keys)

    # ----- heap helpers -------------------------------------------------
    def _less(self, i: int, j: int) -> bool:
        return self._keys[i] < self._keys[j]

    def _exch(self, i: int, j: int) -> None:
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _swim(self, k: int) -> None:
        """Move the element at index ``k`` up until heap order holds."""
        while k > 0:
            parent = (k - 1) // 2
            if not self._less(k, parent):
                break
            self._exch(k, parent)
            k = parent

    def _sink(self, k: int) -> None:
        """Move the element at index ``k`` down until heap order holds."""
        n = len(self._keys)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._less(child + 1, child):
                child += 1
            if not self._less(child, k):
                break
            self._exch(k, child)
            k = child
