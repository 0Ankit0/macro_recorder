from __future__ import annotations

import platform
from queue import Queue, Empty

from macro_recorder.app.countdown import CountdownRunner
from macro_recorder.app.events import AppEvent, ev
from macro_recorder.app.playback_service import PlaybackService
from macro_recorder.app.recording_service import RecordingService
from macro_recorder.domain.models import MacroDocument
from macro_recorder.storage.service import StorageService


class AppController:
    def __init__(
        self,
        recording_backend,
        playback_backend,
        storage: StorageService,
        event_queue: Queue[AppEvent] | None = None,
    ) -> None:
        self.queue: Queue[AppEvent] = event_queue or Queue()
        self.storage = storage
        self.recording = RecordingService(recording_backend, self.queue)
        self.playback = PlaybackService(playback_backend, self.queue)
        self.countdown = CountdownRunner(self.queue)
        self.document = MacroDocument(platform=platform.platform())
        self.active_file: str | None = None

    def load(self, path: str) -> None:
        self.document = self.storage.load(path)
        self.active_file = path
        self.queue.put(ev("document_loaded", path=path, count=len(self.document.actions)))

    def save(self, path: str) -> None:
        self.storage.save(path, self.document)
        self.active_file = path
        self.queue.put(ev("document_saved", path=path))

    def start_record_countdown(self) -> None:
        self.countdown.start(3, "record")

    def start_play_countdown(self) -> None:
        self.countdown.start(3, "play")

    def start_recording_now(self) -> None:
        self.recording.start()

    def stop_recording(self) -> None:
        self.document.actions = self.recording.stop()

    def play_once(self, speed: float) -> None:
        self.playback.play(self.document.actions, speed)

    def start_loop(self, interval_minutes: float, max_runs: int, speed: float) -> None:
        self.playback.start_loop(self.document.actions, interval_minutes, max_runs, speed)

    def emergency_stop(self) -> None:
        self.countdown.cancel()
        self.recording.backend.stop()
        self.playback.stop_loop()
        self.queue.put(ev("emergency_stopped"))

    def pump_events(self) -> list[AppEvent]:
        events: list[AppEvent] = []
        while True:
            try:
                event = self.queue.get_nowait()
                if event.type == "record_action":
                    self.recording.on_action(event.payload["action"])
                if event.type in {"play_done", "play_stopped"}:
                    self.playback.handle_playback_event(event.type)
                events.append(event)
            except Empty:
                break
        return events
