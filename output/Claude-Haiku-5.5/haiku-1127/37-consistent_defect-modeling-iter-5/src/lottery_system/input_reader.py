"""Background stdin reader so that commands can be detected during a draw."""
import queue
import sys
import threading
from typing import Optional


class InputReader:
    """Reads stdin lines in a daemon thread and hands them out via a queue.

    read_line() blocks until a line is available (used for menus).
    poll() waits up to a timeout and returns None if nothing was typed
    (used to detect 'pause', 'continue' and 'terminate' during a draw).
    Both raise EOFError when the input stream is closed.
    """

    def __init__(self, stream=None):
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._eof = False

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._pump, name="stdin-reader", daemon=True)
            self._thread.start()

    def _pump(self) -> None:
        while True:
            try:
                line = self._stream.readline()
            except (OSError, ValueError):
                line = ""
            if line == "":
                self._queue.put(None)
                return
            self._queue.put(line.rstrip("\r\n"))

    def read_line(self, prompt: str = "") -> str:
        if prompt:
            print(prompt, end="", flush=True)
        if self._eof:
            raise EOFError
        self.start()
        item = self._queue.get()
        if item is None:
            self._eof = True
            raise EOFError
        return item.strip()

    def poll(self, timeout: float) -> Optional[str]:
        if self._eof:
            raise EOFError
        self.start()
        try:
            item = self._queue.get(timeout=max(timeout, 0))
        except queue.Empty:
            return None
        if item is None:
            self._eof = True
            raise EOFError
        return item.strip().lower()
