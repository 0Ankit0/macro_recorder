import importlib
import sys
import types
from queue import Queue


class _DummyListener:
    IS_TRUSTED = True

    def __init__(self, *_, **__):
        self.on_press = __.get("on_press")
        self.on_release = __.get("on_release")

    def start(self):
        return None

    def stop(self):
        return None


class _DummyController:
    def press(self, *_):
        return None

    def release(self, *_):
        return None


class _DummyMouseListener(_DummyListener):
    pass


def _load_backend_module():
    keyboard_mod = types.SimpleNamespace(Listener=_DummyListener, Key=object, KeyCode=object, Controller=_DummyController)
    mouse_mod = types.SimpleNamespace(Listener=_DummyMouseListener, Button=object, Controller=_DummyController)
    pynput_mod = types.SimpleNamespace(keyboard=keyboard_mod, mouse=mouse_mod)
    sys.modules["pynput"] = pynput_mod
    sys.modules.pop("macro_recorder.input_backends.pynput_backend", None)
    return importlib.import_module("macro_recorder.input_backends.pynput_backend")


def test_permission_check_uses_non_listener_probe():
    backend = _load_backend_module()

    class FakeListener:
        IS_TRUSTED = True

        def __init__(self, *args, **kwargs):
            raise AssertionError("Listener should not be instantiated")

    backend.keyboard.Listener = FakeListener
    assert backend.keyboard_monitoring_trusted() is True


def test_shortcut_chord_dispatch_and_is_not_recorded():
    backend = _load_backend_module()
    q = Queue()

    class FakeRecordingBackend:
        is_running = True

        def elapsed_ms(self):
            return 42

    monitor = backend.KeyboardShortcutMonitor(q, FakeRecordingBackend())
    monitor._on_press("<cmd>")
    monitor._on_press("<shift>")
    monitor._on_press("r")

    first = q.get_nowait()
    second = q.get_nowait()
    third = q.get_nowait()
    assert first.type == "record_action"
    assert second.type == "record_action"
    assert third.type == "shortcut_triggered"
    assert third.payload["command_id"] == "toggle_recording"
