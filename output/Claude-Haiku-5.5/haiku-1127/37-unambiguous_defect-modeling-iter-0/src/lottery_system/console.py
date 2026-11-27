"""Non-blocking console input handling so commands can be typed during a lottery."""

import queue
import sys
import threading

_EOF_MARKER = "__EOF__"


class InputReader:
    """Reads stdin in a background thread and exposes blocking and polling access."""

    def __init__(self, stream=None):
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._eof = False
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        self._queue.put(_EOF_MARKER)

    def _handle(self, item):
        if item == _EOF_MARKER:
            self._eof = True
            return None
        return item

    @property
    def closed(self) -> bool:
        return self._eof

    def poll(self):
        """Return the next line if available, otherwise None (never blocks)."""
        if self._eof:
            return None
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        return self._handle(item)

    def read_line(self, prompt: str = ""):
        """Block until a line is available. Returns None when input is closed."""
        if prompt:
            print(prompt, end="", flush=True)
        if self._eof:
            return None
        return self._handle(self._queue.get())
