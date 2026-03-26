from __future__ import annotations

from queue import Queue

from macro_recorder.app.events import AppEvent, ev
from macro_recorder.domain.models import MacroAction
from macro_recorder.domain.normalize import MouseMoveCompressor, normalize_timestamps


class RecordingService:
    def __init__(self, backend, event_queue: Queue[AppEvent]):
        self.backend = backend
        self.event_queue = event_queue
        self.actions: list[MacroAction] = []
        self._compressor = MouseMoveCompressor()
        self.is_recording = False

    def start(self) -> None:
        self.actions = []
        self.is_recording = True
        self.backend.start()
        self.event_queue.put(ev("record_started"))

    def stop(self) -> list[MacroAction]:
        self.is_recording = False
        self.backend.stop()
        normalized = normalize_timestamps(self.actions)
        compressed = self._compressor.compress(normalized)
        self.actions = compressed
        self.event_queue.put(ev("record_stopped", count=len(compressed)))
        return compressed

    def on_action(self, action: MacroAction) -> None:
        if self.is_recording:
            self.actions.append(action)
