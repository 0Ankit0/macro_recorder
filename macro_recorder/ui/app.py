from __future__ import annotations

import tkinter as tk

from macro_recorder.app.controller import AppController
from macro_recorder.input_backends.pynput_backend import (
    PynputPlaybackBackend,
    PynputRecordingBackend,
    keyboard_monitoring_trusted,
)
from macro_recorder.storage.service import StorageService
from macro_recorder.ui.dashboard import MacroDashboard


def run_app() -> None:
    root = tk.Tk()
    import queue as queue_module

    queue = queue_module.Queue()
    controller = AppController(
        recording_backend=PynputRecordingBackend(queue),
        playback_backend=PynputPlaybackBackend(),
        storage=StorageService(),
        event_queue=queue,
    )
    permissions_ok = keyboard_monitoring_trusted()
    MacroDashboard(root, controller, permissions_ok)
    root.protocol("WM_DELETE_WINDOW", lambda: (controller.emergency_stop(), root.destroy()))
    root.mainloop()
