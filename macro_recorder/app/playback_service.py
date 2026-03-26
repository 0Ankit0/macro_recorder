from __future__ import annotations

import threading
import time
from queue import Queue

from macro_recorder.app.events import AppEvent, ev
from macro_recorder.domain.models import MacroAction


class PlaybackService:
    def __init__(self, backend, event_queue: Queue[AppEvent]):
        self.backend = backend
        self.event_queue = event_queue
        self._loop_stop = threading.Event()
        self._loop_thread: threading.Thread | None = None
        self.is_playing = False

    def play(self, actions: list[MacroAction], speed: float) -> None:
        self.is_playing = True
        self.backend.play(actions, speed, self.event_queue)

    def start_loop(self, actions: list[MacroAction], interval_minutes: float, max_runs: int, speed: float) -> None:
        self.stop_loop()
        self._loop_stop.clear()

        def run() -> None:
            runs = 0
            while not self._loop_stop.is_set():
                runs += 1
                self.event_queue.put(ev("loop_run_started", run=runs))
                self.play(actions, speed)

                while self.is_playing and not self._loop_stop.is_set():
                    time.sleep(0.05)

                if max_runs > 0 and runs >= max_runs:
                    self.event_queue.put(ev("loop_finished", runs=runs))
                    return

                self.event_queue.put(ev("loop_waiting", run=runs, minutes=interval_minutes))
                deadline = time.time() + interval_minutes * 60
                while time.time() < deadline:
                    if self._loop_stop.is_set():
                        self.event_queue.put(ev("loop_stopped", runs=runs))
                        return
                    time.sleep(0.1)

        self._loop_thread = threading.Thread(target=run, daemon=True)
        self._loop_thread.start()

    def stop_loop(self) -> None:
        self._loop_stop.set()
        self.is_playing = False
        self.backend.stop()

    def handle_playback_event(self, event_type: str) -> None:
        if event_type in {"play_done", "play_stopped"}:
            self.is_playing = False
