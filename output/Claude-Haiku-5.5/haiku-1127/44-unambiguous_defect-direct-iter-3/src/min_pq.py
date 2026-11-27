"""Binary-heap based minimum priority queue."""

from __future__ import annotations

import heapq
import itertools
from typing import Any, Tuple


class MinPQ:
    """Min priority queue backed by ``heapq``.

    Items with equal keys are returned in insertion order thanks to a
    monotonically increasing sequence number, so items themselves are never
    compared. Insert/delete-min run in O(log n).
    """

    def __init__(self) -> None:
        self._heap: list = []
        self._seq = itertools.count()

    def insert(self, key: Any, item: Any) -> None:
        heapq.heappush(self._heap, (key, next(self._seq), item))

    def del_min(self) -> Tuple[Any, Any]:
        """Remove and return ``(key, item)`` with the smallest key."""
        if not self._heap:
            raise IndexError("del_min from an empty priority queue")
        key, _, item = heapq.heappop(self._heap)
        return key, item

    def min_key(self) -> Any:
        if not self._heap:
            raise IndexError("min_key from an empty priority queue")
        return self._heap[0][0]

    def is_empty(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)
