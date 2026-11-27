"""Non-blocking stdin channel used for lottery control commands."""

from __future__ import annotations

import queue
import sys
import threading


class _Sentinel:
    """Marker object with a readable representation."""

    def __init__(self, label: str) -> None:
        self._label = label

    def __repr__(self) -> str:
        return f"<{self._label}>"


NO_INPUT = _Sentinel("NO_INPUT")
END_OF_INPUT = _Sentinel("END_OF_INPUT")


class InputChannel:
    """Reads stdin in a background thread so commands can be polled during a lottery."""

    def __init__(self, stream=None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._read_loop, name="stdin-reader", daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.strip())
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(END_OF_INPUT)

    def get(self):
        """Blocking read. Returns a line or END_OF_INPUT."""
        item = self._queue.get()
        if item is END_OF_INPUT:
            self._queue.put(END_OF_INPUT)
        return item

    def poll(self):
        """Non-blocking read. Returns a line, END_OF_INPUT, or NO_INPUT."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return NO_INPUT
        if item is END_OF_INPUT:
            self._queue.put(END_OF_INPUT)
        return item
