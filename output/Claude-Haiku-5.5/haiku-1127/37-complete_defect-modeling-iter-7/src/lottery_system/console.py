"""Non-blocking console input shared by the CLI and the lottery runner.

A single background thread reads stdin and pushes lines into a queue so the
lottery can check for "pause" / "continue" / "terminate" commands without
blocking the drawing process.
"""

from __future__ import annotations

import queue
import sys
import threading
from typing import TextIO

_EOF = object()


class ConsoleInput:
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._eof = False
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(_EOF)

    def _take(self, item):
        if item is _EOF:
            self._eof = True
            raise EOFError("Input closed")
        return item

    def get(self) -> str:
        """Block until a line is available. Raises EOFError when input closes."""
        if self._eof:
            raise EOFError("Input closed")
        return self._take(self._queue.get())

    def poll(self) -> str:
        """Return the next pending line, or "" if nothing is pending."""
        if self._eof:
            raise EOFError("Input closed")
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return ""
        return self._take(item)

    def prompt(self, message: str) -> str:
        """Print a prompt and block for a line of input."""
        print(message, end="", flush=True)
        return self.get()
