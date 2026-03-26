from __future__ import annotations

import threading
import time
from queue import Queue

from .events import ev, AppEvent


class CountdownRunner:
    def __init__(self, event_queue: Queue[AppEvent]):
        self._queue = event_queue
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, seconds: int, event_prefix: str) -> None:
        self.cancel()
        self._cancel.clear()

        def run() -> None:
            for remaining in range(seconds, 0, -1):
                if self._cancel.is_set():
                    self._queue.put(ev(f"{event_prefix}_cancelled"))
                    return
                self._queue.put(ev(f"{event_prefix}_tick", remaining=remaining))
                time.sleep(1)
            if not self._cancel.is_set():
                self._queue.put(ev(f"{event_prefix}_done"))

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()
