"""Background stdin reader so the lottery can accept control commands while running."""
import queue
import sys
import threading


class InputReader:
    """Reads stdin lines in a daemon thread and serves them through a queue.

    All interactive input goes through this reader so that control commands
    (pause / continue / terminate) can be polled during the lottery without
    blocking the drawing process.
    """

    def __init__(self, stream=None):
        self._stream = stream
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self.eof = False

    def _start(self) -> None:
        if self._thread is None:
            stream = self._stream if self._stream is not None else sys.stdin
            self._thread = threading.Thread(
                target=self._pump, args=(stream,), daemon=True, name="stdin-reader"
            )
            self._thread.start()

    def _pump(self, stream) -> None:
        try:
            for line in stream:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(None)  # EOF sentinel

    def prompt(self, text: str) -> str | None:
        """Print a prompt and wait for one line. Returns None when input is closed."""
        if self.eof:
            print(text)
            return None
        print(text, end="", flush=True)
        self._start()
        item = self._queue.get()
        if item is None:
            self.eof = True
            print()
            return None
        return item.strip()

    def poll(self, timeout: float | None = 0.0) -> tuple[bool, str | None]:
        """Get a line without blocking forever.

        timeout None  -> block until a line (or EOF) arrives
        timeout > 0   -> wait up to timeout seconds
        timeout <= 0  -> return immediately

        Returns (True, line) when a line was received, otherwise (False, None).
        """
        if self.eof:
            return False, None
        self._start()
        try:
            if timeout is None:
                item = self._queue.get()
            elif timeout > 0:
                item = self._queue.get(timeout=timeout)
            else:
                item = self._queue.get_nowait()
        except queue.Empty:
            return False, None
        if item is None:
            self.eof = True
            return False, None
        return True, item
