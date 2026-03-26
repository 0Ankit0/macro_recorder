from __future__ import annotations

import platform
from queue import Empty, Queue

from macro_recorder.app.commands import CommandContext, command_definitions_by_id
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
        *,
        permissions_ok: bool = True,
    ) -> None:
        self.queue: Queue[AppEvent] = event_queue or Queue()
        self.storage = storage
        self.recording = RecordingService(recording_backend, self.queue)
        self.playback = PlaybackService(playback_backend, self.queue)
        self.countdown = CountdownRunner(self.queue)
        self.document = MacroDocument(platform=platform.platform())
        self.active_file: str | None = None
        self.permissions_ok = permissions_ok
        self.backend_ok = permissions_ok
        self._commands = command_definitions_by_id()
        self._record_countdown_active = False
        self._play_countdown_active = False
        self.queue.put(ev("permissions_state", trusted=permissions_ok))

    def load(self, path: str) -> None:
        self.document = self.storage.load(path)
        self.active_file = path
        self.queue.put(ev("document_loaded", path=path, count=len(self.document.actions)))

    def save(self, path: str) -> None:
        self.storage.save(path, self.document)
        self.active_file = path
        self.queue.put(ev("document_saved", path=path))

    def start_record_countdown(self) -> None:
        self._record_countdown_active = True
        self.countdown.start(3, "record")

    def start_play_countdown(self) -> None:
        self._play_countdown_active = True
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
        self._record_countdown_active = False
        self._play_countdown_active = False
        self.countdown.cancel()
        self.recording.backend.stop()
        self.playback.stop_loop()
        self.queue.put(ev("emergency_stopped"))

    def execute_command(self, command_id: str, *, speed: float = 1.0) -> bool:
        definition = self._commands.get(command_id)
        if definition is None:
            return False
        if not definition.availability(self.command_context()):
            return False

        if command_id == "toggle_recording":
            if self.recording.is_recording:
                self.stop_recording()
            else:
                self.start_record_countdown()
            return True
        if command_id == "play_once":
            self.start_play_countdown()
            return True
        if command_id == "emergency_stop":
            self.emergency_stop()
            return True
        return False

    def command_context(self) -> CommandContext:
        return CommandContext(
            permissions_ok=self.permissions_ok,
            backend_ok=self.backend_ok,
            is_recording=self.recording.is_recording,
            is_playing=self.playback.is_playing or self._play_countdown_active,
            is_looping=self.playback._loop_thread is not None and self.playback._loop_thread.is_alive(),
            has_actions=bool(self.document.actions),
        )

    def set_backend_error(self, message: str) -> None:
        self.backend_ok = False
        self.queue.put(ev("backend_error", backend="keyboard_monitor", message=message))

    def pump_events(self) -> list[AppEvent]:
        events: list[AppEvent] = []
        while True:
            try:
                event = self.queue.get_nowait()
                if event.type == "record_action":
                    self.recording.on_action(event.payload["action"])
                elif event.type in {"play_done", "play_stopped"}:
                    self.playback.handle_playback_event(event.type)
                    self._play_countdown_active = False
                elif event.type == "record_done":
                    self._record_countdown_active = False
                elif event.type == "play_done":
                    self._play_countdown_active = False
                elif event.type == "record_cancelled":
                    self._record_countdown_active = False
                elif event.type == "play_cancelled":
                    self._play_countdown_active = False
                elif event.type == "shortcut_triggered":
                    self.execute_command(event.payload["command_id"])
                elif event.type == "backend_error":
                    self.backend_ok = False
                events.append(event)
            except Empty:
                break
        return events
