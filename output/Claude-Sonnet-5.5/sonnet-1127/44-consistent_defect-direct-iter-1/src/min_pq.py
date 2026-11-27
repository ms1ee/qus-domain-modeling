"""Heap based priority queue."""
import heapq
import itertools


class MinPQ:
    def __init__(self):
        self._h = []
        self._c = itertools.count()

    def push(self, key, item):
        heapq.heappush(self._h, (key, next(self._c), item))

    def pop(self):
        key, _, item = heapq.heappop(self._h)
        return key, item

    def is_empty(self):
        return not self._h

    def __len__(self):
        return len(self._h)
