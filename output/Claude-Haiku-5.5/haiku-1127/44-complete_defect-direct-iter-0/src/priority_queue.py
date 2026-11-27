"""Indexed binary min-priority queue used by Dijkstra's algorithm.

Every item stored in the queue is unique and can be looked up in O(1) time,
which allows ``decrease_key`` to run in O(log V). Together with the O(log V)
insert and delete-min operations this yields the O((V+E) log V) complexity
required for Dijkstra's algorithm.
"""

from typing import Any, Dict, Hashable, List


class MinPQ:
    """Min-priority queue backed by a binary heap with an item index."""

    def __init__(self) -> None:
        self._items: List[Hashable] = []          # heap-ordered items
        self._keys: List[Any] = []                # keys parallel to _items
        self._index: Dict[Hashable, int] = {}     # item -> position in heap

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: Hashable) -> bool:
        return item in self._index

    def is_empty(self) -> bool:
        """Return True if the queue holds no items."""
        return not self._items

    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._items)

    def contains(self, item: Hashable) -> bool:
        """Return True if the item is currently in the queue."""
        return item in self._index

    def key_of(self, item: Hashable) -> Any:
        """Return the key associated with an item in the queue."""
        return self._keys[self._index[item]]

    def insert(self, item: Hashable, key: Any) -> None:
        """Insert a new item with the given key.

        Raises:
            ValueError: If the item is already in the queue.
        """
        if item in self._index:
            raise ValueError(f"Item {item!r} is already in the priority queue")
        self._items.append(item)
        self._keys.append(key)
        position = len(self._items) - 1
        self._index[item] = position
        self._sift_up(position)

    def decrease_key(self, item: Hashable, key: Any) -> None:
        """Lower the key of an item already in the queue.

        Raises:
            KeyError: If the item is not in the queue.
            ValueError: If the new key is not strictly smaller than the current key.
        """
        position = self._index[item]
        if not key < self._keys[position]:
            raise ValueError("New key must be strictly smaller than the current key")
        self._keys[position] = key
        self._sift_up(position)

    def push_or_decrease(self, item: Hashable, key: Any) -> bool:
        """Insert the item, or lower its key if the new key is smaller.

        Returns:
            True if the queue was modified, False otherwise.
        """
        if item not in self._index:
            self.insert(item, key)
            return True
        if key < self._keys[self._index[item]]:
            self.decrease_key(item, key)
            return True
        return False

    def min_item(self) -> Hashable:
        """Return the item with the smallest key without removing it."""
        if not self._items:
            raise IndexError("min_item() called on an empty priority queue")
        return self._items[0]

    def min_key(self) -> Any:
        """Return the smallest key without removing its item."""
        if not self._keys:
            raise IndexError("min_key() called on an empty priority queue")
        return self._keys[0]

    def del_min(self) -> Hashable:
        """Remove and return the item with the smallest key.

        Raises:
            IndexError: If the queue is empty.
        """
        if not self._items:
            raise IndexError("del_min() called on an empty priority queue")
        top = self._items[0]
        last_item = self._items.pop()
        last_key = self._keys.pop()
        del self._index[top]
        if self._items:
            self._items[0] = last_item
            self._keys[0] = last_key
            self._index[last_item] = 0
            self._sift_down(0)
        return top

    def _swap(self, i: int, j: int) -> None:
        """Swap two heap positions and keep the index up to date."""
        self._items[i], self._items[j] = self._items[j], self._items[i]
        self._keys[i], self._keys[j] = self._keys[j], self._keys[i]
        self._index[self._items[i]] = i
        self._index[self._items[j]] = j

    def _sift_up(self, k: int) -> None:
        """Move the element at position k up until the heap property holds."""
        while k > 0:
            parent = (k - 1) // 2
            if self._keys[k] < self._keys[parent]:
                self._swap(k, parent)
                k = parent
            else:
                break

    def _sift_down(self, k: int) -> None:
        """Move the element at position k down until the heap property holds."""
        n = len(self._items)
        while True:
            left = 2 * k + 1
            if left >= n:
                break
            smallest = left
            right = left + 1
            if right < n and self._keys[right] < self._keys[left]:
                smallest = right
            if self._keys[smallest] < self._keys[k]:
                self._swap(k, smallest)
                k = smallest
            else:
                break
