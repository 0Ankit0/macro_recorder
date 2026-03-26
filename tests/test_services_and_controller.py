from queue import Queue

from macro_recorder.app.controller import AppController
from macro_recorder.app.playback_service import PlaybackService
from macro_recorder.storage.service import StorageService


class FakeRecordingBackend:
    def __init__(self, q):
        self.q = q
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False


class FakePlaybackBackend:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True

    def play(self, actions, speed, event_queue):
        for i, _ in enumerate(actions, start=1):
            event_queue.put(type("E", (), {"type": "play_progress", "payload": {"index": i, "total": len(actions)}})())
        event_queue.put(type("E", (), {"type": "play_done", "payload": {}})())


def test_controller_record_transitions():
    q = Queue()
    c = AppController(FakeRecordingBackend(q), FakePlaybackBackend(), StorageService(), q)
    c.start_recording_now()
    c.queue.put(type("E", (), {"type": "record_action", "payload": {"action": {"t_ms": 0, "kind": "key_down", "key": "a"}}})())
    c.pump_events()
    c.stop_recording()
    assert len(c.document.actions) == 1


def test_playback_service_stop_rules():
    q = Queue()
    service = PlaybackService(FakePlaybackBackend(), q)
    service.stop_loop()
    assert service.backend.stopped is True


def test_emergency_stop_cancels_countdown_and_playback():
    q = Queue()
    c = AppController(FakeRecordingBackend(q), FakePlaybackBackend(), StorageService(), q)
    c.start_play_countdown()
    c.emergency_stop()
    events = c.pump_events()
    assert any(e.type == "emergency_stopped" for e in events)


def test_shortcut_triggered_dispatches_command():
    q = Queue()
    c = AppController(FakeRecordingBackend(q), FakePlaybackBackend(), StorageService(), q)
    c.queue.put(type("E", (), {"type": "shortcut_triggered", "payload": {"command_id": "toggle_recording"}})())
    c.pump_events()
    assert c._record_countdown_active is True


def test_play_shortcut_requires_actions():
    q = Queue()
    c = AppController(FakeRecordingBackend(q), FakePlaybackBackend(), StorageService(), q)
    assert c.execute_command("play_once") is False
    c.document.actions = [{"t_ms": 0, "kind": "key_down", "key": "a"}]
    assert c.execute_command("play_once") is True
