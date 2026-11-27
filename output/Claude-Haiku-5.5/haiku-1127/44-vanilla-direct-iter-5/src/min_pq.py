"""Binary min-heap priority queue used by Dijkstra's algorithm.

Using a heap gives O(log V) insert and delete-min, which yields the
overall O((V + E) log V) complexity of the shortest-path search.
"""
from __future__ import annotations

from typing import Any


class MinPQ:
    """Binary min-heap of (key, value) pairs ordered by key.

    Keys are compared with ``<``; values are never compared, so they may be
    arbitrary objects (e.g. tuples of station/line states).
    """

    def __init__(self) -> None:
        self._keys: list[Any] = []
        self._values: list[Any] = []

    def __len__(self) -> int:
        return len(self._keys)

    def size(self) -> int:
        """Number of elements currently stored."""
        return len(self._keys)

    def is_empty(self) -> bool:
        """True when the queue holds no elements."""
        return not self._keys

    def min_key(self) -> Any:
        """Return the smallest key without removing it."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        return self._keys[0]

    def insert(self, key: Any, value: Any) -> None:
        """Insert a value with the given priority key (O(log n))."""
        self._keys.append(key)
        self._values.append(value)
        self._sift_up(len(self._keys) - 1)

    def del_min(self) -> tuple[Any, Any]:
        """Remove and return the (key, value) pair with the smallest key."""
        if not self._keys:
            raise IndexError("priority queue is empty")
        min_key, min_value = self._keys[0], self._values[0]
        last_key = self._keys.pop()
        last_value = self._values.pop()
        if self._keys:
            self._keys[0] = last_key
            self._values[0] = last_value
            self._sift_down(0)
        return min_key, min_value

    # ----- internal helpers -----------------------------------------------
    def _swap(self, i: int, j: int) -> None:
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._values[i], self._values[j] = self._values[j], self._values[i]

    def _sift_up(self, k: int) -> None:
        while k > 0:
            parent = (k - 1) // 2
            if self._keys[k] < self._keys[parent]:
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sift_down(self, k: int) -> None:
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
