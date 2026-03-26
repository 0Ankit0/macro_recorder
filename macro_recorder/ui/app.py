from __future__ import annotations

import queue as queue_module
import tkinter as tk

from pynput import keyboard

from macro_recorder.app.controller import AppController
from macro_recorder.input_backends.pynput_backend import (
    KeyboardShortcutMonitor,
    PynputPlaybackBackend,
    PynputRecordingBackend,
    keyboard_monitoring_trusted,
)
from macro_recorder.storage.service import StorageService
from macro_recorder.ui.dashboard import MacroDashboard


def run_app() -> None:
    root = tk.Tk()
    queue = queue_module.Queue()
    recording_backend = PynputRecordingBackend(queue)
    keyboard_controller = keyboard.Controller()
    playback_backend = PynputPlaybackBackend(keyboard_controller=keyboard_controller)

    permissions_ok = keyboard_monitoring_trusted()
    controller = AppController(
        recording_backend=recording_backend,
        playback_backend=playback_backend,
        storage=StorageService(),
        event_queue=queue,
        permissions_ok=permissions_ok,
    )
    shortcut_monitor = KeyboardShortcutMonitor(queue, recording_backend)
    if permissions_ok:
        shortcut_monitor.start()
    else:
        controller.set_backend_error("Global shortcuts unavailable: macOS trust permission not granted.")

    MacroDashboard(root, controller, permissions_ok)
    root.protocol("WM_DELETE_WINDOW", lambda: (shortcut_monitor.stop(), controller.emergency_stop(), root.destroy()))
    root.mainloop()
