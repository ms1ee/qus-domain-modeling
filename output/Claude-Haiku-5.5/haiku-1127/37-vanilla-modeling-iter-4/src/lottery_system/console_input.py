"""Background line reader so that commands can be handled during a draw."""

from __future__ import annotations

import queue
import sys
import threading

_EOF = object()


class ConsoleReader:
    """Reads lines from a stream in a daemon thread and serves them via a queue."""

    def __init__(self, stream=None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._ended = False
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\n"))
        except (OSError, ValueError):
            pass
        self._queue.put(_EOF)

    def read(self, timeout: float | None = None) -> str | None:
        """Return the next input line.

        Blocks when timeout is None; returns None when the timeout expires.
        Raises EOFError when the input stream has ended.
        """
        if self._ended:
            raise EOFError("Input stream closed")
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        if item is _EOF:
            self._ended = True
            raise EOFError("Input stream closed")
        return item.strip()

    def prompt(self, message: str) -> str:
        """Print a prompt and return the next stripped input line."""
        print(message, end="", flush=True)
        line = self.read()
        return line if line is not None else ""
